import sys,unittest,types
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
import windows_resources as r
class Memory(unittest.TestCase):
 def kernel(self,total,available):
  def sample(p):
   p._obj.ullTotalPhys=total;p._obj.ullAvailPhys=available;return 1
  return types.SimpleNamespace(GlobalMemoryStatusEx=sample)
 def test_total_is_not_available_and_units_are_kib(self):
  with patch.object(r,'kernel',return_value=self.kernel(16*1024**3,1536*1024**2)):
   self.assertEqual(r.memory_status_kib(),{'total':16*1024**2,'available':1536*1024})
   self.assertEqual(r.free_memory_kib(),1536*1024)
 def test_invalid_native_readings_fail_closed(self):
  for total,available in [(0,0),(1024,2048)]:
   with patch.object(r,'kernel',return_value=self.kernel(total,available)):
    with self.assertRaises(OSError):r.free_memory_kib()
if __name__=='__main__':unittest.main()
