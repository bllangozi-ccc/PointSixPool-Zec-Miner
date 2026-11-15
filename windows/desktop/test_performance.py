import unittest
from performance_policy import recommend_threads,check_memory,required_memory_kib
class Performance(unittest.TestCase):
 def test_small_host(self):self.assertEqual(recommend_threads(2,8*1024**2,False),1)
 def test_normal_desktop(self):self.assertEqual(recommend_threads(8,8*1024**2,False),2)
 def test_large_host_cap(self):self.assertEqual(recommend_threads(128,128*1024**2,False),4)
 def test_battery(self):self.assertEqual(recommend_threads(16,16*1024**2,True),1)
 def test_unknown_power(self):self.assertEqual(recommend_threads(16,16*1024**2,None),1)
 def test_low_memory(self):self.assertEqual(recommend_threads(16,3*1024**2,False),1)
 def test_bad_resources(self):
  for a,m in[(0,4000000),(4,-1),(True,4000000)]:
   with self.assertRaises(ValueError):recommend_threads(a,m,False)
 def test_small_machine_can_start_one_thread(self):check_memory(1200*1024,1)
 def test_speed_requires_corresponding_headroom(self):
  check_memory(1536*1024,2)
  with self.assertRaises(ValueError):check_memory(1536*1024-1,2)
 def test_not_enough_ram_even_for_lowest_speed(self):
  with self.assertRaises(ValueError):check_memory(1024*1024-1,1)
 def test_limits_retain_four_thread_ceiling(self):
  self.assertEqual(required_memory_kib(4),2560*1024)
  for value in [0,5,True]:
   with self.assertRaises(ValueError):required_memory_kib(value)
if __name__=='__main__':unittest.main()
