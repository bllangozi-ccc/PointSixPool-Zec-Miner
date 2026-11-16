import sys,unittest,tempfile,types,json,os,stat
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import linux_start as m
class LinuxStart(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.patches=[patch.object(m,'CONFIG',self.home/'config/config.json'),patch.object(m.Path,'home',return_value=self.home),patch.object(m.miner,'options',side_effect=lambda v:v),patch.object(m.miner,'verify'),patch.object(m.miner,'start'),patch.object(m.miner,'stop'),patch.object(m,'systemctl'),patch.object(m,'report_failure',return_value={'delivered':True,'receipt':'invented'})]
  for p in self.patches:p.start()
  self.v={'kind':'wallet','identity':'public-test-fixture','worker':'Test','threads':1,'hours':24};m.save_config(self.v)
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def test_saved_setup_private_permissions(self):self.assertEqual(m.load_config(),self.v);self.assertEqual(m.CONFIG.stat().st_mode&511,0o600)
 def test_world_readable_config_refused(self):
  m.CONFIG.chmod(0o644)
  with self.assertRaises(ValueError):m.load_config()
 def test_symlink_config_refused(self):
  other=self.home/'other';m.CONFIG.rename(other);m.CONFIG.symlink_to(other)
  with self.assertRaises(ValueError):m.load_config()
 def test_service_no_uncertain_restart(self):
  with patch.object(m.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='yes\n')):m.install_startup()
  s=(self.home/'.config/systemd/user'/m.UNIT).read_text();self.assertIn('Restart=on-success',s);self.assertNotIn('Restart=always',s);self.assertIn('KillMode=control-group',s);self.assertIn('NoNewPrivileges=true',s)
 def test_uncertain_session_remains_held(self):
  with patch.object(m.miner,'RUNNER',types.SimpleNamespace(is_alive=lambda:False)),patch.dict(m.miner.STATE,{'state':'A submitted share has an uncertain acknowledgement.'}),patch.object(m.signal,'signal'):self.assertEqual(m.run(),2)
 def test_completed_bounded_session_may_continue(self):
  with patch.object(m.miner,'RUNNER',types.SimpleNamespace(is_alive=lambda:False)),patch.dict(m.miner.STATE,{'state':'Selected run time completed.'}),patch.object(m.signal,'signal'):self.assertEqual(m.run(),0)
 def test_requested_sigterm_is_clean_stop(self):
  handlers={}
  runner=types.SimpleNamespace(is_alive=lambda:False)
  def start(value):handlers[m.signal.SIGTERM](m.signal.SIGTERM,None)
  with patch.object(m.miner,'RUNNER',runner),patch.dict(m.miner.STATE,{'state':'Stopped by user.'}),patch.object(m.signal,'signal',side_effect=lambda sig,handler:handlers.update({sig:handler})),patch.object(m.miner,'start',side_effect=start):self.assertEqual(m.run(),0)
if __name__=='__main__':unittest.main()
