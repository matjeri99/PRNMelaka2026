import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sync_bernama import extract

class BernamaTests(unittest.TestCase):
    def test_known_seats(self):
        sample="<section>N.01 BN KUALA LINGGI N.19 PH KESIDANG N.24 PN BEMBAN N.08 — MACHAP JAYA</section>"
        x=extract(sample)
        self.assertEqual(set(x),{"N01","N19","N24"})
        self.assertEqual(x["N19"]["party"],"PH")
    def test_reject_mismatch(self):
        self.assertEqual(extract("N.01 PN KUALA LINGGI N.02 PH KUALA LINGGI"),{})
    def test_ignore_script(self):
        self.assertEqual(extract("<script>N.01 BN KUALA LINGGI</script>"),{})
    def test_no_votes_invented(self):
        self.assertIsNone(extract("N.01 BN KUALA LINGGI")["N01"]["votes"])
if __name__=="__main__":unittest.main()
