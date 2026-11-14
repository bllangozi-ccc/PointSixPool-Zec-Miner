import unittest,sys,tarfile,tempfile,io,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from setup_config import validate,load,options
V={'schema':1,'coin':'ZEC','mode':'MICRO','kind':'wallet','identity':'t1VL5XNfTPehmSxrszsSJC1hJUrYGUHbAFg','worker':'Home-PC','region':'EU'}
class Setup(unittest.TestCase):
 def test_public_config(self):self.assertEqual(options(V)['worker'],'Home-PC')
 def test_secrets_never_allowed(self):
  for field in ['password','token','private_key','seed']:
   with self.assertRaises(ValueError):validate(dict(V,**{field:'secret'}))
 def test_wrong_wallet(self):
  with self.assertRaises(ValueError):validate(dict(V,identity=V['identity'][:-1]+'a'))
 def test_injected_worker(self):
  with self.assertRaises(ValueError):validate(dict(V,worker='PC; bash bad'))
 def test_unknown_region(self):
  with self.assertRaises(ValueError):validate(dict(V,region='elsewhere'))
 def test_solo_not_silently_enabled(self):
  with self.assertRaises(ValueError):validate(dict(V,mode='SOLO'))
 def test_download_config_is_not_autostart(self):self.assertNotIn('start',options(V))
 def test_symlink_refused(self):
  with tempfile.TemporaryDirectory()as t:
   p=Path(t);(p/'actual').write_text('{}');(p/'alias').symlink_to(p/'actual')
   with self.assertRaises(ValueError):load(p/'alias')
 def test_installer_tar_traversal(self):
  spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'installer/install_point6miner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory()as t:
   p=Path(t)
   with tarfile.open(p/'bad.tar.gz','w:gz')as archive:
    i=tarfile.TarInfo('../escape');i.size=1;archive.addfile(i,io.BytesIO(b'x'))
   with self.assertRaises(ValueError):m.extract(p/'bad.tar.gz',p/'out')
   self.assertFalse((p/'escape').exists())
 def test_installer_refuses_archive_links(self):
  spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'installer/install_point6miner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory()as t:
   p=Path(t)
   with tarfile.open(p/'bad.tar.gz','w:gz')as archive:
    i=tarfile.TarInfo('link');i.type=tarfile.SYMTYPE;i.linkname='/etc';archive.addfile(i)
   with self.assertRaises(ValueError):m.extract(p/'bad.tar.gz',p/'out')
if __name__=='__main__':unittest.main()
