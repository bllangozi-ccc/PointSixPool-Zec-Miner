from pathlib import Path
import shutil,hashlib,re,json,tarfile
r=Path(__file__).resolve().parents[1];out=r/'linux-candidate';out.mkdir(exist_ok=True)
for n in ['point6miner_ui.py','performance_policy.py','miner_efficiency.py','miner_links.py','linux_start.py','Start-Server','START-HERE.md','NOTICE.md','SECURITY.md','Start-Desktop','HELP.txt']:
 shutil.copy2(r/n,out/n)
(out/'Start-Server').chmod(0o755);(out/'Start-Desktop').chmod(0o755)
for n in ['licenses','source','assets']:
 shutil.copytree(r/n,out/n,dirs_exist_ok=True,ignore=shutil.ignore_patterns('bin','obj'))
# CI publishes managed files into linux-candidate before this script.
names=['point6miner-equihash']+[str(p.relative_to(out)) for p in sorted((out/'backend').rglob('*')) if p.is_file()]
pins={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in names}
p=out/'point6miner_ui.py';s=p.read_text();s=re.sub(r'^EXPECTED=.*$', 'EXPECTED='+repr(pins),s,count=1,flags=re.M);p.write_text(s)
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n'for p in sorted(out.rglob('*'))if p.is_file()and p.name!='SHA256SUMS'))
with tarfile.open(r/'PointSixPool-Zec-Miner-linux-x64-candidate.tar.gz','w:gz')as t:t.add(out,arcname='PointSixPool-Zec-Miner-linux-x64')
print(json.dumps({'linux_candidate_packaged':True,'no_mining_executed':True}))
