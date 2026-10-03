"""Checks new admin settings, default password, image mapping and task counters."""
import asyncio,os,json,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['BOT_STORAGE_DIR']=tempfile.mkdtemp(prefix='gallery-admin-');os.environ.pop('BOT_ADMIN_PASSWORD',None)
import web_server as s
from aiohttp.test_utils import TestClient,TestServer
async def main():
 app=s.make_app();app.cleanup_ctx.clear();c=TestClient(TestServer(app));await c.start_server()
 try:
  assert (await c.get('/admin')).status==200
  assert (await c.get('/admin/')).status==200
  assert (await c.get('/api/admin/notice/site')).status==401
  assert (await c.post('/api/admin/notice/site',json={'name':'X','subtitle':'','guide':''})).status==401
  assert (await c.post('/api/admin/notice/login',json={'password':'wrong'})).status==401
  assert (await c.post('/api/admin/notice/login',json={'password':'177207'})).status==200
  assert (await c.post('/api/admin/notice/site',json={'name':'','subtitle':'','guide':''})).status==400
  value={'name':'TD MOD TEST','subtitle':'MOD SKIN AOV','guide':'Dòng 1\nDòng 2'}
  assert (await c.post('/api/admin/notice/site',json=value)).status==200
  assert await (await c.get('/api/site')).json()==value
  assert json.loads((s.STORE/'bot_site.json').read_text())==value
  stats=await (await c.get('/api/admin/notice/stats')).json()
  assert all(k in stats['total'] for k in ('created','done','error','task_started','task_done','download','visitors'))
  for name,row in s.IMAGES['heroes'].items():
   assert name in s.CAT
   if row['icon'].startswith('/assets/'):assert (s.ROOT/row['icon'].lstrip('/')).is_file()
  ids={sid for skins in s.CAT.values() for sid in skins.values()}
  assert set(s.IMAGES['skins']).issubset(ids)
  for sid,row in s.IMAGES['skins'].items():
   for k in ('icon','splash'):
    if row.get(k,'').startswith('/assets/'):assert (s.ROOT/row[k].lstrip('/')).is_file()
  missing=next((sid for sid in ids if sid not in s.IMAGES['skins']),None)
  if missing:assert s.skin_summary('missing',missing)['icon']==s.icon(missing)
  await c.post('/api/admin/notice/logout',json={})
  assert (await c.get('/api/admin/notice/site')).status==401
  print('PASS: /admin, default password, protected settings, persistence, task counters, image IDs and fallback')
 finally:await c.close()
asyncio.run(main())
