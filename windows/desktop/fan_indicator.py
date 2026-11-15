"""Native mining connection indicator; animation performs no network or mining work."""
import math
import tkinter as tk
from tkinter import ttk

def connection_state(state):
 if state.get('running'):return 'working'if state.get('connected')is True else'connecting'
 text=state.get('state','')
 if text.startswith(('Ready.','Stopped by you.','Selected run time completed.')):return 'stopped'
 return 'attention'

class FanIndicator(ttk.Frame):
 def __init__(self,parent):
  super().__init__(parent);self.phase=0;self.mode='stopped';self.canvas=tk.Canvas(self,width=40,height=40,bg='#142033',highlightthickness=0);self.canvas.pack(side='left');self.label=ttk.Label(self,text='Stopped');self.label.pack(side='left',padx=(4,12));self.after(80,self.animate)
 def update_state(self,state):
  self.mode=connection_state(state);self.label.configure(text={'working':'Connected','connecting':'Connecting…','stopped':'Stopped','attention':'Needs attention'}[self.mode])
 def animate(self):
  colour={'working':'#17824e','connecting':'#ad740d','stopped':'#79847f','attention':'#c33d39'}[self.mode]
  if self.mode=='working':self.phase=(self.phase+.12)%(2*math.pi)
  c=self.canvas;c.delete('all');c.create_oval(2,2,38,38,outline=colour,width=2)
  shape=[(-2,-3),(-11,-7),(-11,-14),(-3,-15),(4,-9),(3,-2)]
  for i in range(4):
   a=self.phase+i*math.pi/2;points=[]
   for x,y in shape:points.extend((20+x*math.cos(a)-y*math.sin(a),20+x*math.sin(a)+y*math.cos(a)))
   c.create_polygon(points,fill='#f88316' if self.mode=='working' else colour,smooth=True)
  c.create_oval(13,13,27,27,fill=colour,outline=colour);c.create_text(20,20,text='.6',fill='white',font=('Segoe UI',8,'bold'))
  self.after(80,self.animate)
