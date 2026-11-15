"""Server installer resource choices. CPU engine remains limited to four threads."""
from decimal import Decimal,InvalidOperation

def parse_options(values):
 if not isinstance(values,dict)or set(values)-{'server_use','cpu_threads','available_ram_gb'}:raise ValueError('Invalid server performance settings.')
 use=values.get('server_use','shared');threads=values.get('cpu_threads','auto');ram=values.get('available_ram_gb','')
 if use not in ('shared','mining'):raise ValueError('Choose Shared server or Mining Server.')
 if threads not in ('auto','1','2','3','4'):raise ValueError('Choose Auto or 1–4 CPU threads.')
 if not isinstance(ram,str)or len(ram)>16:raise ValueError('Enter available RAM in GB, or leave it blank for automatic detection.')
 ram=ram.strip()
 if ram:
  try:n=Decimal(ram)
  except InvalidOperation:raise ValueError('Enter a valid available-RAM amount.')from None
  if not n.is_finite()or not Decimal('0.25')<=n<=Decimal('1048576'):raise ValueError('Available RAM must be between 0.25 and 1048576 GB.')
  ram=str(n)
 return {'server_use':use,'cpu_threads':threads,'available_ram_gb':ram}

def select_threads(values,cpus,free_kib):
 v=parse_options(values)
 if type(cpus)is not int or cpus<1 or type(free_kib)is not int or free_kib<0:raise ValueError('Server resources could not be measured.')
 # User input can only lower the budget; current host measurements win.
 if v['available_ram_gb']:free_kib=min(free_kib,int(Decimal(v['available_ram_gb'])*1024*1024))
 reserve=2*1024*1024 if v['server_use']=='shared'else 512*1024
 budget=free_kib-reserve
 ram_cap=0 if budget<1024*1024 else min(4,1+(budget-1024*1024)//(512*1024))
 cpu_cap=min(4,max(1,cpus-1))
 cap=min(cpu_cap,ram_cap)
 if cap<1:raise ValueError('Not enough available RAM with system headroom. Close unused software or add RAM, then try again.')
 if v['cpu_threads']!='auto':
  count=int(v['cpu_threads'])
  if count>cap:raise ValueError('The selected CPU setting exceeds current CPU/RAM capacity. Choose Auto or fewer threads.')
  return count
 return min(cap,max(1,cpus//4))if v['server_use']=='shared'else cap
