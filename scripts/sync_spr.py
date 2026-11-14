#!/usr/bin/env python3
"""Unofficial MySPR Semak website JSON collector; rejects uncertain results."""
import datetime as dt
import difflib
import html
from html.parser import HTMLParser
import http.cookiejar
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/results.json"
SEED = json.loads((ROOT / "data/calon_2026.json").read_text("utf-8"))
BASE = "https://mysprsemak.spr.gov.my"
SOURCE = BASE + "/semakan/keputusan/pru-dun"
MYT = dt.timezone(dt.timedelta(hours=8))

class Options(HTMLParser):
    def __init__(self):
        super().__init__()
        self.options = []
        self.current = None
    def handle_starttag(self, tag, attrs):
        if tag == "option":
            self.current = [dict(attrs), ""]
    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data
    def handle_endtag(self, tag):
        if tag == "option" and self.current is not None:
            self.options.append(tuple(self.current))
            self.current = None

class Fetcher:
    def __init__(self):
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.headers = {"User-Agent":"PRN-Melaka-Dashboard/2.0",
                        "Accept":"application/json, text/javascript, */*; q=0.01",
                        "X-Requested-With":"XMLHttpRequest"}
    def get(self):
        with self.opener.open(urllib.request.Request(SOURCE,headers=self.headers),timeout=25) as r:
            return r.read().decode("utf-8","replace")
    def post(self,path,form):
        headers=dict(self.headers,Referer=SOURCE,
                    **{"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"})
        request=urllib.request.Request(BASE+path,
                   data=urllib.parse.urlencode(form).encode(),headers=headers)
        with self.opener.open(request,timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))

def token_of(page):
    m=(re.search(r'name=["\']_token["\'][^>]*value=["\']([^"\']+)',page,re.I)
       or re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']_token["\']',page,re.I)
       or re.search(r'"_token"\s*:\s*"([^"]+)"',page))
    if not m: raise ValueError("MySPR CSRF token missing")
    return m.group(1)

def election_option(page):
    p=Options();p.feed(page)
    for attrs,label in p.options:
        label=" ".join(html.unescape(label).upper().split())
        if "MELAKA" in label and (re.search(r"KE[ -]?16\b",label) or "2026" in label):
            if attrs.get("data-negeri") and attrs.get("value"):
                return attrs["data-negeri"],attrs["value"],label
    return None

def clean_name(name):
    s=unicodedata.normalize("NFKD",name or "").encode("ascii","ignore").decode().upper()
    s=re.sub(r"\b(?:DATUK|DATO|DATIN|SERI|SRI|DR|PROF|IR|HAJI|HJ|HAJAH|HJH|TN|PUAN|ENCIK|MEJAR|KAPTEN|B|BIN|BINTI|A/L|A/P)\b"," ",s)
    return " ".join(re.sub(r"[^A-Z0-9]+"," ",s).split())

def vote_value(value):
    if isinstance(value,bool) or value is None:return None
    v=str(value).replace(",","").strip()
    return int(v) if v.isdigit() else None

def extract_candidates(response, expected):
    """Find a candidate-vote array at any reasonable nesting, not only [0].penamaan."""
    found = []
    def visit(node, depth=0):
        if depth > 7:
            return
        if isinstance(node, list):
            if node and all(isinstance(x, dict) for x in node):
                if all("NamaUndiCalon" in x and "BilUndi" in x for x in node):
                    found.append(node)
            for child in node:
                visit(child, depth+1)
        elif isinstance(node, dict):
            for key, value in node.items():
                if key not in ("html", "script", "view", "markup"):
                    visit(value, depth+1)
    visit(response)
    if not found:
        return [], "SPR has not supplied candidate-vote rows"
    for rows in found:
        if len(rows)==expected:
            return rows, ""
    return max(found, key=len), "Candidate count differs from nomination list"

def match_candidates(seed,raw,require_winner=True):
    if len(raw)!=len(seed["candidates"]):return None,"candidate count mismatch"
    used=set();votes={};winners=[]
    for i,c in enumerate(seed["candidates"]):
        scores=sorted([(difflib.SequenceMatcher(None,clean_name(c["name"]),
                       clean_name(r.get("NamaUndiCalon"))).ratio(),j)
                       for j,r in enumerate(raw) if j not in used],reverse=True)
        if not scores or scores[0][0]<.78 or (len(scores)>1 and scores[0][0]-scores[1][0]<.13):
            return None,"uncertain candidate name: "+c["name"]
        j=scores[0][1];v=vote_value(raw[j].get("BilUndi"))
        if v is None:return None,"missing candidate votes"
        used.add(j);votes[str(i)]=v
        if str(raw[j].get("StatusCalon") or "").upper()=="MNG":winners.append(i)
    if sum(votes.values())<=0:
        return None,"no votes yet"
    top=max(votes.values())
    if len(winners)==1 and votes[str(winners[0])]==top and list(votes.values()).count(top)==1:
        return votes,"official"
    if require_winner:
        return None,"winner not confirmed"
    # Numeric vote tallies are provisional until the SPR winner marker is present.
    if len(winners)>1 or (winners and votes[str(winners[0])]!=top):
        return None,"conflicting winner marker"
    return votes,"preliminary"

def seat_code(row):
    v=str(row.get("KodBahagianPilihanRaya") or row.get("AppendKod") or "").upper()
    m=re.search(r"(\d{1,2})(?!\d)",v)
    return "N"+m.group(1).zfill(2) if m else None

def need_refresh_now(now):
    if os.environ.get("FORCE_SPR_SYNC")=="1":return True
    return ((now.date()==dt.date(2026,11,14) and now.hour>=20)
            or (now.date()==dt.date(2026,11,15) and now.hour<2))

def run():
    now=dt.datetime.now(MYT)
    try:old=json.loads(OUT.read_text("utf-8"))
    except (ValueError,OSError):old={}
    official=dict(old.get("records") or {})
    if len(official)>=28 or not need_refresh_now(now):
        print("No sync needed");return 0
    fetch=Fetcher();page=fetch.get();token=token_of(page)
    election=election_option(page)
    if not election:
        print("Melaka KE-16 not listed; preserving cache");return 0
    state,eid,title=election
    data=fetch.post("/semakan/keputusan/senaraiDunPruDun",
                    {"_token":token,"PilihanrayaId":eid,"RefNegeriId":state})
    duns=data.get("dun") if isinstance(data,dict) else None
    if not isinstance(duns,list) or len(duns)!=28:
        raise ValueError("Expected exactly 28 SPR DUN records")
    lookup={s["id"]:s for s in SEED};missing=[];changed=0
    preliminary={}
    for row in duns:
        code=seat_code(row)
        if code not in lookup:
            missing.append(str(code or row));continue
        try:
            resp=fetch.post("/semakan/keputusan/keputusanPruDun",
                {"_token":token,"kategori":"PRU_DUN","PilihanrayaId":eid,
                 "RefNegeriId":state,"kodbahagian":row.get("AppendKod")})
            raw,explanation=extract_candidates(resp,len(lookup[code]["candidates"]))
            if not raw:
                missing.append(code+": "+explanation);continue
            matched,level=match_candidates(lookup[code],raw,require_winner=False)
            if matched is None:
                missing.append(code+": "+level);continue
            if level=="official":
                if official.get(code,{}).get("votes")!=matched:
                    official[code]={"status":"official","votes":matched,"turnout":None,
                        "source":SOURCE,"notes":"Verified MySPR Semak website JSON",
                        "savedAt":now.isoformat(),"sourceType":"spr_auto"}
                    changed+=1
            elif code not in official:
                preliminary[code]={"status":"unofficial","votes":matched,"turnout":None,
                    "source":SOURCE,"notes":"Undi sementara yang belum diumumkan rasmi SPR",
                    "savedAt":now.isoformat(),"sourceType":"spr_auto"}
        except Exception as e:missing.append(code+": "+str(e)[:100])
        time.sleep(.25)
    payload={"schema":"prn-melaka-2026-spr-v2","election":title,"source":SOURCE,
             "upstream":"SPR website JSON (unofficial integration)",
             "syncedAt":now.isoformat(),"officialCount":len(official),
             "unavailableCount":28-len(official),"records":official,
             "preliminary":preliminary,"preliminaryCount":len(preliminary),
             "warnings":missing[:30]}
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Verified {len(official)}/28; provisional {len(preliminary)}; changed {changed}; unavailable {len(missing)}")
    return 0

if __name__=="__main__":
    try:sys.exit(run())
    except Exception as e:
        print("SPR sync failed; retaining last good cache: "+str(e),file=sys.stderr)
        sys.exit(1)
