import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import point6miner_ui as ui
class Regions(unittest.TestCase):
 def test_exact_micro_endpoints(self):
  self.assertEqual(ui.REGION_POOLS,{'EU':'stratum+tcp://zec4.pointsixpool.com:3034','USA':'stratum+tcp://usa.zec4.pointsixpool.com:3034','ASIA':'stratum+tcp://asia.zec4.pointsixpool.com:3034'})
 def test_region_drives_actual_command(self):
  for region,url in ui.REGION_POOLS.items():
   v={'cpus':[0],'kind':'wallet','identity':'public-wallet','worker':'PC','threads':1,'region':region}
   args=ui.command(v,60);self.assertEqual(args[args.index('--pool')+1],url)
 def test_unknown_region_refused(self):
  with self.assertRaises(ValueError):ui.options({'identity':'x','kind':'wallet','worker':'PC','threads':1,'hours':1,'region':'USA;evil'})
 def test_default_is_original_url(self):
  args=ui.command({'cpus':[0],'kind':'wallet','identity':'public-wallet','worker':'PC','threads':1},60);self.assertIn(ui.REGION_POOLS['EU'],args)
if __name__=='__main__':unittest.main()
