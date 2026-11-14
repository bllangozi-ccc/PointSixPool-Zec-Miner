#!/usr/bin/env python3
"""Guided Linux server setup. Starts only after owner supplies/saves setup."""
from pathlib import Path
import argparse,os,json,sys,subprocess,signal,fcntl,stat,time
import point6miner_ui as miner
from performance_policy import recommend_threads,linux_battery
ROOT=Path(__file__).resolve().parent
CONFIG=Path.home()/'.config/pointsixpool-miner/config.json'
UNIT='pointsixpool-micro.service'
def load_config():
 st=CONFIG.lstat()
 if not stat.S_ISREG(st.st_mode)or st.st_uid!=os.getuid()or st.st_mode&0o077 or st.st_size>4096:raise ValueError('Saved miner setup has unsafe permissions.')
 v=json.loads(CONFIG.read_text());miner.options(v);return v

def save_config(v):
 miner.options(v);CONFIG.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 if CONFIG.parent.is_symlink()or CONFIG.parent.stat().st_uid!=os.getuid():raise ValueError('Unsafe setup directory.')
 tmp=CONFIG.with_name('.config-'+str(os.getpid()));fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w')as f:json.dump(v,f);f.flush();os.fsync(f.fileno())
 os.replace(tmp,CONFIG)

def systemctl(*args):return subprocess.run(['systemctl','--user',*args],check=True,timeout=20)
def install_startup():
 # systemd quoting: paths are data, never shell commands.
 def quote(s):return '"'+str(s).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
 unitdir=Path.home()/'.config/systemd/user';unitdir.mkdir(parents=True,exist_ok=True)
 text='# Managed by PointSixPool setup\n[Unit]\nDescription=PointSixPool MICRO miner (saved owner setup)\nAfter=network-online.target\nWants=network-online.target\n[Service]\nType=simple\nExecStart='+quote(sys.executable)+' -B '+quote(ROOT/'linux_start.py')+' --run\nWorkingDirectory='+quote(ROOT)+'\nRestart=on-success\nRestartSec=10\nTimeoutStopSec=20\nKillMode=control-group\nNoNewPrivileges=true\n[Install]\nWantedBy=default.target\n'
 path=unitdir/UNIT
 if path.is_symlink():raise ValueError('Startup unit path is unsafe.')
 if path.exists()and not path.read_text().startswith('# Managed by PointSixPool setup\n'):raise ValueError('An unrelated startup unit already exists; it was preserved.')
 path.write_text(text);systemctl('daemon-reload');systemctl('enable','--now',UNIT)
 linger=subprocess.run(['loginctl','show-user',str(os.getuid()),'-p','Linger','--value'],capture_output=True,text=True,timeout=5)
 if linger.returncode==0 and linger.stdout.strip()=='yes':print('Automatic start is enabled, including after reboot.')
 else:print('Automatic start is enabled for your user session. Reboot-before-login needs administrator-enabled user lingering; it has not been enabled here.')
 print('To stop: ./Start-Server --stop   To disable automatic start: ./Start-Server --disable-autostart')

def run():
 miner.verify();v=load_config();lockpath=CONFIG.with_name('running.lock');fd=os.open(lockpath,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('This saved worker is already running.')
  def stop(signum=None,frame=None):miner.stop()
  signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);miner.start(v)
  try:
   while miner.RUNNER.is_alive():miner.RUNNER.join(.5)
   with miner.LOCK:completed=miner.STATE['state']=='Selected run time completed.'
  finally:miner.stop()
  # Only an explicitly completed bounded session may be restarted by systemd.
  # Errors and uncertain acknowledgements exit nonzero and remain held.
  return 0 if completed else 2

def setup():
 miner.verify();print('PointSixPool ZEC MICRO · 0.6% pool fee\nEnter public details only. Saving these choices starts your miner. Ctrl+C cancels.')
 kind='registered'if input('Use registered pool ID instead of wallet? [y/N]: ').strip().lower()=='y'else'wallet'
 identity=input('Wallet address: 'if kind=='wallet'else'Registered pool ID: ').strip();worker=input('Worker name [Point6Miner-Linux]: ').strip()or'Point6Miner-Linux'
 cpus=len(os.sched_getaffinity(0));mem=next(int(l.split()[1])for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:'));auto=min(miner.recommended_measured() or 4,recommend_threads(cpus,mem,linux_battery()));choice=input(f'CPU threads [Auto: {auto}; maximum {min(4,cpus)}]: ').strip();threads=int(choice)if choice else auto
 region=input('Region [EU / USA / ASIA; Enter for EU]: ').strip().upper()or'EU'
 v={'kind':kind,'identity':identity,'worker':worker,'threads':threads,'hours':24,'region':region};miner.options(v)
 startup=input('Start automatically for this user after login/reboot support check? [y/N]: ').strip().lower()=='y';save_config(v)
 if startup:install_startup();return 0
 print('Starting MICRO mining. Ctrl+C stops this worker.');return run()

def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group();g.add_argument('--run',action='store_true');g.add_argument('--setup',action='store_true');g.add_argument('--enable-autostart',action='store_true');g.add_argument('--disable-autostart',action='store_true');g.add_argument('--stop',action='store_true');g.add_argument('--status',action='store_true');a=p.parse_args()
 if a.disable_autostart:systemctl('disable','--now',UNIT);return 0
 if a.stop:systemctl('stop',UNIT);return 0
 if a.status:systemctl('status',UNIT);return 0
 if a.enable_autostart:miner.verify();load_config();install_startup();return 0
 return run()if a.run or(CONFIG.exists()and not a.setup)else setup()
if __name__=='__main__':
 try:raise SystemExit(main())
 except (ValueError,OSError,subprocess.SubprocessError)as e:print('Miner stopped: '+str(e),file=sys.stderr);raise SystemExit(2)
