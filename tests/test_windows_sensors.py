import sys,unittest,os,subprocess,ctypes
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
from windows_sensors import parse_sensors,constrain_tree,ProcessEntry
from miner_efficiency import Measurement
class Sensors(unittest.TestCase):
 def test_cpu_only(self):
  r=parse_sensors([{'Identifier':'/nvidiagpu/0/temperature/0','SensorType':'Temperature','Name':'GPU Core','Value':99},{'Identifier':'/intelcpu/0/temperature/0','SensorType':'Temperature','Name':'CPU Package','Value':72}]);self.assertEqual(r['temperature_c'],72);self.assertIsNone(r['watts'])
 def test_package_power_not_core_sum(self):
  r=parse_sensors([{'Identifier':'/intelcpu/0/power/0','SensorType':'Power','Name':'CPU Package','Value':25},{'Identifier':'/intelcpu/0/power/1','SensorType':'Power','Name':'CPU Cores','Value':18}]);self.assertEqual(r['watts'],25)
 def test_nonfinite_excluded(self):self.assertIsNone(parse_sensors([{'Identifier':'/intelcpu/0/temperature/0','SensorType':'Temperature','Value':float('nan')}])['temperature_c'])
 def test_sampled_power_integration(self):
  m=Measurement();r={'temperature_c':50,'watts':20.,'energy_domains':{},'power_scope':'CPU package (sampled sensor power)'}
  for i in range(31):v=m.update(i*2,r,i,i*10.)
  self.assertEqual(v['average_watts'],20);self.assertEqual(v['accepted_work_per_joule'],.25)
 def test_missing_sensor_is_unknown(self):self.assertIsNone(parse_sensors([])['temperature_c'])
 @unittest.skipUnless(os.name=='nt','Win32 non-mining process integration')
 def test_native_affinity_abi(self):
  from windows_resources import available_cpus,kernel
  self.assertEqual(ctypes.sizeof(ProcessEntry),568)
  p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(15)'])
  try:
   cpu=min(available_cpus());constrain_tree(p.pid,[cpu]);k=kernel();mask=ctypes.c_size_t();system=ctypes.c_size_t();self.assertTrue(k.GetProcessAffinityMask(p._handle,ctypes.byref(mask),ctypes.byref(system)));self.assertEqual(mask.value,1<<cpu)
  finally:p.terminate();p.wait(timeout=5)
if __name__=='__main__':unittest.main()
