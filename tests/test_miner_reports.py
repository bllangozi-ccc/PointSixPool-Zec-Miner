import sys,io,json,unittest,urllib.parse,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
import miner_report as m
VALUE={'error_code':'P6M-E101','engine_exit':2,'error_type':'IOException','version':'0.6.0-beta5','threads':1,'run_hours':6,'accepted':7,'rejected':0,'uncertain':0}
class Response(io.BytesIO):
 def __init__(self,status,body):super().__init__(body.encode());self.status=status
class Opener:
 def __init__(self,status=201,receipt='0123456789abcdef'):self.calls=[];self.status=status;self.receipt=receipt
 def open(self,request,timeout):
  self.calls.append(request)
  if request.data is None:return Response(200,'<input type="hidden" name="csrf" value="'+'x'*32+'">')
  return Response(self.status,'<input type="hidden" name="id" value="'+self.receipt+'">')
class Reports(unittest.TestCase):
 def test_exact_csrf_submission_and_real_receipt(self):
  o=Opener();self.assertEqual(m.submit(VALUE,o),'0123456789abcdef');self.assertEqual(len(o.calls),2);fields=urllib.parse.parse_qs(o.calls[1].data.decode());self.assertEqual(fields['csrf'],['x'*32]);self.assertEqual(fields['category'],['mining']);self.assertIn('P6M-E101',fields['details'][0]);self.assertNotIn('wallet',fields['details'][0])
 def test_private_unknown_fields_refused_before_network(self):
  for field in ['wallet','identity','password','logs','hostname']:
   o=Opener()
   with self.assertRaises(ValueError):m.submit({**VALUE,field:'PRIVATE'},o)
   self.assertEqual(o.calls,[])
 def test_missing_receipt_never_claims_success_or_retries(self):
  o=Opener(receipt='bad')
  with self.assertRaises(m.ReportError):m.submit(VALUE,o)
  self.assertEqual(len(o.calls),2)
 def test_no_code_refused(self):
  with self.assertRaises(ValueError):m.payload({**VALUE,'error_code':'unknown'})
 def test_timeout_is_not_retried(self):
  class Broken:
   calls=0
   def open(self,*a,**k):self.calls+=1;raise TimeoutError()
  o=Broken()
  with self.assertRaises(m.ReportError):m.submit(VALUE,o)
  self.assertEqual(o.calls,1)
 def test_network_errors_are_classified_without_private_details(self):
  import socket,ssl
  for reason,code in [(socket.gaierror('PRIVATE'),'P6R-E201'),(ssl.SSLCertVerificationError('PRIVATE'),'P6R-E202'),(TimeoutError('PRIVATE'),'P6R-E203'),(OSError('PRIVATE'),'P6R-E204')]:
   class Broken:
    calls=0
    def open(self,*a,**k):self.calls+=1;raise urllib.error.URLError(reason)
   o=Broken()
   with self.assertRaises(m.ReportError) as caught:m.submit(VALUE,o)
   self.assertIn(code,str(caught.exception));self.assertNotIn('PRIVATE',str(caught.exception));self.assertEqual(o.calls,1)
if __name__=='__main__':unittest.main()
