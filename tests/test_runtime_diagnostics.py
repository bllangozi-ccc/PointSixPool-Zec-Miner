import ast,io,json,re,threading,time,types,unittest
from pathlib import Path
from unittest.mock import Mock
class RuntimeDiagnostics(unittest.TestCase):
 def exercise(self,events,code):
  for name in ('desktop/desktop_backend.py','point6miner_ui.py'):
   with self.subTest(frontend=name):
    tree=ast.parse((Path(__file__).resolve().parents[1]/'windows'/name).read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run');module=ast.Module(body=[fn],type_ignores=[])
    process=types.SimpleNamespace(stdout=io.StringIO(''.join(json.dumps(e)+'\n' for e in events)),wait=lambda timeout:code)
    spawn=Mock(return_value=process);state={'accepted':0,'rejected':0,'uncertain':0,'sessions':0,'accepted_work':0.,'state':''}
    env={'time':time,'STOP':threading.Event(),'LOCK':threading.RLock(),'CHILD':None,'STATE':state,'LOG':[],'verify':lambda:None,'command':lambda *a:[],'subprocess':types.SimpleNamespace(Popen=spawn,PIPE=1,STDOUT=2,CREATE_NO_WINDOW=0),'json':json,'re':re,'terminate':lambda p:None}
    exec(compile(module,name,'exec'),env);env['run']({'hours':1});self.assertEqual(spawn.call_count,1);self.assertFalse(state['running']);yield state
 def test_error_type_and_exit_retained_no_private_message(self):
  for state in self.exercise([{'error':'IOException','message':'PRIVATE wallet endpoint'}],2):
   self.assertIn('P6M-E101',state['state']);self.assertIn('exit 2',state['state']);self.assertIn('IOException',state['state']);self.assertNotIn('PRIVATE',state['state'])
 def test_native_crash_exit_retained(self):
  for state in self.exercise([],-1073741819):self.assertIn('-1073741819',state['state'])
 def test_untrusted_error_string_not_published(self):
  for state in self.exercise([{'error':'SECRET / wallet'}],2):self.assertNotIn('SECRET',state['state']);self.assertIn('UnrecognizedError',state['state'])
 def test_uncertain_share_never_retried(self):
  for state in self.exercise([{'Submitted':1,'Accepted':0,'Rejected':0,'Uncertain':1}],4):self.assertIn('P6M-E103',state['state'])
 def test_incomplete_accounting_never_retried(self):
  for state in self.exercise([{'Submitted':2,'Accepted':1,'Rejected':0,'Uncertain':0}],0):self.assertIn('P6M-E103',state['state'])
 def test_invalid_final_never_retried(self):
  for state in self.exercise([{'Submitted':True,'Accepted':0,'Rejected':0,'Uncertain':0}],0):self.assertIn('P6M-E102',state['state'])
if __name__=='__main__':unittest.main()
