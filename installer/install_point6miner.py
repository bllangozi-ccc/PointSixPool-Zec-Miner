"""Root installer: verified files only; creates an unelevated mining service, never starts it."""
import os,sys,json,base64,fcntl,pathlib,subprocess,hashlib,urllib.request,tarfile,tempfile,shutil,pwd,platform,stat
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from setup_config import validate,options
from server_setup_policy import parse_options,select_threads
BASE=pathlib.Path('/opt/pointsixpool-miner');USER='pointsix-miner';HOME_DIR='/var/lib/pointsix-miner';ORIGIN='https://pointsixpool.com'
# Replaced during packaging with the exact release archive's SHA256.
ARCHIVE_SHA256='RELEASE_ARCHIVE_SHA256';ARCHIVE_URL=ORIGIN+'/static/downloads/PointSixPool-Miner-Linux.tar.gz'
def run(args):return subprocess.run(args,check=True,timeout=120,stdin=subprocess.DEVNULL)
def fetch(url,target,pin):
 if not url.startswith(ORIGIN+'/static/downloads/'):raise ValueError('Untrusted download URL')
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args):raise ValueError('Download redirect refused')
 digest=hashlib.sha256();size=0
 with urllib.request.build_opener(NoRedirect()).open(url,timeout=30)as r,open(target,'wb')as f:
  while True:
   block=r.read(1024*1024)
   if not block:break
   size+=len(block)
   if size>128*1024*1024:raise ValueError('Download too large')
   digest.update(block);f.write(block)
 if digest.hexdigest()!=pin:raise ValueError('Download verification failed; nothing installed.')
def extract(archive,target):
 with tarfile.open(archive,'r:gz')as t:
  entries=t.getmembers()
  if len(entries)>4096 or sum(x.size for x in entries)>512*1024*1024:raise ValueError('Package too large')
  for x in entries:
   p=pathlib.PurePosixPath(x.name)
   if p.is_absolute()or'..'in p.parts or not(x.isdir()or x.isfile())or x.mode&0o6000:raise ValueError('Unsafe package entry')
  target=pathlib.Path(target);target.mkdir(mode=0o700,parents=True,exist_ok=True)
  for x in entries:
   dest=target/pathlib.PurePosixPath(x.name);dest.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
   if x.isdir():dest.mkdir(mode=0o755,exist_ok=True)
   else:
    with t.extractfile(x)as src,open(dest,'xb')as out:shutil.copyfileobj(src,out)
    dest.chmod(0o755 if x.mode&0o111 else 0o644)
def atomic(path,data,mode=0o644):
 path=pathlib.Path(path)
 if path.is_symlink():raise ValueError('Existing symlink refused: '+str(path))
 fd,name=tempfile.mkstemp(prefix='.pointsix-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb')as f:f.write(data);f.flush();os.fchmod(f.fileno(),mode);os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)
def ensure_service_home(account, home=None):
 home=pathlib.Path(HOME_DIR if home is None else home)
 if home.is_symlink():raise ValueError('Service home symlink refused')
 try:st=home.lstat()
 except FileNotFoundError:
  home.mkdir(mode=0o700)
  os.chown(home,account.pw_uid,account.pw_gid)
  st=home.lstat()
 if not stat.S_ISDIR(st.st_mode)or st.st_uid!=account.pw_uid or st.st_gid!=account.pw_gid or st.st_mode&0o022:
  raise ValueError('Unsafe existing service home; stopped.')
 return home
def main():
 if os.geteuid()!=0:raise ValueError('Run installation from your root session. Mining itself runs without root.')
 if platform.system()!='Linux'or platform.machine()not in('x86_64','amd64'):raise ValueError('This download needs64-bit Linux x86_64.')
 if 'avx2'not in pathlib.Path('/proc/cpuinfo').read_text():raise ValueError('This CPU does not support AVX2.')
 if len(sys.argv)!=2:raise ValueError('Copy the complete installation command from the miner page.')
 if len(sys.argv[1])>8192:raise ValueError('Settings too large')
 raw=json.loads(base64.urlsafe_b64decode(sys.argv[1]).decode('utf8'))
 if not isinstance(raw,dict):raise ValueError('Invalid installer settings')
 performance=parse_options(raw.pop('server_options',{}));config=validate(raw)
 free_kib=next(int(line.split()[1])for line in pathlib.Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:'))
 selected_threads=select_threads(performance,len(os.sched_getaffinity(0)),free_kib)
 if not shutil.which('systemctl')or not pathlib.Path('/run/systemd/system').exists():raise ValueError('This simple installer needs a systemd Linux server. Use the advanced download instead.')
 if not shutil.which('taskset'):raise ValueError('Install util-linux first; the bootstrap normally handles this.')
 lockpath=pathlib.Path('/run/lock/pointsixpool-miner-install.lock')
 fd=os.open(lockpath,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for p in [BASE,BASE/'releases']:
   if p.is_symlink()or p.exists()and(p.stat().st_uid!=0 or p.stat().st_mode&0o022):raise ValueError('Unsafe existing install path')
   p.mkdir(parents=True,exist_ok=True)
  try:
   account=pwd.getpwnam(USER)
   if account.pw_dir!=HOME_DIR or account.pw_uid<1 or account.pw_gid==0:raise ValueError('Existing service account differs; stopped.')
  except KeyError:
   run(['useradd','--system','--create-home','--home-dir',HOME_DIR,'--shell','/usr/sbin/nologin',USER]);account=pwd.getpwnam(USER)
  unit=pathlib.Path('/etc/systemd/system/pointsixpool-miner.service')
  marker='# Managed by PointSixPool Miner installer'
  if unit.exists()and marker not in unit.read_text():raise ValueError('An unrelated service already uses this name.')
  for shortcut in ['/start-mining','/stop-mining']:
   p=pathlib.Path(shortcut)
   if p.exists()and marker not in p.read_text():raise ValueError('Existing shortcut is not ours; stopped.')
  active=subprocess.run(['systemctl','is-active','--quiet','pointsixpool-miner.service'],capture_output=True).returncode==0
  if active:raise ValueError('Stop the installed miner with /stop-mining before updating. No changes to a running miner.')
  ensure_service_home(account)
  with tempfile.TemporaryDirectory(prefix='pointsix-install-',dir=BASE)as td:
   temp=pathlib.Path(td);archive=temp/'miner.tar.gz';fetch(ARCHIVE_URL,archive,ARCHIVE_SHA256);extract(archive,temp/'expanded');roots=list((temp/'expanded').iterdir())
   if len(roots)!=1 or not roots[0].is_dir()or not(roots[0]/'Start-Server').is_file():raise ValueError('Unexpected package layout')
   release=BASE/'releases'/ARCHIVE_SHA256[:20]
   if release.exists():
    expected={str(p.relative_to(roots[0])):hashlib.sha256(p.read_bytes()).hexdigest()for p in roots[0].rglob('*')if p.is_file()}
    actual={str(p.relative_to(release)):hashlib.sha256(p.read_bytes()).hexdigest()for p in release.rglob('*')if p.is_file()and not p.is_symlink()and p.stat().st_uid==0}
    if actual!=expected:raise ValueError('Existing release differs from verified package; stopped.')
   else:shutil.move(str(roots[0]),release)
   for p in release.rglob('*'):
    if p.is_file():p.chmod(0o755 if os.access(p,os.X_OK)else 0o644)
   release.chmod(0o755)
  managed=[pathlib.Path('/etc/pointsixpool-miner/config.json'),unit,pathlib.Path('/start-mining'),pathlib.Path('/stop-mining')]
  previous={}
  for item in managed:
   if item.is_symlink():raise ValueError('Existing control-file symlink refused')
   if item.exists():
    st=item.stat()
    if st.st_uid!=0 or st.st_size>32768:raise ValueError('Unsafe existing control file')
    previous[str(item)]=(item.read_bytes(),st.st_mode&0o777,st.st_uid,st.st_gid)
  try:
   configdir=pathlib.Path('/etc/pointsixpool-miner')
   if configdir.is_symlink()or configdir.exists()and(configdir.stat().st_uid!=0 or configdir.stat().st_mode&0o022):raise ValueError('Unsafe system settings directory')
   configdir.mkdir(mode=0o750,exist_ok=True);os.chown(configdir,0,account.pw_gid);configdir.chmod(0o750)
   atomic(configdir/'config.json',json.dumps(options(config,threads=selected_threads)).encode(),0o640);os.chown(configdir/'config.json',0,account.pw_gid)
   # Service file pins the immutable release directory, so no writable current-version link is trusted.
   content=f'''{marker}
  [Unit]
  Description=PointSixPool MICRO miner
  After=network-online.target
  Wants=network-online.target
  [Service]
  Type=simple
  User={USER}
  Group={account.pw_gid}
  WorkingDirectory={release}
  Environment=POINTSIX_MINER_CONFIG=/etc/pointsixpool-miner/config.json
  ExecStart={release}/Start-Server --run
  Restart=on-success
  RestartSec=15
  KillMode=control-group
  TimeoutStopSec=20
  NoNewPrivileges=true
  PrivateTmp=true
  ProtectSystem=strict
  ProtectHome=true
  ReadWritePaths={HOME_DIR}
  UMask=0077
  MemoryMax=3G
  CPUQuota={selected_threads*100}%
  [Install]
  WantedBy=multi-user.target
  '''
   atomic(unit,content.encode())
   for name,action in [('start-mining','start'),('stop-mining','stop')]:
    script=f'#!/bin/sh\n{marker}\nset -eu\nif [ "$(id -u)" -ne 0 ]; then echo "Run this shortcut from your root session."; exit 1; fi\nsystemctl {action} pointsixpool-miner.service\nsystemctl --no-pager --full status pointsixpool-miner.service || true\n'
    atomic('/'+name,script.encode(),0o755)
   run(['systemctl','daemon-reload'])
  except BaseException:
   for item in managed:
    original=previous.get(str(item))
    if original:
     atomic(item,original[0],original[1]);os.chown(item,original[2],original[3])
    elif item.exists()and not item.is_symlink():item.unlink()
   try:run(['systemctl','daemon-reload'])
   except Exception:pass
   raise
  print('Performance: '+('Shared server'if performance['server_use']=='shared'else'Mining Server')+' · '+str(selected_threads)+' CPU thread(s). Re-run setup to change settings.');print('Installation complete. Mining is OFF.\nWallet/ID: '+config['identity']+'\nMachine: '+config['worker']+'\nRegion: '+config['region']+' (currently our EU server)\nStart: /start-mining\nStop: /stop-mining\nOptional start after reboot: systemctl enable pointsixpool-miner.service\nMining runs as '+USER+', never root.\nStats: https://pointsixpool.com/status')
if __name__=='__main__':
 try:main()
 except Exception as e:print('Installation stopped: '+str(e),file=sys.stderr);sys.exit(1)
