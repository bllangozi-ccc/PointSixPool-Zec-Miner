import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'installer'))
from server_setup_policy import parse_options,select_threads
M=1024**2
class Policy(unittest.TestCase):
 def test_default_and_profiles(self):
  self.assertEqual(parse_options({}),{'server_use':'shared','cpu_threads':'auto','available_ram_gb':''})
  self.assertEqual(select_threads({},4,8*M),1)
  self.assertEqual(select_threads({'server_use':'mining'},4,8*M),3)
 def test_engine_cap(self):self.assertEqual(select_threads({'server_use':'mining'},128,128*M),4)
 def test_user_ram_only_lowers_budget(self):
  self.assertEqual(select_threads({'server_use':'mining','available_ram_gb':'1.5'},128,128*M),1)
  with self.assertRaises(ValueError):select_threads({'available_ram_gb':'999'},16,2*M)
 def test_manual_and_capacity(self):
  self.assertEqual(select_threads({'cpu_threads':'2'},8,8*M),2)
  with self.assertRaises(ValueError):select_threads({'cpu_threads':'4'},2,8*M)
  with self.assertRaises(ValueError):select_threads({'server_use':'mining','cpu_threads':'2','available_ram_gb':'1.5'},16,16*M)
 def test_invalid_values(self):
  for value in [{'server_use':'fake'},{'cpu_threads':'100'},{'available_ram_gb':'NaN'},{'available_ram_gb':'-2'},{'available_ram_gb':True},{'extra':1}]:
   with self.subTest(value=value),self.assertRaises(ValueError):parse_options(value)
 def test_unknown_resources(self):
  for cpu,ram in [(0,8*M),(True,8*M),(4,-1),(4,True)]:
   with self.subTest(cpu=cpu,ram=ram),self.assertRaises(ValueError):select_threads({},cpu,ram)
if __name__=='__main__':unittest.main()
