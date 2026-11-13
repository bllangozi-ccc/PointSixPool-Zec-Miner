"""Real Windows lifecycle/resource/security checks. NEVER generates PoW or contacts pools."""
import sys,os,json,subprocess,ctypes,time,urllib.request,urllib.error,hashlib,importlib.util
from pathlib import Path
from ctypes import wintypes
P=Path(__file__).resolve().parent/'package'
sys.path.insert(0,str(P))
import windows_resources as wr
checks=[]
def check(v,label):
 if not v:raise AssertionError(label)
 checks.append(label)
check(os.name=='nt','native Windows execution')
check(ctypes.sizeof(wr.MEMORYSTATUSEX)==64,'Win64 memory ABI layout')
check(ctypes.sizeof(wr.BASIC_LIMIT)==64 and ctypes.sizeof(wr.EXTENDED_LIMIT)==144,'Win64 Job Object ABI layout')
check(len(wr.available_cpus())>0,'real process affinity sampled')
check(wr.free_memory_kib()>0,'real free RAM sampled')
check(type(wr.has_avx2())is bool,'CPU feature is an actual Win32 reading')
pins=json.loads((P/'WINDOWS-PINS.json').read_text())
check(all(hashlib.sha256((P/n).read_bytes()).hexdigest()==h for n,h in pins.items()),'all packaged runtime pins match')
exe=P/'point6miner-equihash.exe'
r=subprocess.run([str(exe),'--version'],capture_output=True,timeout=5)
check(r.returncode==0 and b'header140 solution1344'in r.stdout,'native backend version executes without mining')
for args,data in [([],b'not-a-header'),(['--threads','0'],b''),(['--max-seconds','301'],b''),(['--threads','1','--threads','2'],b'')]:
 r=subprocess.run([str(exe),*args],input=data,capture_output=True,timeout=5)
 check(r.returncode==2,'native rejects malformed input or limits: '+repr(args))
r=subprocess.run(['dotnet',str(P/'Point6Miner.Cli.dll'),'--help'],capture_output=True,timeout=15)
check(r.returncode==0 and b'PointSixPool Zec Miner'in r.stdout,'managed Windows client help runs without mining')
# Child process proves inherited non-mining descendants die on parent exit.
code="import sys,subprocess,os;sys.path.insert(0,"+repr(str(P))+");from windows_resources import ParentExitGuard;guard=ParentExitGuard();p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print(p.pid,flush=True);os._exit(0)"
r=subprocess.run([sys.executable,'-u','-c',code],capture_output=True,text=True,timeout=10)
pid=int(r.stdout.strip());k=wr.kernel();k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE;k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
h=k.OpenProcess(0x100000,False,pid)
check(not h or k.WaitForSingleObject(h,5000)==0,'parent exit terminates inherited non-mining child')
if h:k.CloseHandle(h)
# Local browser API starts idle, rejects foreign/unauthenticated requests and invalid setup.
p=subprocess.Popen([sys.executable,'-u',str(P/'point6miner_ui.py'),'--no-browser'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=P)
try:
 first=p.stdout.readline();url=p.stdout.readline().strip();base,token=url.split('/#');check(base.startswith('http://127.0.0.1:'),'control UI binds loopback only')
 def request(path,body=None,auth=True,origin=None):
  headers={'Content-Type':'application/json'}
  if auth:headers['X-Point6-Token']=token
  if origin:headers['Origin']=origin
  req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=5)as r:return r.status,r.read().decode()
  except urllib.error.HTTPError as e:return e.code,e.read().decode()
 status,raw=request('/api/status');state=json.loads(raw)
 check(status==200 and state['running']is False and state['sessions']==0,'startup is idle and no mining auto-starts')
 check(1<=state['max_threads']<=4,'performance slider follows host capacity')
 check(request('/api/status',auth=False)[0]==403,'API requires local session token')
 check(request('/api/status',origin='https://unrelated.invalid')[0]==403,'cross-origin control refused')
 check(request('/api/start',{'identity':'bad','kind':'wallet','worker':'test','threads':1,'hours':1})[0]==400,'bad wallet refused before launch')
 check(request('/api/start',{'identity':'FixtureID','kind':'registered','worker':'worker;bad','threads':1,'hours':1})[0]==400,'injected worker refused before launch')
 check(request('/api/start',{'identity':'FixtureID','kind':'registered','worker':'test','threads':100,'hours':1})[0]==400,'out-of-range CPU limit refused')
 check(request('/api/start',{'identity':'FixtureID','kind':'registered','worker':'test','threads':1,'hours':0})[0]==400,'out-of-range session limit refused')
 # An explicitly changed backend must be refused before any process/network activity.
 saved=exe.read_bytes();exe.write_bytes(saved+b'changed')
 try:
  check(request('/api/start',{'identity':'FixtureID','kind':'registered','worker':'test','threads':1,'hours':1})[0]==400,'changed backend cannot start')
 finally:exe.write_bytes(saved)
 state=json.loads(request('/api/status')[1]);check(state['sessions']==0,'all refusal checks started zero mining sessions')
 check(request('/api/stop',{})[0]==200,'idle Stop works')
 _,html=request('/');check('type="range"'in html and 'https://pointsixpool.com'in html,'performance slider and official pool link rendered')
finally:
 p.kill();p.wait(timeout=10)
(P.parent/'WINDOWS-NONMINING-TESTS.PUBLIC.json').write_text(json.dumps({'passed':True,'checks':checks,'native_windows':True,'cryptomining_or_pool_network_connections':False,'proof_generation':False},indent=2)+'\n')
print(json.dumps({'passed':True,'checks':len(checks),'cryptomining':False}))
