"""CP9 cycle3: bounded genuine source recovery, not a blocked-source retry.
An oversized public PDF is a document-local hold, not an access-control failure.
"""
from __future__ import annotations
import gzip,json,re,time,os
from pathlib import Path
from urllib.parse import urlparse,urljoin
from collections import Counter
from bs4 import BeautifulSoup
import requests
from . import capture_cp9_evidence as cap
from .reconcile_cp9_timelines import decode,milestones
from .analyze_cp7_empirical import parse_republic_us
ROOT=cap.ROOT;BASE=ROOT/'data/phase1d/cp9';OUT=BASE/'cycle-3-bounded-documents-linked-rounds'
CAMPAIGNS=[{'url':'https://republic.com/unbanked','discovery':'Old Ternio issuer explicitly links new Unbanked campaign; canonical page independently discovered by web search. Legal conversion not assumed.'},{'url':'https://republic.com/quickloadz','discovery':'QuickLoadz2022 issuer references second campaign; canonical2024 page independently discovered by web search.'},{'url':'https://republic.com/alpha-flow','discovery':'Exact Campaign3 link in hash-captured September6,2022 AlphaFlow issuer post.'}]
def safe(u):
 p=urlparse(u);return cap.safe(u) or (p.scheme=='https' and p.hostname=='uploads.republic.co' and not p.username and not p.password)
class BoundedClient:
 def __init__(self,group,budget):
  self.group=group;self.budget=budget;self.downloaded=0;self.errors=0;self.records=[];self.s=requests.Session();self.s.headers.update({'User-Agent':cap.UA,'Accept-Encoding':'gzip, deflate'})
 def get(self,item):
  r={**item,'source_group':self.group,'retrieval_started_at':cap.now()};response=None
  try:
   if self.errors>=2:r['status']='NOT_ATTEMPTED_ACCESS_CIRCUIT';return r,None
   if self.downloaded>=self.budget:r['status']='NOT_ATTEMPTED_BYTE_BUDGET';return r,None
   if not safe(item['url']):raise ValueError('public allowlist violation')
   time.sleep(.45);started=time.monotonic();response=self.s.get(item['url'],timeout=(8,25),stream=True,allow_redirects=False)
   redirects=[]
   for _ in range(3):
    if not response.is_redirect:break
    dest=urljoin(response.url,response.headers.get('Location',''))
    if not safe(dest) or re.search(r'/(login|auth|signup|sign_in)(/|\?|$)',dest):break
    redirects.append(dest);response.close();response=self.s.get(dest,timeout=(8,25),stream=True,allow_redirects=False)
   r.update(http_status=response.status_code,final_url=response.url,redirects=redirects,content_type=response.headers.get('content-type',''))
   rawparts=[];size=0
   for chunk in response.iter_content(65536):
    size+=len(chunk);self.downloaded+=len(chunk)
    if size>48_000_000 or self.downloaded>self.budget:
     r.update(status='DOCUMENT_LOCAL_BYTE_LIMIT_HOLD',downloaded_bytes=size);return r,None
    if time.monotonic()-started>120:r.update(status='DOCUMENT_LOCAL_TIME_LIMIT_HOLD',downloaded_bytes=size);return r,None
    rawparts.append(chunk)
   raw=b''.join(rawparts);h=cap.sha(raw);packed=gzip.compress(raw,mtime=0);p=OUT/'captures'/f'{h}.bin.gz'
   try:cap.put(p,packed)
   except FileExistsError:
    if p.read_bytes()!=packed:raise ValueError('capture collision')
   r.update(source_path=str(p.relative_to(ROOT)),raw_sha256=h,gzip_sha256=cap.sha(packed),bytes=len(raw),received_at=cap.now())
   if response.status_code!=200:
    r['status']='HTTP_ERROR_OR_UNFOLLOWED_REDIRECT'
    if response.status_code in {401,403,429} or response.status_code>=500:self.errors+=1
    return r,None
   title=''
   if 'html' in r['content_type']:
    s=BeautifulSoup(raw,'html.parser');title=s.title.get_text(' ',strip=True) if s.title else ''
   if re.search(r'just a moment|access denied|verify you are human|^log in|^sign in',title,re.I):
    r['status']='ACCESS_PAGE_NOT_EVIDENCE';self.errors+=1;return r,None
   r['status']='PUBLIC_CAPTURED_UNADJUDICATED';return r,raw
  except requests.RequestException as e:
   self.errors+=1;r.update(status='NETWORK_ERROR',error=type(e).__name__+':'+str(e)[:200]);return r,None
  finally:
   if response is not None:response.close()
   self.records.append(r);cap.put(OUT/'receipts'/f'{self.group}-{len(self.records):04d}.json',cap.jb(r))

def main():
 if OUT.exists():raise SystemExit('Refusing cycle3 overwrite')
 OUT.mkdir(parents=True)
 before={str(p.relative_to(ROOT)):cap.sha(p.read_bytes()) for p in (ROOT/'data').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
 cap.put(OUT/'preserved_before.json',cap.jb(before))
 cap.put(OUT/'protocol.json',cap.jb({'started_at':cap.now(),'source_commit':os.getenv('GITHUB_SHA'),'version':'0.6.4-dev.research.3','Jev_choice':'bounded_resume_and_new_campaigns','Jev_selection_probability':1.0,'Jev_confidence':1.0,'limits':{'document_bytes':48000000,'all_document_download_bytes':300000000,'per_document_seconds':120},'rules':['Only incomplete/size-held docs resumed. Existing validcaptures not downloaded again.','Local size/time hold does not trigger source-wide access circuit.','Two actual access/network errors stop source; no authentication or blockedSEC retries.','New campaigns identified by issuer links and native discovery, not random slug guesses.','All fetched content unadjudicated; SAFE caps never priced followon success.','Previous files immutable; no rates, main merge or plateau.']}))
 c=BoundedClient('linked-campaigns',24000000);new=[];extra_docs=[];timelines=[]
 for item in CAMPAIGNS:
  r,raw=c.get(item)
  if raw is None:continue
  parsed=parse_republic_us(raw,{'url':item['url'],'final_url':r['final_url'],'content_sha256':r['raw_sha256'],'capture_path':r['source_path']})
  if parsed:new.append(parsed)
  s=BeautifulSoup(raw,'html.parser')
  root=s.select_one('.offerings-show[data-segment]');seg={}
  if root:
   try:seg=json.loads(root['data-segment'])
   except ValueError:pass
  for el in s.select('.js-update_section_placeholder[data-url]'):
   url=urljoin(item['url'],el['data-url'])
   if url!=item['url']+'/show_updates':continue
   rr,rb=c.get({'url':url,'campaign_url':item['url'],'parent_sha256':r['raw_sha256']})
   if rb is None:continue
   try:
    html,ss=decode(rb);launch,close,ms=milestones(html,ss)
    binding=bool(parsed and parsed['successful_close_date']==close and seg.get('url')==item['url'] and seg.get('slug')==urlparse(item['url']).path.strip('/') and seg.get('id'))
    timelines.append({'campaign_url':item['url'],'first_live_date':launch,'offering_year':int(launch[:4]),'native_completion_date':close,'date_fields_verified':binding,'native_offering_id':seg.get('id'),'source_path':rr['source_path'],'source_sha256':rr['raw_sha256'],'parent_sha256':r['raw_sha256'],'milestones':ms,'year_in_study':2020<=int(launch[:4])<=2025,'estimation_eligible':False,'census_complete':False})
   except (ValueError,KeyError,TypeError) as e:timelines.append({'campaign_url':item['url'],'status':'TIMELINE_SCHEMA_HOLD','error':str(e)[:180],'source_sha256':rr['raw_sha256']})
  for a in s.select('.offerings-shared-documents_section__document-link[href]'):
   label=a.get_text(' ',strip=True);u=urljoin(item['url'],a['href'])
   if re.search(r'\bForm\s*C\b',label,re.I) and safe(u):extra_docs.append({'url':u,'label':label,'campaign_url':item['url'],'parent_sha256':r['raw_sha256'],'discovery':'Exactnewcampaignpublicdocumentlink'})
 previous=json.loads((BASE/'cycle-2-documents-posts/manifest.json').read_text())
 unfinished=[{k:v for k,v in r.items() if k in {'url','label','campaign_url','parent_sha256'}} for r in previous if r['source_group']=='native-documents' and r['status'] in {'NOT_ATTEMPTED_SOURCE_CIRCUIT_OPEN','REQUEST_OR_VALIDATION_ERROR'}]
 queue=list({r['url']:r for r in extra_docs+unfinished}.values());cap.put(OUT/'document_queue.json',cap.jb(queue))
 d=BoundedClient('resumed-public-documents',300000000);docs=[]
 for item in queue:
  r,raw=d.get(item)
  if raw is not None:docs.append({**item,'source_path':r['source_path'],'source_sha256':r['raw_sha256'],'bytes':r['bytes'],'pdf_magic_verified':raw.startswith(b'%PDF-'),'status':'PUBLIC_DOCUMENT_CONTENT_ADJUDICATION_PENDING','identity_admitted':False,'estimation_eligible':False})
 cap.put(OUT/'new_campaign_candidates.json',cap.jb(new));cap.put(OUT/'new_campaign_timelines.json',cap.jb(timelines));cap.put(OUT/'document_candidates.json',cap.jb(docs));cap.put(OUT/'manifest.json',cap.jb(c.records+d.records))
 intact=all((ROOT/p).is_file() and cap.sha((ROOT/p).read_bytes())==h for p,h in before.items())
 if not intact:raise AssertionError('Prior evidence changed')
 summary={'completed_at':cap.now(),'version':'0.6.4-dev.research.3','prior_data_files_preserved':len(before),'all_prior_data_unchanged':intact,'new_campaign_pages_parsed':len(new),'new_timelines_parsed':len(timelines),'new_timeline_pairs_verified':sum(r.get('date_fields_verified',False) for r in timelines),'new_public_document_captures':len(docs),'new_pdf_magic_verified':sum(r['pdf_magic_verified'] for r in docs),'document_downloaded_bytes_including_partial_holds':d.downloaded,'source_status_counts':dict(Counter(r['source_group']+':'+r.get('status','UNHANDLED') for r in c.records+d.records)),'rates_promoted':False,'census_complete':False,'research_plateau':False}
 cap.put(OUT/'summary.json',cap.jb(summary));print(cap.jb(summary).decode())
if __name__=='__main__':main()
