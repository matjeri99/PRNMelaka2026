#!/usr/bin/env python3
"""Best-effort MyUndi public seat table reader.

Never replace a supplied 19:59 snapshot with stale, zero or unparseable values.
A later, complete candidate tally can refresh one constituency only if its
leading count is at least as high as the existing reported leading count.
Status LEPAS is calculated conservatively with registered electorate as the
maximum number of possible votes (not the historic snapshot's turnout model).
"""
from html.parser import HTMLParser
import datetime as dt
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"data/myundi.json"
SEED=json.loads((ROOT/"data/calon_2026.json").read_text("utf-8"))
VTO=json.loads((ROOT/"data/vto.json").read_text("utf-8"))
URL="https://www.myundi.com.my/dotadmin/kerusi"
MYT=dt.timezone(dt.timedelta(hours=8))
MAP={
    "BARISAN NASIONAL":"BN","PAKATAN HARAPAN":"PH",
    "PERIKATAN NASIONAL":"PN","PARTI BERSAMA MALAYSIA":"BERSAMA",
    "PARTI PRIBUMI BERSATU MALAYSIA":"BERSATU",
    "PARTI BUMIPUTERA PERKASA MALAYSIA":"PUTRA",
    "BEBAS":"BEBAS"
}
PARTY_RE="|".join(sorted((re.escape(p) for p in MAP),key=len,reverse=True))
SEAT_PATTERN=re.compile(r"\bN\s*0?([1-9]|1\d|2[0-8])\s*[·\-\s]+\s*MELAKA\b",re.I)
ENTRY_PATTERN=re.compile(
    r"\b("+PARTY_RE+r")\b\s+(.{2,110}?)\s+(\d[\d,]*)\s+(?:TIDAK\s+RASMI|RASMI)\b",re.I)

class Visible(HTMLParser):
    def __init__(self):
        super().__init__();self.text=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):self.hidden=max(0,self.hidden-1)
    def handle_data(self,content):
        if not self.hidden and content.strip():self.text.append(content.strip())

def text_content(page):
    parser=Visible();parser.feed(page)
    return " ".join(" ".join(parser.text).split()).upper()

def parse_seats(page):
    text=text_content(page)
    sections=list(SEAT_PATTERN.finditer(text))
    parsed={}
    seed={s["id"]:s for s in SEED}
    for index,m in enumerate(sections):
        code="N"+m.group(1).zfill(2)
        seat=seed.get(code)
        if not seat:continue
        end=sections[index+1].start() if index+1<len(sections) else len(text)
        section=text[m.end():end]
        values=[]
        for candidate in ENTRY_PATTERN.finditer(section):
            party=MAP.get(candidate.group(1).upper())
            try:votes=int(candidate.group(3).replace(",",""))
            except ValueError:continue
            values.append((party,votes))
        expected=sorted(c["party"] for c in seat["candidates"])
        if sorted(p for p,v in values)!=expected:continue
        if len(values)!=len(seat["candidates"]):continue
        if not any(v>0 for p,v in values):continue
        values.sort(key=lambda item:item[1],reverse=True)
        if len(values)<2 or values[0][1]==values[1][1]:continue
        registered=(VTO.get("areas",{}).get(code) or {}).get("registered")
        total=sum(n for p,n in values)
        if not isinstance(registered,int) or registered<total:continue
        # Upper bound on additional votes after the latest totals: at most
        # electorate minus all votes so far. Conservative even if 100% do not vote.
        possible_remaining=max(0,registered-total)
        threshold=values[1][1]+possible_remaining+1
        parsed[code]={"party":values[0][0],"leaderVotes":values[0][1],
                      "threshold":threshold,"passed":values[0][1]>=threshold,
                      "status":"unofficial","candidateVotes":dict(values),
                      "thresholdMethod":"registered_upper_bound"}
    return parsed

def run():
    request=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (compatible; Melaka Nightboard/3.1)",
                                                 "Accept":"text/html,application/xhtml+xml"})
    with urllib.request.urlopen(request,timeout=25) as res:
        page=res.read(8_000_000).decode("utf-8","replace")
    newer=parse_seats(page)
    cache=json.loads(OUTPUT.read_text("utf-8"))
    original=cache.get("seats") or {}
    changed=0
    now=dt.datetime.now(MYT).isoformat()
    for code,seat in newer.items():
        old=original.get(code)
        if not old or seat["leaderVotes"]<old.get("leaderVotes",0):
            continue
        if (seat.get("leaderVotes")==old.get("leaderVotes")
            and seat.get("party")==old.get("party")
            and "candidateVotes" not in old):
            # Existing photographed value remains because a matching number does
            # not prove the webpage is newer than the supplied screenshot.
            continue
        if (seat.get("leaderVotes")==old.get("leaderVotes")
            and seat.get("party")==old.get("party")
            and seat.get("candidateVotes")==old.get("candidateVotes")):
            continue
        seat["observedAt"]=now
        seat["sourceType"]="myundi_public_webpage"
        original[code]=seat
        changed+=1
    if changed:
        cache["seats"]=original
        cache["counts"]={"reported":len(original),"passed":sum(v.get("passed") is True for v in original.values())}
        cache["fetchedAt"]=now
        cache["status"]="unofficial"
        OUTPUT.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"MyUndi: parsed {len(newer)} valid DUN; refreshed {changed}; retained {len(original)} screenshot/verified DUN")
    return 0

if __name__=="__main__":
    try:sys.exit(run())
    except Exception as e:
        print("MyUndi unavailable; last snapshot retained: "+str(e))
        sys.exit(0)
