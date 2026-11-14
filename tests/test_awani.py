import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sync_awani import discover, parse_article

class AWANITests(unittest.TestCase):
    def test_official_party_totals(self):
        page = """<html><head><meta property="og:title" content="PRN Melaka: keputusan rasmi SPR"/>
        <meta property="article:published_time" content="2026-11-14T22:00:00+08:00"></head>
        <body><p>PRN Melaka 2026. Suruhanjaya Pilihan Raya (SPR) mengumumkan keputusan rasmi.</p>
        <p>BN memperoleh 15 kerusi, diikuti Pakatan Harapan (PH) dengan dua kerusi
        manakala Perikatan Nasional (PN) memenangi satu kerusi.</p></body></html>"""
        found = parse_article(page, "https://www.astroawani.com/example")
        self.assertEqual(found["parties"], {"BN":15,"PH":2,"PN":1})
        self.assertEqual(found["officialCount"],18)

    def test_unofficial_is_rejected(self):
        page = """<head><meta property="og:title" content="[TIDAK RASMI] PRN Melaka"/>
        <meta property="article:published_time" content="2026-11-14T22:00:00+08:00"></head>
        <p>PRN Melaka SPR keputusan rasmi BN memperoleh 15 kerusi, PH dengan dua kerusi
        PN memenangi satu kerusi</p>"""
        self.assertIsNone(parse_article(page, "https://www.astroawani.com/example"))

    def test_missing_count_rejected(self):
        page = """<head><meta property="article:published_time" content="2026-11-14T22:00:00+08:00"></head>
        <p>PRN Melaka SPR keputusan rasmi BN memperoleh 15 kerusi</p>"""
        self.assertIsNone(parse_article(page, "https://www.astroawani.com/example"))

    def test_discover_only_awani_article(self):
        page = '<a href="/berita-politik/prn-melaka-2026-update">Here</a><a href="https://other.com/berita-politik/melaka">Other</a>'
        self.assertEqual(discover(page), ["https://www.astroawani.com/berita-politik/prn-melaka-2026-update"])
