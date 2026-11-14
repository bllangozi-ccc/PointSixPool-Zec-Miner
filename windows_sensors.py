"""Optional read-only LibreHardwareMonitor WMI adapter. No installation/elevation."""
import json, math, os, subprocess, time, ctypes
from pathlib import Path
from ctypes import wintypes
_last_failure = -1000.


def parse_sensors(rows):
    if isinstance(rows, dict): rows = [rows]
    if not isinstance(rows, list) or len(rows) > 256: raise ValueError('Invalid sensor response')
    temperatures=[];packages={}
    for row in rows:
        if not isinstance(row,dict):continue
        identifier=row.get('Identifier','');kind=row.get('SensorType');value=row.get('Value');name=row.get('Name')
        if not isinstance(identifier,str)or not identifier.startswith(('/intelcpu/','/amdcpu/')):continue
        if type(value)not in(int,float)or not math.isfinite(value):continue
        if kind=='Temperature'and 0<value<200:temperatures.append(value)
        if kind=='Power'and name in('CPU Package','Package','CPU Package Power')and 0<value<2000:packages[identifier.rsplit('/power/',1)[0]]=value
    return {'temperature_c':max(temperatures)if temperatures else None,'watts':sum(packages.values())if packages else None,
            'energy_domains':{},'power_scope':'CPU package (sampled sensor power)'if packages else None}


def read():
    global _last_failure
    unavailable={'temperature_c':None,'watts':None,'energy_domains':{},'power_scope':None}
    if os.name!='nt' or time.monotonic()-_last_failure<60:return unavailable
    script="$ErrorActionPreference='Stop'; @(Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Sensor | Where-Object {$_.Identifier -match '^/(intelcpu|amdcpu)/'} | Select-Object Identifier,SensorType,Name,Value) | ConvertTo-Json -Compress"
    exe=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    try:
        p=subprocess.run([str(exe),'-NoLogo','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
        if p.returncode or len(p.stdout)>65536:raise ValueError('Sensor provider unavailable')
        result=parse_sensors(json.loads(p.stdout))
        if result['temperature_c'] is None and result['watts'] is None:raise ValueError('No supported CPU sensors')
        return result
    except (OSError,ValueError,subprocess.SubprocessError):
        _last_failure=time.monotonic();return unavailable


class ProcessEntry(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),('priority',wintypes.LONG),('flags',wintypes.DWORD),('exe',wintypes.WCHAR*260)]


def constrain_tree(pid,cpus):
    """Set affinity only for the miner root and its current descendants."""
    k=ctypes.WinDLL('kernel32',use_last_error=True);handle=wintypes.HANDLE
    k.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];k.CreateToolhelp32Snapshot.restype=handle
    k.Process32FirstW.argtypes=[handle,ctypes.POINTER(ProcessEntry)];k.Process32NextW.argtypes=[handle,ctypes.POINTER(ProcessEntry)]
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=handle
    k.SetProcessAffinityMask.argtypes=[handle,ctypes.c_size_t];k.CloseHandle.argtypes=[handle]
    snap=k.CreateToolhelp32Snapshot(2,0)
    if snap==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    parents={};entry=ProcessEntry();entry.size=ctypes.sizeof(entry)
    try:
        more=k.Process32FirstW(snap,ctypes.byref(entry))
        while more:parents[entry.pid]=entry.parent;more=k.Process32NextW(snap,ctypes.byref(entry))
    finally:k.CloseHandle(snap)
    selected={pid}
    while True:
        more={p for p,parent in parents.items()if parent in selected}
        if more<=selected:break
        selected|=more
    mask=sum(1<<c for c in cpus)
    for p in selected:
        h=k.OpenProcess(0x0200,False,p)
        if not h:
            # A disappearing child is normal; the known live root must be controllable.
            if p==pid:raise ctypes.WinError(ctypes.get_last_error())
            continue
        try:
            if not k.SetProcessAffinityMask(h,mask):raise ctypes.WinError(ctypes.get_last_error())
        finally:k.CloseHandle(h)
