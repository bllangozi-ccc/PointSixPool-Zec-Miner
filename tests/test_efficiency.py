import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
import unittest, tempfile
from pathlib import Path
from miner_efficiency import Measurement,thermal_action,measured_preset,linux_sample,hardware
class Efficiency(unittest.TestCase):
 def reading(self,v=0):return {'temperature_c':50,'energy_domains':{'package':(v,10000000000)},'power_scope':'CPU package (RAPL)'}
 def test_missing_power_is_unknown(self):
  m=Measurement();r={'temperature_c':None,'energy_domains':{},'power_scope':None};m.update(0,r,0);self.assertIsNone(m.update(60,r,2)['average_watts'])
 def test_actual_energy_and_work(self):
  m=Measurement()
  for i in range(31):r=m.update(i*2,self.reading(i*20000000),i, i*8.)
  self.assertEqual(r['average_watts'],10);self.assertAlmostEqual(r['accepted_work_per_joule'],.4)
 def test_wrap(self):
  m=Measurement();m.update(0,self.reading(9990000000),0,0);m.update(2,self.reading(10000000),1,8);self.assertEqual(m.joules,20)
 def test_gap_invalidates(self):
  m=Measurement();m.update(0,self.reading(),0);self.assertFalse(m.update(20,self.reading(10000000),1)['measurement_complete'])
 def test_unknown_work_not_ranked(self):
  self.assertIsNone(measured_preset([{'threads':4,'accepted_shares':40,'measurement_complete':True,'elapsed_seconds':3600}]))
 def test_preset_uses_work_per_joule(self):
  base={'accepted_shares':40,'measurement_complete':True,'elapsed_seconds':3600}
  self.assertEqual(measured_preset([{**base,'threads':2,'accepted_work_per_joule':3},{**base,'threads':4,'accepted_work_per_joule':2}]),2)
 def test_thermal_hysteresis(self):
  self.assertEqual(thermal_action(None),'unavailable');self.assertEqual(thermal_action(76),'reduce');self.assertEqual(thermal_action(70,True),'reduce');self.assertEqual(thermal_action(64,True),'normal');self.assertEqual(thermal_action(85),'stop')
 def test_cpu_sensor_allowlist(self):
  with tempfile.TemporaryDirectory() as p:
   d=Path(p)/'class/hwmon/hwmon0';d.mkdir(parents=True);(d/'name').write_text('nvme');(d/'temp1_input').write_text('99000');self.assertIsNone(linux_sample(Path(p))['temperature_c']);(d/'name').write_text('coretemp');self.assertEqual(linux_sample(Path(p))['temperature_c'],99)
 def test_hardware_has_no_gpu_claim(self):self.assertFalse(hardware()['gpu_mining_supported'])
 def test_backward_counter_rejected(self):
  m=Measurement();m.update(1,self.reading(),2)
  with self.assertRaises(ValueError):m.update(2,self.reading(1),1)
if __name__=='__main__':unittest.main()
