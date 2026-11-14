#!/usr/bin/env python3
"""Best-effort AWANI news reader for official SPR party seat totals.
No individual DUN winners or candidate votes are inferred from news totals.
"""
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "awani.json"
BASE = "https://www.astroawani.com"
TOPIC = BASE + "/topic/prn-melaka"
INITIAL = BASE + "/berita-politik/terkini-prn-melaka-bn-raih-15-kerusi-lepasi-majoriti-50-peratus-bentuk-kerajaan-negeri-spr"
MYT = timezone(timedelta(hours=8))
WORDS = dict(satu=1, dua=2, tiga=3, empat=4, lima=5, enam=6,
             tujuh=7, lapan=8, sembilan=9, sepuluh=10)
NUM = r"(?:\d{1,2}|satu|dua|tiga|empat|lima|enam|tujuh|lapan|sembilan|sepuluh)"

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words, self.links, self.meta = [], [], {}
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript"): self.hidden += 1
        if tag == "a" and a.get("href"): self.links.append(a["href"])
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key and a.get("content"): self.meta[key.lower()] = a["content"]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"): self.hidden = max(0, self.hidden-1)

    def handle_data(self, value):
        if not self.hidden and value.strip(): self.words.append(value.strip())

def reader(html):
    r = Reader(); r.feed(html); return r

def fetch(url):
    req = Request(url, headers={"User-Agent":"Mozilla/5.0", "Accept":"text/html,application/xhtml+xml"})
    with urlopen(req, timeout=12) as response:
        return response.read(3000000).decode("utf-8", "replace")

def discover(html):
    links = []
    for href in reader(html).links:
        url = urljoin(BASE, href.split("#")[0].split("?")[0])
        path = urlparse(url).path.lower()
        if url.startswith(BASE+"/") and "/berita-" in path and "melaka" in path and url not in links:
            links.append(url)
    return links[:35]

def party_count(text, names):
    for name in names:
        p = r"\b" + name + r"\s+(?:telah\s+)?(?:memperoleh|memenangi|meraih|menang|dengan)\s+(" + NUM + r")\s+(?:daripada\s+28\s+)?kerusi"
        m = re.search(p, text, re.I)
        if m:
            token = m.group(1).lower()
            return int(token) if token.isdigit() else WORDS.get(token)
    return None

def published(r, text):
    for k in ("article:published_time", "datepublished"):
        value = r.meta.get(k)
        if value:
            try:
                t = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return (t if t.tzinfo else t.replace(tzinfo=MYT)).astimezone(MYT).isoformat()
            except ValueError: pass
    m = re.search(r"14\s*/\s*11\s*/\s*2026\s*\|\s*(\d{2}):(\d{2})\s*MYT", text, re.I)
    return "2026-11-14T"+m.group(1)+":"+m.group(2)+":00+08:00" if m else None

def parse_article(html, url):
    r = reader(html)
    text = " ".join(" ".join(r.words).split())
    headline = r.meta.get("og:title", " ".join(r.words[:8])).lower()
    if "tidak rasmi" in headline or "prn melaka" not in text.lower() or "spr" not in text.lower():
        return None
    if not re.search(r"keputusan rasmi|pengumuman rasmi|suruhanjaya pilihan raya\s*\(SPR\)\s+mengesahkan", text, re.I):
        return None
    ts = published(r, text)
    if not ts or not ts.startswith("2026-11-14T"): return None
    parties = {
        "BN":party_count(text,[r"Barisan Nasional\s*\(BN\)",r"Barisan Nasional",r"BN"]),
        "PH":party_count(text,[r"Pakatan Harapan\s*\(PH\)",r"Pakatan Harapan",r"PH"]),
        "PN":party_count(text,[r"Perikatan Nasional\s*\(PN\)",r"Perikatan Nasional",r"PN"])
    }
    if any(v is None or v < 0 for v in parties.values()): return None
    count = sum(parties.values())
    if not 1 <= count <= 28: return None
    return dict(parties=parties, officialCount=count, publishedAt=ts, sourceUrl=url,
                sourceName="Astro AWANI (pengumuman SPR)", status="official_reported")

def update():
    cache = json.loads(DATA.read_text("utf-8"))
    urls = [INITIAL]
    try: urls = discover(fetch(TOPIC)) + urls
    except Exception as e: print("Topic discovery unavailable:", e)
    results = []
    for url in dict.fromkeys(urls):
        try:
            candidate = parse_article(fetch(url), url)
            if candidate: results.append(candidate)
        except Exception as e: print("Article unavailable:", url, str(e)[:80])
    prev = cache.get("parties", {})
    valid = [x for x in results if x["officialCount"] >= cache.get("officialCount",0)
             and all(x["parties"][p] >= prev.get(p,0) for p in ("BN","PH","PN"))]
    if not valid:
        print("No newer complete official SPR tally available; existing cache retained")
        return
    latest = max(valid, key=lambda x: (x["officialCount"],x["publishedAt"]))
    if latest["parties"] == cache.get("parties"):
        print("AWANI: No new official seat totals")
        return
    cache.update(latest)
    cache.pop("announcedAsOf", None)  # new article may cite a different as-of
    cache["updatedAt"] = datetime.now(MYT).isoformat()
    DATA.write_text(json.dumps(cache,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("AWANI updated:",latest["officialCount"],latest["parties"])

if __name__ == "__main__":
    try: update()
    except Exception as e: print("AWANI collector failed, retaining last cache:",e)
