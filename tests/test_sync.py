import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sync_spr import SEED,match_candidates,token_of,election_option,seat_code,vote_value

class Tests(unittest.TestCase):
    def test_token(self):
        self.assertEqual(token_of('<input name="_token" value="abc">'),"abc")
    def test_election(self):
        self.assertEqual(election_option('<option data-negeri="M" value="16">PRU DUN MELAKA KE-16</option>'),("M","16","PRU DUN MELAKA KE-16"))
    def test_all_candidates(self):
        for seat in SEED:
            raw=[{"NamaUndiCalon":c["name"],"BilUndi":10000-i*100,
                  "StatusCalon":"MNG" if i==0 else "KLH"} for i,c in enumerate(seat["candidates"])]
            mapped,reason=match_candidates(seat,raw)
            self.assertEqual(reason,"",seat["id"]+": "+reason)
            self.assertEqual(len(mapped),len(raw))
    def test_no_winner(self):
        seat=SEED[0]
        raw=[{"NamaUndiCalon":c["name"],"BilUndi":1000-i,"StatusCalon":""} for i,c in enumerate(seat["candidates"])]
        self.assertIsNone(match_candidates(seat,raw)[0])
    def test_codes(self):
        self.assertEqual(seat_code({"KodBahagianPilihanRaya":"N.1"}),"N01")
        self.assertEqual(seat_code({"AppendKod":"28"}),"N28")
    def test_votes(self):
        self.assertEqual(vote_value("12,345"),12345)
        self.assertIsNone(vote_value(None))
if __name__=="__main__":unittest.main()
