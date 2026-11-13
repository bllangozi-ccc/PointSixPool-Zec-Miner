#!/usr/bin/env python3
"""Point6Miner Linux public beta. Loopback UI; never mines until Start."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import argparse,collections,hashlib,hmac,json,os,platform,re,secrets,shutil,signal,subprocess,threading,time,webbrowser
ROOT=Path(__file__).resolve().parent
EXPECTED={'Point6Miner.Cli.dll': 'e52840601304aeb00d7f5b227a004454978e42eea790a5e0b484165a62f65e47', 'Point6Miner.Core.dll': '022f39f737328d6a5002b46ab5b49ef4feeb0088eecb57a10b37e5eeb35401ae', 'Point6Miner.Cli.runtimeconfig.json': '9950d4583cfc9a106857c0d5b8a75b53e8774852b57b80bc3823a74d44a4d87f', 'Point6Miner.Cli.deps.json': '704bff02eeeb10db94877f048c786591cf721e351cf726c461a305503b99915d', 'point6miner-equihash': '75b9ad17fbc6f2995013bd87ba9c9ab5c810e99105ed0f38b7528959bc6548af'}
POOL='stratum+tcp://zec4.pointsixpool.com:3034'
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.RLock();STOP=threading.Event();CHILD=None;RUNNER=None
STATE={'running':False,'state':'Ready. Mining is off.','accepted':0,'rejected':0,'uncertain':0,'sessions':0}
LOG=collections.deque(maxlen=40)

def verify():
 for name,pin in EXPECTED.items():
  p=ROOT/name
  if p.is_symlink()or not p.is_file()or p.stat().st_size>8*1024*1024 or hashlib.sha256(p.read_bytes()).hexdigest()!=pin:raise ValueError('Package integrity check failed: '+name)
 if platform.system()!='Linux'or platform.machine()not in('x86_64','amd64'):raise ValueError('This release supports Linux x86_64 only.')
 if 'avx2'not in Path('/proc/cpuinfo').read_text():raise ValueError('This CPU does not provide the required AVX2 support.')
 if not shutil.which('dotnet')or not shutil.which('taskset'):raise ValueError('Install the .NET10 runtime and taskset first; see README.')
 result=subprocess.run(['dotnet','--list-runtimes'],capture_output=True,text=True,timeout=5)
 if result.returncode or not any(line.startswith('Microsoft.NETCore.App 10.')for line in result.stdout.splitlines()):raise ValueError('The .NET10 runtime is required.')
 if os.geteuid()==0:raise ValueError('Run Point6Miner as your normal user, not root.')

def options(value):
 if not isinstance(value,dict)or set(value)!={'identity','kind','worker','threads','hours'}:raise ValueError('Complete the miner setup fields.')
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
 threads=value['threads'];hours=value['hours'];available=sorted(os.sched_getaffinity(0))
 if type(threads)is not int or not 1<=threads<=min(4,len(available)):raise ValueError('Choose 1–4 available CPU threads.')
 if type(hours)is not int or not 1<=hours<=24:raise ValueError('Choose a run time of 1–24 hours.')
 memory=next(int(line.split()[1])for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:'))
 if memory<3*1024*1024:raise ValueError('At least3GiB of free memory is required before starting.')
 return {**value,'cpus':available[:threads]}

def command(v,seconds):
 return ['taskset','-c',','.join(map(str,v['cpus'])),'dotnet',str(ROOT/'Point6Miner.Cli.dll'),'--mine','--pool',POOL,'--address',v['identity'],'--identity-kind',v['kind'],'--worker',v['worker'],'--solver',str(ROOT/'point6miner-equihash'),'--solver-sha256',EXPECTED['point6miner-equihash'],'--solver-threads',str(v['threads']),'--difficulty','0.0001220703125','--max-seconds',str(max(1,min(3600,int(seconds)))),'--max-shares','100','--reconnects','0','--solver-seconds','120','--cpu-seconds','110','--solver-memory-mib','2048']

def stop():
 STOP.set()
 with LOCK:p=CHILD
 if p is not None and p.poll()is None:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:p.wait(timeout=8)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   p.wait(timeout=5)
 with LOCK:STATE['state']='Stopped by you.';STATE['running']=False

def run(v):
 global CHILD
 deadline=time.monotonic()+v['hours']*3600
 try:
  while not STOP.is_set()and time.monotonic()<deadline:
   verify();final=None
   with LOCK:
    session_base={k:STATE[k]for k in ['accepted','rejected','uncertain']}
    if STOP.is_set():break
    CHILD=subprocess.Popen(command(v,deadline-time.monotonic()),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True);p=CHILD;STATE['sessions']+=1;STATE['state']='Mining MICRO. Waiting for accepted work.'
   while True:
    line=p.stdout.readline(8193)
    if not line:break
    if len(line)>8192:raise ValueError('Unexpected oversized miner output; stopped.')
    try:
     event=json.loads(line)
     if isinstance(event,dict)and all(k in event for k in['Submitted','Accepted','Rejected','Uncertain']):final=event
     elif isinstance(event,dict)and'Kind'in event:
      with LOCK:
       LOG.append(str(event.get('Kind',''))[:32]+': '+str(event.get('Message',''))[:200])
       if event['Kind']in('accepted','rejected'):STATE[event['Kind']]+=1
    except (ValueError,TypeError):pass
   code=p.wait(timeout=10)
   with LOCK:CHILD=None
   if STOP.is_set():break
   if final is None:raise ValueError('No complete miner result. Stopped; no automatic replay.')
   if not all(type(final[k])is int and final[k]>=0 for k in['Submitted','Accepted','Rejected','Uncertain']):raise ValueError('Invalid miner result; stopped.')
   with LOCK:
    for key,field in [('accepted','Accepted'),('rejected','Rejected'),('uncertain','Uncertain')]:STATE[key]=session_base[key]+final[field]
   if code==4 or final['Uncertain']or final['Submitted']!=final['Accepted']+final['Rejected']:raise ValueError('A submitted share has an uncertain acknowledgement. Stopped; that proof is never replayed.')
   if code not in(0,3):raise ValueError('The miner refused the configuration or runtime. Check your ID, runtime and pool status.')
   STOP.wait(2) # Fresh session and fresh nonces only after an unambiguous result.
  with LOCK:
   if not STOP.is_set():STATE['state']='Selected run time completed.'
 except Exception as e:
  with LOCK:STATE['state']=str(e)[:250]
 finally:
  with LOCK:p=CHILD;CHILD=None;STATE['running']=False
  if p is not None and p.poll()is None:
   try:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=8)
   except ProcessLookupError:pass
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)

def start(value):
 global RUNNER
 v=options(value);verify()
 with LOCK:
  if RUNNER is not None and RUNNER.is_alive():raise ValueError('Already running. Stop before changing setup.')
  STOP.clear();STATE.update(running=True,state='Starting…',accepted=0,rejected=0,uncertain=0,sessions=0);LOG.clear();RUNNER=threading.Thread(target=run,args=(v,),daemon=True);RUNNER.start()

HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Point6Miner · MICRO</title><style>body{font:16px system-ui;background:#111b17;color:#f2f6f3;max-width:760px;margin:30px auto;padding:20px}section{padding:22px;border:1px solid #456151;border-radius:16px;margin:18px 0}label{display:block;margin:14px 0}input,select,button{font:inherit;padding:12px;min-height:44px;border-radius:7px}input,select{display:block;width:100%;box-sizing:border-box;background:#eef2ed;color:#17261e;border:1px solid #96ac9e}button{background:#e3ba57;color:#17261e;border:0;margin:10px 8px 0 0}button:disabled{opacity:.5}small,p{line-height:1.6;color:#cbd9cf}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#f5d995}:focus-visible{outline:3px solid #f5d995;outline-offset:3px}</style><h1>Point6Miner</h1><p>Zcash MICRO · Linux public beta · Your computer, your Start button.</p><section><h2>Miner setup</h2><p>Preset: stratum+tcp://zec4.pointsixpool.com:3034</p><label>ID type<select id="kind"><option value="wallet">ZEC receiving wallet</option><option value="registered">Registered PointSixPool / mining ID</option></select></label><label>Wallet address or registered ID<input id="identity" autocomplete="off" spellcheck="false" maxlength="64" placeholder="Public receiving address or registered ID only"></label><label>Worker name<input id="worker" value="Point6-Rig" maxlength="32" autocomplete="off"></label><label>CPU threads<select id="threads"><option>1</option><option>2</option><option>3</option><option>4</option></select></label><label>Run time (hours)<input id="hours" type="number" min="1" max="24" value="6"></label><button id="start">Start mining</button><button id="stop" disabled>Stop</button><p>Mining is off until you press Start. No automatic startup or installation service. Never enter a recovery phrase, password, payment key or private key.</p></section><section><h2>Live miner status</h2><p id="status" role="status">Ready. Mining is off.</p><p id="counts">Accepted:0 · Rejected:0 · Uncertain:0</p><details><summary>Recent miner messages</summary><pre id="log"></pre></details></section><section><h2>Rewards &amp; help</h2><p>MICRO shares eligible PPLNS pool work. It does not guarantee immediate earnings: rewards require actual pool blocks, maturity and eligible work. Pool fee:0.6%; minimum payout:0.001ZEC. CPU mining is much slower than ASIC mining and may cost more in electricity than it earns.</p><p>Requires Linux x86_64 with AVX2, the .NET10 runtime, Python3, taskset, and at least3GiB free memory. Threads default to1. Other coins and Windows builds are not included.</p><a href="https://pointsixpool.com/getting-started" target="_blank" rel="noreferrer">Pool help</a></section><script nonce="NONCE">'use strict';const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);const el=id=>document.getElementById(id);async function call(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'X-Point6-Token':token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d;}async function refresh(){try{const d=await call('/api/status');el('status').textContent=d.state;el('counts').textContent='Accepted:'+d.accepted+' · Rejected:'+d.rejected+' · Uncertain:'+d.uncertain;el('log').textContent=d.log.join('\\n');el('start').disabled=d.running;el('stop').disabled=!d.running;}catch(e){el('status').textContent=e.message;}}el('start').onclick=async()=>{el('start').disabled=true;try{await call('/api/start',{identity:el('identity').value.trim(),kind:el('kind').value,worker:el('worker').value.trim(),threads:Number(el('threads').value),hours:Number(el('hours').value)});await refresh();}catch(e){el('status').textContent=e.message;el('start').disabled=false;}};el('stop').onclick=async()=>{try{await call('/api/stop',{});await refresh();}catch(e){el('status').textContent=e.message;}};refresh();setInterval(refresh,2000);</script></html>'''

class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def log_message(self,*args):pass
 def allowed(self):
  origin='http://127.0.0.1:'+str(self.server.server_port)
  return self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port)and self.headers.get('Origin',origin)==origin and hmac.compare_digest(self.headers.get('X-Point6-Token',''),TOKEN)
 def reply(self,code,value,html=False):
  nonce=secrets.token_urlsafe(16);raw=(value.replace('NONCE',nonce).encode()if html else json.dumps(value,allow_nan=False).encode());self.send_response(code);self.send_header('Content-Type','text/html; charset=utf-8'if html else'application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'nonce-"+nonce+"'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if self.path=='/'and self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port):return self.reply(200,HTML,True)
  if self.path!='/api/status'or not self.allowed():return self.reply(403,{'error':'Local session verification required.'})
  with LOCK:v={**STATE,'log':list(LOG)}
  return self.reply(200,v)
 def do_POST(self):
  if self.path not in('/api/start','/api/stop')or not self.allowed():return self.reply(403,{'error':'Local session verification required.'})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<=1024 or self.headers.get('Content-Type')!='application/json':raise ValueError('Invalid request.')
   value=json.loads(self.rfile.read(length))
   if self.path=='/api/start':start(value)
   else:
    if value!={}:raise ValueError('Invalid Stop request.')
    stop()
   return self.reply(200,{'saved':True})
  except (ValueError,OSError,subprocess.SubprocessError)as e:return self.reply(400,{'error':str(e)[:250]})

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args();server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
 url='http://127.0.0.1:'+str(server.server_port)+'/#'+TOKEN
 print('Point6Miner is off. Open this local session URL on this computer:\n'+url,flush=True)
 if not args.no_browser:webbrowser.open(url)
 try:server.serve_forever(poll_interval=.3)
 except KeyboardInterrupt:pass
 finally:stop();server.server_close()
if __name__=='__main__':main()
