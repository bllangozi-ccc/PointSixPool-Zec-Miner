"""Public dashboard links; no balances or ownership claims."""
import hashlib,re

def portal_url(kind,identity):
 if kind=='registered':return 'https://pointsixpool.com/dashboard#mining'
 if kind!='wallet' or not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9]{30,40}',identity):return 'https://pointsixpool.com/status'
 return 'https://pointsixpool.com/status#mining=workers&miner='+hashlib.sha256(identity.encode('ascii')).hexdigest()
