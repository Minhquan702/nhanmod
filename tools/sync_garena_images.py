"""Refresh presentation images only. Never modifies mod IDs/resources."""
import asyncio,aiohttp,concurrent.futures,html,io,json,re,unicodedata,urllib.request
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BASE='https://lienquan.garena.vn/hoc-vien/tuong-skin/'
def norm(s):return re.sub(r'[^a-z0-9]','', ''.join(c for c in unicodedata.normalize('NFD',s.casefold().replace('đ','d')) if not unicodedata.combining(c)))
def fetch(url):
 for i in range(3):
  try:return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25).read()
  except Exception:
   if i==2:raise

def attrs(s):return dict(re.findall(r'([\w-]+)="([^"]*)"',s))
def main():
 cat=json.loads((ROOT/'web_catalog.json').read_text());catalog={norm(h):h for h in cat}
 listing=fetch(BASE).decode();pages=[]
 for a in re.findall(r'<a\b[^>]*class="st-heroes__item".*?</a>',listing,re.S):
  at=attrs(a.split('>')[0]);im=re.search(r'<img[^>]+>',a)
  if im:
   ia=attrs(im[0]);h=catalog.get(norm(html.unescape(ia.get('alt',''))))
   if h:pages.append((h,at['href'],ia['src']))
 assets=ROOT/'assets'/'garena';assets.mkdir(exist_ok=True)
 result={'source':BASE,'heroes':{},'skins':{}};tasks=[];errors=[]
 def page(row):
  h,url,thumb=row;cache=ROOT/'tools'/'page_cache';cache.mkdir(exist_ok=True);f=cache/(norm(h)+'.html');t=f.read_text() if f.exists() else fetch(url).decode();f.write_text(t);out=[]
  thumbs={k:html.unescape(v) for k,v in re.findall(r'href="#(heroSkin-\d+)"[^>]*>\s*<img[^>]*src="([^"]+)"',t,re.S)}
  skins={norm(n):(n,sid) for n,sid in cat[h].items()}
  for block in re.findall(r'<div\b[^>]*class="hero__skins--detail[^\"]*".*?</div>',t,re.S):
   key=re.search(r'id="([^"]+)"',block);title=re.search(r'<h3>(.*?)</h3>',block,re.S);pic=re.search(r'<picture>\s*<img[^>]*src="([^"]+)"',block)
   if not (key and title and pic):continue
   label=html.unescape(re.sub(r'<[^>]+>','',title[1])).strip();short=label[len(h):].strip() if norm(label).startswith(norm(h)) else label
   match=skins.get(norm(short))
   if norm(label)==norm(h):match=next(((n,sid) for n,sid in cat[h].items() if str(sid).endswith('00')),None)
   if match:out.append((str(match[1]),thumbs.get(key[1]),html.unescape(pic[1])))
  return h,thumb,out
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  for f in concurrent.futures.as_completed([pool.submit(page,r) for r in pages]):
   try:
    h,thumb,rows=f.result();tasks.append(('hero',h,thumb,160));
    for sid,icon,splash in rows:
     if icon:tasks.append(('icon',sid,icon,160))
     tasks.append(('splash',sid,splash,800))
   except Exception as e:errors.append(str(e))
 print('Matched heroes',len(pages),'image tasks',len(tasks),flush=True)
 async def downloads():
  gate=asyncio.Semaphore(24)
  async with aiohttp.ClientSession(trust_env=True,timeout=aiohttp.ClientTimeout(total=30)) as client:
   async def download(row):
    kind,key,url,size=row;name=(norm(key) if kind=='hero' else key)+'-'+kind+'.webp';p=assets/name
    async with gate:
     try:
      if not p.exists():
       async with client.get(url) as response:
        response.raise_for_status();data=await response.read()
       im=Image.open(io.BytesIO(data)).convert('RGB');im.thumbnail((size,size));im.save(p,'WEBP',quality=78,method=4)
      path='/assets/garena/'+name
     except Exception as e:
      errors.append(str(e));path=url
     if kind=='hero':result['heroes'][key]={'icon':path,'source':url}
     else:result['skins'].setdefault(key,{})[kind]=path;result['skins'][key][kind+'_source']=url
   await asyncio.gather(*(download(r) for r in tasks))
 asyncio.run(downloads())
 (ROOT/'garena_images.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print('Saved',len(result['heroes']),'heroes',len(result['skins']),'skins; errors',len(errors),flush=True)
 if errors:print(errors[:5])
if __name__=='__main__':main()
