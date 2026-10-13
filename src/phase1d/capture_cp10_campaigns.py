"""CP10 second empirical collection: native campaign validation and large PDFs.
Current sitemap omissions remain explicit. No user profiles or access bypass.
"""
from __future__ import annotations
import csv,gzip,hashlib,json,re,time,threading,os
from pathlib import Path
from urllib.parse import urlparse,urljoin
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from bs4 import BeautifulSoup
import requests
from . import capture_cp9_cycle3 as old
from .capture_cp9_evidence import put,jb,sha,now
from .reconcile_cp9_timelines import decode,MilestoneOracle,date
from .analyze_cp7_empirical import parse_republic_us
ROOT=old.ROOT;BASE=ROOT/'data/phase1d/cp10';OUT=BASE/'collection-2-campaigns-large-docs'
lock=threading.Lock();next_time=0.;access_errors=0

def limited_get(client,item):
 global next_time,access_errors
 with lock:
  if access_errors>=2:
   r={**item,'source_group':client.group,'status':'NOT_ATTEMPTED_SHARED_SOURCE_ACCESS_CIRCUIT'};client.records.append(r);put(OUT/'receipts'/f'{client.group}-{len(client.records):04d}.json',jb(r));return r,None
  delay=max(0,next_time-time.monotonic())
  if delay:time.sleep(delay)
  next_time=time.monotonic()+.55
 r,raw=client.get(item)
 if r.get('http_status') in {401,403,429} or r['status']=='NETWORK_ERROR':
  with lock:access_errors+=1
 return r,raw

def parse_timeline(raw):
 h,s=decode(raw);a=[]
 for node in s.select('article.offerings-updates-shared-milestone_card'):
  d=node.select_one('.offerings-updates-shared-milestone_card__date-day-month');y=node.select_one('.offerings-updates-shared-milestone_card__date-year');t=node.select_one('.offerings-updates-shared-milestone_card__title')
  if not(d and y and t):raise ValueError('incomplete native milestone')
  a.append((date(d.get_text(' ',strip=True),y.get_text(' ',strip=True)),t.get_text(' ',strip=True)))
 oracle=MilestoneOracle();oracle.feed(h)
 if a!=oracle.out:raise ValueError('independent native milestone parser disagreement')
 if any(d>'2026-10-10' for d,t in a):raise ValueError('milestone after frozen cutoff')
 launches=[d for d,t in a if t.startswith('Launched')];closes=[d for d,t in a if t.startswith('Successfully raised')]
 if len(launches)>1 or len(closes)>1:raise ValueError('ambiguous repeated launch/close')
 first=launches[0] if launches else None;closed=closes[0] if closes else None
 if first and closed and first>closed:raise ValueError('reversed campaign chronology')
 return {'first_live_date':first,'successful_completion_date':closed,'offering_year':int(first[:4]) if first else None,'year_in_study':bool(first and '2020-01-01'<=first<='2025-12-31'),'milestones':a,'independent_parsers_agree':True}

def worker(number,queue):
 c=old.BoundedClient('campaign-worker-'+str(number),1400000000);records=[]
 for item in queue:
  r,raw=limited_get(c,item)
  row={**item,'classification':'SOURCE_UNAVAILABLE','estimation_eligible':False,'historical_census_complete':False}
  if raw is None:row['request_status']=r['status'];records.append(row);continue
  row.update(source_path=r['source_path'],source_sha256=r['raw_sha256'],final_url=r['final_url'])
  s=BeautifulSoup(raw,'html.parser');root=s.select_one('.offerings-show[data-segment]');segment={}
  if root:
   try:segment=json.loads(root['data-segment'])
   except (ValueError,TypeError):pass
  parsed=parse_republic_us(raw,{'url':item['url'],'final_url':r['final_url'],'content_sha256':r['raw_sha256'],'capture_path':r['source_path']})
  canonical=item['url'].rstrip('/')
  if r['final_url'].rstrip('/')!=canonical:
   row.update(classification='REDIRECT_ALIAS_OR_SCOPE_HOLD',native_segment_id=segment.get('id'),native_segment_url=segment.get('url'));records.append(row);continue
  bound=bool(segment.get('id') and segment.get('slug')==urlparse(canonical).path.strip('/') and segment.get('url','').rstrip('/')==canonical)
  if not bound:
   row.update(classification='PUBLIC_NON_CAMPAIGN_OR_UNRESOLVED_SCHEMA',native_fields_candidate=parsed,page_title=s.title.get_text(' ',strip=True) if s.title else None);records.append(row);continue
  row.update(classification='NATIVE_CAMPAIGN_IDENTIFIER_BOUND',native_offering_id=segment['id'],native_state=root.get('data-state'),fields=parsed,first_live_date=None,successful_completion_date=None,offering_year=None,year_in_study=False,date_fields_verified=False,company_economic_round_identity_verified=False)
  links=[urljoin(canonical,n['data-url']) for n in s.select('.js-update_section_placeholder[data-url]')]
  if canonical+'/show_updates' in links:
   tr,tb=limited_get(c,{'url':canonical+'/show_updates','campaign_url':canonical,'parent_sha256':r['raw_sha256'],'discovery':'Exact source-linked public native timeline'})
   row['timeline_request_status']=tr['status']
   if tb is not None:
    row.update(timeline_source_path=tr['source_path'],timeline_source_sha256=tr['raw_sha256'])
    try:
     timeline=parse_timeline(tb);row.update(timeline)
     parent_close=(parsed or {}).get('successful_close_date')
     mismatch=bool(parent_close and parent_close!=timeline['successful_completion_date'])
     row['date_fields_verified']=bool(timeline['first_live_date'] and not mismatch)
     if mismatch:row['date_hold']='NATIVE_PARENT_AND_TIMELINE_CLOSE_DISAGREE'
     elif not timeline['first_live_date']:row['date_hold']='NO_UNIQUE_NATIVE_LAUNCH_MILESTONE'
    except (ValueError,KeyError,TypeError) as e:row['date_hold']='TIMELINE_SCHEMA_OR_CHRONOLOGY:'+str(e)[:160]
  else:row['date_hold']='NO_EXACT_SOURCE_LINKED_TIMELINE'
  records.append(row)
  put(OUT/'campaign_receipts'/f'{number}-{len(records):04d}.json',jb(row))
 put(OUT/f'campaign_worker_{number}.json',jb(records));return records,c.records

def large_documents():
 manifest=json.loads((BASE/'collection-1/manifest.json').read_text());queue=[{k:r[k] for k in ['url','label','campaign_url','parent_sha256'] if k in r} for r in manifest if r['status']=='DOCUMENT_LOCAL_BYTE_LIMIT_HOLD'];assert len(queue)==5
 put(OUT/'large_document_queue.json',jb(queue));rows=[];errors=0
 session=requests.Session();session.headers.update({'User-Agent':old.cap.UA,'Accept-Encoding':'identity'})
 for item in queue:
  record={**item,'status':'UNSTARTED','source_group':'large-documents','chunks':[],'estimation_eligible':False,'full_semantic_review_complete':False};response=None
  try:
   if errors>=2:record['status']='NOT_ATTEMPTED_ACCESS_CIRCUIT';continue
   time.sleep(.6);started=time.monotonic();response=session.get(item['url'],timeout=(8,30),stream=True,allow_redirects=False)
   for _ in range(3):
    if not response.is_redirect:break
    dest=urljoin(response.url,response.headers.get('Location',''))
    if not old.safe(dest) or re.search(r'/(login|auth|sign_in)(/|\?|$)',dest):break
    response.close();response=session.get(dest,timeout=(8,30),stream=True,allow_redirects=False)
   record.update(http_status=response.status_code,final_url=response.url,content_type=response.headers.get('content-type',''),started_at=now())
   if response.status_code!=200:
    record['status']='HTTP_OR_REDIRECT_HOLD';errors+=int(response.status_code in {401,403,429} or response.status_code>=500);continue
   digest=hashlib.sha256();buf=bytearray();total=0;prefix=b''
   def chunk_save(b):
    h=sha(b);packed=gzip.compress(b,mtime=0);path=OUT/'document_chunks'/f'{h}.bin.gz'
    try:put(path,packed)
    except FileExistsError:
     if path.read_bytes()!=packed:raise ValueError('chunk hash collision')
    record['chunks'].append({'path':str(path.relative_to(ROOT)),'raw_sha256':h,'gzip_sha256':sha(packed),'raw_bytes':len(b)})
   for block in response.iter_content(1048576):
    if not prefix:prefix=block[:8]
    digest.update(block);buf.extend(block);total+=len(block)
    while len(buf)>=32000000:chunk_save(bytes(buf[:32000000]));del buf[:32000000]
    if total>256000000 or time.monotonic()-started>180:
     record['status']='LARGE_DOCUMENT_INDIVIDUAL_LIMIT_HOLD';break
   if buf:chunk_save(bytes(buf))
   record.update(raw_bytes=total,raw_sha256=digest.hexdigest(),pdf_magic_verified=prefix.startswith(b'%PDF-'),capture_format='ORDERED_GZIP_CHUNKS_RECONSTRUCT_RAW',received_at=now())
   length=response.headers.get('content-length')
   if record['status']!='LARGE_DOCUMENT_INDIVIDUAL_LIMIT_HOLD':
    if length and not response.headers.get('content-encoding') and int(length)!=total:record['status']='HTTP_CONTENT_LENGTH_MISMATCH'
    else:record['status']='PUBLIC_FULL_DOCUMENT_CAPTURED' if record['pdf_magic_verified'] else 'NON_PDF_RESPONSE_HOLD'
  except (requests.RequestException,ValueError) as e:
   record.update(status='REQUEST_OR_INTEGRITY_HOLD',error=type(e).__name__+':'+str(e)[:200]);errors+=int(isinstance(e,requests.RequestException))
  finally:
   if response is not None:response.close()
   rows.append(record);put(OUT/'large_document_receipts'/f'{len(rows):03d}.json',jb(record))
 put(OUT/'large_document_manifest.json',jb(rows));return rows

def main():
 if OUT.exists():raise SystemExit('Refusing CP10 collection2 overwrite')
 OUT.mkdir(parents=True);old.OUT=OUT
 before={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/'data').rglob('*') if p.is_file() and not p.is_relative_to(OUT)};put(OUT/'preserved_before.json',jb(before))
 entries=json.loads((BASE/'collection-1/sitemap_url_entries.json').read_text());native={r['url'].rstrip('/'):r for r in entries if re.fullmatch('/[A-Za-z0-9._-]+/?',urlparse(r['url']).path)}
 with (ROOT/'data/phase1d/cp9/adjudication/republic_us_candidate_union.csv').open(newline='',encoding='utf-8') as f:known=list(csv.DictReader(f))
 known_urls={r['source_url'].rstrip('/') for r in known};missing=sorted(known_urls-set(native))
 queue=[{'url':u,'sitemap_url':r['sitemap_url'],'sitemap_sha256':r['sitemap_sha256'],'discovery':'Published native single-segment path; not assumed campaign, no /@profile collection'} for u,r in sorted(native.items()) if u not in known_urls]
 assert len(native)==1353 and len(queue)==1242 and len(missing)==14
 put(OUT/'native_nonprofile_queue.json',jb(queue));put(OUT/'historical_campaigns_missing_current_sitemap.json',jb({'known_campaigns_absent':missing,'count':len(missing),'action':'All previous records preserved. Current sitemap is demonstrably not complete historical coverage.'}))
 put(OUT/'protocol.json',jb({'version':'0.6.5-dev.research.2','source_commit':os.getenv('GITHUB_SHA'),'started_at':now(),'Jev_choice':'A_campaign_validation_first_B_in_parallel','selection_probability':1.0,'confidence':1.0,'rules':['No /@individual profile fetches. Single-segment events/noncampaigns explicitly classified.','Do not replace historical missing campaigns with current-only frame.','Exact native DOM identifier/slug/url and source-linked milestones, with independent date parser.','Shared source circuit after2HTTPaccess/networkerrors; aliases and missingdates held.','Five previously size-held public PDFs stored as ordered32MBgzipchunks; max256MBand180sec perfile.','No outcome, economicround, historical census or numerical-prior promotion.']}))
 with ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(worker,i,queue[i::3]) for i in range(3)];large=pool.submit(large_documents)
  done=[f.result() for f in futures];large_rows=large.result()
 records=[r for pair in done for r in pair[0]];receipts=[r for pair in done for r in pair[1]];put(OUT/'native_page_classifications.json',jb(records));put(OUT/'manifest.json',jb(receipts))
 campaigns=[r for r in records if r['classification']=='NATIVE_CAMPAIGN_IDENTIFIER_BOUND'];put(OUT/'native_campaign_candidates.json',jb(campaigns))
 unchanged=all((ROOT/p).is_file() and sha((ROOT/p).read_bytes())==h for p,h in before.items());assert unchanged,'Prior evidence changed'
 summary={'checkpoint':'CP10','version':'0.6.5-dev.research.2','completed_at':now(),'prior_data_files_preserved':len(before),'all_prior_data_unchanged':unchanged,'new_single_path_URLs_classified':len(records),'new_native_identifier_bound_campaigns':len(campaigns),'new_campaign_dates_source_verified':sum(r.get('date_fields_verified',False) for r in campaigns),'new_launch_year_eligible_candidates':sum(r.get('year_in_study',False) and r.get('date_fields_verified',False) for r in campaigns),'new_successful_completion_milestones':sum(bool(r.get('successful_completion_date')) for r in campaigns),'known_legacy_campaigns_retained':len(known),'known_legacy_campaigns_missing_current_sitemap':len(missing),'classification_counts':dict(Counter(r['classification'] for r in records)),'source_status_counts':dict(Counter(r['status'] for r in receipts)),'large_document_requests':len(large_rows),'large_documents_fully_captured':sum(r['status']=='PUBLIC_FULL_DOCUMENT_CAPTURED' for r in large_rows),'large_document_holds':sum(r['status']!='PUBLIC_FULL_DOCUMENT_CAPTURED' for r in large_rows),'all_current_single_path_candidates_attempted':all(not r['status'].startswith('NOT_ATTEMPTED') for r in receipts),'full_historical_census_complete':False,'rates_promoted':False,'phase_complete':False,'global_plateau':False,'limitation':'Native campaign fields and current discovery-frame validation are not canonical economic-round identities, dated outcomes, or complete historical population.'}
 put(OUT/'summary.json',jb(summary));print(jb(summary).decode())
if __name__=='__main__':main()
