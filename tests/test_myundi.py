import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sync_myundi import parse_seats, SEED

class MyUndiTests(unittest.TestCase):
    def fixture(self,n="1,200",other="800"):
        seat=next(s for s in SEED if s["id"]=="N10")
        labels={"BN":"Barisan Nasional","PH":"Pakatan Harapan"}
        return ('<html><h1>N10 · Melaka</h1><h2>Asahan</h2><p>Majoriti: 400</p>'+
                ''.join('<p>'+labels[c["party"]]+'</p><p>'+c["name"]+'</p><p>'+(
                  n if c["party"]=="BN" else other)+'</p><small>Tidak Rasmi</small>' for c in seat["candidates"])+
                '<h3>Jumlah undi</h3></html>')
    def test_parses_numbers(self):
        out=parse_seats(self.fixture(n="12,000",other="8,000"))
        self.assertIn("N10",out)
        self.assertEqual(out["N10"]["party"],"BN")
        self.assertEqual(out["N10"]["leaderVotes"],12000)
        self.assertIsInstance(out["N10"]["threshold"],int)
    def test_reject_zero_totals(self):
        self.assertEqual(parse_seats(self.fixture(n="0",other="0")),{})
    def test_reject_incomplete_seat(self):
        self.assertEqual(parse_seats('<h1>N10 · Melaka</h1><p>Barisan Nasional Along 20,000 Tidak Rasmi</p>'),{})
    def test_skip_script(self):
        self.assertEqual(parse_seats('<script>N10 · Melaka Barisan Nasional Along 50000 Tidak Rasmi</script>'),{})
if __name__=="__main__":unittest.main()
