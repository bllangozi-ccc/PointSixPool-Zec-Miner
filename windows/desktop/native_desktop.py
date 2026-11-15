"""Original PointSixPool native desktop. No mining or network calls on opening."""
import sys,os,json,re,threading,webbrowser,time
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from miner_efficiency import recommended_measured
from miner_links import portal_url
from setup_config import load as load_setup
from performance_policy import recommend_threads,windows_battery
from fan_indicator import FanIndicator
from modern_ui import theme,Header,ShareChart,MiningSignal
import miner_report

class MinerWindow:
 def __init__(self,root,backend):
  self.root=root;self.b=backend;self.busy=False;self.closing=False;self.running=False;self.last_report_error='';self.setting_auto=False;self.auto_mode=True
  root.title('PointSixPool Miner');icon_root=Path(sys._MEIPASS) if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2];self.icon=tk.PhotoImage(file=str(icon_root/'assets/pointsixpool.png'));root.iconphoto(True,self.icon);root.geometry('1000x790');root.minsize(860,700);root.configure(bg='#f3f5f4');root.protocol('WM_DELETE_WINDOW',self.close)
  theme(root);header=Header(root,self.icon);header.pack(fill='x',padx=12,pady=(10,8))
  tabs=ttk.Notebook(root);tabs.pack(fill='both',expand=True,padx=20,pady=(0,10));dash=ttk.Frame(tabs,padding=14);devices=ttk.Frame(tabs,padding=24);help_page=ttk.Frame(tabs,padding=24)
  for page,name in [(dash,'Dashboard'),(devices,'Devices'),(help_page,'Help')]:tabs.add(page,text=name)
  setup=ttk.Frame(dash);setup.pack(side='left',fill='y',padx=(0,18));live=ttk.Frame(dash);live.pack(side='left',fill='both',expand=True);setup.columnconfigure(0,weight=1);setup.columnconfigure(1,weight=1)
  self.kind=tk.StringVar(value='Wallet address');self.identity=tk.StringVar();self.worker=tk.StringVar(value='Point6Miner-Desktop');self.coin=tk.StringVar(value='ZEC');self.threads=tk.IntVar(value=1);self.hours=tk.IntVar(value=6);self.thread_label=tk.StringVar(value='Performance · 1 CPU thread')
  ttk.Label(setup,text='Add wallet address or PointSixPool ID').grid(row=0,column=0,sticky='w',pady=5);self.idtype=ttk.Combobox(setup,textvariable=self.kind,values=['Wallet address','Registered pool ID'],state='readonly',width=20);self.idtype.grid(row=0,column=1,sticky='e')
  self.address_box=ttk.Entry(setup,textvariable=self.identity);self.address_box.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(0,12))
  ttk.Label(setup,text='Add worker name').grid(row=2,column=0,sticky='w',pady=5);ttk.Label(setup,text='Choose coin').grid(row=2,column=1,sticky='w',padx=(12,0));self.worker_box=ttk.Entry(setup,textvariable=self.worker);self.worker_box.grid(row=3,column=0,sticky='ew');self.coin_box=ttk.Combobox(setup,textvariable=self.coin,values=['ZEC'],state='readonly');self.coin_box.grid(row=3,column=1,sticky='ew',padx=(12,0))
  self.region=tk.StringVar(value='EU');ttk.Label(setup,text='Region · MICRO mode').grid(row=4,column=0,sticky='w',pady=(10,0));self.region_box=ttk.Combobox(setup,textvariable=self.region,values=['EU','USA','ASIA'],state='readonly');self.region_box.grid(row=5,column=0,sticky='ew');self.region_note=tk.StringVar(value='EU · zec4.pointsixpool.com:3034 · Currently served in EU');ttk.Label(setup,textvariable=self.region_note,wraplength=235).grid(row=5,column=1,sticky='w',padx=(12,0));self.region_box.bind('<<ComboboxSelected>>',lambda event:self.select_region())
  ttk.Label(setup,textvariable=self.thread_label).grid(row=6,column=0,columnspan=2,sticky='w',pady=(16,0));self.slider=ttk.Scale(setup,from_=1,to=min(12,len(backend.available_cpus())),command=self.performance);self.slider.bind('<ButtonPress-1>',lambda e:setattr(self,'auto_mode',False));self.slider.bind('<KeyPress>',lambda e:setattr(self,'auto_mode',False));self.slider.set(1);self.slider.grid(row=7,column=0,columnspan=2,sticky='ew');self.speed_hint=None;self.slider.bind('<Enter>',self.show_speed_hint);self.slider.bind('<Leave>',self.hide_speed_hint);self.slider.bind('<FocusOut>',self.hide_speed_hint);self.auto_button=ttk.Button(setup,text='Auto · recommended',command=self.auto_performance);self.auto_button.grid(row=8,column=0,columnspan=2,sticky='e',pady=6);self.auto_performance();ttk.Label(setup,text='Stop mining to adjust performance.',style='Muted.TLabel').grid(row=9,column=0,columnspan=2,sticky='w',pady=6)
  powerrow=ttk.Frame(live);powerrow.pack(fill='x',pady=(8,12));self.power=ttk.Button(powerrow,text='▶  Start Mining',style='Primary.TButton',command=self.toggle);self.power.pack(side='left');self.status=tk.StringVar(value='Ready. Mining is off.');status_row=ttk.Frame(live);status_row.pack(fill='x');self.fan=FanIndicator(status_row);self.fan.pack(side='left');self.quick_report=ttk.Button(powerrow,text='Report error',command=self.report_error);self.quick_report.pack(side='right',padx=(6,0));self.quick_report.state(['disabled']);ttk.Button(powerrow,text='Copy diagnostics',command=self.copy_error).pack(side='right',padx=(6,0));ttk.Label(status_row,textvariable=self.status,wraplength=380,anchor='w',justify='left').pack(side='left',fill='x',expand=True)
  metrics=ttk.Frame(live,padding=(0,6));metrics.pack(fill='x');self.counts={}
  for i,(key,title)in enumerate([('accepted','Accepted shares'),('rejected','Rejected shares'),('uncertain','Uncertain shares')]):
   f=ttk.Frame(metrics,padding=(6,0));f.grid(row=i,column=0,sticky='ew',pady=0);metrics.columnconfigure(0,weight=1);ttk.Label(f,text=title,style='Muted.TLabel').pack(side='left');v=tk.StringVar(value='0');self.counts[key]=v;ttk.Label(f,textvariable=v,style='Rejected.Metric.TLabel' if key=='rejected'else'Uncertain.Metric.TLabel'if key=='uncertain'else'Metric.TLabel').pack(side='right')
  self.mining_signal=MiningSignal(live);self.mining_signal.pack(fill='x')
  self.share_chart=ShareChart(live);self.share_chart.pack(fill='x',pady=(0,10))
  ttk.Label(live,text='Rewards follow eligible work and mature blocks.',style='Muted.TLabel',wraplength=380).pack(anchor='w');self.messages=tk.Text(live,width=1,height=2,font=('Consolas',9),state='disabled',bg='#0b111c',fg='#a5b4c8',relief='flat');self.messages.pack(fill='both',expand=True,pady=(10,0))
  ttk.Label(devices,text='CPU mining',style='Heading.TLabel').pack(anchor='w');ttk.Label(devices,text=f'Available CPU threads in this build: {min(12,len(backend.available_cpus()))}\nAVX2 CPU required. Free RAM: 1 GiB for one thread; 0.5 GiB per extra thread.\nGPU mining is not supported by this build.\nFor temperature and automatic thermal protection, run LibreHardwareMonitor with CPU monitoring enabled. Some sensors require administrator permission. Keep it open while mining. If no supported CPU sensor is detected, temperature protection is not active.',wraplength=780).pack(anchor='w',pady=20);self.telemetry=tk.StringVar(value='Hardware telemetry: reading…');ttk.Label(devices,textvariable=self.telemetry,wraplength=780).pack(anchor='w',pady=10);ttk.Label(devices,text='Run time · hours').pack(anchor='w');self.duration=ttk.Spinbox(devices,from_=1,to=24,textvariable=self.hours,width=10);self.duration.pack(anchor='w',pady=8);ttk.Button(devices,text='Enable temperature readings · setup guide ↗',command=lambda:webbrowser.open('https://github.com/LibreHardwareMonitor/LibreHardwareMonitor')).pack(anchor='w',pady=8)
  ttk.Label(help_page,text='Start in three steps',style='Heading.TLabel').pack(anchor='w');ttk.Label(help_page,text='1. Add your public ZEC receiving wallet or registered pool ID.\n2. Name this worker and choose its performance.\n3. Press Start Mining. Press Stop to finish.\n\nZEC MICRO preset: zec4.pointsixpool.com:3034\nPool fee: 0.6% · Minimum payout: 0.001 ZEC\nRewards depend on actual blocks, maturity and eligible work.\nCPU electricity can cost more than earnings.\n\nNever enter private keys, wallet seeds or payment passphrases.',wraplength=780).pack(anchor='w',pady=20);ttk.Button(help_page,text='Open pool help ↗',command=lambda:webbrowser.open('https://pointsixpool.com/getting-started')).pack(anchor='w')
  ttk.Button(help_page,text='Copy miner error code',command=self.copy_error).pack(anchor='w',pady=4)
  ttk.Button(help_page,text='Troubleshoot error codes ↗',command=lambda:webbrowser.open('https://github.com/bllangozi-ccc/PointSixPool-Zec-Miner#miner-error-codes')).pack(anchor='w',pady=4)
  self.report_button=ttk.Button(help_page,text='Send error to PointSixPool',command=self.report_error);self.report_button.pack(anchor='w',pady=4);self.report_busy=False
  ttk.Label(help_page,text='Sends the error code and counters only. No wallet or full logs.',style='Muted.TLabel').pack(anchor='w')
  footer=ttk.Frame(root,padding=(16,8));footer.pack(fill='x',side='bottom',before=tabs);ttk.Button(footer,text='View my stats & earnings ↗',command=lambda:webbrowser.open(portal_url('wallet'if self.kind.get()=='Wallet address'else'registered',self.identity.get().strip()))).pack(side='left',padx=(0,8));ttk.Button(footer,text='pointsixpool.com ↗',command=lambda:webbrowser.open('https://pointsixpool.com')).pack(side='left');ttk.Label(footer,text='Mining starts only when you choose.',style='Muted.TLabel').pack(side='right');self.apply_download_setup();self.root.after(300,self.refresh)
 def error_summary(self):
  with self.b.LOCK:state=self.b.STATE.get('state','')
  code=re.search(r'P6M-E\d{3}',state)
  if not code:return 'No miner error code is available yet.'
  summary='PointSixPool Miner · Windows · '+code.group()
  exit_code=re.search(r'Engine exit (-?\d+)',state)
  if exit_code:summary+=' · engine exit '+exit_code.group(1)
  error_type=re.search(r'Engine exit -?\d+ · ([A-Za-z.]{1,80})(?:\.| ·)',state)
  if error_type:summary+=' · '+error_type.group(1)
  reason=re.search(r' · (solver-exit|solver-start|solver-affinity|solver-io|engine-error)(?=\.| ·)',state)
  if reason:summary+=' · '+reason.group(1)
  native=re.search(r' · solver exit (-?\d+)',state)
  if native:summary+=' · solver exit '+native.group(1)
  return summary+('\n'+self.last_report_error if self.last_report_error else '')
 def copy_error(self):
  self.root.clipboard_clear();self.root.clipboard_append(self.error_summary());messagebox.showinfo('Miner diagnostics','Copied the error code and engine exit status. No wallet, mining ID or credentials were included.',parent=self.root)
 def report_error(self):
  with self.b.LOCK:state=dict(self.b.STATE)
  text=state.get('state','');code=re.search(r'P6M-E\d{3}',text)
  if not code:messagebox.showinfo('Report miner error','No engine error code is available yet.',parent=self.root);return
  value={'error_code':code.group(),'version':'0.6.0-beta7','threads':self.threads.get(),'run_hours':self.hours.get(),'accepted':state['accepted'],'rejected':state['rejected'],'uncertain':state['uncertain']}
  exit_code=re.search(r'Engine exit (-?\d+)',text)
  if exit_code:value['engine_exit']=int(exit_code.group(1))
  error_type=re.search(r'Engine exit -?\d+ · ([A-Za-z.]{1,80})(?:\.| ·)',text)
  if error_type:value['error_type']=error_type.group(1)
  reason=re.search(r' · (solver-exit|solver-start|solver-affinity|solver-io|engine-error)(?=\.| ·)',text)
  if reason:value['engine_reason']=reason.group(1)
  native=re.search(r' · solver exit (-?\d+)',text)
  if native:value['solver_exit']=int(native.group(1))
  if self.report_busy:return
  self.report_busy=True;self.report_button.state(['disabled']);self.quick_report.state(['disabled'])
  def send():
   try:
    ident=miner_report.submit(value);self.root.after(0,lambda:messagebox.showinfo('Report received','Saved in Owner Reports. Reference: '+ident,parent=self.root))
   except (miner_report.ReportError,ValueError) as error:
    message=str(error);self.last_report_error=message;self.root.after(0,lambda:messagebox.showwarning('Report not confirmed',message,parent=self.root))
   finally:
    self.report_busy=False
    if not self.closing:self.root.after(0,lambda:self.report_button.state(['!disabled']))
  threading.Thread(target=send,daemon=True).start()
 def apply_download_setup(self):
  folder=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2]
  try:
   config=load_setup(folder/'point6miner-settings.json')
   if config:
    self.kind.set('Wallet address' if config['kind']=='wallet'else'Registered pool ID');self.identity.set(config['identity']);self.worker.set(config['worker']);self.region.set(config['region']);self.select_region();self.status.set('Your downloaded settings are ready. Check them, then press Start Mining.')
  except (OSError,ValueError) as e:self.status.set(str(e)+' Enter your settings below.')
 def select_region(self):
  region=self.region.get();host='zec4.pointsixpool.com' if region=='EU' else region.lower()+'.zec4.pointsixpool.com';self.region_note.set((region+' · ')+host+':3034 · Currently served in EU')
 def show_speed_hint(self,event=None):
  self.hide_speed_hint()
  text='Performance is locked while mining. Stop mining to adjust speed, then press Start Mining.' if self.running else 'Choose CPU threads before starting. Auto uses up to 4 threads. Manually choose up to 12, subject to CPU and free RAM. Lower speed leaves more capacity for other apps.'
  tip=tk.Toplevel(self.root);tip.wm_overrideredirect(True);tip.geometry(f'+{self.slider.winfo_rootx()+12}+{self.slider.winfo_rooty()+28}');ttk.Label(tip,text=text,padding=8,wraplength=400).pack();self.speed_hint=tip
 def hide_speed_hint(self,event=None):
  if self.speed_hint is not None:self.speed_hint.destroy();self.speed_hint=None
 def performance(self,value):
  n=max(1,min(12,len(self.b.available_cpus()),round(float(value))));self.threads.set(n);self.thread_label.set(('Auto'if self.auto_mode else'Manual')+f' · {n} CPU thread'+('s'if n!=1 else''))
 def auto_performance(self):
  try:
   n=min(recommended_measured() or 4,recommend_threads(len(self.b.available_cpus()),self.b.free_memory_kib(),windows_battery()));self.setting_auto=True;self.auto_mode=True;self.slider.set(n);self.performance(n)
  except (OSError,ValueError):self.setting_auto=True;self.auto_mode=True;self.slider.set(1);self.performance(1)
  finally:self.setting_auto=False
 def toggle(self):
  if self.busy:return
  self.busy=True;self.power.state(['disabled'])
  try:
   if self.running:threading.Thread(target=self.stop_worker,daemon=True).start();return
   value={'kind':'wallet'if self.kind.get()=='Wallet address'else'registered','identity':self.identity.get().strip(),'worker':self.worker.get().strip(),'threads':self.threads.get(),'hours':self.hours.get(),'region':self.region.get()};self.b.start(value)
  except Exception as e:messagebox.showerror('Check miner setup',str(e)[:250],parent=self.root)
  self.busy=False
 def stop_worker(self):
  try:self.b.stop()
  except Exception as e:
   with self.b.LOCK:self.b.STATE['state']=str(e)[:250]
  finally:self.busy=False
 def refresh(self):
  if self.closing:return
  with self.b.LOCK:s=dict(self.b.STATE);logs=list(self.b.LOG)
  try:ram=f"{self.b.free_memory_kib()/1024**2:.1f} GiB available RAM"
  except (OSError,ValueError):ram='Available RAM awaiting reading'
  total=s['hardware'].get('total_memory_kib')
  if isinstance(total,int)and total>0:ram+=f" / {total/1024**2:.1f} GiB total"
  e=s.get('efficiency',{}); temp=s.get('temperature_c'); watts=e.get('average_watts'); work=e.get('accepted_work_per_joule');self.telemetry.set(f"{ram} · CPU threads available: {s['hardware']['available_cpu_threads']} · AVX2: {s['hardware'].get('avx2')} · Temperature: {str(round(temp,1))+' °C' if temp is not None else 'No CPU sensor detected'}\nThermal control: {('Active · reduce at 75 °C, stop at 85 °C' if s.get('thermal_control') == 'normal' else 'Reduced speed · cooling' if s.get('thermal_control') == 'reduce' else 'Stopped for cooling' if s.get('thermal_control') == 'stop' else 'Not active · CPU temperature sensor required')} · Measured power: {str(round(watts,2))+' W (CPU package)' if watts is not None else 'No CPU package-power sensor detected'}\nAccepted work/J: {format(work,'.5g') if work is not None else 'Measuring · allow 60 seconds' if watts is not None else 'Requires measured CPU package power'} · Power excludes the rest of the machine.");self.running=s['running'];self.fan.update_state(s);self.status.set(s['state']);self.power.configure(text='■  Stop Mining'if self.running else'▶  Start Mining');self.power.state(['disabled']if self.busy else['!disabled'])
  for w in [self.address_box,self.worker_box,self.slider,self.duration,self.auto_button]:w.state(['disabled']if self.running or self.busy else['!disabled'])
  self.idtype.configure(state='disabled'if self.running or self.busy else'readonly');self.region_box.configure(state='disabled'if self.running or self.busy else'readonly')
  self.quick_report.state(['!disabled']if re.search(r'P6M-E\d{3}',s['state'])and not self.report_busy else['disabled'])
  self.mining_signal.set_running(s['running'])
  self.share_chart.sample(s['accepted'])
  for k,v in self.counts.items():v.set(str(s[k]))
  self.messages.configure(state='normal');self.messages.delete('1.0','end');self.messages.insert('1.0','\n'.join(logs[-3:]));self.messages.configure(state='disabled');self.root.after(500,self.refresh)
 def close(self):
  if self.closing:return
  self.hide_speed_hint();self.closing=True;self.power.state(['disabled']);self.status.set('Stopping miner before closing…')
  def finish():
   try:self.b.stop()
   finally:self.root.after(0,self.root.destroy)
  threading.Thread(target=finish,daemon=True).start()

def main():
 root=tk.Tk()
 try:
  import desktop_backend as b
  b.GUARD=b.ParentExitGuard();window=MinerWindow(root,b)
  if '--smoke-test'in sys.argv:
   def smoke():
    try:
     assert not b.STATE['running']and b.CHILD is None;
     root.geometry('860x700');root.update();root.update_idletasks()
     for control in [window.power,window.slider,window.share_chart,window.messages,window.quick_report]:
      assert control.winfo_ismapped()
      assert control.winfo_rootx()+control.winfo_width()<=root.winfo_rootx()+root.winfo_width()+2
      assert control.winfo_rooty()+control.winfo_height()<=root.winfo_rooty()+root.winfo_height()+2
     with b.LOCK:b.STATE['state']='P6M-E101 · Engine exit 2 · IOException. No complete result; stopped without replay.'
     window.refresh();assert 'disabled'not in window.quick_report.state();assert 'P6M-E101'in window.error_summary()
     with b.LOCK:b.STATE['state']='Ready. Mining is off.'
     window.refresh()
 
     if os.environ.get('POINTSIX_SMOKE_EXPECT_SETUP')=='1':assert window.worker.get()=='Desktop-CI'and window.region.get()=='ASIA'and window.identity.get()=='t1VL5XNfTPehmSxrszsSJC1hJUrYGUHbAFg'
     window.running=True;window.show_speed_hint();assert any('Stop mining to adjust speed' in str(c.cget('text')) for c in window.speed_hint.winfo_children());window.hide_speed_hint();window.running=False;assert window.power.cget('text')=='▶  Start Mining';assert window.thread_label.get().startswith('Auto');out=Path(os.environ.get('POINTSIX_SMOKE_RESULT','DESKTOP-SMOKE.PUBLIC.json'));out.write_text(json.dumps({'passed':True,'native_gui_opened':True,'mining_started':False,'python_commands_required':False,'bundled_executable':bool(getattr(sys,'frozen',False))}))
    except Exception as error:
     import traceback
     out=Path(os.environ.get('POINTSIX_SMOKE_RESULT','DESKTOP-SMOKE.PUBLIC.json'));out.write_text(json.dumps({'passed':False,'error_type':type(error).__name__,'source_lines':[frame.lineno for frame in traceback.extract_tb(error.__traceback__)],'mining_started':b.STATE['running'],'bundled_executable':bool(getattr(sys,'frozen',False)),'controls':[{'widget':str(control),'visible':bool(control.winfo_ismapped()),'right':control.winfo_rootx()+control.winfo_width()-root.winfo_rootx(),'bottom':control.winfo_rooty()+control.winfo_height()-root.winfo_rooty()}for control in [window.power,window.slider,window.share_chart,window.messages,window.quick_report]],'window':[root.winfo_width(),root.winfo_height()]}))
    finally:window.close()
   root.after(1000,smoke)
  root.mainloop()
 except Exception as e:
  if '--smoke-test'in sys.argv:
   import traceback
   Path(os.environ.get('POINTSIX_SMOKE_RESULT','DESKTOP-SMOKE.PUBLIC.json')).write_text(json.dumps({'passed':False,'error_type':type(e).__name__,'source_lines':[frame.lineno for frame in traceback.extract_tb(e.__traceback__)],'mining_started':False}))
  else:root.withdraw();messagebox.showerror('PointSixPool Zec Miner',str(e)[:250],parent=root)
  root.destroy()
if __name__=='__main__':main()
