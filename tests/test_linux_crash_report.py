import sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import linux_crash_report as c
class Crash(unittest.TestCase):
 def test_safe_report_and_no_duplicate(self):
  with tempfile.TemporaryDirectory()as h:
   send=Mock(return_value='a'*16);state={'accepted':12,'uncertain':1,'engine_exit':4,'password':'do-not-send','raw_log':'do-not-send'};config={'worker':'Linux85','threads':1,'identity':'do-not-send'}
   a=c.report_failure(state,config,'P6M-E103','ValueError',300,home=h,sender=send,invocation='b'*32);b=c.report_failure(state,config,home=h,sender=send,invocation='b'*32);self.assertTrue(a['delivered']);self.assertTrue(b['duplicate_held']);send.assert_called_once();v=send.call_args.args[0];self.assertEqual(v['worker'],'Linux85');self.assertNotIn('do-not-send',json.dumps(v));self.assertEqual(len(v['server_id']),32);self.assertEqual(next(Path(h).rglob('crash-*.json')).stat().st_mode&511,0o600)
 def test_network_failure_saved_no_replay(self):
  with tempfile.TemporaryDirectory()as h:
   send=Mock(side_effect=OSError('SECRET'));a=c.report_failure({}, {'worker':'Linux85'},home=h,sender=send,invocation='c'*32);b=c.report_failure({}, {'worker':'Linux85'},home=h,sender=send,invocation='c'*32);self.assertFalse(a['delivered']);self.assertFalse(a['automatic_retry']);send.assert_called_once();self.assertNotIn('SECRET',next(Path(h).rglob('crash-*.json')).read_text())
 def test_invalid_or_private_fields_rejected(self):
  for v in [{'error_code':'P6M-E101','identity':'bad'},{'error_code':'P6M-E101','worker':'unsafe\ntext'},{'error_code':'P6M-E101','accepted':True}]:
   with self.assertRaises(ValueError):c.payload(v)
if __name__=='__main__':unittest.main()
