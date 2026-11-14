from miner_efficiency import hardware, monitor, recommended_measured
#!/usr/bin/env python3
"""Point6Miner Linux public beta. Loopback UI; never mines until Start."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from performance_policy import recommend_threads,linux_battery
import argparse,collections,hashlib,hmac,json,os,platform,re,secrets,shutil,signal,subprocess,threading,time,webbrowser
ROOT=Path(__file__).resolve().parent
EXPECTED={'Point6Miner.Cli.dll': 'e52840601304aeb00d7f5b227a004454978e42eea790a5e0b484165a62f65e47', 'Point6Miner.Core.dll': '022f39f737328d6a5002b46ab5b49ef4feeb0088eecb57a10b37e5eeb35401ae', 'Point6Miner.Cli.runtimeconfig.json': '9950d4583cfc9a106857c0d5b8a75b53e8774852b57b80bc3823a74d44a4d87f', 'Point6Miner.Cli.deps.json': '704bff02eeeb10db94877f048c786591cf721e351cf726c461a305503b99915d', 'point6miner-equihash': '75b9ad17fbc6f2995013bd87ba9c9ab5c810e99105ed0f38b7528959bc6548af'}
POOL='stratum+tcp://zec4.pointsixpool.com:3034'
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.RLock();STOP=threading.Event();CHILD=None;RUNNER=None;TELEMETRY=None
STATE={'running':False,'state':'Ready. Mining is off.','accepted':0,'rejected':0,'uncertain':0,'sessions':0,'accepted_work':0.,'hardware':hardware()}
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
       if event['Kind']=='accepted':
        target=event.get('AcceptedTarget')
        if isinstance(target,str) and re.fullmatch(r'[0-9A-Fa-f]{64}',target):STATE['accepted_work']+=2.**256/(int(target,16)+1)
        else:STATE['work_measurement_unavailable']=True
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
 global RUNNER,TELEMETRY
 v=options(value);verify()
 with LOCK:
  if RUNNER is not None and RUNNER.is_alive():raise ValueError('Already running. Stop before changing setup.')
  if TELEMETRY is not None and TELEMETRY.is_alive():raise ValueError('Previous telemetry is stopping. Try again in a moment.')
  STOP.clear();STATE.update(running=True,state='Starting…',accepted=0,rejected=0,uncertain=0,sessions=0,accepted_work=0.,work_measurement_unavailable=False);LOG.clear();TELEMETRY=threading.Thread(target=monitor,args=(sys.modules[__name__],v['threads']),daemon=True);TELEMETRY.start();RUNNER=threading.Thread(target=run,args=(v,),daemon=True);RUNNER.start()

HTML='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PointSixPool Zec Miner</title><style>\n:root{color-scheme:light;--bg:#f3f5f4;--panel:#fff;--ink:#142b2a;--muted:#566a68;--line:#d7e0de;--green:#167149;--gold:#a86b35}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px system-ui,Segoe UI,sans-serif}header{display:flex;align-items:center;gap:24px;padding:18px 28px;background:var(--panel);border-bottom:1px solid var(--line);flex-wrap:wrap}.brand{font-size:21px;font-weight:750}.brand span{color:var(--green)}nav{display:flex;gap:6px;flex-wrap:wrap}button,input,select{font:inherit}nav button{border:0;background:transparent;color:var(--muted);padding:10px 14px;border-radius:8px;cursor:pointer}nav button[aria-selected=true]{color:var(--green);background:#edf5ef;font-weight:700}main{max-width:1080px;margin:auto;padding:24px}.heading{display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap}h1{font-size:24px;margin:0}h2{font-size:18px}p{line-height:1.55}.subtle{color:var(--muted);font-size:14px}.badge{font-size:13px;padding:7px 11px;border:1px solid var(--line);border-radius:20px}.layout{display:grid;grid-template-columns:1.1fr 1fr;gap:20px;margin-top:20px}.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:24px;min-width:0}.launch{text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:350px}.power{width:144px;height:144px;border:8px solid #d8eadf;border-radius:50%;background:#f6fbf7;color:var(--green);font-size:54px;cursor:pointer}.power:disabled{opacity:.6;cursor:wait}.power[data-running=true]{color:#b33333;border-color:#edcccc;background:#fff7f7}.power-label{font-size:20px;font-weight:700;margin:16px 0 5px}label{display:block;font-size:14px;font-weight:600;margin:12px 0 5px}input,select{display:block;width:100%;min-height:44px;border:1px solid #aebfba;border-radius:8px;padding:10px;background:#fff;color:var(--ink)}input[type=range]{padding:0;accent-color:var(--green)}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:20px}.metric{margin:0}.metric dt{font-size:13px;color:var(--muted)}.metric dd{font-size:27px;font-weight:700;margin:8px 0 0;font-variant-numeric:tabular-nums}.metric small{font-size:12px;color:var(--muted)}.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.notice{border-left:3px solid var(--gold);padding-left:12px}details{margin-top:16px}summary{cursor:pointer;padding-block:10px}pre{font:12px ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:200px;overflow:auto}a{color:var(--green)}:focus-visible{outline:3px solid #a86b35;outline-offset:3px}[hidden]{display:none!important}footer{max-width:1080px;margin:0 auto;padding:12px 24px 24px;color:var(--muted);font-size:13px}button{min-height:44px}@media(max-width:720px){header{padding:14px;gap:10px}main{padding:16px}.layout,.grid{grid-template-columns:1fr}.launch{min-height:260px}.row{grid-template-columns:1fr}}\n</style></head><body><header><div class="brand">PointSix<span>Pool</span> <small>Zec Miner</small></div><nav aria-label="Miner navigation" role="tablist"><button role="tab" data-view="dashboard" aria-selected="true">Dashboard</button><button role="tab" data-view="devices" aria-selected="false">Devices</button><button role="tab" data-view="help" aria-selected="false">Help</button></nav></header><main><div class="heading"><h1>Your miner, at a glance</h1><span class="badge">Zcash · MICRO · 0.6% pool fee</span></div><section data-screen="dashboard"><div class="layout"><article class="card launch"><button class="power" id="power" type="button" aria-label="Start mining" data-running="false">▶</button><div class="power-label" id="power-label">Start mining</div><p id="status" role="status">Ready. Mining is off.</p><span class="subtle">Mining starts only when you press Start.</span></article><article class="card"><h2>Connect your worker</h2><label for="kind">Mining identity</label><select id="kind"><option value="wallet">Anonymous · ZEC receiving wallet</option><option value="registered">Registered PointSixPool ID</option></select><label for="identity">Wallet address or registered ID</label><input id="identity" maxlength="64" autocomplete="off" spellcheck="false" placeholder="Your public receiving address"><label for="worker">Worker name</label><input id="worker" value="Point6Miner-Linux" maxlength="32" autocomplete="off"><label for="threads">Performance · <output id="thread-label">1 CPU thread</output></label><input id="threads" type="range" min="1" max="4" value="1"><div class="row"><div><label for="hours">Run time · hours</label><input id="hours" type="number" min="1" max="24" value="6"></div><p class="subtle">Lower performance leaves more CPU capacity for other apps.</p></div></article></div><div class="grid"><dl class="card metric"><dt>Accepted shares · this run</dt><dd id="accepted">0</dd><small>Acknowledged by the pool</small></dl><dl class="card metric"><dt>Rejected shares · this run</dt><dd id="rejected">0</dd><small>Not credited</small></dl><dl class="card metric"><dt>Uncertain acknowledgements</dt><dd id="uncertain">0</dd><small>Never automatically replayed</small></dl></div><article class="card" style="margin-top:20px"><p id="counts" class="subtle">Accepted:0 · Rejected:0 · Uncertain:0</p><p class="notice">Rewards depend on eligible work and mature pool blocks. Hashrate, unpaid balance and profitability are not estimated from share counts.</p><details><summary>Recent miner messages</summary><pre id="log"></pre></details></article></section><section data-screen="devices" hidden><article class="card" style="margin-top:20px"><h2>CPU mining</h2><p id="device-info">Checking available CPU capacity…</p><p>Use the performance slider on Dashboard to select how many available CPU threads this miner may use.</p><p class="subtle">This build requires AVX2 and at least 3 GiB free memory before mining. GPU mining is not supported by this build.</p></article></section><section data-screen="help" hidden><article class="card" style="margin-top:20px"><h2>Start in three steps</h2><ol><li>Enter your ZEC receiving wallet or registered PointSixPool ID.</li><li>Name this worker and choose its CPU performance level.</li><li>Press Start. Press Stop before changing setup or closing the miner.</li></ol><p>Pool preset: <strong>zec4.pointsixpool.com:3034</strong> · MICRO.</p><p>Pool fee 0.6% · Minimum payout 0.001 ZEC. Rewards require eligible work, actual blocks, maturity and payment checks. CPU electricity can cost more than earnings.</p><p>Never enter a recovery phrase, private key, payment passphrase or wallet password.</p><a href="https://pointsixpool.com/getting-started" target="_blank" rel="noopener noreferrer">Pool setup and help ↗</a></article></section></main><footer><a href="https://pointsixpool.com" target="_blank" rel="noopener noreferrer">pointsixpool.com</a> · No automatic mining or startup service.</footer><script nonce="NONCE">\n\'use strict\';const token=location.hash.slice(1);history.replaceState(null,\'\',location.pathname);const el=id=>document.getElementById(id);let running=false,busy=false,autoApplied=false;\nfor(const tab of document.querySelectorAll(\'[data-view]\'))tab.onclick=()=>{for(const t of document.querySelectorAll(\'[data-view]\'))t.setAttribute(\'aria-selected\',String(t===tab));for(const view of document.querySelectorAll(\'[data-screen]\'))view.hidden=view.dataset.screen!==tab.dataset.view;};\nel(\'threads\').oninput=()=>el(\'thread-label\').textContent=el(\'threads\').value+\' CPU thread\'+(el(\'threads\').value===\'1\'?\'\':\'s\');\nasync function call(path,body){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);try{const r=await fetch(path,{method:body?\'POST\':\'GET\',headers:{\'X-Point6-Token\':token,\'Content-Type\':\'application/json\'},body:body?JSON.stringify(body):undefined,signal:controller.signal});const d=await r.json();if(!r.ok)throw Error(d.error||\'Request failed\');return d;}finally{clearTimeout(timer);}}\nasync function refresh(){try{const d=await call(\'/api/status\');running=d.running;el(\'threads\').max=d.max_threads;if(!autoApplied&&Number.isInteger(d.recommended_threads)){el(\'threads\').value=d.recommended_threads;autoApplied=true;}if(Number(el(\'threads\').value)>d.max_threads)el(\'threads\').value=d.max_threads;el(\'threads\').oninput();el(\'device-info\').textContent=\'CPU mining · up to \'+d.max_threads+\' available threads in this build.\';el(\'status\').textContent=d.state;el(\'device-info\').textContent+=\' Temperature: \'+(d.temperature_c==null?\'unavailable\':d.temperature_c+\' °C\')+\'; thermal control: \'+(d.thermal_control||\'unavailable\')+\'; measured CPU package power: \'+(d.efficiency?.average_watts==null?\'unavailable\':d.efficiency.average_watts.toFixed(2)+\' W\')+\'; accepted work/J: \'+(d.efficiency?.accepted_work_per_joule==null?\'collecting / unavailable\':d.efficiency.accepted_work_per_joule.toPrecision(4));for(const k of[\'accepted\',\'rejected\',\'uncertain\'])el(k).textContent=d[k];el(\'counts\').textContent=\'Accepted:\'+d.accepted+\' · Rejected:\'+d.rejected+\' · Uncertain:\'+d.uncertain;el(\'log\').textContent=d.log.join(\'\\n\');el(\'power\').dataset.running=String(running);el(\'power\').textContent=running?\'■\':\'▶\';el(\'power\').setAttribute(\'aria-label\',running?\'Stop mining\':\'Start mining\');el(\'power-label\').textContent=running?\'Stop mining\':\'Start mining\';for(const id of[\'kind\',\'identity\',\'worker\',\'threads\',\'hours\'])el(id).disabled=running;}catch(e){el(\'status\').textContent=e.name===\'AbortError\'?\'Local miner did not respond. Check that it is still open.\':e.message;}}\nel(\'power\').onclick=async()=>{if(busy)return;busy=true;el(\'power\').disabled=true;try{if(running)await call(\'/api/stop\',{});else await call(\'/api/start\',{identity:el(\'identity\').value.trim(),kind:el(\'kind\').value,worker:el(\'worker\').value.trim(),threads:Number(el(\'threads\').value),hours:Number(el(\'hours\').value)});await refresh();}catch(e){el(\'status\').textContent=e.message;}finally{busy=false;el(\'power\').disabled=false;}};refresh();setInterval(()=>{if(!busy)refresh();},2000);\n</script></body></html>\n'

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
  with LOCK:v={**STATE,'log':list(LOG),'max_threads':min(4,len(os.sched_getaffinity(0))),'recommended_threads':min(recommended_measured() or 4,recommend_threads(len(os.sched_getaffinity(0)),next(int(l.split()[1])for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')),linux_battery()))}
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
