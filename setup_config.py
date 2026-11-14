"""Public mining settings only. Never stores login tokens, passwords or keys."""
import json,re,hashlib
from pathlib import Path
REGIONS=('EU','USA','ASIA')
def validate(v):
 if not isinstance(v,dict)or set(v)!={'schema','coin','mode','kind','identity','worker','region'}:raise ValueError('Invalid miner settings file.')
 if type(v['schema'])is not int or v['schema']!=1 or v['coin']!='ZEC'or v['mode']!='MICRO'or v['region']not in REGIONS:raise ValueError('Unsupported coin, mode or region.')
 if not isinstance(v['worker'],str)or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}',v['worker']):raise ValueError('Use a simple machine name, up to32 letters, numbers, underscores or hyphens.')
 a=v['identity']
 if not isinstance(a,str):raise ValueError('Enter a public receiving wallet or registered mining ID.')
 if v['kind']=='registered':
  if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{2,63}',a):raise ValueError('Invalid registered mining ID.')
 elif v['kind']=='wallet':
  alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
  if not 30<=len(a)<=40 or any(c not in alphabet for c in a):raise ValueError('Enter a transparent ZEC mainnet wallet address.')
  n=0
  for c in a:n=n*58+alphabet.index(c)
  raw=b'\0'*(len(a)-len(a.lstrip('1')))+n.to_bytes((n.bit_length()+7)//8,'big')
  if len(raw)!=26 or raw[:2]not in(b'\x1c\xb8',b'\x1c\xbd')or hashlib.sha256(hashlib.sha256(raw[:22]).digest()).digest()[:4]!=raw[22:]:raise ValueError('The ZEC wallet address checksum does not match.')
 else:raise ValueError('Unknown mining identity type.')
 return dict(v)
def load(path):
 p=Path(path)
 if not p.exists():return None
 if p.is_symlink()or not p.is_file()or p.stat().st_size>4096:raise ValueError('Unsafe miner settings file.')
 return validate(json.loads(p.read_text(encoding='utf-8-sig')))
def options(v,threads=1,hours=24):
 v=validate(v);return {k:v[k]for k in ('kind','identity','worker','region')}|{'threads':threads,'hours':hours}
