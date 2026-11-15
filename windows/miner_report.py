"""Explicit user-triggered, allowlisted diagnostics through the existing report form."""
import http.cookiejar,json,re,socket,ssl,urllib.error,urllib.parse,urllib.request
from html.parser import HTMLParser
ORIGIN='https://pointsixpool.com'
class ReportError(Exception):pass
class Fields(HTMLParser):
 def __init__(self):super().__init__();self.fields={}
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='input'and a.get('name')in ('csrf','id')and a.get('type')=='hidden':self.fields[a['name']]=a.get('value','')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ReportError('Unexpected report redirect; nothing was confirmed.')
def payload(value):
 allowed={'error_code','engine_exit','solver_exit','error_type','engine_reason','version','threads','run_hours','accepted','rejected','uncertain','elapsed_seconds'}
 if not isinstance(value,dict)or set(value)-allowed:raise ValueError('Unexpected diagnostic field.')
 if not re.fullmatch(r'P6M-E\d{3}',value.get('error_code','')):raise ValueError('No reportable miner error code yet.')
 for k,v in value.items():
  if k in ('threads','run_hours','accepted','rejected','uncertain','elapsed_seconds'):
   if type(v)is not int or not 0<=v<=10**10:raise ValueError('Invalid diagnostic measurement.')
  elif k in ('engine_exit','solver_exit'):
   if type(v)is not int or not -2**31<=v<=2**32-1:raise ValueError('Invalid engine exit status.')
  elif k=='engine_reason':
   if v not in ('solver-exit','solver-start','solver-affinity','solver-io','engine-error'):raise ValueError('Invalid engine reason.')
  elif k=='error_type':
   if not isinstance(v,str)or not re.fullmatch(r'[A-Za-z.]{1,80}',v):raise ValueError('Invalid error type.')
  elif not isinstance(v,str)or not re.fullmatch(r'[A-Za-z0-9.\-]{1,64}',v):raise ValueError('Invalid diagnostic label.')
 return {'category':'mining','page':'/point6miner','summary':'Desktop miner '+value['error_code'],'details':'User-triggered desktop diagnostic report.\n'+json.dumps(value,sort_keys=True,indent=2)}
def submit(value,opener=None):
 fields=payload(value)
 if opener is None:opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),NoRedirect())
 def read(request):
  try:
   with opener.open(request,timeout=10)as response:
    body=response.read(131073)
    if len(body)>131072:raise ReportError('Report response exceeded its safe size limit.')
    return response.status,body.decode('utf-8')
  except urllib.error.HTTPError as e:
   if e.code==429:raise ReportError('Report limit reached. Wait before trying again; no automatic retry.')from None
   raise ReportError('Report was not confirmed (HTTP '+str(e.code)+'). Do not repeatedly submit.')from None
  except (OSError,UnicodeError) as error:
   reason=error.reason if isinstance(error,urllib.error.URLError) else error
   if isinstance(reason,ssl.SSLCertVerificationError):code,help='P6R-E202','HTTPS certificate verification failed. Check the device clock and trusted certificates; do not disable certificate checks.'
   elif isinstance(reason,ssl.SSLError):code,help='P6R-E205','A secure HTTPS connection could not be established.'
   elif isinstance(reason,socket.gaierror):code,help='P6R-E201','The pool website could not be resolved. Check DNS or open pointsixpool.com in your browser.'
   elif isinstance(reason,(TimeoutError,socket.timeout)):code,help='P6R-E203','The report connection timed out.'
   elif isinstance(reason,UnicodeError):code,help='P6R-E206','The report response could not be read.'
   else:code,help='P6R-E204','The report connection failed. Check your firewall, proxy or internet connection.'
   phase='receipt' if request.data is not None else 'form'
   raise ReportError(code+' · '+phase+' · '+help+' Delivery was not confirmed; no automatic retry. Copy diagnostics or use https://pointsixpool.com/report-error.')from None
 _,html=read(urllib.request.Request(ORIGIN+'/report-error',headers={'User-Agent':'PointSixPool-Miner/0.6'}));p=Fields();p.feed(html);csrf=p.fields.get('csrf','')
 if not re.fullmatch(r'[A-Za-z0-9_\-]{20,128}',csrf):raise ReportError('Report form could not be verified.')
 status,html=read(urllib.request.Request(ORIGIN+'/report-error',data=urllib.parse.urlencode({**fields,'csrf':csrf}).encode(),headers={'Origin':ORIGIN,'Content-Type':'application/x-www-form-urlencoded','User-Agent':'PointSixPool-Miner/0.6'}));p=Fields();p.feed(html);ident=p.fields.get('id','')
 if status!=201 or not re.fullmatch(r'[0-9a-f]{16}',ident):raise ReportError('Report receipt was not confirmed. Do not repeatedly submit.')
 return ident
