#!/usr/bin/env python3
"""Conservative Bernama seat-status fallback for the public Melaka 2026 dashboard.

Only reads public election coverage HTML. If markup changes or results disappear,
retain last valid snapshot. Never interpret unofficial standings as SPR results.
"""
from html.parser import HTMLParser
import datetime as dt
import html
import json
from pathlib import Path
import re
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
SEED=json.loads((ROOT/"data/calon_2026.json").read_text("utf-8"))
CACHE=ROOT/"data/bernama.json"
URL="https://election.bernama.com/prn/melaka/2026/"
MYT=dt.timezone(dt.timedelta(hours=8))
KNOWN={s["id"]:s["name"] for s in SEED}

class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__();self.out=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.out.append(data.strip())

def normal(s):
    return re.sub(r"\s+"," ",html.unescape(str(s))).strip().upper()

def extract(html_content):
    parser=TextOnly();parser.feed(html_content)
    text=normal(" ".join(parser.out))
    # Only accept entries where the expected DUN name follows its seat code.
    # We do not accept bare political-party labels elsewhere on the page.
    seats={}
    for m in re.finditer(r"\bN\s*\.?\s*0?([1-9]|1\d|2[0-8])\s+(BN|PH|PN|BERSATU|BERSAMA|BEBAS|PUTRA|[—–-])\s+",text,re.I):
        code="N"+m.group(1).zfill(2)
        party=m.group(2).upper()
        expected=normal(KNOWN.get(code,""))
        following=text[m.end():m.end()+len(expected)+28]
        if not expected or not following.startswith(expected) or party in ("—","–","-"):
            continue
        if party not in {c["party"] for c in next(s for s in SEED if s["id"]==code)["candidates"]}:
            continue
        seats[code]={"party":party,"status":"unofficial","votes":None}
    return seats

def run():
    req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (compatible; MelakaElectionTracker/3.0)",
                                             "Accept":"text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req,timeout=22) as res:
        content=res.read(4_000_000).decode("utf-8","replace")
    fresh=extract(content)
    previous=json.loads(CACHE.read_text("utf-8"))
    existing=previous.get("seats") or {}
    if len(fresh)<len(existing) or len(fresh)==0:
        print(f"Bernama page currently returned only {len(fresh)} matching seats; keeping {len(existing)} saved results.")
        return 0
    if fresh==existing:
        print(f"Bernama snapshot unchanged ({len(fresh)}/28)")
        return 0
    previous.update({"seats":fresh,"reportedCount":len(fresh),
       "retrievedAt":dt.datetime.now(MYT).isoformat(),"source":URL,
       "status":"unofficial","officialCount":0})
    CACHE.write_text(json.dumps(previous,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Bernama unofficial standings refreshed: {len(fresh)}/28")
    return 0

if __name__=="__main__":
    try:raise SystemExit(run())
    except Exception as e:
        print("Bernama backup source unavailable; retaining last valid snapshot: "+str(e))
        raise SystemExit(0)
