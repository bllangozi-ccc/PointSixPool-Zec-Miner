"""Original PointSixPool native desktop. No mining or network calls on opening."""
import sys,os,json,re,threading,webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from miner_efficiency import recommended_measured
from miner_links import portal_url
from performance_policy import recommend_threads,windows_battery

class MinerWindow:
 def __init__(self,root,backend):
  self.root=root;self.b=backend;self.busy=False;self.closing=False;self.running=False;self.setting_auto=False;self.auto_mode=True
  root.title('PointSixPool Miner');icon_root=Path(sys._MEIPASS) if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2];self.icon=tk.PhotoImage(file=str(icon_root/'assets/pointsixpool.png'));root.iconphoto(True,self.icon);root.geometry('920x700');root.minsize(720,600);root.configure(bg='#f3f5f4');root.protocol('WM_DELETE_WINDOW',self.close)
  style=ttk.Style(root);style.theme_use('clam');style.configure('.',font=('Segoe UI',11),background='#f3f5f4',foreground='#183831');style.configure('TNotebook.Tab',padding=(18,10));style.configure('TEntry',padding=8);style.configure('Primary.TButton',font=('Segoe UI',18,'bold'),padding=(22,15),foreground='#146b48');style.configure('Heading.TLabel',font=('Segoe UI',20,'bold'));style.configure('Metric.TLabel',font=('Segoe UI',23,'bold'));style.configure('Muted.TLabel',foreground='#536b63')
  header=ttk.Frame(root,padding=(24,16));header.pack(fill='x');ttk.Label(header,text='PointSixPool',style='Heading.TLabel').pack(side='left');ttk.Label(header,text='Zec Miner  ·  MICRO  ·  0.6% fee',style='Muted.TLabel').pack(side='right')
  tabs=ttk.Notebook(root);tabs.pack(fill='both',expand=True,padx=20,pady=(0,10));dash=ttk.Frame(tabs,padding=20);devices=ttk.Frame(tabs,padding=24);help_page=ttk.Frame(tabs,padding=24)
  for page,name in [(dash,'Dashboard'),(devices,'Devices'),(help_page,'Help')]:tabs.add(page,text=name)
  setup=ttk.Frame(dash);setup.pack(fill='x');setup.columnconfigure(0,weight=1);setup.columnconfigure(1,weight=1)
  self.kind=tk.StringVar(value='Wallet address');self.identity=tk.StringVar();self.worker=tk.StringVar(value='Point6Miner-Desktop');self.coin=tk.StringVar(value='ZEC');self.threads=tk.IntVar(value=1);self.hours=tk.IntVar(value=6);self.thread_label=tk.StringVar(value='Performance · 1 CPU thread')
  ttk.Label(setup,text='Add wallet address or PointSixPool ID').grid(row=0,column=0,sticky='w',pady=5);self.idtype=ttk.Combobox(setup,textvariable=self.kind,values=['Wallet address','Registered pool ID'],state='readonly',width=20);self.idtype.grid(row=0,column=1,sticky='e')
  self.address_box=ttk.Entry(setup,textvariable=self.identity);self.address_box.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(0,12))
  ttk.Label(setup,text='Add worker name').grid(row=2,column=0,sticky='w',pady=5);ttk.Label(setup,text='Choose coin').grid(row=2,column=1,sticky='w',padx=(12,0));self.worker_box=ttk.Entry(setup,textvariable=self.worker);self.worker_box.grid(row=3,column=0,sticky='ew');self.coin_box=ttk.Combobox(setup,textvariable=self.coin,values=['ZEC'],state='readonly');self.coin_box.grid(row=3,column=1,sticky='ew',padx=(12,0))
  self.region=tk.StringVar(value='EU');ttk.Label(setup,text='Region · MICRO mode').grid(row=4,column=0,sticky='w',pady=(10,0));self.region_box=ttk.Combobox(setup,textvariable=self.region,values=['EU','USA','ASIA'],state='readonly');self.region_box.grid(row=5,column=0,sticky='ew');self.region_note=tk.StringVar(value='EU · zec4.pointsixpool.com:3034 · Currently served in EU');ttk.Label(setup,textvariable=self.region_note,wraplength=350).grid(row=5,column=1,sticky='w',padx=(12,0));self.region_box.bind('<<ComboboxSelected>>',lambda event:self.select_region())
  ttk.Label(dash,textvariable=self.thread_label).pack(anchor='w',pady=(16,0));self.slider=ttk.Scale(dash,from_=1,to=min(4,len(backend.available_cpus())),command=self.performance);self.slider.bind('<ButtonPress-1>',lambda e:setattr(self,'auto_mode',False));self.slider.bind('<KeyPress>',lambda e:setattr(self,'auto_mode',False));self.slider.set(1);self.slider.pack(fill='x');self.auto_button=ttk.Button(dash,text='Auto · recommended',command=self.auto_performance);self.auto_button.pack(anchor='e');self.auto_performance();ttk.Label(dash,text='Auto starts conservatively. Drag to override. Stop mining before changing speed.',style='Muted.TLabel').pack(anchor='w')
  self.power=ttk.Button(dash,text='▶  Start Mining',style='Primary.TButton',command=self.toggle);self.power.pack(pady=(20,8));self.status=tk.StringVar(value='Ready. Mining is off.');ttk.Label(dash,textvariable=self.status,wraplength=780,anchor='center',justify='center').pack(fill='x')
  metrics=ttk.Frame(dash,padding=(0,20));metrics.pack(fill='x');self.counts={}
  for i,(key,title)in enumerate([('accepted','Accepted shares'),('rejected','Rejected shares'),('uncertain','Uncertain acknowledgements')]):
   metrics.columnconfigure(i,weight=1);f=ttk.Frame(metrics,padding=10);f.grid(row=0,column=i,sticky='ew');ttk.Label(f,text=title,style='Muted.TLabel').pack();v=tk.StringVar(value='0');self.counts[key]=v;ttk.Label(f,textvariable=v,style='Metric.TLabel').pack()
  ttk.Label(dash,text='Opening this app never starts mining. Rewards require eligible work and mature pool blocks.',style='Muted.TLabel',wraplength=800).pack(anchor='w');self.messages=tk.Text(dash,height=3,font=('Consolas',9),state='disabled',bg='#f9fbfa',fg='#29483b',relief='flat');self.messages.pack(fill='both',expand=True,pady=(10,0))
  ttk.Label(devices,text='CPU mining',style='Heading.TLabel').pack(anchor='w');ttk.Label(devices,text=f'Available CPU threads in this build: {min(4,len(backend.available_cpus()))}\nAVX2 CPU and at least 3 GiB free RAM required before starting.\nGPU mining is not supported by this build.\nThermal protection requires a supported CPU sensor; unavailable sensors provide no thermal control.',wraplength=780).pack(anchor='w',pady=20);self.telemetry=tk.StringVar(value='Hardware telemetry: reading…');ttk.Label(devices,textvariable=self.telemetry,wraplength=780).pack(anchor='w',pady=10);ttk.Label(devices,text='Run time · hours').pack(anchor='w');self.duration=ttk.Spinbox(devices,from_=1,to=24,textvariable=self.hours,width=10);self.duration.pack(anchor='w',pady=8);ttk.Button(devices,text='Optional Windows sensor setup ↗',command=lambda:webbrowser.open('https://github.com/LibreHardwareMonitor/LibreHardwareMonitor')).pack(anchor='w',pady=8)
  ttk.Label(help_page,text='Start in three steps',style='Heading.TLabel').pack(anchor='w');ttk.Label(help_page,text='1. Add your public ZEC receiving wallet or registered pool ID.\n2. Name this worker and choose its performance.\n3. Press Start Mining. Press Stop to finish.\n\nZEC MICRO preset: zec4.pointsixpool.com:3034\nPool fee: 0.6% · Minimum payout: 0.001 ZEC\nRewards depend on actual blocks, maturity and eligible work.\nCPU electricity can cost more than earnings.\n\nNever enter private keys, wallet seeds or payment passphrases.',wraplength=780).pack(anchor='w',pady=20);ttk.Button(help_page,text='Open pool help ↗',command=lambda:webbrowser.open('https://pointsixpool.com/getting-started')).pack(anchor='w')
  footer=ttk.Frame(root,padding=(20,8));footer.pack(fill='x');ttk.Button(footer,text='View my stats & earnings ↗',command=lambda:webbrowser.open(portal_url('wallet'if self.kind.get()=='Wallet address'else'registered',self.identity.get().strip()))).pack(side='left',padx=(0,8));ttk.Button(footer,text='pointsixpool.com ↗',command=lambda:webbrowser.open('https://pointsixpool.com')).pack(side='left');ttk.Label(footer,text='No automatic mining or background startup service.',style='Muted.TLabel').pack(side='right');self.root.after(300,self.refresh)
 def select_region(self):
  region=self.region.get();host='zec4.pointsixpool.com' if region=='EU' else region.lower()+'.zec4.pointsixpool.com';self.region_note.set((region+' · ')+host+':3034 · Currently served in EU')
 def performance(self,value):
  n=max(1,min(4,len(self.b.available_cpus()),round(float(value))));self.threads.set(n);self.thread_label.set(('Auto'if self.auto_mode else'Manual')+f' · {n} CPU thread'+('s'if n!=1 else''))
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
  e=s.get('efficiency',{}); temp=s.get('temperature_c'); watts=e.get('average_watts'); work=e.get('accepted_work_per_joule');self.telemetry.set(f"CPU threads available: {s['hardware']['available_cpu_threads']} · AVX2: {s['hardware'].get('avx2')} · Temperature: {str(round(temp,1))+' °C' if temp is not None else 'unavailable'}\nThermal control: {s.get('thermal_control','unavailable')} · Measured power: {str(round(watts,2))+' W (CPU package)' if watts is not None else 'unavailable'}\nAccepted work/J: {format(work,'.5g') if work is not None else 'collecting / unavailable'} · Power excludes the rest of the machine.");self.running=s['running'];self.status.set(s['state']);self.power.configure(text='■  Stop Mining'if self.running else'▶  Start Mining');self.power.state(['disabled']if self.busy else['!disabled'])
  for w in [self.address_box,self.worker_box,self.slider,self.duration,self.auto_button]:w.state(['disabled']if self.running or self.busy else['!disabled'])
  self.idtype.configure(state='disabled'if self.running or self.busy else'readonly');self.region_box.configure(state='disabled'if self.running or self.busy else'readonly')
  for k,v in self.counts.items():v.set(str(s[k]))
  self.messages.configure(state='normal');self.messages.delete('1.0','end');self.messages.insert('1.0','\n'.join(logs[-3:]));self.messages.configure(state='disabled');self.root.after(500,self.refresh)
 def close(self):
  if self.closing:return
  self.closing=True;self.power.state(['disabled']);self.status.set('Stopping miner before closing…')
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
    assert not b.STATE['running']and b.CHILD is None;assert window.power.cget('text')=='▶  Start Mining';assert window.thread_label.get().startswith('Auto');out=Path(os.environ.get('POINTSIX_SMOKE_RESULT','DESKTOP-SMOKE.PUBLIC.json'));out.write_text(json.dumps({'passed':True,'native_gui_opened':True,'mining_started':False,'python_commands_required':False,'bundled_executable':bool(getattr(sys,'frozen',False))}));window.close()
   root.after(1000,smoke)
  root.mainloop()
 except Exception as e:root.withdraw();messagebox.showerror('PointSixPool Zec Miner',str(e)[:250],parent=root);root.destroy()
if __name__=='__main__':main()
