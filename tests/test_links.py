import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from miner_links import portal_url
class Links(unittest.TestCase):
 def test_wallet_group(self):self.assertEqual(portal_url('wallet','t1VL5XNfTPehmSxrszsSJC1hJUrYGUHbAFg'),'https://pointsixpool.com/status#mining=workers&miner=f298614142b85cae5800913fbf1efc8b25851596d332bc4d2563977f63390cab')
 def test_registered_not_in_url(self):self.assertEqual(portal_url('registered','private-account'),'https://pointsixpool.com/dashboard#mining')
 def test_missing_identity(self):self.assertEqual(portal_url('wallet',''),'https://pointsixpool.com/status')
 def test_no_url_injection(self):self.assertEqual(portal_url('wallet','https://attacker.invalid/'),'https://pointsixpool.com/status')
if __name__=='__main__':unittest.main()
