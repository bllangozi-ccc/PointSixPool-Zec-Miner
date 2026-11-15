from performance_policy import check_memory,required_memory_kib
#!/usr/bin/env python3
"""PointSixPool Zec Miner Windows candidate. Loopback UI; never mines until Start."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import argparse,collections,hashlib,hmac,json,os,platform,re,secrets,shutil,signal,subprocess,threading,time,webbrowser
from windows_resources import available_cpus,free_memory_kib,has_avx2,ParentExitGuard
ROOT=Path(__file__).resolve().parent
GUARD=None
EXPECTED=json.loads((ROOT/'WINDOWS-PINS.json').read_text())
POOL='stratum+tcp://zec4.pointsixpool.com:3034'
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.RLock();STOP=threading.Event();CHILD=None;RUNNER=None
STATE={'running':False,'state':'Ready. Mining is off.','accepted':0,'rejected':0,'uncertain':0,'sessions':0}
LOG=collections.deque(maxlen=40)

def verify():
 for name,pin in EXPECTED.items():
  p=ROOT/name
  if p.is_symlink()or not p.is_file()or p.stat().st_size>8*1024*1024 or hashlib.sha256(p.read_bytes()).hexdigest()!=pin:raise ValueError('Package integrity check failed: '+name)
 if platform.system()!='Windows'or platform.machine().lower()not in('x86_64','amd64'):raise ValueError('This release supports Windows x64 only.')
 if not has_avx2():raise ValueError('This CPU does not provide the required AVX2 support.')
 if not shutil.which('dotnet'):raise ValueError('Install the official .NET 10 x64 runtime first; see README.')
 result=subprocess.run(['dotnet','--list-runtimes'],capture_output=True,text=True,timeout=5)
 if result.returncode or not any(line.startswith('Microsoft.NETCore.App 10.')for line in result.stdout.splitlines()):raise ValueError('The .NET10 runtime is required.')

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
 threads=value['threads'];hours=value['hours'];available=available_cpus()
 if type(threads)is not int or not 1<=threads<=min(4,len(available)):raise ValueError('Choose 1–4 available CPU threads.')
 if type(hours)is not int or not 1<=hours<=24:raise ValueError('Choose a run time of 1–24 hours.')
 memory=free_memory_kib()
 check_memory(memory,threads)
 return {**value,'cpus':available[:threads]}

def command(v,seconds):
 return ['dotnet',str(ROOT/'Point6Miner.Cli.dll'),'--mine','--pool',POOL,'--address',v['identity'],'--identity-kind',v['kind'],'--worker',v['worker'],'--solver',str(ROOT/'point6miner-equihash.exe'),'--solver-sha256',EXPECTED['point6miner-equihash.exe'],'--solver-threads',str(v['threads']),'--difficulty','0.0001220703125','--max-seconds',str(max(1,min(3600,int(seconds)))),'--max-shares','100','--reconnects','0','--solver-seconds','120','--cpu-seconds','110','--solver-memory-mib',str((required_memory_kib(v['threads'])-512*1024)//1024)]

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
 with LOCK:STATE['state']='Stopped by you.';STATE['running']=False

def run(v):
 global CHILD
 deadline=time.monotonic()+v['hours']*3600
 try:
  while not STOP.is_set()and time.monotonic()<deadline:
   verify();final=None;runtime_error=None
   with LOCK:
    session_base={k:STATE[k]for k in ['accepted','rejected','uncertain']}
    if STOP.is_set():break
    CHILD=subprocess.Popen(command(v,deadline-time.monotonic()),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);p=CHILD;STATE['sessions']+=1;STATE['state']='MICRO mining. Waiting for accepted work.'
   while True:
    line=p.stdout.readline(8193)
    if not line:break
    if len(line)>8192:raise ValueError('Unexpected oversized miner output; stopped.')
    try:
     event=json.loads(line)
     if isinstance(event,dict)and all(k in event for k in['Submitted','Accepted','Rejected','Uncertain']):final=event
     elif isinstance(event,dict)and isinstance(event.get('error'),str):
      runtime_error=event['error'] if re.fullmatch(r'[A-Za-z.]{1,80}',event['error']) else 'UnrecognizedError'
     elif isinstance(event,dict)and'Kind'in event:
      with LOCK:
       LOG.append(str(event.get('Kind',''))[:32]+': '+str(event.get('Message',''))[:200])
       if event['Kind']in('accepted','rejected'):STATE[event['Kind']]+=1
       if event['Kind']=='accepted':STATE['state']='MICRO mining · accepted shares arriving.'
    except (ValueError,TypeError):pass
   code=p.wait(timeout=10)
   with LOCK:CHILD=None
   if STOP.is_set():break
   if final is None:raise ValueError('P6M-E101 · Engine exit '+str(code)+' · '+(runtime_error or 'No error type received')+'. No complete result; stopped without replay. Copy this code to support.')
   if not all(type(final[k])is int and final[k]>=0 for k in['Submitted','Accepted','Rejected','Uncertain']):raise ValueError('P6M-E102 · Invalid engine result; stopped without replay.')
   with LOCK:
    for key,field in [('accepted','Accepted'),('rejected','Rejected'),('uncertain','Uncertain')]:STATE[key]=session_base[key]+final[field]
   if code==4 or final['Uncertain']or final['Submitted']!=final['Accepted']+final['Rejected']:raise ValueError('P6M-E103 · Share acknowledgement uncertain; stopped. That proof is never replayed.')
   if code not in(0,3):raise ValueError('The miner refused the configuration or runtime. Check your ID, runtime and pool status.')
   STOP.wait(2) # Fresh session and fresh nonces only after an unambiguous result.
  with LOCK:
   if not STOP.is_set():STATE['state']='Selected run time completed.'
 except Exception as e:
  with LOCK:STATE['state']=str(e)[:250]
 finally:
  with LOCK:p=CHILD;CHILD=None;STATE['running']=False
  terminate(p)

def start(value):
 global RUNNER
 v=options(value);verify()
 with LOCK:
  if RUNNER is not None and RUNNER.is_alive():raise ValueError('Already running. Stop before changing setup.')
  STOP.clear();STATE.update(running=True,state='Starting…',accepted=0,rejected=0,uncertain=0,sessions=0);LOG.clear();RUNNER=threading.Thread(target=run,args=(v,),daemon=True);RUNNER.start()

HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PointSixPool Zec Miner · MICRO</title><style>body{font:16px system-ui;background:#111b17;color:#f2f6f3;max-width:760px;margin:30px auto;padding:20px}section{padding:22px;border:1px solid #456151;border-radius:16px;margin:18px 0}label{display:block;margin:14px 0}input,select,button{font:inherit;padding:12px;min-height:44px;border-radius:7px}input,select{display:block;width:100%;box-sizing:border-box;background:#eef2ed;color:#17261e;border:1px solid #96ac9e}button{background:#e3ba57;color:#17261e;border:0;margin:10px 8px 0 0}button:disabled{opacity:.5}small,p{line-height:1.6;color:#cbd9cf}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#f5d995}:focus-visible{outline:3px solid #f5d995;outline-offset:3px}</style><h1>PointSixPool Zec Miner</h1><p>Zcash MICRO · Windows beta · Your computer, your Start button.</p><section><h2>Miner setup</h2><p><a href="https://pointsixpool.com" target="_blank" rel="noreferrer">pointsixpool.com</a> · Pool fee 0.6%</p><p>Preset: stratum+tcp://zec4.pointsixpool.com:3034</p><label>ID type<select id="kind"><option value="wallet">ZEC receiving wallet</option><option value="registered">Registered PointSixPool / mining ID</option></select></label><label>Wallet address or registered ID<input id="identity" autocomplete="off" spellcheck="false" maxlength="64" placeholder="Public receiving address or registered ID only"></label><label>Worker name<input id="worker" value="Point6-Rig" maxlength="32" autocomplete="off"></label><label>Performance · <output id="thread-label">1 CPU thread</output><input id="threads" type="range" min="1" max="4" step="1" value="1" aria-label="CPU threads"></label><p>Lower uses fewer CPU threads; maximum is four in this beta. This is a thread limit, not a temperature control.</p><label>Run time (hours)<input id="hours" type="number" min="1" max="24" value="6"></label><button id="start">Start mining</button><button id="stop" disabled>Stop</button><p>Mining is off until you press Start. No automatic startup or installation service. Never enter a recovery phrase, password, payment key or private key.</p></section><section><h2>Live miner status</h2><p id="status" role="status">Ready. Mining is off.</p><p id="counts">Accepted:0 · Rejected:0 · Uncertain:0</p><details><summary>Recent miner messages</summary><pre id="log"></pre></details></section><section><h2>Rewards &amp; help</h2><p>MICRO shares eligible PPLNS pool work. It does not guarantee immediate earnings: rewards require actual pool blocks, maturity and eligible work. Pool fee:0.6%; minimum payout:0.001ZEC. CPU mining is much slower than ASIC mining and may cost more in electricity than it earns.</p><p>Requires Windows x64 with AVX2, the .NET 10 x64 runtime, Python 3 and at least 3 GiB free memory. Threads default to one. GPU mining and other coins are not included.</p><a href="https://pointsixpool.com/getting-started" target="_blank" rel="noreferrer">Pool help</a></section><script nonce="NONCE">'use strict';const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);const el=id=>document.getElementById(id);el('threads').oninput=()=>el('thread-label').textContent=el('threads').value+' CPU thread'+(el('threads').value==='1'?'':'s');async function call(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'X-Point6-Token':token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d;}async function refresh(){try{const d=await call('/api/status');el('threads').max=d.max_threads;el('threads').title=d.running?'Performance is locked while mining. Stop mining to adjust speed, then press Start Mining.':'Choose CPU threads before starting. Lower speed leaves more capacity for other apps.';if(Number(el('threads').value)>d.max_threads)el('threads').value=d.max_threads;el('threads').oninput();el('status').textContent=d.state;el('counts').textContent='Accepted:'+d.accepted+' · Rejected:'+d.rejected+' · Uncertain:'+d.uncertain;el('log').textContent=d.log.join('\\n');el('start').disabled=d.running;el('stop').disabled=!d.running;}catch(e){el('status').textContent=e.message;}}el('start').onclick=async()=>{el('start').disabled=true;try{await call('/api/start',{identity:el('identity').value.trim(),kind:el('kind').value,worker:el('worker').value.trim(),threads:Number(el('threads').value),hours:Number(el('hours').value)});await refresh();}catch(e){el('status').textContent=e.message;el('start').disabled=false;}};el('stop').onclick=async()=>{try{await call('/api/stop',{});await refresh();}catch(e){el('status').textContent=e.message;}};refresh();setInterval(refresh,2000);</script></html>'''

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
  with LOCK:v={**STATE,'log':list(LOG),'max_threads':min(4,len(available_cpus()))}
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
 global GUARD
 GUARD=ParentExitGuard()
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args();server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
 url='http://127.0.0.1:'+str(server.server_port)+'/#'+TOKEN
 print('PointSixPool Zec Miner is off. Open this local session URL on this computer:\n'+url,flush=True)
 if not args.no_browser:webbrowser.open(url)
 try:server.serve_forever(poll_interval=.3)
 except KeyboardInterrupt:pass
 finally:stop();server.server_close()
if __name__=='__main__':main()
