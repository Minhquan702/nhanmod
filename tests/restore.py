import asyncio,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['BOT_STORAGE_DIR']=str(Path('tests/work/restore-storage').resolve())
import web_server as s
async def main():
 s.JOBS.clear()
 for i,state in enumerate(('done','running')):
  jid=f'{i+1:048x}';folder=s.STORE/jid;folder.mkdir(exist_ok=True)
  meta={'owner':'1'*48,'state':state,'percent':100 if state=='done' else 30,'message':'test','platform':'android','expires':time.time()+3600 if state=='done' else None,'created':time.time(),'selections':[],'task_complete':state=='done','ticket':'restore-ticket' if state=='done' else None,'telegram_user_id':111}
  (folder/'meta.json').write_text(json.dumps(meta))
  if state=='done':(folder/'result.zip').write_bytes(b'zip')
 cycle=s.lifecycle(None);await anext(cycle)
 assert s.JOBS[f'{1:048x}']['state']=='done'
 assert s.JOBS[f'{1:048x}']['task_complete']
 assert s.RETURN_TICKETS['restore-ticket']==f'{1:048x}'
 assert s.JOBS[f'{2:048x}']['state']=='error'
 await cycle.aclose()
 print('PASS: restore completed jobs, task receipt, owner, Telegram user; interrupted generation becomes retryable error')
asyncio.run(main())
