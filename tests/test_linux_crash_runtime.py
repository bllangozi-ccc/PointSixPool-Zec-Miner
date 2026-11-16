import ast,io,json,re,threading,time,types,unittest
from pathlib import Path
from unittest.mock import Mock
class Runtime(unittest.TestCase):
 def case(self,events,code):
  tree=ast.parse((Path(__file__).resolve().parents[1]/'point6miner_ui.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run');p=types.SimpleNamespace(stdout=io.BytesIO(b''.join(json.dumps(e).encode()+b'\n'for e in events)),wait=lambda timeout:code);state={'accepted':0,'rejected':0,'uncertain':0,'sessions':0,'accepted_work':0.};send=Mock(return_value={'delivered':True,'receipt':'invented'});env={'time':time,'STOP':threading.Event(),'LOCK':threading.RLock(),'CHILD':None,'STATE':state,'LOG':[],'verify':lambda:None,'command':lambda*a:[],'subprocess':types.SimpleNamespace(Popen=Mock(return_value=p),PIPE=1,STDOUT=2),'json':json,'re':re,'report_failure':send};exec(compile(ast.Module(body=[fn],type_ignores=[]),'run','exec'),env);env['run']({'hours':1,'worker':'Linux85','threads':1});send.assert_called_once();self.assertFalse(state['running']);return state,send.call_args.args
 def test_engine_error_preserved_without_secret(self):
  state,args=self.case([{'error':'IOException','message':'SECRET'}],2);self.assertEqual(state['engine_exit'],2);self.assertEqual(state['error_type'],'IOException');self.assertNotIn('SECRET',str(args));self.assertEqual(state['error_code'],'P6M-E101')
 def test_uncertain_held_reported(self):
  state,args=self.case([{'Submitted':1,'Accepted':0,'Rejected':0,'Uncertain':1}],4);self.assertEqual(state['error_code'],'P6M-E103');self.assertEqual(state['uncertain'],1)
 def test_native_solver_error_preserved(self):
  state,args=self.case([{'error':'SolverFailureException','reason':'solver-exit','solver_exit':-11}],2);self.assertEqual(state['solver_exit'],-11);self.assertEqual(state['engine_reason'],'solver-exit')
if __name__=='__main__':unittest.main()
