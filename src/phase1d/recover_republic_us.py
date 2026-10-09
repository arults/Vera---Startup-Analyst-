#!/usr/bin/env python3
"""Bounded public recovery. Visible-list exhaustion NEVER proves historical coverage."""
from __future__ import annotations
import argparse, base64, gzip, hashlib, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

SEEDS = ('https://republic.com/companies/portfolio', 'https://republic.com/funded-ventures',
         'https://republic.com/reg-cf-offerings', 'https://republic.com/investment-opportunities')
HOSTS = {'republic.com', 'www.republic.com'}
REJECT = set(('login register signup about learn blog jobs raise invest terms privacy contact companies '
 'investment-opportunities ventures trading sharedrops launchpad tokenization infrastructure advisory note '
 'wallet help risks accessibility insights events security reg-cf-offerings funded-ventures api app capital '
 'capital-r cookie-disclosure ai-machine-learning blockchain search academy').split())
SCHEMA = 'phase1d-republic-us-recovery-v1'
PUBLIC_API = '/api/offerings/republic_note_public_deals'

def now(): return datetime.now(timezone.utc).isoformat()
def sha256(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()

def canonical_candidate(url: str, base: str = 'https://republic.com/') -> str | None:
    p = urlsplit(urljoin(base, url))
    if p.scheme != 'https' or p.netloc not in HOSTS: return None
    parts = [x for x in p.path.split('/') if x]
    if not parts or any(not re.fullmatch(r'[A-Za-z0-9._-]+', x) for x in parts): return None
    # Special case before general /companies exclusion: legacy probe had this backwards.
    if len(parts) == 2 and parts[0] == 'companies':
        if parts[1] in {'portfolio', 'new', 'search'}: return None
    elif len(parts) != 1 or parts[0] in REJECT: return None
    return 'https://republic.com/' + '/'.join(parts)

def safe_next(url: str, seed: str) -> bool:
    p, s = urlsplit(urljoin(seed, url)), urlsplit(seed)
    return p.scheme == 'https' and p.netloc in HOSTS and p.path.rstrip('/') == s.path.rstrip('/')

def public_api_url(url: str) -> bool:
    p = urlsplit(url)
    return p.scheme == 'https' and p.netloc in HOSTS and p.path == PUBLIC_API and not p.query

def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)+'\n', encoding='utf-8')
    os.replace(tmp, path)

def load_snapshot(root: Path, digest: str) -> bytes:
    if not re.fullmatch(r'[0-9a-f]{64}', digest): raise ValueError('invalid digest')
    r = json.loads((root/'snapshots'/f'{digest}.json').read_text())
    if r.get('encoding') != 'gzip+base64': raise ValueError('unknown encoding')
    raw = gzip.decompress(base64.b64decode(r['data'], validate=True))
    if r['sha256'] != digest or sha256(raw) != digest or len(raw) != r['bytes']:
        raise ValueError('snapshot integrity failure')
    return raw

def store_snapshot(root: Path, raw: bytes) -> str:
    if len(raw) > 12_000_000: raise ValueError('oversize source; not silently truncated')
    h = sha256(raw); target = root/'snapshots'/f'{h}.json'
    if target.exists():
        if load_snapshot(root,h) != raw: raise ValueError('corrupted prior capture')
    else:
        atomic_json(target, {'sha256':h, 'bytes':len(raw), 'encoding':'gzip+base64',
            'data':base64.b64encode(gzip.compress(raw,mtime=0)).decode('ascii')})
    return h

def new_manifest(run_id: str) -> dict:
    return {'schema':SCHEMA, 'run_id':run_id, 'created_at':now(), 'captures':[], 'errors':[],
        'seeds_completed':[], 'directory_stops':[], 'candidate_urls':[],
        'census_status':'CENSUS_INCOMPLETE', 'rates_promoted':False,
        'scope':'Native discovery candidates only. Historical layer-A/B coverage unresolved.',
        'date_policy':'deadline is not successful_close or first_live; no year imputation.'}

def record_capture(m: dict, c: dict) -> bool:
    key = (c['url'],c['kind'],c['sha256'])
    if any((x['url'],x['kind'],x['sha256']) == key for x in m['captures']): return False
    c['candidate_urls'] = sorted({u for v in c.get('candidate_urls',[]) if (u:=canonical_candidate(v))})
    c['candidate_count'] = len(c['candidate_urls'])
    m['captures'].append(c)
    m['candidate_urls'] = sorted({u for x in m['captures'] for u in x['candidate_urls']})
    return True

def checkpoint(root: Path, m: dict) -> None:
    m['updated_at'] = now()
    n = len(list((root/'checkpoints').glob('*.json'))) + 1
    atomic_json(root/'checkpoints'/f'{n:06d}.json', m)
    atomic_json(root/'manifest.json', m)

def verify(root: Path, m: dict) -> dict:
    for h in {c['sha256'] for c in m['captures']}: load_snapshot(root,h)
    checks = {
      'schema':m['schema']==SCHEMA,
      'historical_census_incomplete':m['census_status']=='CENSUS_INCOMPLETE',
      'no_rate_promotion':m['rates_promoted'] is False,
      'per_page_not_cumulative':all(c['candidate_count']==len(set(c['candidate_urls'])) for c in m['captures']),
      'union_reconciles':m['candidate_urls']==sorted({u for c in m['captures'] for u in c['candidate_urls']}),
      'distinct_responses_preserved':len(m['captures'])==len({(c['url'],c['kind'],c['sha256']) for c in m['captures']}),
      'snapshot_hashes_verified':True,
      'canonical_urls':all(canonical_candidate(u)==u for u in m['candidate_urls']),
      'public_api_only':all(public_api_url(c['url']) for c in m['captures'] if c['kind']=='public_api'),
      'timestamps_present':all(bool(c.get('captured_at')) for c in m['captures'])}
    return {'passed':sum(checks.values()),'total':len(checks),'checks':checks,
            'scope':'Capture-integrity checks ONLY, not historical census completion.'}

def main():
    from playwright.sync_api import sync_playwright
    p = argparse.ArgumentParser(); p.add_argument('--run-id',required=True)
    p.add_argument('--steps-per-seed',type=int,default=8); args=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args.run_id) or not 1<=args.steps_per_seed<=20:
        raise ValueError('invalid bounded-run parameters')
    root=Path(__file__).resolve().parents[2]/'data/phase1d/republic_us_recovery'/args.run_id
    root.mkdir(parents=True,exist_ok=True); current=root/'manifest.json'
    m=json.loads(current.read_text()) if current.exists() else new_manifest(args.run_id)
    if m['run_id']!=args.run_id or not all(verify(root,m)['checks'].values()):
        raise ValueError('refuse invalid resume checkpoint')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        ctx=browser.new_context(locale='en-US',viewport={'width':1440,'height':1100})
        page=ctx.new_page()
        def on_response(resp):
            if not public_api_url(resp.url) or resp.request.method!='GET': return
            try:
                if resp.status!=200: raise ValueError(f'public API HTTP {resp.status}')
                raw=resp.body(); body=json.loads(raw)
                links=['https://republic.com/'+r['slug'] for r in body
                    if isinstance(r,dict) and isinstance(r.get('slug'),str)] if isinstance(body,list) else []
                record_capture(m,{'url':resp.url,'kind':'public_api','status':resp.status,'captured_at':now(),
                    'sha256':store_snapshot(root,raw),'candidate_urls':links,
                    'raw_row_count':len(body) if isinstance(body,list) else None})
            except Exception as e: m['errors'].append({'url':resp.url,'error':str(e),'at':now()})
            checkpoint(root,m)
        page.on('response',on_response)
        for seed in SEEDS:
            if seed in m['seeds_completed']: continue
            stop='STEP_LIMIT'
            try:
                resp=page.goto(seed,wait_until='domcontentloaded',timeout=45000)
                if resp is None or resp.status!=200: raise ValueError(f'HTTP {resp.status if resp else None}')
                page.wait_for_timeout(1600); seen=set(); stable=0
                for step in range(args.steps_per_seed):
                    if not safe_next(page.url,seed): raise ValueError('redirect outside permitted directory')
                    links=page.locator('a[href]').evaluate_all('(xs)=>xs.map(x=>x.href)')
                    urls=sorted({u for v in links if (u:=canonical_candidate(v,page.url))})
                    state=sha256(json.dumps(urls).encode()); stable=stable+1 if state in seen else 0; seen.add(state)
                    tables=page.locator('table').evaluate_all('(ts)=>ts.map(t=>({headers:Array.from(t.querySelectorAll("th")).map(x=>x.innerText),rows:Array.from(t.querySelectorAll("tr")).map(r=>({cells:Array.from(r.querySelectorAll("td")).map(x=>x.innerText),links:Array.from(r.querySelectorAll("a[href]")).map(x=>x.href)}))}))')
                    record_capture(m,{'url':page.url,'seed':seed,'kind':'directory_dom','status':200,'step':step,
                        'captured_at':now(),'sha256':store_snapshot(root,page.content().encode()),
                        'candidate_urls':urls,'title':page.title(),'text':page.locator('body').inner_text(),'tables':tables})
                    checkpoint(root,m)
                    print(json.dumps({'seed':seed,'step':step,'page_candidates':len(urls),'union':len(m['candidate_urls'])}),flush=True)
                    nxt=page.locator('a[rel="next"]'); target=nxt.first.get_attribute('href') if nxt.count() else None
                    if target and safe_next(urljoin(page.url,target),seed):
                        resp=page.goto(urljoin(page.url,target),wait_until='domcontentloaded',timeout=30000)
                        if resp is None or resp.status!=200: raise ValueError('pagination HTTP failure')
                        page.wait_for_timeout(1000); continue
                    more=page.get_by_role('button',name=re.compile(r'^(load more|show more|load more (companies|deals|offerings)|show more (companies|deals|offerings))$',re.I))
                    if more.count() and more.first.is_visible() and more.first.is_enabled():
                        more.first.click(timeout=3000); page.wait_for_timeout(1000); continue
                    if stable>=2:
                        stop='VISIBLE_LIST_STABLE_NOT_HISTORICAL_COMPLETENESS'; break
                    page.evaluate('window.scrollTo(0,document.body.scrollHeight)'); page.wait_for_timeout(1000)
                m['seeds_completed'].append(seed)
            except Exception as e:
                stop='ACCESS_OR_CAPTURE_ERROR';m['errors'].append({'url':seed,'error':str(e),'at':now()})
            m['directory_stops'].append({'seed':seed,'reason':stop,'at':now()});checkpoint(root,m)
        browser.close()
    gates=verify(root,m)
    summary={k:m[k] for k in ('run_id','census_status','rates_promoted','errors','directory_stops')}
    summary.update({'capture_count':len(m['captures']),'candidate_count':len(m['candidate_urls']),
        'integrity_gates':gates,'completed_seed_count':len(m['seeds_completed']),
        'per_directory_candidate_counts':{s:len({u for c in m['captures'] if c.get('seed')==s for u in c['candidate_urls']}) for s in SEEDS},
        'api_capture_row_counts':[c['raw_row_count'] for c in m['captures'] if c['kind']=='public_api'],
        'manifest_sha256':sha256(current.read_bytes())})
    atomic_json(root/'summary.json',summary);print(json.dumps(summary,sort_keys=True),flush=True)
    if gates['passed']!=gates['total']: raise SystemExit(2)
if __name__=='__main__': main()
