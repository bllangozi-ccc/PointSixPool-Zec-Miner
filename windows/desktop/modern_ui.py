"""Native dark theme and recorded-share chart. No mining, network or invented data."""
import time
import tkinter as tk
from tkinter import ttk
BG='#0b111c';PANEL='#142033';TEXT='#eef3fa';MUTED='#a5b4c8';ORANGE='#ff972f';GREEN='#51d89c'
def glossy(root,top,bottom,edge,width=120,height=40,radius=9):
 image=tk.PhotoImage(master=root,width=width,height=height)
 def rgb(colour):return tuple(int(colour[i:i+2],16)for i in (1,3,5))
 upper,lower=rgb(top),rgb(bottom)
 for y in range(height):
  inset=0
  if y<radius:inset=round(radius-(max(0,radius*radius-(radius-y)**2))**.5)
  elif y>=height-radius:inset=round(radius-(max(0,radius*radius-(y-(height-radius-1))**2))**.5)
  amount=y/max(1,height-1);base=tuple(round(a*(1-amount)+b*amount)for a,b in zip(upper,lower))
  if y==height//2:base=lower
  colour='#%02x%02x%02x'%base;left,right=inset,width-inset
  if left<right:image.put(edge,to=(left,y,right,y+1))
  if left+1<right-1 and y not in (0,height-1):image.put(colour,to=(left+1,y,right-1,y+1))
 return image

def chevrons(root):
 image=tk.PhotoImage(master=root,width=26,height=24)
 for y in range(2,22):
  point=10-abs(y-11.5)
  for shift in (0,8):
   for x in range(26):
    if shift+point*.7<=x<shift+point*.7+4:image.put(ORANGE,to=(x,y))
 return image

def theme(root):
 root.configure(bg=BG);s=ttk.Style(root);s.theme_use('clam')
 s.configure('.',font=('Segoe UI',10),background=PANEL,foreground=TEXT)
 s.configure('TFrame',background=PANEL,borderwidth=0,lightcolor=PANEL,darkcolor=PANEL,bordercolor=PANEL);s.configure('TLabel',background=PANEL,foreground=TEXT)
 s.configure('TNotebook',background=BG,borderwidth=0,lightcolor=BG,darkcolor=BG,bordercolor=BG);s.configure('TNotebook.Tab',background=BG,foreground=MUTED,padding=(18,9),borderwidth=0)
 s.map('TNotebook.Tab',background=[('selected',PANEL)],foreground=[('selected',ORANGE)])
 s.configure('TButton',padding=(12,7),background='#263951',foreground=TEXT,borderwidth=1,bordercolor='#3d516b',focuscolor=ORANGE)
 s.map('TButton',background=[('active','#344e6c'),('disabled','#1c293b')],foreground=[('disabled','#8190a5')])
 s.configure('Primary.TButton',font=('Segoe UI',14,'bold'),padding=(22,10),background='#147d5a',foreground='white',bordercolor='#49d5a0')
 s.map('Primary.TButton',background=[('active','#19946b'),('disabled','#28443d')])
 for name in ['TEntry','TCombobox','TSpinbox']:
  s.configure(name,fieldbackground=BG,background='#273b55',foreground=TEXT,bordercolor='#3d516b',lightcolor='#3d516b',darkcolor='#3d516b',padding=6,arrowcolor=ORANGE,insertcolor=TEXT)
  s.map(name,fieldbackground=[('readonly',BG),('disabled','#1a2636')],foreground=[('readonly',TEXT),('disabled','#8293a9')])
 s.configure('TScale',background=PANEL,troughcolor=BG,sliderlength=24)
 s.configure('Heading.TLabel',font=('Segoe UI',20,'bold'),foreground=TEXT)
 s.configure('Metric.TLabel',font=('Segoe UI',21,'bold'),foreground=GREEN)
 s.configure('Rejected.Metric.TLabel',foreground=ORANGE);s.configure('Uncertain.Metric.TLabel',foreground='#ff6f7c')
 s.configure('Muted.TLabel',foreground=MUTED)
 root.option_add('*TCombobox*Listbox.background',BG);root.option_add('*TCombobox*Listbox.foreground',TEXT);root.option_add('*TCombobox*Listbox.selectBackground','#344e6c')
 assets=[glossy(root,'#41464e','#111821','#697b8f'),glossy(root,'#565747','#181e25',ORANGE),glossy(root,'#27303c','#151d28','#354456'),glossy(root,'#46584e','#10221b','#6ddaa4'),chevrons(root)]
 root._point6_theme_assets=assets
 s.element_create('Point6.Gloss','image',assets[0],('disabled',assets[2]),('active',assets[1]),border=9,sticky='nswe')
 s.element_create('Point6.PrimaryGloss','image',assets[3],('disabled',assets[2]),('active',assets[1]),border=9,sticky='nswe')
 s.element_create('Point6.Chevron','image',assets[4],sticky='e')
 s.layout('TButton',[('Point6.Gloss',{'sticky':'nswe','children':[('Button.padding',{'sticky':'nswe','children':[('Button.label',{'sticky':'nswe'})]})]})])
 s.layout('Primary.TButton',[('Point6.PrimaryGloss',{'sticky':'nswe','children':[('Button.padding',{'sticky':'nswe','children':[('Point6.Chevron',{'side':'right','sticky':'e'}),('Button.label',{'sticky':'nswe'})]})]})])
 s.configure('Primary.TButton',font=('Segoe UI',12,'bold'),padding=(12,9))
 return s
class Header(tk.Canvas):
 def __init__(self,parent,icon=None):
  self.icon=icon.subsample(max(1,icon.width()//36)) if icon is not None else None
  super().__init__(parent,height=72,highlightthickness=0,bg=BG);self.bind('<Configure>',self.draw)
 def draw(self,event=None):
  self.delete('all');w=max(1,self.winfo_width())
  for x in range(0,w,8):
   t=x/w;rgb=(int(20+12*t),int(32+13*t),int(51+17*t));colour='#%02x%02x%02x'%rgb;self.create_rectangle(x,0,x+8,72,fill=colour,outline=colour)
  self.create_line(0,71,w,71,fill='#3d516b');self.create_rectangle(20,21,24,51,fill=ORANGE,outline=ORANGE)
  if self.icon:self.create_image(34,36,image=self.icon)
  self.create_text(65,28,text='PointSixPool Miner',anchor='w',fill=TEXT,font=('Segoe UI',21,'bold'))
  self.create_text(66,52,text='ZCASH MAINNET · CPU MINING',anchor='w',fill=MUTED,font=('Segoe UI',9))
  self.create_text(w-24,29,text='ZEC  /  MICRO',anchor='e',fill=GREEN,font=('Segoe UI',12,'bold'));self.create_text(w-24,51,text='0.6% pool fee',anchor='e',fill=ORANGE,font=('Segoe UI',10))
class ShareChart(tk.Canvas):
 def __init__(self,parent):
  super().__init__(parent,width=1,height=92,background=BG,highlightthickness=1,highlightbackground='#304159');self.points=[];self.last=None;self.bind('<Configure>',lambda e:self.draw())
 def sample(self,count):
  if type(count)is not int or count<0:return
  now=time.monotonic()
  if self.last is not None and count<self.last:self.points=[]
  self.last=count;self.points.append((now,count));self.points=[p for p in self.points if now-p[0]<=120];self.draw()
 def draw(self):
  self.delete('all');w=max(120,self.winfo_width());h=92
  self.create_text(12,13,text='ACCEPTED SHARES · LAST 2 MIN',anchor='w',fill=MUTED,font=('Segoe UI',8,'bold'))
  if len(self.points)<2:
   self.create_text(12,52,text='Waiting for recorded samples',anchor='w',fill=MUTED,font=('Segoe UI',10));return
  left,right,top,bottom=42,w-14,28,72;lo=min(v for _,v in self.points);hi=max(lo+1,max(v for _,v in self.points));start=self.points[0][0];duration=max(1,self.points[-1][0]-start)
  for value,y in [(hi,top),(lo,bottom)]:
   self.create_line(left,y,right,y,fill='#25354a');self.create_text(left-7,y,text=str(value),anchor='e',fill=MUTED,font=('Segoe UI',8))
  xy=[]
  for t,v in self.points:xy.extend((left+(t-start)/duration*(right-left),bottom-(v-lo)/(hi-lo)*(bottom-top)))
  if len(xy)>=4:self.create_polygon(left,bottom,*xy,right,bottom,fill='#133e3d',outline='');self.create_line(*xy,fill=GREEN,width=2)
  self.create_text(left,84,text='−'+str(int(duration))+'s',anchor='w',fill=MUTED,font=('Segoe UI',8));self.create_text(right,84,text='now',anchor='e',fill=MUTED,font=('Segoe UI',8))

class MiningSignal(tk.Canvas):
 """Decorative route only; motion follows the local mining running state."""
 def __init__(self,parent):
  super().__init__(parent,width=1,height=38,bg=PANEL,highlightthickness=0)
  self.running=False;self.phase=0.;self.last=time.monotonic();self.bind('<Configure>',lambda event:self.draw());self.after(40,self.tick)
 def set_running(self,value):
  self.running=bool(value)
 def tick(self):
  now=time.monotonic()
  if self.running:self.phase=(self.phase+min(.1,now-self.last)/5)%1
  self.last=now;self.draw();self.after(40,self.tick)
 def draw(self):
  self.delete('all');w=max(160,self.winfo_width());xs=[18+(w-36)*i/3 for i in range(4)];y=17
  self.create_line(xs[0],y,xs[-1],y,fill='#34465c',width=2)
  # Machine: fixed housing, fan hub. Pool: six connected nodes. Block: cube. Network: peers.
  x=xs[0];self.create_rectangle(x-11,y-11,x+11,y+11,outline=MUTED,width=2);self.create_oval(x-6,y-6,x+6,y+6,outline=ORANGE,width=2)
  import math
  x=xs[1]
  for i in range(6):
   a=i*math.pi/3;b=(i+1)*math.pi/3
   self.create_line(x+10*math.cos(a),y+10*math.sin(a),x+10*math.cos(b),y+10*math.sin(b),fill=ORANGE)
   self.create_oval(x+10*math.cos(a)-2,y+10*math.sin(a)-2,x+10*math.cos(a)+2,y+10*math.sin(a)+2,fill=ORANGE,outline='')
  self.create_oval(x-3,y-3,x+3,y+3,fill=GREEN,outline='')
  x=xs[2];self.create_polygon(x,y-12,x+10,y-6,x+10,y+6,x,y+12,x-10,y+6,x-10,y-6,outline=MUTED,fill=PANEL,width=2);self.create_line(x-10,y-6,x,y,x+10,y-6,fill=MUTED);self.create_line(x,y,x,y+12,fill=MUTED)
  x=xs[3]
  for dx,dy in [(-9,-8),(9,-8),(0,10)]:
   self.create_line(x,y,x+dx,y+dy,fill=MUTED);self.create_oval(x+dx-3,y+dy-3,x+dx+3,y+dy+3,fill=ORANGE,outline='')
  self.create_oval(x-3,y-3,x+3,y+3,fill=GREEN,outline='')
  if self.running:
   distance=self.phase*2;position=distance if distance<=1 else 2-distance
   x=xs[0]+(xs[-1]-xs[0])*position
   self.create_oval(x-6,y-6,x+6,y+6,fill='#274f47',outline='');self.create_oval(x-3,y-3,x+3,y+3,fill=GREEN,outline='')
