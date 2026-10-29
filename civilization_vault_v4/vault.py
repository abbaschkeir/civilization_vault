#!/usr/bin/env python3
"""Civilization Vault v0.4: bounded, resumable, priority-led 48-hour acquisition.
Python 3.10+; standard library. Does not crawl general websites.
"""
import argparse, concurrent.futures, datetime, hashlib, json, os, re, shutil, sqlite3, sys, threading, time, urllib.request, urllib.parse, urllib.error, xml.etree.ElementTree as ET
from pathlib import Path

HERE=Path(__file__).resolve().parent
UA='CivilizationVault/0.4 (personal offline education; contact site owner for bulk permissions)'
CHUNK=1024*1024
lock=threading.Lock()

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sizefmt(n):
    for u in ['B','KB','MB','GB','TB']:
        if abs(n)<1000: return f'{n:.2f} {u}'
        n/=1000
    return f'{n:.2f} PB'
def clean(s): return re.sub(r'[^a-zA-Z0-9_.-]+','_',s).strip('._')[:140] or 'file'
def ssl_url(u): return urllib.parse.urlsplit(u).scheme == 'https'
def request(u,headers=None,timeout=35): return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA,**(headers or {})}),timeout=timeout)
def free_bytes(root): return shutil.disk_usage(root).free

def init_db(root):
    d=root/'_metadata';d.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(d/'files.sqlite3',check_same_thread=False,timeout=60)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, url TEXT, relative_path TEXT, bytes INTEGER, sha256 TEXT, status TEXT, updated TEXT, note TEXT)')
    con.commit();return con

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*CHUNK),b''):h.update(b)
    return h.hexdigest()

def kiwix_discover(max_entries=1200, max_per_topic=3, languages=('eng',)):
    """Use official Kiwix OPDS public catalog. Filter to preferred recovery topics."""
    url='https://opds.library.kiwix.org/catalog/v2/entries?count='+str(max_entries)
    with request(url) as resp: xml=resp.read(12*1024*1024)
    root=ET.fromstring(xml)
    ns={'a':'http://www.w3.org/2005/Atom','opds':'http://opds-spec.org/2010/catalog'}
    keywords=[('wikipedia',0, '00_BOOTSTRAP'),('wiktionary',1,'01_EDUCATION'),('wikibooks',0,'01_EDUCATION'),('wikivoyage',2,'11_MAPS'),('wikisource',2,'01_EDUCATION'),('stack_exchange',1,'06_COMPUTING'),('ifixit',0,'05_ENGINEERING'),('medical',0,'02_MEDICINE'),('medicine',0,'02_MEDICINE'),('pharmac',1,'02_MEDICINE'),('ted',2,'01_EDUCATION'),('gutenberg',2,'01_EDUCATION'),('openstax',0,'01_EDUCATION'),('khan',1,'01_EDUCATION'),('wikipedia_en',0,'00_BOOTSTRAP')]
    entries=[]
    for item in root.findall('a:entry',ns):
        title=item.findtext('a:title',default='',namespaces=ns)
        lower=title.lower().replace('-','_')
        matched=next(((k,p,category) for k,p,category in keywords if k in lower),None)
        if not matched: continue
        text=' '.join((x.text or '') for x in item.iter() if x.tag.split('}')[-1] in ('language','name'))
        # Name-based restriction keeps selection predictable; OPDS language metadata is inconsistent.
        if languages and not (any(x in lower for x in ('_en_','_eng_','english','en.wikipedia','enwiki')) or matched[0] in ('ifixit','openstax','medical','medicine','khan','ted')): continue
        links=[]
        for link in item.findall('a:link',ns):
            href=link.get('href','');rel=link.get('rel','');typ=link.get('type','')
            if ssl_url(href) and ('acquisition' in rel or href.lower().split('?')[0].endswith('.zim')): links.append((href,typ))
        if not links: continue
        # Favor explicit direct ZIM URLs.
        links.sort(key=lambda x: 0 if x[0].lower().split('?')[0].endswith('.zim') else 1)
        href=links[0][0]
        if not href.lower().split('?')[0].endswith('.zim') and 'application/x-zim' not in links[0][1]: continue
        label=clean(title)
        entries.append({'id':'kiwix_'+label,'url':href,'category':matched[2],'filename':label+'.zim','priority':matched[1], 'title':title,'origin':'Kiwix OPDS','expected_bytes':None})
    result=[];counts={}
    for e in sorted(entries,key=lambda x:(x['priority'],x['title'])):
        topic=e['title'].split('_')[0].lower()
        if counts.get(topic,0)>=max_per_topic:continue
        counts[topic]=counts.get(topic,0)+1;result.append(e)
    return result

def llm_discover():
    """Resolve selected GGUF models via Hugging Face's published repository API.
    Select one quantization, rather than downloading every variation.
    """
    specs=json.loads((HERE/'llm_models.json').read_text(encoding='utf8'))
    discovered=[]
    for spec in specs:
        repo=spec['repo']
        api='https://huggingface.co/api/models/'+urllib.parse.quote(repo,safe='/')+'/tree/main?recursive=true'
        try:
            with request(api,timeout=35) as response:
                tree=json.load(response)
            candidates=[f for f in tree if f.get('type')=='file' and f.get('path','').lower().endswith('.gguf') and spec['pattern'].lower() in f['path'].lower()]
            if not candidates: raise ValueError('No matching GGUF in repository')
            # Prefer the shallowest, smallest single-file quantization.
            candidates.sort(key=lambda f:(f['path'].count('/'),f.get('size') or 0,f['path']))
            f=candidates[0]; name=f['path']
            source='https://huggingface.co/'+repo+'/resolve/main/'+urllib.parse.quote(name,safe='/')
            oid=(f.get('lfs') or {}).get('oid')
            entry={'id':'llm_'+spec['id'],'title':spec['purpose']+' ('+repo+')',
              'url':source,'filename':clean(spec['id'])+'.gguf',
              'category':'10_OFFLINE_AI','priority':spec['priority'],
              'origin':'Hugging Face: '+repo, 'expected_bytes':f.get('size')}
            if oid and len(oid)==64: entry['sha256']=oid
            discovered.append(entry)
            print('AI model discovered:',repo,name,sizefmt(f.get('size') or 0))
        except Exception as exc:
            print('AI model discovery failed:',repo,str(exc),file=sys.stderr)
    return discovered

def static_items():
    data=json.loads((HERE/'sources.json').read_text(encoding='utf8'))
    return [x for x in data if x.get('url') and ssl_url(x['url'])]

def discover(root,kiwix=True,llms=True):
    items=static_items()
    if kiwix:
        try:
            found=kiwix_discover();items+=found
            print(f'Kiwix OPDS discovery: {len(found)} matched packages')
        except Exception as e:print('Kiwix discovery unavailable:',e,file=sys.stderr)
    if llms:
        items+=llm_discover()
    ids=set();dedup=[]
    for e in items:
        if e['id'] not in ids: dedup.append(e);ids.add(e['id'])
    dedup.sort(key=lambda x:(int(x['priority']), x['category'],x['title']))
    dest=root/'_metadata'/'queue.json';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps({'generated':now(),'items':dedup},indent=2),encoding='utf8')
    return dedup

def load_queue(root):
    p=root/'_metadata'/'queue.json'
    if not p.exists():raise SystemExit('Run discover first to create the download queue')
    return json.loads(p.read_text(encoding='utf8'))['items']

def record(con, e, relative, size, digest, status, note=''):
    with lock:
        con.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?)',(e['id'],e['url'],str(relative),size,digest,status,now(),note));con.commit()

def download_one(e, root, con, deadline, reserve, maxfile, retries, stop):
    rel=Path(e['category'])/e['filename']
    if any(p in ('.','..') for p in rel.parts) or not ssl_url(e['url']):return ('SKIP',e['id'],'unsafe path/url')
    dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True)
    with lock:
        row=con.execute('SELECT bytes,sha256,status FROM files WHERE id=?',(e['id'],)).fetchone()
    if dst.exists():
        if row and row[2]=='done' and dst.stat().st_size==row[0]:return ('EXISTS',e['id'],sizefmt(row[0]))
        return ('SKIP',e['id'],'existing file not recorded as verified; run verify or inspect')
    part=Path(str(dst)+'.part')
    for attempt in range(retries+1):
        if stop.is_set() or time.monotonic()>=deadline: return ('PAUSE',e['id'],'time limit')
        start=part.stat().st_size if part.exists() else 0
        if start>maxfile:return ('SKIP',e['id'],'partial file above per-file cap')
        try:
            headers={'Range':f'bytes={start}-'} if start else {}
            with request(e['url'],headers,timeout=45) as r:
                if not ssl_url(r.geturl()):raise RuntimeError('non-HTTPS redirect')
                status=getattr(r,'status',200)
                if start and status==200:
                    # Range ignored: restart from zero; never append full response to partial.
                    start=0
                if start and status!=206:raise RuntimeError(f'unexpected resume status {status}')
                if status==206:
                    cr=r.headers.get('Content-Range','')
                    if not cr.startswith(f'bytes {start}-'):raise RuntimeError('invalid Content-Range')
                typ=r.headers.get('Content-Type','').lower()
                if 'text/html' in typ:raise RuntimeError('HTML response, not an archive')
                remaining=r.headers.get('Content-Length')
                if remaining and remaining.isdigit():
                    total=start+int(remaining)
                    if total>maxfile: return ('SKIP',e['id'],f'file {sizefmt(total)} exceeds cap {sizefmt(maxfile)}')
                    if int(remaining)+reserve>free_bytes(root):return ('SPACE',e['id'],'insufficient free space')
                h=hashlib.sha256()
                if start:
                    with part.open('rb') as old:
                        for block in iter(lambda:old.read(4*CHUNK),b''):h.update(block)
                amount=start
                with part.open('ab' if start else 'wb') as out:
                    while True:
                        if stop.is_set() or time.monotonic()>deadline:return ('PAUSE',e['id'],sizefmt(amount))
                        block=r.read(CHUNK)
                        if not block:break
                        if amount+len(block)>maxfile: return ('SKIP',e['id'],'unknown-length file exceeded cap')
                        if free_bytes(root)<reserve+256*CHUNK:
                            stop.set();return ('SPACE',e['id'],'free disk reserve reached')
                        out.write(block);h.update(block);amount+=len(block)
                if remaining and remaining.isdigit() and amount-start!=int(remaining):raise IOError('incomplete transfer')
                expected=e.get('sha256')
                checksum=h.hexdigest()
                if expected and checksum.lower()!=expected.lower():raise IOError('published SHA256 mismatch')
                os.replace(part,dst)
                record(con,e,rel,amount,checksum,'done',e.get('origin',''))
                return ('DONE',e['id'],sizefmt(amount))
        except (OSError,urllib.error.URLError,RuntimeError,ValueError,IOError) as ex:
            if attempt==retries:return ('ERROR',e['id'],str(ex))
            time.sleep(min(10*(attempt+1),45))
    return ('ERROR',e['id'],'unexpected')

def verify(root, con,all_files=False):
    rows=con.execute('SELECT id,relative_path,bytes,sha256 FROM files WHERE status="done"').fetchall()
    failed=0
    for i,rel,bytes_,h in rows:
        p=root/rel
        ok=p.is_file() and p.stat().st_size==bytes_ and sha256(p)==h
        print('OK' if ok else 'FAIL',i,rel)
        if not ok:failed+=1
    print(f'Verified {len(rows)-failed}/{len(rows)} records');return failed==0

def run(args):
    root=Path(args.root).expanduser().resolve();root.mkdir(parents=True,exist_ok=True)
    secondary=Path(args.secondary).expanduser().resolve() if args.secondary else None
    if secondary:
        secondary.mkdir(parents=True,exist_ok=True)
        if root==secondary or os.path.samefile(root,secondary):
            raise SystemExit('Primary and secondary must be different directories')
        if os.name!='nt' and root.stat().st_dev==secondary.stat().st_dev:
            raise SystemExit('Both roots are on the same filesystem, not two disks')
    con=init_db(root)
    if args.command=='discover':
        items=discover(root,not args.no_kiwix,not args.no_llms)
        for e in items:print(f"[{e['priority']}] {e['id']} {e['title']}")
        return
    if args.command=='verify':
        good=verify(root,con)
        if secondary:
            second_db=init_db(secondary)
            good=verify(secondary,second_db) and good
        if not good:sys.exit(2)
        return
    if args.command=='sync':
        if not secondary: raise SystemExit('--secondary is required for sync')
        if args.mode!='copies': raise SystemExit('sync is only for copies mode')
        second_db=init_db(secondary)
        rows=con.execute('SELECT id,url,relative_path,bytes,sha256 FROM files WHERE status="done"').fetchall()
        for sid,url,rel,nbytes,digest in rows:
            src=root/rel;dst=secondary/rel
            if not src.is_file() or src.stat().st_size!=nbytes:
                print('SOURCE MISSING',rel);continue
            if dst.exists():
                if dst.stat().st_size==nbytes and sha256(dst)==digest:
                    print('BACKUP OK',rel);continue
                print('BACKUP CONFLICT; inspect manually',rel);continue
            if free_bytes(secondary)<nbytes+int(args.reserve_gb*1e9):
                print('BACKUP DISK FULL');break
            dst.parent.mkdir(parents=True,exist_ok=True)
            part=Path(str(dst)+'.copying')
            with src.open('rb') as reader,part.open('wb') as writer:
                shutil.copyfileobj(reader,writer,4*CHUNK)
            if sha256(part)!=digest:
                part.unlink();print('BACKUP HASH ERROR',rel);continue
            os.replace(part,dst)
            second_db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?)',
                (sid,url,rel,nbytes,digest,'done',now(),'offline backup'))
            second_db.commit()
            print('BACKED UP',rel)
        return
    items=load_queue(root)
    if args.command=='plan':
        for e in items:
            if e['priority']<=args.max_priority:print(f"[{e['priority']}] {e['id']}: {e['url']}")
        return
    if args.command=='run':
        print('Running acquisition. Ctrl+C stops cleanly; rerun to resume.')
        if args.workers<1 or args.workers>4: raise SystemExit('Use 1 to 4 workers with HDDs')
        if args.reserve_gb<500: raise SystemExit('At least 500 GB reserve is required')
        reserve=int(args.reserve_gb*1e9);maxfile=int(args.max_file_gb*1e9)
        candidates=[x for x in items if x['priority']<=args.max_priority]
        if args.mode=='capacity' and not secondary:raise SystemExit('capacity mode requires --secondary')
        deadline=time.monotonic()+args.hours*3600
        print('Mode:',args.mode,'| primary:',root,'| secondary:',secondary or 'none')
        if args.mode=='copies' and secondary: print('SECOND DISK IS NOT UPDATED DURING RUN. Execute sync afterward.')
        if args.mode=='copies' and not secondary:print('WARNING: ONLY ONE COPY. Add a second disk and run sync.')
        stop=threading.Event()
        try:
            # Small bounded batches ensure priority order, rather than launching entire queue at once.
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                for i in range(0,len(candidates),args.workers):
                    if stop.is_set() or time.monotonic()>=deadline or free_bytes(root)<reserve+CHUNK:break
                    batch=candidates[i:i+args.workers]
                    futures=[]
                    for e in batch:
                        target=root; db=con
                        if args.mode=='capacity':
                            ix=candidates.index(e)
                            target=secondary if ix%2 else root
                            db=init_db(target) if target==secondary else con
                        futures.append(pool.submit(download_one,e,target,db,deadline,reserve,maxfile,args.retries,stop))
                    for f in concurrent.futures.as_completed(futures):
                        status,sid,note=f.result();print(f'{status:7s} {sid}: {note}',flush=True)
                        if status=='SPACE':stop.set()
        except KeyboardInterrupt:
            stop.set();print('Interrupted, partial downloads retained.')
        print('Finished. Run verify when convenient.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',default=os.environ.get('VAULT_ROOT','./VAULT'))
    p.add_argument('--secondary',default=None,help='Second physical disk')
    p.add_argument('--mode',choices=('copies','capacity'),default='copies')
    sub=p.add_subparsers(dest='command',required=True)
    sp=sub.add_parser('discover');sp.add_argument('--no-kiwix',action='store_true');sp.add_argument('--no-llms',action='store_true')
    sp=sub.add_parser('plan');sp.add_argument('--max-priority',type=int,default=2)
    sp=sub.add_parser('run');sp.add_argument('--hours',type=float,default=48);sp.add_argument('--workers',type=int,default=2);sp.add_argument('--max-priority',type=int,default=2);sp.add_argument('--reserve-gb',type=float,default=750);sp.add_argument('--max-file-gb',type=float,default=350);sp.add_argument('--retries',type=int,default=3)
    sub.add_parser('verify')
    sp=sub.add_parser('sync');sp.add_argument('--reserve-gb',type=float,default=750)
    run(p.parse_args())
