"""Root integration uses only a temporary filesystem and mocked service/account commands."""
import sys,os,unittest,tempfile,tarfile,io,types,importlib.util,pathlib,json,base64,shutil,subprocess
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
VALUE={'schema':1,'coin':'ZEC','mode':'MICRO','kind':'wallet','identity':'t1VL5XNfTPehmSxrszsSJC1hJUrYGUHbAFg','worker':'Installer-Test','region':'EU'}
@unittest.skipUnless(os.geteuid()==0,'Temporary-root installer integration; run with sudo, never uses host service commands')
class Installation(unittest.TestCase):
 def run_install(self,fail=False,collision=False):
  with tempfile.TemporaryDirectory()as td:
   top=pathlib.Path(td);spec=importlib.util.spec_from_file_location('test_installer',ROOT/'installer/install_point6miner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   def mapped(value):
    v=str(value)
    if v.startswith(('/etc/','/run/','/proc/','/start-mining','/stop-mining')):return top/v.lstrip('/')
    return pathlib.Path(value)
   (top/'proc').mkdir();(top/'proc/meminfo').write_text('MemAvailable: 8388608 kB\n');(top/'proc/cpuinfo').write_text('flags: avx2\n');(top/'run/systemd/system').mkdir(parents=True);(top/'run/lock').mkdir();(top/'etc/systemd/system').mkdir(parents=True);m.BASE=top/'opt/pointsixpool-miner';m.pathlib=types.SimpleNamespace(Path=mapped,PurePosixPath=pathlib.PurePosixPath)
   archive=top/'package.tar.gz'
   with tarfile.open(archive,'w:gz')as t:
    info=tarfile.TarInfo('miner/Start-Server');info.size=20;info.mode=0o755;t.addfile(info,io.BytesIO(b'#!/bin/sh\nexit 0    \n'))
   calls=[]
   def run(args):
    calls.append(args)
    if fail and args==['systemctl','daemon-reload']:raise RuntimeError('fixture reload failure')
    return subprocess.CompletedProcess(args,0)
   m.run=run;m.fetch=lambda url,target,pin:shutil.copy2(archive,target)
   account=types.SimpleNamespace(pw_dir=m.HOME_DIR,pw_uid=12345,pw_gid=12345)
   if collision:(top/'start-mining').write_text('unrelated original')
   with patch.object(m.os,'sched_getaffinity',return_value=set(range(8))),patch.object(m.pwd,'getpwnam',return_value=account),patch.object(m.shutil,'which',return_value='/fixture/tool'),patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1)),patch.object(sys,'argv',['installer',base64.urlsafe_b64encode(json.dumps(VALUE).encode()).decode()]):
    if fail or collision:
     with self.assertRaises((ValueError,RuntimeError)):m.main()
    else:m.main()
   self.assertFalse(any(len(c)>1 and c[0]=='systemctl'and c[1]in('start','enable','restart')for c in calls))
   if collision:self.assertEqual((top/'start-mining').read_text(),'unrelated original');return
   if fail:self.assertFalse((top/'start-mining').exists());self.assertFalse((top/'etc/systemd/system/pointsixpool-miner.service').exists());return
   config=top/'etc/pointsixpool-miner/config.json';self.assertEqual(config.stat().st_mode&0o777,0o640);self.assertEqual(config.stat().st_uid,0);self.assertEqual(json.loads(config.read_text())['threads'],2)
   unit=(top/'etc/systemd/system/pointsixpool-miner.service').read_text();self.assertIn('CPUQuota=200%',unit);self.assertIn('User=pointsix-miner',unit);self.assertIn('Restart=on-success',unit);self.assertNotIn('Restart=always',unit);self.assertIn('systemctl start pointsixpool-miner.service',(top/'start-mining').read_text())
 def test_install_does_not_start_mining(self):self.run_install()
 def test_failed_install_rolls_back_controls(self):self.run_install(fail=True)
 def test_existing_unrelated_shortcut_preserved(self):self.run_install(collision=True)
if __name__=='__main__':unittest.main()
