"""CP9 immutable issuer bridge and source-linked public update collection.
Filing histories are not platform censuses, first-live dates or closure proof.
No authentication, private endpoints or access bypass.
"""
from __future__ import annotations
import csv, gzip, hashlib, io, json, re, time, os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/phase1d'
OUT=DATA/'cp9/cycle-1-issuer-history-updates'
UA='VeraResearch/0.6.4 (arults; 109891188+arults@users.noreply.github.com)'
CUTOFF='2026-10-10'
def now():return datetime.now(timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def jb(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def put(path,b):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(b)
def rows(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def csvnew(path,rs):
    keys=list(dict.fromkeys(k for r in rs for k in r));s=io.StringIO(newline='')
    w=csv.DictWriter(s,fieldnames=keys);w.writeheader();w.writerows(rs);put(path,s.getvalue().encode())
def canon(s):return re.sub('[^a-z0-9]','',s.lower())
def safe(url):
    p=urlparse(url)
    return p.scheme=='https' and not p.username and not p.password and p.hostname in {'data.sec.gov','republic.com','uploads.republic.com','www.khealth.com','khealth.com'}
def checked_source(row):
    p=(ROOT/row['capture_path']).resolve()
    if not p.is_relative_to(ROOT.resolve()):raise ValueError('source path escapes root')
    raw=gzip.decompress(p.read_bytes())
    if sha(raw)!=row['source_content_sha256']:raise ValueError('source content hash mismatch')
    return raw

def bridge():
    out=[]
    for filename,funding in [('cohort_manifest.csv','PRIOR_PHASE1B_CONFIRMED_FUNDED'),('excluded_2020_wefunder_offerings.csv','PRIOR_PHASE1B_UNCONFIRMED_OR_EXCLUDED')]:
        path=ROOT/'data'/filename
        for row in rows(path):
            out.append({**row,'bridge_source':'data/'+filename,'bridge_source_sha256':sha(path.read_bytes()),'bridge_status':funding,'native_first_live_date':None,'native_offering_year':None,'new_live_observation':False,'phase1d_estimation_eligible':False,'scope':'SEC_INITIAL_FORM_C_2020_RECONSTRUCTION_NOT_NATIVE_FIRST_LIVE_CENSUS'})
    keys=[r['offering_key'] for r in out]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate Wefunder offering key')
    if any(not r['initial_form_c_date'].startswith('2020-') for r in out):raise ValueError('unexpected initial Form C year')
    put(OUT/'wefunder_2020_preserved_frame.json',jb(out));return out

def build_queues(frame):
    campaigns=rows(DATA/'cp8/cycle-2-native-outcomes/republic_us_candidate_union.csv')
    sec={};updates=[];docs=[];bindings=[]
    def issuer(cik,name,platform,url):
        if cik and re.fullmatch(r'\d{1,10}',cik):
            cik=str(int(cik));sec.setdefault(cik,{'cik':cik,'url':f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json','associations':[]})['associations'].append({'name':name,'platform':platform,'source_url':url})
    campaigns.sort(key=lambda r:(r['campaign_name']!='Trusst',r['source_url']))
    for row in campaigns:
        raw=checked_source(row);soup=BeautifulSoup(raw,'html.parser');u=row['source_url'];p=urlparse(u)
        if p.hostname!='republic.com' or not re.fullmatch(r'/[\w.-]+',p.path):raise ValueError('noncanonical campaign source')
        root=soup.select_one('.offerings-show[data-segment]');segment={}
        if root:
            try:segment=json.loads(root['data-segment'])
            except (ValueError,KeyError):pass
        matched=segment.get('slug')==p.path.strip('/') and segment.get('url')==u and bool(segment.get('id'))
        bindings.append({'source_url':u,'campaign_name':row['campaign_name'],'legal_name':row['legal_name_from_platform'],'native_offering_id':segment.get('id') if matched else None,'native_slug_bound':matched,'native_state':root.get('data-state') if root else None,'source_sha256':row['source_content_sha256'],'source_path':row['capture_path'],'economic_round_identity_resolved':False,'first_live_date':None})
        for node in soup.select('.js-update_section_placeholder[data-url]'):
            url=urljoin(u,node['data-url'])
            if url==u+'/show_updates':updates.append({'url':url,'campaign_url':u,'legal_name':row['legal_name_from_platform'],'parent_sha256':row['source_content_sha256'],'native_offering_id':segment.get('id') if matched else None})
        for a in soup.select('.offerings-shared-documents_section__document-link[href]'):
            label=a.get_text(' ',strip=True);url=urljoin(u,a['href'])
            if re.search(r'\bForm\s+C\b|SAFE Amendment',label,re.I) and safe(url) and ('/documents/' in url or urlparse(url).hostname=='uploads.republic.com'):
                docs.append({'url':url,'label':label,'campaign_url':u,'parent_sha256':row['source_content_sha256']})
        issuer(row['filing_cik_from_platform_links'],row['legal_name_from_platform'],'republic_us',u)
    for r in frame:issuer(r['issuer_cik'],r['issuer_name'],'wefunder',r['sec_initial_url'])
    updates=list({r['url']:r for r in updates}.values());docs=list({r['url']:r for r in docs}.values())
    put(OUT/'issuer_history_queue.json',jb(list(sec.values())))
    put(OUT/'native_update_queue.json',jb(updates));put(OUT/'public_document_queue.json',jb(docs))
    csvnew(OUT/'republic_native_identifier_bindings.csv',bindings)
    return list(sec.values()),updates,docs,bindings

class PublicClient:
    def __init__(self,group):
        self.group=group;self.errors=0;self.records=[];self.s=requests.Session();self.s.headers.update({'User-Agent':UA,'Accept-Encoding':'gzip, deflate'})
    def get(self,item):
        r={**item,'retrieval_started_at':now(),'source_group':self.group}
        if self.errors>=2:
            r['status']='NOT_ATTEMPTED_SOURCE_CIRCUIT_OPEN';self.records.append(r);return r,None
        if not safe(item['url']):raise ValueError('outside public-source allowlist')
        try:
            time.sleep(.4)
            response=self.s.get(item['url'],timeout=(8,20),allow_redirects=False,stream=True)
            redirects=[]
            for _ in range(3):
                if not response.is_redirect:break
                dest=urljoin(response.url,response.headers.get('Location',''))
                if not safe(dest) or re.search(r'/(?:login|auth|signup|sign_in)(?:/|\?|$)',dest):break
                redirects.append(dest);response.close();response=self.s.get(dest,timeout=(8,20),allow_redirects=False,stream=True)
            body=[];size=0
            for chunk in response.iter_content(65536):
                size+=len(chunk)
                if size>12_000_000:raise ValueError('response byte limit')
                body.append(chunk)
            raw=b''.join(body);response.close();h=sha(raw);gz=gzip.compress(raw,mtime=0);path=OUT/'captures'/f'{h}.bin.gz'
            try:put(path,gz)
            except FileExistsError:
                if path.read_bytes()!=gz:raise ValueError('capture hash collision')
            r.update(http_status=response.status_code,final_url=response.url,redirects=redirects,raw_sha256=h,gzip_sha256=sha(gz),source_path=str(path.relative_to(ROOT)),bytes=len(raw),received_at=now(),content_type=response.headers.get('content-type',''))
            if response.status_code!=200:
                r['status']='HTTP_ERROR_OR_UNFOLLOWED_REDIRECT';self.errors+=1
            elif 'html' in r['content_type']:
                soup=BeautifulSoup(raw,'html.parser');title=soup.title.get_text(' ',strip=True) if soup.title else ''
                if re.search(r'just a moment|access denied|verify you are human|^log in|^sign in',title,re.I):r['status']='ACCESS_PAGE_NOT_EVIDENCE';self.errors+=1
                else:r['status']='PUBLIC_CAPTURED_UNADJUDICATED'
            else:r['status']='PUBLIC_CAPTURED_UNADJUDICATED'
            self.records.append(r);put(OUT/'receipts'/f'{self.group}-{len(self.records):04d}.json',jb(r))
            return r,raw if r['status']=='PUBLIC_CAPTURED_UNADJUDICATED' else None
        except (requests.RequestException,ValueError) as e:
            self.errors+=1;r.update(status='REQUEST_OR_VALIDATION_ERROR',error=type(e).__name__+':'+str(e)[:300]);self.records.append(r)
            put(OUT/'receipts'/f'{self.group}-{len(self.records):04d}.json',jb(r));return r,None

def api_rows(payload):
    d=payload.get('filings',{}).get('recent',payload)
    if not isinstance(d,dict) or not isinstance(d.get('accessionNumber'),list):raise ValueError('missing filing arrays')
    fields=['accessionNumber','filingDate','form','fileNumber','primaryDocument']
    if len({len(d.get(k,[])) for k in fields})!=1:raise ValueError('ragged filing arrays')
    return [{k:d[k][i] for k in fields} for i in range(len(d['form']))]

def histories(queue):
    c=PublicClient('sec-history');identities=[];filings=[]
    for item in queue:
        receipt,raw=c.get(item)
        if raw is None:continue
        try:
            x=json.loads(raw)
            if str(int(x['cik']))!=item['cik'] or not x.get('name'):raise ValueError('CIK or name mismatch')
            names=[x['name']]+[z['name'] for z in x.get('formerNames',[]) if isinstance(z,dict) and z.get('name')]
            related=api_rows(x);extra=x.get('filings',{}).get('files',[]);all_files=True
            for older in extra:
                name=older.get('name','')
                if not re.fullmatch(r'CIK\d{10}-submissions-\d{3}\.json',name):all_files=False;continue
                rr,rb=c.get({'cik':item['cik'],'url':'https://data.sec.gov/submissions/'+name,'parent_sha256':receipt['raw_sha256']})
                if rb is None:all_files=False;continue
                for f in api_rows(json.loads(rb)):
                    f['source_sha256']=rr['raw_sha256'];related.append(f)
            for f in related:
                if f['form'] in {'C','C/A','C-U','C-U/A','C-W','C-AR','C-AR/A','C-TR'} and f['filingDate']<=CUTOFF:
                    filings.append({**f,'cik':item['cik'],'issuer_name':x['name'],'source_sha256':f.get('source_sha256',receipt['raw_sha256']),'filing_date_is_not_first_live':True,'closure_inferred':False})
            for a in item['associations']:
                identities.append({**a,'cik':item['cik'],'regulator_name':x['name'],'name_exact_normalized_match':canon(a['name']) in {canon(n) for n in names},'all_submissions_pages_captured':all_files,'source_sha256':receipt['raw_sha256'],'status':'REGULATOR_IDENTITY_CANDIDATE_NOT_ECONOMIC_ROUND','native_first_live_date':None})
        except (ValueError,TypeError,KeyError) as e:identities.append({'cik':item['cik'],'status':'SCHEMA_OR_IDENTITY_HOLD','error':str(e)[:200]})
    put(OUT/'issuer_identity_candidates.json',jb(identities));put(OUT/'regcf_filing_history_candidates.json',jb(filings));return c.records

def updates(queue):
    c=PublicClient('republic-updates');observations=[]
    for item in queue:
        receipt,raw=c.get(item)
        if raw is None:continue
        soup=BeautifulSoup(raw,'html.parser')
        for tag in soup(['script','style','noscript']):tag.decompose()
        text=soup.get_text('\n',strip=True);path=OUT/'texts'/f'{receipt['raw_sha256']}.txt'
        if not path.exists():put(path,text.encode())
        dates=sorted(set([n.get('datetime') for n in soup.find_all('time',datetime=True)]+[n.get('data-time') for n in soup.find_all(attrs={'data-time':True})]))
        links=sorted(set(urljoin(item['campaign_url'],a['href']) for a in soup.find_all('a',href=True) if a['href'].startswith('/'+urlparse(item['campaign_url']).path.strip('/')+'/')))
        observations.append({**item,'source_sha256':receipt['raw_sha256'],'source_path':receipt['source_path'],'text_path':str(path.relative_to(ROOT)),'text_chars':len(text),'raw_dom_times':dates,'source_linked_urls':links,'status':'PUBLIC_FRAGMENT_REQUIRES_EVENT_AND_DATE_ADJUDICATION','estimation_eligible':False})
    put(OUT/'native_update_fragment_candidates.json',jb(observations));return c.records

def primary():
    c=PublicClient('acquirer');c.get({'url':'https://www.khealth.com/blog/about-k/k-health-acquires-trusst/','company':'Trusst','purpose':'Acquisition announcement; NOT exact closing date or investor cashflow date','discovery':'Official acquirer result discovered by web search on 2026-10-10'});return c.records

def main():
    if OUT.exists():raise SystemExit('Refusing CP9 checkpoint overwrite')
    OUT.mkdir(parents=True)
    before={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/'data').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
    put(OUT/'preserved_before.json',jb(before))
    put(OUT/'protocol.json',jb({'started_at':now(),'source_commit':os.environ.get('GITHUB_SHA'),'version':'0.6.4-dev.research.1','cutoff':CUTOFF,'Jev_routes_probability':1.0,'Jev_routes_confidence':1.0,'source_scope':'Separate regulator identity/history bridge and on-platform public updates. No original study definition changes.','rules':['No access bypass or authentication.','Two error circuit per source; no blocked ZIP retries.','Old frame import is not new live evidence.','C-TR not closure; Form C not funding; filing date not first-live.','Announcement not transaction or payout date.','No economic-round or outcome promotion without independent adjudication.','No prior promotion, no main merge, no plateau inference.']}))
    frame=bridge();sq,uq,dq,bindings=build_queues(frame)
    with ThreadPoolExecutor(max_workers=3) as p:
        fut=[p.submit(histories,sq),p.submit(updates,uq),p.submit(primary)];manifest=[r for f in fut for r in f.result()]
    put(OUT/'manifest.json',jb(manifest))
    preserved=all((ROOT/p).is_file() and sha((ROOT/p).read_bytes())==h for p,h in before.items())
    from collections import Counter
    ident=json.loads((OUT/'issuer_identity_candidates.json').read_text());fil=json.loads((OUT/'regcf_filing_history_candidates.json').read_text());ups=json.loads((OUT/'native_update_fragment_candidates.json').read_text())
    summary={'completed_at':now(),'version':'0.6.4-dev.research.1','preserved_existing_data_files':len(before),'all_previous_data_unchanged':preserved,'wefunder_preserved_frame_rows':len(frame),'wefunder_prior_funded_rows':sum(r['bridge_status']=='PRIOR_PHASE1B_CONFIRMED_FUNDED' for r in frame),'wefunder_prior_unconfirmed_or_excluded':sum(r['bridge_status']=='PRIOR_PHASE1B_UNCONFIRMED_OR_EXCLUDED' for r in frame),'republic_native_offering_ids_bound':sum(r['native_slug_bound'] for r in bindings),'native_offering_id_is_not_economic_round':True,'issuer_histories_queued':len(sq),'issuer_identity_candidate_links':len(ident),'regcf_filing_history_rows':len(fil),'native_update_fragments_captured':len(ups),'public_documents_discovered_not_yet_fetched':len(dq),'source_status_counts':dict(Counter((r['source_group']+':'+r['status']) for r in manifest)),'four_native_censuses_complete':False,'rates_promoted':False,'research_plateau':False,'new_results_require_adjudication':True}
    if not preserved:raise AssertionError('previous data changed')
    put(OUT/'summary.json',jb(summary));print(jb(summary).decode())
if __name__=='__main__':main()
