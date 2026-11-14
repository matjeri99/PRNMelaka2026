#!/usr/bin/env python3
"""Best-effort reader for the PUBLIC SPR dashboard landing page.

Conservative: never guess VTO from registered electors or media quotes.
No undocumented backend or private API calls. Retains the last sourced snapshot
unless the public page displays a clearly labelled state-wide VTO and timestamp.
"""
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"data"/"vto.json"
URL="https://dashboard.spr.gov.my/"
MYT=dt.timezone(dt.timedelta(hours=8))

class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):self.skip=max(0,self.skip-1)
    def handle_data(self,s):
        if not self.skip and s.strip():self.parts.append(s.strip())
def extract_vto(page):
    parser=Visible();parser.feed(page)
    txt=" ".join(parser.parts)
    # Only accept a percentage explicitly described as state-wide turnout.
    match=re.search(r"(?:Peratus(?:an)?\s+(?:Keluar|Kehadiran)\s+Mengundi|Kadar\s+Keluar\s+Mengundi|VTO\s+Keseluruhan)\s*:?\s*(\d{1,3}(?:\.\d{1,2})?)\s*%",txt,re.I)
    if not match:return None
    percent=float(match.group(1))
    if not (0<percent<=100):return None
    # A time mark is required; scraping time is not the SPR's observation time.
    t=re.search(r"(?:Setakat|Sehingga|Data\s+sehingga|Dikemas\s+kini)\s*(?:jam|pada\s+pukul)?\s*(\d{1,2})[:.](\d{2})\s*(pagi|petang|malam|tengah\s+hari)?",txt,re.I)
    if not t:return None
    hr,minute=int(t.group(1)),int(t.group(2))
    label=(t.group(3) or "").lower()
    if label=="tengah hari":hr=12
    elif label in ("petang","malam") and hr<12:hr+=12
    if hr>23 or minute>59:return None
    when=dt.datetime(2026,11,14,hr,minute,tzinfo=MYT)
    return {"percentage":percent,"asOf":when.isoformat()}

def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (compatible; PRN-Melaka-VTO/2.1)","Accept":"text/html"})
    with urllib.request.urlopen(req,timeout=25) as res:
        page=res.read(4_000_000).decode("utf-8","replace")
    fresh=extract_vto(page)
    if not fresh:
        print("No timestamped state-wide VTO visible in public HTML. Keep sourced historical snapshot; official site may load data via JavaScript.")
        return 0
    cache=json.loads(FILE.read_text("utf-8"))
    old=cache.get("percentage")
    last=cache.get("asOf")
    if old is not None and fresh["percentage"]<float(old):
        print("VTO lower than prior snapshot; skip unverified downgrade");return 0
    if last and fresh["asOf"]<=last:
        print("No newer VTO observation");return 0
    cache.update(fresh)
    cache["source"]=URL
    cache["sourceLabel"]="Snapshot daripada halaman awam Dashboard SPR"
    cache["sourceType"]="spr_public_dashboard"
    cache["feedStatus"]="official_page_snapshot"
    cache["collectedAt"]=dt.datetime.now(MYT).isoformat()
    history=cache.setdefault("history",[])
    if not history or history[-1]["asOf"]<fresh["asOf"]:
        history.append({"asOf":fresh["asOf"],"percentage":fresh["percentage"],"votedCount":None,"source":URL})
    # The registered total differs from the denominator used in reports.
    cache["votedCount"]=None
    cache["pollingDenominator"]=None
    FILE.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("New validated state-wide VTO snapshot:",fresh)
    return 0
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as ex:
        print("VTO fetch failed; previous cited snapshot retained: "+str(ex),file=sys.stderr)
        sys.exit(1)
