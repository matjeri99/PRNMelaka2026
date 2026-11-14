import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sync_vto import extract_vto

class TestVto(unittest.TestCase):
    def test_strict_snapshot(self):
        sample='<html><h2>Kehadiran Mengundi</h2><p>Peratus Keluar Mengundi: 61.25%</p><span>Setakat jam 3:30 petang</span></html>'
        self.assertEqual(extract_vto(sample),{'percentage':61.25,'asOf':'2026-11-14T15:30:00+08:00'})
    def test_no_timestamp(self):
        self.assertIsNone(extract_vto('<p>Peratus Keluar Mengundi 77.12%</p>'))
    def test_not_registered_voters_percent(self):
        self.assertIsNone(extract_vto('<h2>Jumlah Pemilih</h2><p>687,697</p><p>Senarai DUN</p>'))
    def test_not_unrelated_percentage(self):
        self.assertIsNone(extract_vto('<p>Margin ralat 5.00%</p><p>Setakat jam 4:00 petang</p>'))
    def test_script_only_injection(self):
        self.assertIsNone(extract_vto('<script>Peratus Keluar Mengundi 78.00%; Setakat jam 3:20 petang</script>'))
if __name__=="__main__":unittest.main()
