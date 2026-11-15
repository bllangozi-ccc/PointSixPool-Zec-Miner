"""Windows-only resource checks and parent-exit process cleanup; no mining on import."""
import ctypes
from ctypes import wintypes
import os

class MEMORYSTATUSEX(ctypes.Structure):
 _fields_=[('dwLength',wintypes.DWORD),('dwMemoryLoad',wintypes.DWORD)]+[(n,ctypes.c_ulonglong)for n in ('ullTotalPhys','ullAvailPhys','ullTotalPageFile','ullAvailPageFile','ullTotalVirtual','ullAvailVirtual','ullAvailExtendedVirtual')]
class BASIC_LIMIT(ctypes.Structure):
 _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
class IO_COUNTERS(ctypes.Structure):
 _fields_=[(n,ctypes.c_ulonglong)for n in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
class EXTENDED_LIMIT(ctypes.Structure):
 _fields_=[('BasicLimitInformation',BASIC_LIMIT),('IoInfo',IO_COUNTERS)]+[(n,ctypes.c_size_t)for n in ('ProcessMemoryLimit','JobMemoryLimit','PeakProcessMemoryUsed','PeakJobMemoryUsed')]

def kernel():
 if os.name!='nt':raise OSError('Windows is required.')
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.GetCurrentProcess.restype=wintypes.HANDLE
 k.GetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
 k.GlobalMemoryStatusEx.argtypes=[ctypes.POINTER(MEMORYSTATUSEX)]
 k.IsProcessorFeaturePresent.argtypes=[wintypes.DWORD]
 k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];k.CreateJobObjectW.restype=wintypes.HANDLE
 k.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
 k.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
 k.CloseHandle.argtypes=[wintypes.HANDLE]
 return k

def available_cpus():
 k=kernel();mask=ctypes.c_size_t();system=ctypes.c_size_t()
 if not k.GetProcessAffinityMask(k.GetCurrentProcess(),ctypes.byref(mask),ctypes.byref(system)):raise ctypes.WinError(ctypes.get_last_error())
 result=[i for i in range(ctypes.sizeof(mask)*8)if mask.value&(1<<i)]
 if not result:raise OSError('No available CPU affinity.')
 return result

def memory_status_kib():
 k=kernel();m=MEMORYSTATUSEX();m.dwLength=ctypes.sizeof(m)
 if not k.GlobalMemoryStatusEx(ctypes.byref(m)):raise ctypes.WinError(ctypes.get_last_error())
 total=m.ullTotalPhys//1024;available=m.ullAvailPhys//1024
 if not 0<=available<=total or total<=0:raise OSError('Windows returned an invalid physical RAM reading.')
 return {'total':total,'available':available}

def free_memory_kib():return memory_status_kib()['available']

def has_avx2():return bool(kernel().IsProcessorFeaturePresent(40))

class ParentExitGuard:
 """Put this UI and inherited children in a kill-on-last-handle-close job.

 Keep the handle open for this process's lifetime. Do not close it while serving:
 closing it intentionally terminates the UI and all its inherited children.
 """
 def __init__(self):
  k=kernel();h=k.CreateJobObjectW(None,None)
  if not h:raise ctypes.WinError(ctypes.get_last_error())
  limits=EXTENDED_LIMIT();limits.BasicLimitInformation.LimitFlags=0x2000
  if not k.SetInformationJobObject(h,9,ctypes.byref(limits),ctypes.sizeof(limits)):
   error=ctypes.get_last_error();k.CloseHandle(h);raise ctypes.WinError(error)
  if not k.AssignProcessToJobObject(h,k.GetCurrentProcess()):
   error=ctypes.get_last_error();k.CloseHandle(h);raise ctypes.WinError(error)
  self.handle=h
