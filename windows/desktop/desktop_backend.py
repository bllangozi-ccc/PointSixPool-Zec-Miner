from performance_policy import check_memory,required_memory_kib
from miner_links import portal_url
from miner_efficiency import hardware, monitor
#!/usr/bin/env python3
"""PointSixPool Zec Miner Windows candidate. Loopback UI; never mines until Start."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import sys,argparse,collections,hashlib,hmac,json,os,platform,re,secrets,shutil,signal,subprocess,threading,time,webbrowser
from windows_resources import available_cpus,free_memory_kib,has_avx2,ParentExitGuard
ROOT=Path(sys._MEIPASS)/'miner' if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
GUARD=None
EXPECTED=json.loads((ROOT/'WINDOWS-PINS.json').read_text())
POOL='stratum+tcp://zec4.pointsixpool.com:3034'
REGION_POOLS={'EU':POOL,'USA':'stratum+tcp://usa.zec4.pointsixpool.com:3034','ASIA':'stratum+tcp://asia.zec4.pointsixpool.com:3034'}
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.RLock();STOP=threading.Event();CHILD=None;RUNNER=None;TELEMETRY=None
STATE={'connected':False,'running':False,'state':'Ready. Mining is off.','accepted':0,'rejected':0,'uncertain':0,'sessions':0,'accepted_work':0.,'hardware':hardware()}
LOG=collections.deque(maxlen=40)

def verify():
 if platform.system()!='Windows' or platform.machine().lower()not in('x86_64','amd64'):raise ValueError('This release supports Windows x64 only.')
 if not has_avx2():raise ValueError('This CPU does not provide the required AVX2 support.')
 if not isinstance(EXPECTED,dict)or not 3<=len(EXPECTED)<=512:raise ValueError('Package integrity manifest is invalid.')
 for name,pin in EXPECTED.items():
  rel=Path(name)
  if rel.is_absolute()or '..'in rel.parts:raise ValueError('Package integrity path is invalid.')
  p=ROOT/rel
  if p.is_symlink()or not p.is_file()or not 0<p.stat().st_size<=32*1024*1024 or hashlib.sha256(p.read_bytes()).hexdigest()!=pin:raise ValueError('Package integrity check failed: '+name)
 if 'backend/Point6Miner.Cli.exe'not in EXPECTED:raise ValueError('Bundled mining engine is missing.')

def options(value):
 if not isinstance(value,dict)or set(value) not in ({'identity','kind','worker','threads','hours'},{'identity','kind','worker','threads','hours','region'}):raise ValueError('Complete the miner setup fields.')
 if value.get('region','EU')not in REGION_POOLS:raise ValueError('Choose EU, USA or ASIA.')
 kind=value['kind'];identity=value['identity'];worker=value['worker']
 if kind not in('wallet','registered')or not isinstance(identity,str)or not isinstance(worker,str):raise ValueError('Choose a wallet or registered ID.')
 if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}',worker):raise ValueError('Use 1–32 letters, numbers, underscores or hyphens for the worker.')
 if kind=='registered':
  if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{2,63}',identity):raise ValueError('Enter your registered PointSixPool or mining account ID without a worker suffix.')
 else:
  alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
  if not 30<=len(identity)<=40 or any(c not in alphabet for c in identity):raise ValueError('Enter a transparent ZEC mainnet receiving address.')
  n=0
  for c in identity:n=n*58+alphabet.index(c)
  raw=b'\0'*(len(identity)-len(identity.lstrip('1')))+n.to_bytes((n.bit_length()+7)//8,'big')
  if len(raw)!=26 or raw[:2]not in(b'\x1c\xb8',b'\x1c\xbd')or not hmac.compare_digest(hashlib.sha256(hashlib.sha256(raw[:22]).digest()).digest()[:4],raw[22:]):raise ValueError('ZEC mainnet address checksum failed.')
 threads=value['threads'];hours=value['hours'];available=available_cpus()
 if type(threads)is not int or not 1<=threads<=min(4,len(available)):raise ValueError('Choose 1–4 available CPU threads.')
 if type(hours)is not int or not 1<=hours<=24:raise ValueError('Choose a run time of 1–24 hours.')
 memory=free_memory_kib()
 check_memory(memory,threads)
 return {**value,'cpus':available[:threads]}

def command(v,seconds):
 return [str(ROOT/'backend/Point6Miner.Cli.exe'),'--mine','--pool',REGION_POOLS[v.get('region','EU')],'--address',v['identity'],'--identity-kind',v['kind'],'--worker',v['worker'],'--solver',str(ROOT/'point6miner-equihash.exe'),'--solver-sha256',EXPECTED['point6miner-equihash.exe'],'--solver-threads',str(v['threads']),'--difficulty','0.0001220703125','--max-seconds',str(max(1,min(3600,int(seconds)))),'--max-shares','100','--reconnects','0','--solver-seconds','120','--cpu-seconds','110','--solver-memory-mib',str((required_memory_kib(v['threads'])-512*1024)//1024)]

def terminate(p):
 if p is None or p.poll()is not None:return
 taskkill=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/taskkill.exe'
 result=subprocess.run([str(taskkill),'/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:raise ValueError('Could not stop the miner. Close the miner window to stop its protected process group.')

def stop():
 STOP.set()
 with LOCK:p=CHILD
 terminate(p)
 with LOCK:STATE['state']='Stopped by you.';STATE['running']=False;STATE['connected']=False

def run(v):
 global CHILD
 deadline=time.monotonic()+v['hours']*3600
 try:
  while not STOP.is_set()and time.monotonic()<deadline:
   verify();final=None;runtime_error=None;runtime_reason=None;solver_exit=None
   with LOCK:
    session_base={k:STATE[k]for k in ['accepted','rejected','uncertain']}
    if STOP.is_set():break
    CHILD=subprocess.Popen(command(v,deadline-time.monotonic()),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);p=CHILD;STATE['sessions']+=1;STATE['connected']=False;STATE['state']='MICRO mining. Waiting for accepted work.'
   while True:
    line=p.stdout.readline(8193)
    if not line:break
    if len(line)>8192:raise ValueError('Unexpected oversized miner output; stopped.')
    try:
     event=json.loads(line)
     if isinstance(event,dict)and all(k in event for k in['Submitted','Accepted','Rejected','Uncertain']):final=event
     elif isinstance(event,dict)and isinstance(event.get('error'),str):
      runtime_error=event['error'] if re.fullmatch(r'[A-Za-z.]{1,80}',event['error']) else 'UnrecognizedError'
      solver_exit=event.get('solver_exit') if type(event.get('solver_exit'))is int and -2**31<=event['solver_exit']<=2**32-1 else None
      runtime_reason=event.get('reason') if event.get('reason') in ('solver-exit','solver-start','solver-affinity','solver-io','engine-error') else None
     elif isinstance(event,dict)and'Kind'in event:
      with LOCK:
       LOG.append(str(event.get('Kind',''))[:32]+': '+str(event.get('Message',''))[:200])
       if event['Kind']=='authorized':STATE['connected']=True
       if event['Kind']in('accepted','rejected'):STATE[event['Kind']]+=1
       if event['Kind']=='accepted':STATE['state']='MICRO mining · accepted shares arriving.'
       if event['Kind']=='accepted':
        target=event.get('AcceptedTarget')
        if isinstance(target,str) and re.fullmatch(r'[0-9A-Fa-f]{64}',target):STATE['accepted_work']+=2.**256/(int(target,16)+1)
        else:STATE['work_measurement_unavailable']=True
    except (ValueError,TypeError):pass
   code=p.wait(timeout=10)
   with LOCK:CHILD=None;STATE['connected']=False
   if STOP.is_set():break
   if final is None:raise ValueError('P6M-E101 · Engine exit '+str(code)+' · '+(runtime_error or 'No error type received')+(' · '+runtime_reason if runtime_reason else '')+(' · solver exit '+str(solver_exit) if solver_exit is not None else '')+'. No complete result; stopped without replay. Copy this code to support.')
   if not all(type(final[k])is int and final[k]>=0 for k in['Submitted','Accepted','Rejected','Uncertain']):raise ValueError('P6M-E102 · Invalid engine result; stopped without replay.')
   with LOCK:
    for key,field in [('accepted','Accepted'),('rejected','Rejected'),('uncertain','Uncertain')]:STATE[key]=session_base[key]+final[field]
   if code==4 or final['Uncertain']or final['Submitted']!=final['Accepted']+final['Rejected']:raise ValueError('P6M-E103 · Share acknowledgement uncertain; stopped. That proof is never replayed.')
   if code not in(0,3):raise ValueError('The miner refused the configuration or runtime. Check your ID, runtime and pool status.')
   with LOCK:STATE['state']='Connection ended · retrying fresh work in 10 seconds…' if final.get('StopReason')=='connection-ended' else 'Session complete · connecting to fresh work…'
   STOP.wait(10 if final.get('StopReason')=='connection-ended' else 2) # Fresh session and fresh nonces only after an unambiguous result.
  with LOCK:
   if not STOP.is_set():STATE['state']='Selected run time completed.'
 except Exception as e:
  with LOCK:STATE['state']=str(e)[:250]
 finally:
  with LOCK:p=CHILD;CHILD=None;STATE['running']=False;STATE['connected']=False
  terminate(p)

def start(value):
 global RUNNER,TELEMETRY
 v=options(value);verify()
 with LOCK:
  if RUNNER is not None and RUNNER.is_alive():raise ValueError('Already running. Stop before changing setup.')
  if TELEMETRY is not None and TELEMETRY.is_alive():raise ValueError('Previous telemetry is stopping. Try again in a moment.')
  STOP.clear();STATE.update(running=True,state='Starting…',accepted=0,rejected=0,uncertain=0,sessions=0,accepted_work=0.,work_measurement_unavailable=False,dashboard_url=portal_url(v['kind'],v['identity']));LOG.clear();TELEMETRY=threading.Thread(target=monitor,args=(sys.modules[__name__],v['threads']),daemon=True);TELEMETRY.start();RUNNER=threading.Thread(target=run,args=(v,),daemon=True);RUNNER.start()
