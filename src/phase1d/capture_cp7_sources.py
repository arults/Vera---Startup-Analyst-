#!/usr/bin/env python3
"""Bounded, public-only CP7 source collection; immutable outputs and no inference."""
from __future__ import annotations
import concurrent.futures, csv, gzip, hashlib, json, os, re, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse, urljoin
import requests
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/phase1d'
HOSTS = {'wefunder.com':'wefunder','www.wefunder.com':'wefunder','republic.com':'republic_us','www.republic.com':'republic_us','www.startengine.com':'startengine','startengine.com':'startengine','www.crowdcube.com':'crowdcube','crowdcube.com':'crowdcube','europe.republic.com':'republic_europe'}
def now(): return datetime.now(timezone.utc).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def csvrows(path):
    with path.open(encoding='utf-8', newline='') as f: return list(csv.DictReader(f))
def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(data)
def jbytes(obj): return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
def cleanurl(url):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password: return None
    if any(s in p.path.lower() for s in ['/auth/', '/login','/signup','/register','/users/']): return None
    return urlunparse((p.scheme,p.netloc,p.path.rstrip('/') or '/', '', '', ''))
def build_queue():
    seen={}
    def add(url,reason):
        url=cleanurl(url)
        if not url:return
        platform=HOSTS[urlparse(url).hostname]
        seen.setdefault(url,{'url':url,'platform':platform,'reasons':[]})['reasons'].append(reason)
    for filename in ['cp1_tavily_candidates_us.csv','cp1_tavily_candidates_eu_web.csv']:
        for r in csvrows(DATA/filename):
            u=r['url'];p=urlparse(u)
            if p.hostname not in HOSTS or HOSTS[p.hostname]=='republic_europe':continue
            if HOSTS[p.hostname]=='startengine' and not re.match(r'^/(offering/)?[^/]+/?$',p.path):continue
            if HOSTS[p.hostname]=='crowdcube' and '/companies/' not in p.path:continue
            if HOSTS[p.hostname]=='republic_us' and not re.match(r'^/[^/]+/?$',p.path):continue
            if HOSTS[p.hostname]=='wefunder' and not re.match(r'^/[^/]+/?$',p.path):continue
            if p.path.strip('/') in {'explore','companies','invest','search','portfolio','press','blog','learn','raise'}:continue
            add(u,'prior_discovery_queue:'+filename)
    archive=DATA/'republic_us_archive/gh-37894925070-1/candidates.json'
    for r in json.loads(archive.read_text()):
        if '2020' in str(r.get('deadline_raw')):add(r['candidate_url'],'archive2020_deadline_resolution_not_cohort_assignment')
    for r in csvrows(DATA/'cp2_republic_europe_rounds_raw.csv'):
        if r['funded_year']=='2026':add(r['candidate_url'],'previously_omitted_2026_followup_universe')
    for r in csvrows(DATA/'cp3_republic_europe_identity_review_decisions.csv'):
        if r['review_disposition'].startswith('HELD'):add(r['business_url']+'/sections/about','held_identity_public_about_section')
    return sorted(seen.values(),key=lambda r:(r['platform'],r['url']))
def capture_group(platform,queue,out):
    session=requests.Session()
    session.headers.update({'User-Agent':'VeraResearch/0.6.2 (public investment research; no authentication)'})
    rows=[]; blocked=0
    for item in queue:
        row={**item,'attempted_at':now(),'status':'PENDING','http_status':None,'content_sha256':None}
        if blocked>=5:
            row.update(status='NOT_ATTEMPTED_DOMAIN_CIRCUIT_OPEN',reason='five blocked/error responses; no repeated retries');rows.append(row);continue
        try:
            r=session.get(item['url'], timeout=(10,20), allow_redirects=False);redirects=0
            while r.is_redirect and redirects<4:
                dest=urljoin(r.url,r.headers.get('Location',''))
                if not cleanurl(dest):break
                r=session.get(dest, timeout=(10,20), allow_redirects=False);redirects+=1
            row.update(http_status=r.status_code,final_url=r.url,received_at=now())
            raw=r.content;h=digest(raw);row['content_sha256']=h
            compressed=gzip.compress(raw,mtime=0);target=out/'captures'/f'{h}.html.gz'
            if not target.exists():write_new(target,compressed)
            row['capture_path']=str(target.relative_to(ROOT));row['capture_gzip_sha256']=digest(compressed)
            if r.status_code==200:
                soup=BeautifulSoup(raw,'html.parser');row['title']=soup.title.get_text(' ',strip=True) if soup.title else ''
                for tag in soup(['script','style','noscript']):tag.decompose()
                text=soup.get_text('\n',strip=True);row['text_sha256']=digest(text.encode());tp=out/'captures'/f'{h}.txt.gz'
                if not tp.exists():write_new(tp,gzip.compress(text.encode(),mtime=0))
                row['text_path']=str(tp.relative_to(ROOT));row['text_chars']=len(text);row['status']='PUBLIC_CAPTURED_UNADJUDICATED'
                if re.search(r'^(Just a moment|Access denied|Log in|Login)',row['title'],re.I):row['status']='ACCESS_OR_LOGIN_PAGE';blocked+=1
            else:row['status']='HTTP_ERROR_OR_REDIRECT';blocked+=1
        except requests.RequestException as e:row.update(status='REQUEST_ERROR',error=type(e).__name__+': '+str(e)[:300]);blocked+=1
        rows.append(row)
        with (out/f'journal-{platform}.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
        time.sleep(.35)
    return rows
def main():
    out=DATA/'cp7'/'cycle-1'
    if out.exists():raise SystemExit('Refusing to overwrite CP7 cycle-1')
    out.mkdir(parents=True);queue=build_queue();write_new(out/'queue.json',jbytes(queue))
    write_new(out/'started.json',jbytes({'started_at':now(),'source_commit':os.environ.get('GITHUB_SHA'),'cutoff':'2026-10-09','intent':'real public campaign evidence; not a census or plateau claim'}))
    by=defaultdict(list)
    for r in queue:by[r['platform']].append(r)
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futs={pool.submit(capture_group,p,rs,out):p for p,rs in by.items()}
        for fut in concurrent.futures.as_completed(futs):rows.extend(fut.result())
    rows.sort(key=lambda r:(r['platform'],r['url']));write_new(out/'manifest.json',jbytes(rows))
    from collections import Counter
    summary={'completed_at':now(),'queued':len(queue),'by_platform':{},'rates_promoted':False,'census_completed':False,'research_plateau':False}
    for platform in by:
        rs=[r for r in rows if r['platform']==platform];summary['by_platform'][platform]={'queued':len(rs),'status_counts':dict(Counter(r['status'] for r in rs))}
    write_new(out/'summary.json',jbytes(summary));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
