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
 allowed={'error_code','engine_exit','solver_exit','engine_reason','error_type','version','threads','accepted','rejected','uncertain','elapsed_seconds','worker','server_id','report_id','event_utc','service_result','service_exit_status','memory_available_mib','memory_total_mib','cpu_threads_available','runtime_marker'}
 if not isinstance(value,dict)or set(value)-allowed:raise ValueError('Unexpected diagnostic field.')
 if not re.fullmatch(r'P6M-E\d{3}',value.get('error_code','')):raise ValueError('Invalid error code.')
 for k,v in value.items():
  if k in ('threads','accepted','rejected','uncertain','elapsed_seconds','memory_available_mib','memory_total_mib','cpu_threads_available'):
   if type(v)is not int or not 0<=v<=10**10:raise ValueError('Invalid measurement.')
  elif k in ('engine_exit','solver_exit'):
   if type(v)is not int or not -2**31<=v<=2**32-1:raise ValueError('Invalid exit status.')
  elif not isinstance(v,str)or not re.fullmatch(r'[A-Za-z0-9_.:+-]{1,80}',v):raise ValueError('Invalid diagnostic label.')
 return {'category':'mining','page':'/point6miner','summary':'Linux miner '+value['error_code'],'details':'Automatic Linux miner crash report. Device-reported data; no credentials or raw logs.\n'+json.dumps(value,sort_keys=True,indent=2)}
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


def report_failure(state,setup,error_code='P6M-E101',error_type='RuntimeError',elapsed=0,service_result='',service_exit_status='',home=None,sender=None,invocation=None):
 """One bounded attempt per invocation; preserve local report on network failure."""
 import os,uuid,datetime,stat
 from pathlib import Path
 home=Path.home()if home is None else Path(home);folder=home/'.local/state/pointsixpool-miner'
 folder.mkdir(mode=0o700,parents=True,exist_ok=True)
 for parent in [folder,folder.parent,folder.parent.parent]:
  if parent.is_symlink()or parent.stat().st_uid!=os.getuid():raise ValueError('Unsafe report directory.')
 ident=folder/'server-id'
 try:
  fd=os.open(ident,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'w')as f:f.write(uuid.uuid4().hex)
 except FileExistsError:pass
 st=ident.lstat()
 if not stat.S_ISREG(st.st_mode)or st.st_uid!=os.getuid()or st.st_mode&0o077 or st.st_size!=32:raise ValueError('Unsafe server identifier.')
 server=ident.read_text();run=invocation or os.environ.get('INVOCATION_ID')or uuid.uuid4().hex
 if not re.fullmatch('[a-f0-9]{32}',server)or not re.fullmatch('[a-f0-9]{32}',run):raise ValueError('Invalid report identifier.')
 marker=folder/('crash-'+run+'.json');v={'version':'0.6.0-beta9','server_id':server,'report_id':run,'event_utc':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'error_code':error_code,'error_type':error_type,'elapsed_seconds':max(0,int(elapsed))}
 try:
  memory={line.split(':')[0]:int(line.split()[1])//1024 for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith(('MemAvailable:','MemTotal:'))}
  v.update(memory_available_mib=memory['MemAvailable'],memory_total_mib=memory['MemTotal'],cpu_threads_available=len(os.sched_getaffinity(0)))
 except(OSError,ValueError,KeyError,AttributeError):pass
 for k in ('accepted','rejected','uncertain'):
  if type(state.get(k))is int and 0<=state[k]<=10**10:v[k]=state[k]
 for k in ('engine_exit','solver_exit'):
  if type(state.get(k))is int:v[k]=state[k]
 if state.get('runtime_marker')in('out-of-memory','stack-overflow','runtime-fatal','unhandled-exception'):v['runtime_marker']=state['runtime_marker']
 if state.get('engine_reason')in('solver-exit','solver-start','solver-affinity','solver-io','engine-error'):v['engine_reason']=state['engine_reason']
 for k in ('worker','threads'):
  if k in setup:v[k]=setup[k]
 if service_result:v['service_result']=service_result
 if service_exit_status:v['service_exit_status']=service_exit_status
 payload(v)
 try:fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 except FileExistsError:return {'duplicate_held':True}
 with os.fdopen(fd,'w')as f:json.dump({'diagnostic':v,'delivery':'attempted-not-confirmed'},f);f.flush();os.fsync(f.fileno())
 try:receipt=(sender or submit)(v);result={'delivered':True,'receipt':receipt}
 except Exception as e:result={'delivered':False,'error_type':type(e).__name__,'automatic_retry':False}
 # Retain only bounded reports for this miner; never scan or touch unrelated files.
 own=sorted(folder.glob('crash-????????????????????????????????.json'),key=lambda p:p.stat().st_mtime,reverse=True)
 for old in own[20:]:
  if old.is_file()and not old.is_symlink()and old.stat().st_uid==os.getuid():old.unlink()
 return result
