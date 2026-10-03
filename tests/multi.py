from pathlib import Path
import json,subprocess,sys,zipfile
root=Path(__file__).resolve().parents[1];cat=json.loads((root/'web_catalog.json').read_text())
selected=[]
for hero,skins in cat.items():
 name,sid=next(iter(skins.items()));selected.append({'tuong':hero,'skin':name,'id':sid})
 if len(selected)==15:break
job=Path('tests/work/gen15').resolve();job.mkdir(parents=True,exist_ok=True)
for name in ('Data','Resources_1'):
 if not (job/name).exists():(job/name).symlink_to(root/name,target_is_directory=True)
(job/'request.json').write_text(json.dumps({'selections':selected,'platform':'both','bright':True,'cosmetics':True}))
with (job/'worker.log').open('w') as f:r=subprocess.run([sys.executable,str(root/'web_worker.py'),str(job)],stdout=f,stderr=f,timeout=240)
if r.returncode:print((job/'worker.log').read_text()[-4000:]);raise SystemExit(1)
with zipfile.ZipFile(job/'result.zip') as z:
 assert not z.testzip();assert len(z.read('DanhSáchSkin.txt').decode().splitlines())==15
print('PASS: 15 heroes, both platforms, bright + cosmetics, CRC, skin list; size', (job/'result.zip').stat().st_size)
