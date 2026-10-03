import asyncio,hashlib,hmac,json,time,sys,tempfile,os
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['BOT_STORAGE_DIR']=str(Path('tests/work/api-storage').resolve());os.environ['BOT_TOKEN']='123456:test';os.environ['BOT_PUBLIC_URL']='https://bot.example.test';os.environ['BOT_ADMIN_PASSWORD']='admin-test'
import web_server as s
from telegram_auth import validate_init_data
from aiohttp.test_utils import TestClient,TestServer
from aiohttp import web

def auth(uid,date=None):
 d={'auth_date':str(int(date or time.time())),'user':json.dumps({'id':uid,'first_name':'Test'})}
 secret=hmac.new(b'WebAppData',os.environ['BOT_TOKEN'].encode(),hashlib.sha256).digest()
 d['hash']=hmac.new(secret,'\n'.join(f'{k}={v}' for k,v in sorted(d.items())).encode(),hashlib.sha256).hexdigest()
 return urlencode(d)
async def main():
 s.JOBS.clear()
 app=s.make_app();app.cleanup_ctx.clear() # Keep test jobs queued; no processing during HTTP assertions.
 a=TestClient(TestServer(app));b=TestClient(TestServer(app));await a.start_server();await b.start_server()
 ha={'X-Telegram-Init-Data':auth(111)};hb={'X-Telegram-Init-Data':auth(222)}
 assert (await a.get('/api/jobs')).status==401
 assert (await a.get('/api/me',headers={'X-Telegram-Init-Data':auth(111,time.time()-90000)})).status==401
 assert (await a.get('/api/me',headers=ha)).status==200
 hero,skins=next(iter(s.CAT.items()));skin,sid=next(iter(skins.items()));selection={'tuong':hero,'skin':skin,'id':sid}
 data={'selections':[selection],'platform':'android','bright':True,'cosmetics':True}
 bad=dict(data,selections=[dict(selection,id='99999')]);assert (await a.post('/api/jobs',json=bad,headers=ha)).status==400
 assert (await a.post('/api/jobs',json=dict(data,selections=[selection]*16),headers=ha)).status==400
 r=await a.post('/api/jobs',json=data,headers=ha);assert r.status==202; jid=(await r.json())['id']
 assert (await b.get('/api/jobs/'+jid,headers=hb)).status==404
 assert (await a.post('/api/jobs',json=data,headers=ha)).status==429
 assert len((await (await a.get('/api/jobs',headers=ha)).json())['jobs'])==1
 assert not (await (await b.get('/api/jobs',headers=hb)).json())['jobs']
 job=s.JOBS[jid];job.update(state='done',percent=100,expires=time.time()+3600)
 (job['folder']/'result.zip').write_bytes(b'test-result')
 assert (await a.get('/api/jobs/'+jid+'/download',headers=ha)).status==403
 assert (await a.post('/api/jobs/'+jid+'/download-link',headers=ha)).status==403
 async def short(url):return 'https://short.example.test/test'
 s.create_short_link=short
 r=await a.post('/api/jobs/'+jid+'/task',headers=ha);assert r.status==200
 ticket=job['ticket'];assert (await a.get('/task/complete/wrong')).status==404
 assert (await a.get('/task/complete/'+ticket,allow_redirects=False)).status==303
 assert job['task_complete']
 link=await (await a.post('/api/jobs/'+jid+'/download-link',headers=ha)).json()
 token=job['download_token'];r=await b.get('/file/'+token);assert r.status==200;assert await r.read()==b'test-result'
 assert (await a.get('/api/admin/notice/stats')).status==401
 assert (await a.post('/api/admin/notice/login',json={'password':'admin-test'})).status==200
 assert (await a.get('/api/admin/notice/stats')).status==200
 from aiohttp import FormData
 import io,wave
 stream=io.BytesIO()
 with wave.open(stream,'wb') as wav:
  wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(8000);wav.writeframes(b'\0\0'*800)
 form=FormData();form.add_field('file',stream.getvalue(),filename='test.wav',content_type='audio/wav')
 assert (await a.post('/api/admin/notice/music/upload',data=form)).status==200
 music=await (await a.get('/api/music')).json();assert music['enabled'] and music['url']
 assert (await b.get(music['url'])).status==200
 assert (await a.post('/api/admin/notice/music',json={'enabled':False,'title':'Test music'})).status==200
 assert not (await (await a.get('/api/music')).json())['enabled']
 from PIL import Image
 image=io.BytesIO();Image.new('RGB',(2,2),'red').save(image,format='PNG')
 form=FormData();form.add_field('file',image.getvalue(),filename='test.png',content_type='image/png')
 response=await a.post('/api/admin/notice/upload',data=form);assert response.status==200
 media=await response.json();assert (await b.get(media['url'])).status==200
 assert (await a.post('/api/admin/notice',json={'enabled':True,'title':'Test','html':'<script>bad()</script><p>Hello</p>'})).status==200
 n=await (await a.get('/api/notice')).json();assert '<script' not in n['html']
 job['expires']=time.time()-1;assert (await b.get('/file/'+token)).status==410
 s.save_job(jid);saved=json.loads((job['folder']/'meta.json').read_text());assert saved['telegram_user_id']==111 and saved['task_complete']
 await a.close();await b.close()
 print('PASS: Telegram signature/expiry, ownership, limits, queue, task gate, external download, admin authorization, HTML sanitization, expired file, persistent metadata')
asyncio.run(main())
