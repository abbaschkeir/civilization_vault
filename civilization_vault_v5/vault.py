#!/usr/bin/env python3
"""Civilization Vault v0.5: tiered, allowlist-driven, resumable acquisition across several disks.
Python 3.10+; standard library only. Implements VAULT_PLAN.md (repository root).
Sources are an explicit allowlist in sources.json; nothing is crawled or guessed.
"""
import argparse, concurrent.futures as cf, datetime, hashlib, json, os, re, shutil, sqlite3, sys, threading, time
import urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

VERSION = '0.5'
HERE = Path(__file__).resolve().parent
UA = f'CivilizationVault/{VERSION} (personal offline preservation archive)'
CHUNK = 1024 * 1024
META = '_metadata'
DBNAME = 'vault5.sqlite3'
TYPES = ('kiwix', 'hf', 'github_release', 'github_source', 'url', 'http_index', 's3', 'manual')
lock = threading.Lock()


# ---------- small helpers ----------

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

def sizefmt(n):
    if n is None: return '?'
    for u in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1000: return f'{n:.2f} {u}'
        n /= 1000
    return f'{n:.2f} PB'

def clean(s): return re.sub(r'[^a-zA-Z0-9_.+-]+', '_', s).strip('._')[:160] or 'file'

def is_https(u): return urllib.parse.urlsplit(u).scheme == 'https'

def natural(s): return [(0, int(t), '') if t.isdigit() else (1, 0, t) for t in re.split(r'(\d+)', s)]

def request(url, headers=None, timeout=60, method='GET'):
    req = urllib.request.Request(url, method=method, headers={'User-Agent': UA, **(headers or {})})
    host = urllib.parse.urlsplit(url).hostname or ''
    # Unredirected: tokens are never forwarded to CDN/mirror hosts on redirect.
    if host == 'huggingface.co' and os.environ.get('HF_TOKEN'):
        req.add_unredirected_header('Authorization', 'Bearer ' + os.environ['HF_TOKEN'])
    if host == 'api.github.com':
        req.add_header('Accept', 'application/vnd.github+json')
        if os.environ.get('GITHUB_TOKEN'): req.add_unredirected_header('Authorization', 'Bearer ' + os.environ['GITHUB_TOKEN'])
    return urllib.request.urlopen(req, timeout=timeout)

def get_bytes(url, timeout=120):
    with request(url, timeout=timeout) as r: return r.read()

def get_text(url): return get_bytes(url).decode('utf8', 'replace')

def get_json(url): return json.loads(get_bytes(url))

def get_json_pages(url):
    """Follow RFC 5988 Link: rel="next" pagination (Hugging Face tree API)."""
    out = []
    while url:
        with request(url, timeout=120) as r:
            out += json.loads(r.read())
            m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get('Link', ''))
        url = m.group(1) if m else None
    return out


# ---------- source resolution ----------

def make_item(src, name, url, size=None, sha256=None, md5=None, title=None):
    parts = [clean(p) for p in name.split('/') if p]
    if not parts or any(p in ('.', '..') for p in parts): raise ValueError(f'unsafe file name {name!r}')
    sub = '/'.join(parts)
    return {'id': f"{src['id']}/{sub}", 'source': src['id'], 'tier': src['tier'], 'category': src['category'],
            'path': f"{src['category']}/{clean(src['id'])}/{sub}", 'url': url, 'bytes': size,
            'sha256': sha256.lower() if sha256 else None, 'md5': md5.lower() if md5 else None,
            'title': title or src.get('title', src['id']), 'license': src.get('license', '')}

_cache = {}

def kiwix_catalog():
    if 'kiwix' not in _cache:
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        root = ET.fromstring(get_bytes('https://opds.library.kiwix.org/catalog/v2/entries?count=100000', timeout=180))
        books = {}
        for e in root.findall('a:entry', ns):
            link = next((l for l in e.findall('a:link', ns) if 'acquisition' in l.get('rel', '')), None)
            if link is None: continue
            key = (e.findtext('a:name', '', ns), e.findtext('a:flavour', '', ns) or '')
            rec = {'updated': e.findtext('a:updated', '', ns), 'href': link.get('href', ''),
                   'length': int(link.get('length') or 0) or None, 'title': e.findtext('a:title', '', ns)}
            if key not in books or rec['updated'] > books[key]['updated']: books[key] = rec
        print(f'Kiwix catalog: {len(root.findall("a:entry", ns))} entries')
        _cache['kiwix'] = books
    return _cache['kiwix']

def resolve_kiwix(src):
    rec = kiwix_catalog().get((src['name'], src.get('flavour', '')))
    if not rec: raise ValueError(f"not in Kiwix catalog: name={src['name']} flavour={src.get('flavour', '')!r}")
    meta4 = rec['href']
    # The catalog links to a metalink (.meta4) file, not the ZIM itself; the ZIM URL is the same path without it.
    url = meta4[:-len('.meta4')] if meta4.endswith('.meta4') else meta4
    if not is_https(url) or not url.endswith('.zim'): raise ValueError(f'unexpected Kiwix acquisition link {meta4}')
    sha = None
    if meta4.endswith('.meta4'):
        m = re.search(r'<hash type="sha-256">([0-9a-fA-F]{64})</hash>', get_text(meta4))
        sha = m.group(1) if m else None
    return [make_item(src, url.rsplit('/', 1)[-1], url, rec['length'], sha256=sha, title=f"{rec['title']} ({src['name']} {src.get('flavour', '')})".strip())]

def check_shards(paths):
    groups = {}
    for p in paths:
        m = re.match(r'^(.*)-(\d{5})-of-(\d{5})\.(gguf|safetensors)$', p)
        if m: groups.setdefault((m.group(1), int(m.group(3))), set()).add(int(m.group(2)))
    for (prefix, n), got in groups.items():
        if got != set(range(1, n + 1)): raise ValueError(f'{prefix}: only {len(got)} of {n} shards matched; include all shards')

def resolve_hf(src):
    repo = src['repo']
    info = get_json(f'https://huggingface.co/api/models/{repo}')
    if info.get('gated') and not os.environ.get('HF_TOKEN'):
        raise ValueError('gated repository: accept its terms on huggingface.co and set HF_TOKEN')
    rev = src.get('revision') or info['sha']
    tree = get_json_pages(f'https://huggingface.co/api/models/{repo}/tree/{rev}?recursive=true')
    files = [f for f in tree if f.get('type') == 'file'
             and any(re.search(p, f['path']) for p in src['include'])
             and not any(re.search(p, f['path']) for p in src.get('exclude', []))]
    if not files: raise ValueError('no repository files match the include patterns')
    check_shards([f['path'] for f in files])
    out = []
    for f in files:
        oid = (f.get('lfs') or {}).get('oid')
        url = f'https://huggingface.co/{repo}/resolve/{rev}/' + urllib.parse.quote(f['path'], safe='/')
        out.append(make_item(src, f['path'], url, f.get('size'), sha256=oid if oid and len(oid) == 64 else None,
                             title=f"{src.get('title', repo)} @ {rev[:10]}"))
    return out

def github_releases(repo):
    key = 'gh:' + repo
    if key not in _cache:
        try: _cache[key] = get_json(f'https://api.github.com/repos/{repo}/releases?per_page=30')
        except urllib.error.HTTPError as e:
            if e.code in (403, 429): raise ValueError('GitHub API rate limit (60 requests/hour without a token); set GITHUB_TOKEN or rerun later with --sources') from e
            raise
    return _cache[key]

def resolve_github_release(src):
    repo = src['repo']
    rel = next((r for r in github_releases(repo) if not r.get('draft') and (src.get('prerelease') or not r.get('prerelease'))
                and re.search(src.get('tag', '.'), r['tag_name'])), None)
    if not rel: raise ValueError('no published release matches')
    tag, out, seen = rel['tag_name'], [], set()
    for pat in src.get('assets', []):
        hits = [a for a in rel['assets'] if re.search(pat, a['name'])]
        if not hits: raise ValueError(f'release {tag}: no asset matches {pat}')
        for a in hits:
            if a['name'] in seen: continue
            seen.add(a['name'])
            digest = a.get('digest') or ''
            out.append(make_item(src, a['name'], a['browser_download_url'], a.get('size'),
                                 sha256=digest[7:] if digest.startswith('sha256:') else None, title=f"{src.get('title', repo)} {tag}"))
    if src.get('source'):
        out.append(make_item(src, f"{repo.split('/')[1]}-{tag}-source.tar.gz",
                             f'https://codeload.github.com/{repo}/tar.gz/refs/tags/{urllib.parse.quote(tag)}', title=f"{src.get('title', repo)} {tag} source"))
    return out

def resolve_github_source(src):
    """Pin the branch head through git's smart-HTTP ref advertisement, which uses no GitHub API quota."""
    repo = src['repo']
    refs = get_text(f'https://github.com/{repo}.git/info/refs?service=git-upload-pack')
    if src.get('branch'):
        m = re.search(r'([0-9a-f]{40}) refs/heads/' + re.escape(src['branch']) + r'\n', refs)
        branch = src['branch']
    else:
        m = re.search(r'([0-9a-f]{40}) HEAD\x00', refs)
        b = re.search(r'symref=HEAD:refs/heads/(\S+)', refs)
        branch = b.group(1) if b else 'HEAD'
    if not m: raise ValueError('could not read the branch head from the repository')
    sha = m.group(1)
    return [make_item(src, f"{repo.split('/')[1]}-{sha[:12]}-source.tar.gz", f'https://codeload.github.com/{repo}/tar.gz/{sha}',
                      title=f"{src.get('title', repo)} @ {branch} {sha[:10]}")]

def resolve_url(src):
    url = src['url']
    if not is_https(url): raise ValueError('only https URLs are allowed')
    name = src.get('filename') or urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit('/', 1)[-1])
    return [make_item(src, name, url, src.get('bytes'), sha256=src.get('sha256'), md5=src.get('md5'))]

def resolve_http_index(src):
    index = src['index']
    names = {}
    for href in re.findall(r'href="([^"]+)"', get_text(index), re.I):
        name = urllib.parse.unquote(href.split('?')[0].rstrip('/').rsplit('/', 1)[-1])
        if name and re.search(src['match'], name) and name not in names:
            names[name] = src['base'] + urllib.parse.quote(name) if src.get('base') else urllib.parse.urljoin(index, href)
    if not names: raise ValueError(f"index has no file matching {src['match']}")
    chosen = sorted(names, key=natural)
    if src.get('pick') == 'latest':  # newest per family: names that differ only in their numbers are one family
        fam = {}
        for n in chosen: fam[re.sub(r'\d+', '#', n)] = n
        chosen = sorted(fam.values(), key=natural)
    sums = {}
    if src.get('checksums'):
        for line in get_text(urllib.parse.urljoin(index, src['checksums'])).splitlines():
            m = re.match(r'^([0-9a-fA-F]{64}|[0-9a-fA-F]{32})\s+\*?(\S+)\s*$', line.strip())
            if m: sums[m.group(2).rsplit('/', 1)[-1]] = m.group(1)
    out = []
    for n in chosen:
        h = sums.get(n)
        url = names[n]
        if not is_https(url): raise ValueError(f'non-https file link {url}')
        out.append(make_item(src, n, url, sha256=h if h and len(h) == 64 else None, md5=h if h and len(h) == 32 else None))
    return out

def resolve_s3(src):
    host = f"{src['bucket']}.{src['endpoint']}"
    out, token, pages = [], None, 0
    while True:
        q = {'list-type': '2', 'max-keys': '1000', 'prefix': src.get('prefix', '')}
        if token: q['continuation-token'] = token
        root = ET.fromstring(get_bytes(f'https://{host}/?' + urllib.parse.urlencode(q)))
        ns = {'s': root.tag[1:].split('}')[0]}
        for c in root.findall('s:Contents', ns):
            key = c.findtext('s:Key', '', ns)
            if not re.search(src['match'], key): continue
            etag = (c.findtext('s:ETag', '', ns) or '').strip('"')
            out.append(make_item(src, key, f'https://{host}/' + urllib.parse.quote(key), int(c.findtext('s:Size', '0', ns)),
                                 md5=etag if re.fullmatch(r'[0-9a-f]{32}', etag) else None))
        token, pages = root.findtext('s:NextContinuationToken', None, ns), pages + 1
        if pages % 50 == 0: print(f"  {src['id']}: {pages} listing pages, {len(out)} matching objects", flush=True)
        if not token: break
    if not out: raise ValueError(f"no S3 keys match {src['match']}")
    return out

RESOLVERS = {'kiwix': resolve_kiwix, 'hf': resolve_hf, 'github_release': resolve_github_release, 'github_source': resolve_github_source,
             'url': resolve_url, 'http_index': resolve_http_index, 's3': resolve_s3}

def load_sources():
    cfg = json.loads((HERE / 'sources.json').read_text(encoding='utf8'))
    ids = set()
    for i, s in enumerate(cfg['sources']):
        for k in ('id', 'tier', 'category', 'type'):
            if k not in s: raise SystemExit(f'sources.json entry {i}: missing {k}')
        if s['id'] in ids: raise SystemExit(f"sources.json: duplicate id {s['id']}")
        if s['type'] not in TYPES: raise SystemExit(f"sources.json {s['id']}: unknown type {s['type']}")
        if str(s['tier']) not in cfg['tiers']: raise SystemExit(f"sources.json {s['id']}: tier {s['tier']} not defined")
        if clean(s['category']) != s['category']: raise SystemExit(f"sources.json {s['id']}: unsafe category")
        ids.add(s['id']); s['order'] = i
    return cfg

def probe(it):
    """HEAD request: confirms the link works and learns the size when the catalog did not give one."""
    for attempt in range(4):
        try:
            with request(it['url'], timeout=60, method='HEAD') as r:
                if not is_https(r.geturl()): return 'redirects to non-HTTPS'
                n = r.headers.get('Content-Length')
                if n and n.isdigit() and not it['bytes']: it['bytes'] = int(n)
            return None
        except urllib.error.HTTPError as e:
            if e.code in (403, 405): return None  # some servers refuse HEAD but serve GET
            if e.code not in (429, 500, 502, 503, 504) or attempt == 3: return f'HTTP {e.code}'
        except Exception as e:
            if attempt == 3: return str(e)
        time.sleep(5 * (attempt + 1))  # servers such as NCBI throttle bursts


# ---------- disks and records ----------

class Disk:
    def __init__(self, path):
        self.root = Path(path).expanduser().resolve()
        (self.root / META).mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.root / META / DBNAME, check_same_thread=False, timeout=60)
        self.con.execute('PRAGMA journal_mode=WAL')
        self.con.execute('CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, source TEXT, tier INTEGER, relative_path TEXT, url TEXT, bytes INTEGER, sha256 TEXT, status TEXT, updated TEXT, note TEXT)')
        self.con.commit()

    def __repr__(self): return str(self.root)
    def free(self): return shutil.disk_usage(self.root).free
    def total(self): return shutil.disk_usage(self.root).total

    def get(self, iid):
        with lock: return self.con.execute('SELECT bytes, sha256, status FROM files WHERE id=?', (iid,)).fetchone()

    def has(self, iid):
        row = self.get(iid)
        return bool(row and row[2] == 'done')

    def put(self, it, size, digest, status, note=''):
        with lock:
            self.con.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?)',
                             (it['id'], it['source'], it['tier'], it['path'], it['url'], size, digest, status, now(), note))
            self.con.commit()

    def rows(self, status='done'):
        with lock: return self.con.execute('SELECT id, relative_path, bytes, sha256 FROM files WHERE status=?', (status,)).fetchall()

def open_disks(paths, allow_same=False):
    if not paths: raise SystemExit('Give at least one --disk')
    disks = [Disk(p) for p in paths]
    for i, a in enumerate(disks):
        for b in disks[i + 1:]:
            if a.root == b.root: raise SystemExit(f'--disk {a} given twice')
            if not allow_same and a.root.stat().st_dev == b.root.stat().st_dev:
                raise SystemExit(f'{a} and {b} are on the same device; copies there do not protect anything (use --allow-same-device only for testing)')
    return disks

def queue_path(disk): return disk.root / META / 'queue.json'

def load_queue(disks):
    for d in disks:
        if queue_path(d).exists(): return json.loads(queue_path(d).read_text(encoding='utf8'))
    raise SystemExit('No queue found; run discover first')

def copies_for(q, tier, ndisks): return min(int(q['tiers'][str(tier)]['copies']), ndisks)

def copy_tools(root):
    dst = root / '_tools'; dst.mkdir(exist_ok=True)
    for f in (HERE / 'vault.py', HERE / 'sources.json', HERE / 'README.md', HERE.parent / 'VAULT_PLAN.md'):
        if f.exists(): shutil.copy2(f, dst / f.name)

def hash_file(path, md5=False):
    h, m = hashlib.sha256(), hashlib.md5() if md5 else None
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * CHUNK), b''):
            h.update(b)
            if m: m.update(b)
    return h.hexdigest(), m.hexdigest() if m else None


# ---------- download ----------

def download(it, disk, deadline, reserve, maxfile, retries, stop):
    dst = disk.root / it['path']
    part, side = dst.with_name(dst.name + '.part'), dst.with_name(dst.name + '.part.json')
    dst.parent.mkdir(parents=True, exist_ok=True)
    row = disk.get(it['id'])
    if dst.exists():
        if row and row[2] == 'done' and dst.stat().st_size == row[0]: return 'EXISTS', sizefmt(row[0])
        if row and row[2] == 'corrupt': dst.unlink()
        else: return 'SKIP', f'{dst} exists but is not recorded as verified; inspect or delete it'
    if it.get('bytes') and it['bytes'] > maxfile: return 'SKIP', f"{sizefmt(it['bytes'])} exceeds --max-file-gb"
    for attempt in range(retries + 1):
        if stop.is_set() or time.monotonic() >= deadline: return 'PAUSE', 'time limit or stop requested'
        start = part.stat().st_size if part.exists() else 0
        meta = json.loads(side.read_text(encoding='utf8')) if start and side.exists() else {}
        if start and meta.get('url') != it['url']: start = 0  # a different version of the file is now queued
        headers = {}
        if start:
            headers['Range'] = f'bytes={start}-'
            # If-Range: the server sends the whole new file (200) instead of appending bytes of a changed file.
            if meta.get('validator'): headers['If-Range'] = meta['validator']
        try:
            with request(it['url'], headers, timeout=60) as r:
                if not is_https(r.geturl()): raise RuntimeError('redirected to a non-HTTPS URL')
                status = getattr(r, 'status', 200)
                if start and status == 200: start = 0
                elif start and status != 206: raise RuntimeError(f'unexpected resume status {status}')
                if status == 206 and not r.headers.get('Content-Range', '').startswith(f'bytes {start}-'): raise RuntimeError('invalid Content-Range')
                if 'text/html' in r.headers.get('Content-Type', '').lower() and not dst.suffix.lower() in ('.html', '.htm'):
                    raise RuntimeError('server returned an HTML page instead of the file')
                length = r.headers.get('Content-Length')
                remaining = int(length) if length and length.isdigit() else None
                if remaining is not None and start + remaining > maxfile: return 'SKIP', f'{sizefmt(start + remaining)} exceeds --max-file-gb'
                if remaining is not None and remaining + reserve > disk.free(): return 'SPACE', f'{disk} lacks room for {sizefmt(remaining)}'
                if not start:
                    etag = r.headers.get('ETag')
                    side.write_text(json.dumps({'url': it['url'], 'validator': etag if etag and not etag.startswith('W/') else r.headers.get('Last-Modified')}), encoding='utf8')
                h, m = hashlib.sha256(), hashlib.md5() if it.get('md5') else None
                if start:
                    with part.open('rb') as old:
                        for b in iter(lambda: old.read(4 * CHUNK), b''):
                            h.update(b)
                            if m: m.update(b)
                amount, blocks = start, 0
                with part.open('ab' if start else 'wb') as out:
                    while True:
                        if stop.is_set() or time.monotonic() > deadline: return 'PAUSE', f'{sizefmt(amount)} kept in .part'
                        b = r.read(CHUNK)
                        if not b: break
                        if amount + len(b) > maxfile: return 'SKIP', 'file of unknown length exceeded --max-file-gb'
                        blocks += 1
                        if blocks % 64 == 0 and disk.free() < reserve: return 'SPACE', f'{disk} reached its free-space reserve'
                        out.write(b); h.update(b)
                        if m: m.update(b)
                        amount += len(b)
            if remaining is not None and amount - start != remaining: raise IOError('incomplete transfer')
            digest = h.hexdigest()
            bad = (it.get('sha256') and digest != it['sha256']) or (m and m.hexdigest() != it['md5'])
            if bad:
                part.unlink(missing_ok=True); side.unlink(missing_ok=True)
                raise IOError('checksum mismatch against the published hash; partial file discarded')
            os.replace(part, dst); side.unlink(missing_ok=True)
            disk.put(it, amount, digest, 'done', 'verified against published hash' if (it.get('sha256') or m) else 'hash recorded at download')
            return 'DONE', sizefmt(amount)
        except (OSError, urllib.error.URLError, RuntimeError, ValueError) as ex:
            if attempt == retries: return 'ERROR', str(ex)
            time.sleep(min(10 * (attempt + 1), 45))
    return 'ERROR', 'unexpected'

def choose_disk(it, disks, reserve, inflight):
    for d in disks:  # resume where a partial copy already exists
        if (d.root / (it['path'] + '.part')).exists(): return d
    need = (it.get('bytes') or 0) + reserve
    room = [(d.free() - inflight[d.root], d) for d in disks]
    room = [x for x in room if x[0] >= need]
    return max(room, key=lambda x: x[0])[1] if room else None


# ---------- copying, verification, reporting ----------

def copy_verified(src_disk, dst_disk, it, rel, nbytes, digest):
    src, dst = src_disk.root / rel, dst_disk.root / rel
    if not src.is_file() or src.stat().st_size != nbytes: return f'source missing or wrong size on {src_disk}'
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + '.copying')
    h = hashlib.sha256()
    with src.open('rb') as reader, tmp.open('wb') as writer:
        for b in iter(lambda: reader.read(4 * CHUNK), b''):
            writer.write(b); h.update(b)
    if h.hexdigest() != digest:
        tmp.unlink()
        return f'hash mismatch reading {src}; run verify on {src_disk}'
    os.replace(tmp, dst)
    dst_disk.put(it, nbytes, digest, 'done', f'copied from {src_disk}')
    return None

def record_of(disk, iid):
    with lock: return disk.con.execute('SELECT relative_path, bytes, sha256 FROM files WHERE id=? AND status=?', (iid, 'done')).fetchone()

def write_manifest(q, disks, dest_root=None):
    held = {it['id']: [str(d.root) for d in disks if d.has(it['id'])] for it in q['items']}
    roots = [Path(dest_root)] if dest_root else [d.root for d in disks]
    for root in roots:
        lines = ['tier\tid\ttitle\tbytes\tsha256\tlicense\tpath\tcopies\turl']
        md = [f'# Civilization Vault manifest', '', f'Generated {now()} by vault.py {VERSION}. Plan: `_tools/VAULT_PLAN.md`. '
              'Check any file with `py -3 _tools/vault.py --disk <this drive> verify`.', '']
        for tier in sorted(q['tiers'], key=int):
            items = [it for it in q['items'] if str(it['tier']) == tier]
            have = [it for it in items if held[it['id']]]
            md += [f"## P{tier}: {q['tiers'][tier].get('label', '')}", '',
                   f"{len(have)}/{len(items)} files present, {sizefmt(sum(it['bytes'] or 0 for it in have))}", '',
                   '| Category | Title | File | Size | SHA-256 (first 16) | Copies |', '|---|---|---|---|---|---|']
            for it in items:
                rec = next((record_of(d, it['id']) for d in disks if d.has(it['id'])), None)
                sha = (rec[2] if rec else it.get('sha256')) or ''
                lines.append('\t'.join(str(x) for x in (tier, it['id'], it['title'], it['bytes'] or '', sha, it.get('license', ''), it['path'], len(held[it['id']]), it['url'])))
                if held[it['id']]:
                    md.append(f"| {it['category']} | {it['title']} | `{it['path']}` | {sizefmt(it['bytes'])} | `{sha[:16]}` | {len(held[it['id']])} |")
            md.append('')
        if q.get('manual'):
            md += ['## Manual acquisitions (not downloadable by this tool)', '']
            md += [f"- **P{m['tier']} {m['id']}**: {m.get('title', '')}. {m.get('instructions', '')}" for m in q['manual']]
        (root / 'MANIFEST.tsv').write_text('\n'.join(lines) + '\n', encoding='utf8')
        (root / 'MANIFEST.md').write_text('\n'.join(md) + '\n', encoding='utf8')


# ---------- commands ----------

def cmd_discover(args, disks):
    cfg = load_sources()
    only = re.compile(args.sources) if args.sources else None
    prev = None
    if only:
        try: prev = load_queue(disks)
        except SystemExit: pass
    items, errors, manual = [], {}, []
    for src in cfg['sources']:
        if src['type'] == 'manual':
            manual.append({k: src.get(k) for k in ('id', 'tier', 'category', 'title', 'instructions', 'license')}); continue
        if only and not only.search(src['id']): continue
        try:
            got = RESOLVERS[src['type']](src)
            for it in got: it['order'] = src['order']
            items += got
            print(f"OK    P{src['tier']} {src['id']}: {len(got)} file(s), {sizefmt(sum(i['bytes'] or 0 for i in got))}"
                  + (f", {sum(1 for i in got if not i['bytes'])} of unknown size" if any(not i['bytes'] for i in got) else ''), flush=True)
        except Exception as e:
            errors[src['id']] = str(e); print(f"FAIL  P{src['tier']} {src['id']}: {e}", file=sys.stderr, flush=True)
    if prev:  # partial refresh: keep previously resolved items of the sources not refreshed
        keep = [it for it in prev['items'] if not only.search(it['source'])]
        items = keep + items
        errors = {**{k: v for k, v in prev.get('errors', {}).items() if not only.search(k)}, **errors}
    if not args.no_probe:
        targets = [it for it in items if it['bytes'] is None and not it['url'].startswith('https://codeload.github.com/')]
        if targets: print(f'Checking {len(targets)} links without a published size...', flush=True)
        with cf.ThreadPoolExecutor(8) as pool:
            for it, err in zip(targets, pool.map(probe, targets)):
                if err: errors[it['id']] = f'link check failed: {err}'; print(f"FAIL  {it['id']}: {err}", file=sys.stderr)
    ids, dedup = set(), []
    for it in sorted(items, key=lambda x: (x['tier'], x['order'], natural(x['path']))):
        if it['id'] not in ids: ids.add(it['id']); dedup.append(it)
    q = {'generated': now(), 'version': VERSION, 'sources_version': cfg.get('version'), 'tiers': cfg['tiers'],
         'items': dedup, 'manual': manual, 'errors': errors}
    for d in disks:
        queue_path(d).write_text(json.dumps(q, indent=1), encoding='utf8')
        copy_tools(d.root)
    print_plan(q, disks, 3)
    if errors: print(f'\n{len(errors)} problem(s), see above. Failed sources are left out of the queue until fixed; '
                     'files whose link check failed stay queued and are retried by run.')

def print_plan(q, disks, max_tier):
    n = len(disks)
    print(f"\nQueue generated {q['generated']} (sources {q.get('sources_version')}), {len(disks)} disk(s)")
    print(f"{'Tier':<6}{'Files':>8}{'Logical':>13}{'Unknown':>9}{'Copies':>8}{'Raw needed':>13}{'Still to write':>16}")
    total_raw = total_left = 0
    for tier in sorted(q['tiers'], key=int):
        if int(tier) > max_tier: continue
        items = [it for it in q['items'] if str(it['tier']) == tier]
        logical = sum(it['bytes'] or 0 for it in items)
        c = copies_for(q, tier, n)
        left = sum((it['bytes'] or 0) * max(0, c - sum(d.has(it['id']) for d in disks)) for it in items)
        total_raw += logical * c; total_left += left
        print(f"P{tier:<5}{len(items):>8}{sizefmt(logical):>13}{sum(1 for it in items if not it['bytes']):>9}{c:>8}{sizefmt(logical * c):>13}{sizefmt(left):>16}")
    print(f"{'Total':<44}{sizefmt(total_raw):>13}{sizefmt(total_left):>16}")
    for d in disks: print(f'  {d}: {sizefmt(d.free())} free of {sizefmt(d.total())}')
    free = sum(d.free() for d in disks)
    print('Fits on the given disks.' if total_left < free * 0.9 else f'DOES NOT FIT: {sizefmt(total_left)} still to write, {sizefmt(free)} free.')
    if q.get('manual'): print(f"{len([m for m in q['manual'] if m['tier'] <= max_tier])} manual acquisition(s); see `status` or MANIFEST.md.")

def cmd_plan(args, disks):
    q = load_queue(disks)
    print_plan(q, disks, args.max_tier)
    if args.list:
        for it in q['items']:
            if it['tier'] <= args.max_tier: print(f"[P{it['tier']}] {sizefmt(it['bytes']):>10}  {it['id']}")

def cmd_run(args, disks):
    q = load_queue(disks)
    if not 1 <= args.workers <= 8: raise SystemExit('Use 1 to 8 workers')
    if args.reserve_gb < 50: print(f'WARNING: --reserve-gb {args.reserve_gb} is below the 50 GB recommended for large disks')
    reserve, maxfile = int(args.reserve_gb * 1e9), int(args.max_file_gb * 1e9)
    only = re.compile(args.only) if args.only else None
    todo = [it for it in q['items'] if it['tier'] <= args.max_tier and (not only or only.search(it['id']))]
    deadline, stop = time.monotonic() + args.hours * 3600, threading.Event()
    inflight = {d.root: 0 for d in disks}
    counts = {}
    print(f"Downloading {len(todo)} file(s) up to P{args.max_tier} onto {', '.join(map(str, disks))}. Ctrl+C stops cleanly; rerun to resume.")
    print('Extra copies required by each tier are made afterwards by `sync`.')
    pending = iter(todo)
    futures = {}
    try:
        with cf.ThreadPoolExecutor(args.workers) as pool:
            while True:
                while len(futures) < args.workers and not stop.is_set() and time.monotonic() < deadline:
                    it = next(pending, None)
                    if it is None: break
                    if any(d.has(it['id']) for d in disks): counts['EXISTS'] = counts.get('EXISTS', 0) + 1; continue
                    d = choose_disk(it, disks, reserve, inflight)
                    if not d:
                        counts['SPACE'] = counts.get('SPACE', 0) + 1
                        print(f"SPACE   {it['id']}: no disk has {sizefmt((it['bytes'] or 0) + reserve)} free"); continue
                    inflight[d.root] += it.get('bytes') or 0
                    futures[pool.submit(download, it, d, deadline, reserve, maxfile, args.retries, stop)] = (it, d)
                if not futures: break
                done, _ = cf.wait(futures, return_when=cf.FIRST_COMPLETED)
                for f in done:
                    it, d = futures.pop(f)
                    inflight[d.root] -= it.get('bytes') or 0
                    status, note = f.result()
                    counts[status] = counts.get(status, 0) + 1
                    print(f"{status:7s} P{it['tier']} {it['id']} -> {d}: {note}", flush=True)
    except KeyboardInterrupt:
        stop.set(); print('Interrupted; partial downloads are kept and resume on the next run.')
    print('Summary:', ', '.join(f'{k} {v}' for k, v in sorted(counts.items())) or 'nothing to do')
    write_manifest(q, disks)

def cmd_sync(args, disks):
    q = load_queue(disks)
    reserve = int(args.reserve_gb * 1e9)
    made = short = 0
    try:
        for it in q['items']:
            if it['tier'] > args.max_tier: continue
            need = copies_for(q, it['tier'], len(disks))
            have = [d for d in disks if d.has(it['id'])]
            if not have or len(have) >= need: continue
            rel, nbytes, digest = record_of(have[0], it['id'])
            while len(have) < need:
                room = [d for d in disks if d not in have and d.free() >= nbytes + reserve]
                if not room:
                    short += 1; print(f"NO SPACE for another copy of {it['id']} ({sizefmt(nbytes)})"); break
                target = max(room, key=lambda d: d.free())
                err = copy_verified(have[0], target, it, rel, nbytes, digest)
                if err: print(f"ERROR   {it['id']}: {err}"); break
                have.append(target); made += 1
                print(f"COPIED  P{it['tier']} {it['id']} -> {target} ({sizefmt(nbytes)})", flush=True)
    except KeyboardInterrupt:
        print('Interrupted; rerun sync to continue.')
    print(f'Sync: {made} copies made, {short} files short of space.')
    write_manifest(q, disks)

def cmd_verify(args, disks):
    failed = 0
    for d in disks:
        rows = d.rows()
        print(f'Verifying {len(rows)} file(s) on {d}' + (' (sizes only)' if args.quick else ''), flush=True)
        for iid, rel, nbytes, digest in rows:
            p = d.root / rel
            ok = p.is_file() and p.stat().st_size == nbytes and (args.quick or hash_file(p)[0] == digest)
            if not ok:
                failed += 1
                with lock:
                    d.con.execute('UPDATE files SET status=?, updated=?, note=? WHERE id=?', ('corrupt', now(), 'failed verify', iid)); d.con.commit()
                print(f'FAIL {d}: {rel} (marked corrupt; sync restores it from another copy, run re-downloads it otherwise)')
    print(f'Verify finished: {failed} failure(s).')
    try: write_manifest(load_queue(disks), disks)
    except SystemExit: pass
    if failed: sys.exit(2)

def cmd_export(args, disks):
    q = load_queue(disks)
    dest = Disk(args.dest)
    if any(dest.root == d.root for d in disks): raise SystemExit('--dest must differ from every --disk')
    made = 0
    for it in q['items']:
        if it['tier'] > args.max_tier or dest.has(it['id']): continue
        src = next((d for d in disks if d.has(it['id'])), None)
        if not src: print(f"MISSING {it['id']} (not downloaded yet)"); continue
        rel, nbytes, digest = record_of(src, it['id'])
        if dest.free() < nbytes + int(args.reserve_gb * 1e9): print(f"NO SPACE on {dest} for {it['id']}"); continue
        err = copy_verified(src, dest, it, rel, nbytes, digest)
        print(f"ERROR   {it['id']}: {err}" if err else f"EXPORTED P{it['tier']} {it['id']} ({sizefmt(nbytes)})", flush=True)
        made += 0 if err else 1
    queue_path(dest).write_text(json.dumps(q, indent=1), encoding='utf8')
    copy_tools(dest.root)
    write_manifest(q, disks + [dest], dest.root)
    print(f'Export: {made} file(s) copied to {dest}; MANIFEST.md and _tools/ written there.')

def cmd_status(args, disks):
    q = load_queue(disks)
    n = len(disks)
    print(f"Queue {q['generated']} | sources {q.get('sources_version')} | {n} disk(s)")
    print(f"{'Tier':<6}{'Files':>7}{'Complete':>10}{'Short':>7}{'Missing':>9}{'Stored':>13}  Copies")
    for tier in sorted(q['tiers'], key=int):
        items = [it for it in q['items'] if str(it['tier']) == tier]
        need = copies_for(q, tier, n)
        held = [sum(d.has(it['id']) for d in disks) for it in items]
        stored = sum(it['bytes'] or 0 for it, h in zip(items, held) if h)
        print(f"P{tier:<5}{len(items):>7}{sum(h >= need for h in held):>10}{sum(0 < h < need for h in held):>7}{sum(h == 0 for h in held):>9}{sizefmt(stored):>13}  {need} ({q['tiers'][tier].get('label', '')})")
    for d in disks:
        print(f"  {d}: {len(d.rows())} verified files, {len(d.rows('corrupt'))} corrupt, {sizefmt(d.free())} free of {sizefmt(d.total())}")
    if q.get('errors'):
        print(f"\n{len(q['errors'])} discovery error(s):")
        for k, v in q['errors'].items(): print(f'  {k}: {v}')
    if q.get('manual'):
        print('\nManual acquisitions:')
        for m in q['manual']: print(f"  P{m['tier']} {m['id']}: {m.get('title', '')}")

def cmd_manifest(args, disks):
    write_manifest(load_queue(disks), disks)
    print('MANIFEST.md and MANIFEST.tsv written to every disk.')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--disk', action='append', default=[], help='Vault root on one physical disk; repeat for each disk')
    p.add_argument('--allow-same-device', action='store_true', help='Testing only: allow several --disk roots on one device')
    sub = p.add_subparsers(dest='command', required=True)
    sp = sub.add_parser('discover', help='Resolve sources.json into a download queue (needs internet)')
    sp.add_argument('--sources', help='Regex: refresh only matching source ids, keep the rest of the existing queue')
    sp.add_argument('--no-probe', action='store_true', help='Skip HEAD checks of links without a published size')
    sp = sub.add_parser('plan', help='Sizes per tier against disk capacity')
    sp.add_argument('--max-tier', type=int, default=3); sp.add_argument('--list', action='store_true')
    sp = sub.add_parser('run', help='Download queued files (one copy each)')
    sp.add_argument('--hours', type=float, default=48); sp.add_argument('--workers', type=int, default=2)
    sp.add_argument('--max-tier', type=int, default=2); sp.add_argument('--reserve-gb', type=float, default=750)
    sp.add_argument('--max-file-gb', type=float, default=350); sp.add_argument('--retries', type=int, default=3)
    sp.add_argument('--only', help='Regex on item ids, e.g. for a test download')
    sp = sub.add_parser('sync', help='Make the extra verified copies each tier requires')
    sp.add_argument('--max-tier', type=int, default=3); sp.add_argument('--reserve-gb', type=float, default=750)
    sp = sub.add_parser('verify', help='Re-hash every recorded file on every disk')
    sp.add_argument('--quick', action='store_true', help='Check sizes only')
    sp = sub.add_parser('export', help='Copy tiers up to --max-tier to a small offline drive')
    sp.add_argument('--dest', required=True); sp.add_argument('--max-tier', type=int, default=0); sp.add_argument('--reserve-gb', type=float, default=1)
    sub.add_parser('status', help='Completeness per tier, copies, errors and manual items')
    sub.add_parser('manifest', help='Rewrite MANIFEST.md / MANIFEST.tsv on every disk')
    a = p.parse_args()
    ds = open_disks(a.disk, a.allow_same_device)
    {'discover': cmd_discover, 'plan': cmd_plan, 'run': cmd_run, 'sync': cmd_sync, 'verify': cmd_verify,
     'export': cmd_export, 'status': cmd_status, 'manifest': cmd_manifest}[a.command](a, ds)
