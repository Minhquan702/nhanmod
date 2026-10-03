import json,subprocess,sys,zipfile,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];base=Path(__file__).resolve().parent/'work'
cat=json.loads((root/'web_catalog.json').read_text());features=json.loads((root/'skin_features.json').read_text())
featured=next(({'tuong':h,'skin':n,'id':sid} for h,skins in cat.items() for n,sid in skins.items() if sid in features and features[sid]),None)
print('Featured test:',featured,flush=True)
base.mkdir(parents=True,exist_ok=True)
rows=[]
for i,(platform,bright,cosmetics) in enumerate([('android',False,False),('ios',True,True),('both',False,True)]):
 job=base/f'gen{i}';job.mkdir(parents=True,exist_ok=True)
 for name in ('Data','Resources_1'):
  if not (job/name).exists():(job/name).symlink_to(root/name,target_is_directory=True)
 data={'selections':[featured],'platform':platform,'bright':bright,'cosmetics':cosmetics}
 (job/'request.json').write_text(json.dumps(data))
 with (job/'worker.log').open('w') as f:r=subprocess.run([sys.executable,str(root/'web_worker.py'),str(job)],stdout=f,stderr=f,timeout=180)
 if r.returncode:
  print((job/'worker.log').read_text()[-6000:]);raise SystemExit(r.returncode)
 with zipfile.ZipFile(job/'result.zip') as z:
  assert not z.testzip();names=z.namelist()
  assert any('HeroInfoLua.pkg.bytes' in n for n in names) or platform=='both'
  if platform=='android':assert not any(n.startswith('Resources/') or n=='iOS.zip' for n in names)
  if platform=='ios':assert all(not n.startswith('com.garena') for n in names)
  if platform=='both':assert 'iOS.zip' in names
  rows.append({'platform':platform,'bright':bright,'cosmetics':cosmetics,'size':(job/'result.zip').stat().st_size,'entries':len(names),'crc':'PASS'})
 print('PASS',rows[-1],flush=True)
(base/'generation_results.json').write_text(json.dumps(rows,indent=2))
