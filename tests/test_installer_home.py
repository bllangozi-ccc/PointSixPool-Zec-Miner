import ast, pathlib, tempfile, os, types, unittest
source=(pathlib.Path(__file__).resolve().parents[1]/'installer/install_point6miner.py').read_text(); tree=ast.parse(source);f=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='ensure_service_home');ns={'pathlib':pathlib,'os':os,'stat':__import__('stat'),'HOME_DIR':'/unused'};exec(compile(ast.Module(body=[f],type_ignores=[]),'installer-home','exec'),ns);ensure=ns['ensure_service_home'];account=types.SimpleNamespace(pw_uid=os.getuid() if hasattr(os,"getuid") else -1,pw_gid=os.getgid() if hasattr(os,"getgid") else -1)
@unittest.skipUnless(os.name=="posix","Linux installer state directory tests")
class HomeTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.temp.name)/'home'
 def tearDown(self):self.temp.cleanup()
 def test_missing_home_recreated(self):ensure(account,self.p);self.assertEqual(self.p.stat().st_mode&511,0o700)
 def test_existing_keeps_files(self):ensure(account,self.p);(self.p/'retained').write_text('state');ensure(account,self.p);self.assertEqual((self.p/'retained').read_text(),'state')
 def test_symlink_refused(self):self.p.symlink_to(self.temp.name);self.assertRaises(ValueError,ensure,account,self.p)
 def test_file_refused(self):self.p.write_text('file');self.assertRaises(ValueError,ensure,account,self.p)
 def test_wrong_owner_refused(self):ensure(account,self.p);other=types.SimpleNamespace(pw_uid=os.getuid()+1,pw_gid=os.getgid());self.assertRaises(ValueError,ensure,other,self.p)
 def test_writable_home_refused(self):ensure(account,self.p);self.p.chmod(0o777);self.assertRaises(ValueError,ensure,account,self.p)
if __name__=="__main__":unittest.main()
