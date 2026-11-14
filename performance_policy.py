"""Conservative initial CPU allocation. Not thermal or battery-life control."""
def recommend_threads(available,free_kib,on_battery=None):
 if type(available)is not int or available<1:raise ValueError('CPU availability is unknown.')
 if type(free_kib)is not int or free_kib<0:raise ValueError('Free memory is unknown.')
 cap=min(4,available)
 if on_battery is not False or free_kib<4*1024*1024:return 1
 return min(cap,max(1,available//4))

def windows_battery():
 import ctypes
 from ctypes import wintypes
 class Power(ctypes.Structure):
  _fields_=[('ac',wintypes.BYTE),('flags',wintypes.BYTE),('percent',wintypes.BYTE),('reserved',wintypes.BYTE),('life',wintypes.DWORD),('full',wintypes.DWORD)]
 try:
  p=Power();k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetSystemPowerStatus.argtypes=[ctypes.POINTER(Power)];k.GetSystemPowerStatus.restype=wintypes.BOOL
  if not k.GetSystemPowerStatus(ctypes.byref(p)):return None
  return True if p.ac==0 else False if p.ac==1 else None
 except (OSError,AttributeError):return None

def linux_battery():
 from pathlib import Path
 try:
  supplies=list(Path('/sys/class/power_supply').iterdir())
  if not supplies:return False
  batteries=[p for p in supplies if(p/'type').read_text().strip()=='Battery']
  if not batteries:return False
  states=[(p/'status').read_text().strip()for p in batteries]
  if any(s=='Discharging'for s in states):return True
  return False if all(s in('Charging','Full','Not charging')for s in states)else None
 except (OSError,ValueError):return None
