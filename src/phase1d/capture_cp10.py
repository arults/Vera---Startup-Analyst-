"""CP10 actual source expansion. Current sitemap != all historical offerings.
No credential use, authentication bypass, unrelated hosts or silent data overwrite.
"""
from __future__ import annotations
import csv,gzip,json,re,io,os
from pathlib import Path
from urllib.parse import urlparse,urljoin
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from defusedxml import ElementTree as ET
import fitz
from pypdf import PdfReader
from . import capture_cp9_cycle3 as old
from .capture_cp9_evidence import put,jb,sha,now
ROOT=old.ROOT
OUT=ROOT/'data/phase1d/cp10/collection-1'
INDEX='https://republic.com/sitemaps/sitemap.xml'

def sitemap(client,approved):
 queue=[{'url':INDEX,'discovery':'CP1 successful native sitemap-index URL; exact index children may have been excluded by an over-narrow host filter.'}];seen=set();nodes=[];entries=[];excluded=[]
 while queue and len(seen)<100:
  item=queue.pop(0)
  if item['url'] in seen:continue
  seen.add(item['url']);r,raw=client.get(item)
  if raw is None:continue
  try:
   decoded=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw
   if len(decoded)>80000000:raise ValueError('decompressed sitemap byte limit')
   tree=ET.fromstring(decoded);kind=tree.tag.rsplit('}',1)[-1]
   if kind not in {'sitemapindex','urlset'}:raise ValueError('not a sitemap XML root')
   locs=[]
   for node in tree:
    loc=next((x.text.strip() for x in node if x.tag.rsplit('}',1)[-1]=='loc' and x.text),None)
    lastmod=next((x.text.strip() for x in node if x.tag.rsplit('}',1)[-1]=='lastmod' and x.text),None)
    if loc:locs.append((urljoin(item['url'],loc),lastmod))
   nodes.append({'url':item['url'],'kind':kind,'loc_count':len(locs),'source_path':r['source_path'],'source_sha256':r['raw_sha256']})
   if kind=='sitemapindex':
    for u,lastmod in locs:
     p=urlparse(u);host=p.hostname or ''
     public_host=host in {'republic.com','www.republic.com','republic.co'} or any(host.endswith(s) for s in ['.republic.com','.republic.co','.amazonaws.com','.cloudfront.net'])
     if p.scheme=='https' and not p.username and not p.password and p.port in {None,443} and public_host and re.search(r'\.xml(?:\.gz)?$',p.path,re.I):
      approved.add(u);queue.append({'url':u,'parent_url':item['url'],'parent_sha256':r['raw_sha256'],'discovery':'Exact child URL published in native sitemap index; public-CDN resource only.'})
     else:excluded.append({'url':u,'parent_url':item['url'],'reason':'PUBLIC_SOURCE_HOST_SCHEME_OR_SITEMAP_PATH_HOLD'})
   else:
    for u,lastmod in locs:
     p=urlparse(u)
     if p.scheme=='https' and p.hostname in {'republic.com','www.republic.com'} and not p.username:
      entries.append({'url':u,'lastmod_metadata_not_launch':lastmod,'sitemap_url':item['url'],'sitemap_sha256':r['raw_sha256'],'campaign_identity_verified':False,'historical_census_eligible':False})
     else:excluded.append({'url':u,'parent_url':item['url'],'reason':'NON_NATIVE_URL_ENTRY'})
  except (ValueError,ET.ParseError,OSError) as e:nodes.append({'url':item['url'],'error':str(e)[:200],'source_sha256':r['raw_sha256']})
 unique={r['url']:r for r in entries};put(OUT/'sitemap_nodes.json',jb(nodes));put(OUT/'sitemap_url_entries.json',jb(list(unique.values())));put(OUT/'sitemap_excluded.json',jb(excluded));put(OUT/'sitemap_pending_children.json',jb(queue))
 published_children_done=not queue and not any(r.get('reason')=='PUBLIC_SOURCE_HOST_SCHEME_OR_SITEMAP_PATH_HOLD' for r in excluded) and len(nodes)==len(seen) and all('error' not in n for n in nodes)
 summary={'root_url':INDEX,'index_documents_parsed':sum(n.get('kind')=='sitemapindex' for n in nodes),'urlset_documents_parsed':sum(n.get('kind')=='urlset' for n in nodes),'distinct_native_URLs':len(unique),'pending_child_requests':len(queue),'excluded_entries_or_children':len(excluded),'captured_published_sitemap_tree_complete':published_children_done,'platform_historical_census_complete':False,'lastmod_is_not_launch_date':True}
 put(OUT/'sitemap_summary.json',jb(summary));return summary

def document_review(raw,item,receipt):
 pdf=raw.startswith(b'%PDF-');r={**item,'source_path':receipt['source_path'],'source_sha256':receipt['raw_sha256'],'bytes':len(raw),'pdf_magic_verified':pdf,'full_semantic_review_complete':False,'estimation_eligible':False}
 if not pdf:r['status']='NON_PDF_DOCUMENT_RESPONSE_REVIEW_REQUIRED';return r
 try:
  a=fitz.open(stream=raw,filetype='pdf');b=PdfReader(io.BytesIO(raw));texts=[];comparisons=[]
  if len(a)!=len(b.pages):raise ValueError('independent PDF page-count disagreement')
  for i in range(min(4,len(a))):
   x=' '.join(a[i].get_text().split());y=' '.join((b.pages[i].extract_text() or '').split());texts.append({'page':i+1,'pymupdf_text':x,'pypdf_text':y})
   comparisons.append({'page':i+1,'pymupdf_chars':len(x),'pypdf_chars':len(y),'pymupdf_sha256':sha(x.encode()),'pypdf_sha256':sha(y.encode()),'both_have_text':len(x)>40 and len(y)>40})
  path=OUT/'document_previews'/f"{receipt['raw_sha256']}.json";put(path,jb(texts))
  r.update(page_count=len(a),preview_path=str(path.relative_to(ROOT)),preview_checks=comparisons,status='PUBLIC_PDF_CAPTURE_AND_DUAL_PARSER_PREVIEW_NOT_SEMANTIC_ADMISSION')
 except Exception as e:r.update(status='PDF_PARSE_OR_ENCRYPTION_HOLD',error=type(e).__name__+':'+str(e)[:200])
 return r

def documents(client):
 manifest=json.loads((ROOT/'data/phase1d/cp9/cycle-3-bounded-documents-linked-rounds/manifest.json').read_text())
 queue=[{k:r[k] for k in ['url','label','campaign_url','parent_sha256'] if k in r} for r in manifest if r['source_group']=='resumed-public-documents' and r['status'] in {'NOT_ATTEMPTED_BYTE_BUDGET','DOCUMENT_LOCAL_BYTE_LIMIT_HOLD'}]
 assert len(queue)==106 and len({r['url'] for r in queue})==106
 put(OUT/'document_queue.json',jb(queue));rows=[]
 for item in queue:
  receipt,raw=client.get(item)
  if raw is not None:
   row=document_review(raw,item,receipt);rows.append(row);put(OUT/'document_receipts'/f'{len(rows):04d}.json',jb(row))
 put(OUT/'document_candidates.json',jb(rows))
 return {'queue_count':len(queue),'public_document_responses_captured':len(rows),'PDFs_captured':sum(r['pdf_magic_verified'] for r in rows),'dual_parser_previews':sum('preview_path' in r for r in rows),'non_PDF_or_parse_holds':sum(r['status']!='PUBLIC_PDF_CAPTURE_AND_DUAL_PARSER_PREVIEW_NOT_SEMANTIC_ADMISSION' for r in rows),'downloaded_bytes':client.downloaded,'not_attempted':sum(r['status'].startswith('NOT_ATTEMPTED') for r in client.records),'individual_holds':sum(r['status'].startswith('DOCUMENT_LOCAL') for r in client.records),'capture_queue_resolved_without_holds':len(rows)==len(queue),'semantic_review_complete':False}

def main():
 if OUT.exists():raise SystemExit('Refusing immutable CP10 overwrite')
 OUT.mkdir(parents=True);old.OUT=OUT
 before={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/'data').rglob('*') if p.is_file() and not p.is_relative_to(OUT)};put(OUT/'preserved_before.json',jb(before))
 approved=set();original_safe=old.safe
 old.safe=lambda u:original_safe(u) or u in approved
 put(OUT/'protocol.json',jb({'started_at':now(),'source_commit':os.getenv('GITHUB_SHA'),'version':'0.6.5-dev.research.1','Jev_choice':'execute_source_linked_traversal_and_remaining_docs','Jev_selection_probability':1.0,'Jev_confidence':1.0,'source_scope':'Exact existing public document queue and child sitemap links published by native index; no login, auth bypass or unrelated source changes.','rules':['Prior successful documents not redownloaded.','Source access/network circuit after2errors; no blocked SEC/StartEngine/Crowdcube retries.','2GBdocument budget,48MBindividual and120seconds limits remain explicit holds, not plateau.','Current sitemap tree not all historical campaigns; lastmod not firstlive.','PDF structural previews do not prove issuer identity/economic round/outcomes.','No numerical rates, main merge, complete-study or global plateau claims.']}))
 s=old.BoundedClient('public-sitemaps',160000000);d=old.BoundedClient('remaining-native-documents',2000000000)
 with ThreadPoolExecutor(max_workers=2) as pool:
  sf=pool.submit(sitemap,s,approved);df=pool.submit(documents,d);sr=sf.result();dr=df.result()
 manifest=s.records+d.records;put(OUT/'manifest.json',jb(manifest))
 preserved=all((ROOT/p).is_file() and sha((ROOT/p).read_bytes())==h for p,h in before.items())
 assert preserved,'Prior evidence changed'
 summary={'checkpoint':'CP10','version':'0.6.5-dev.research.1','completed_at':now(),'prior_data_files_preserved':len(before),'all_prior_data_unchanged':preserved,'sitemap':sr,'documents':dr,'source_status_counts':dict(Counter(r['source_group']+':'+r.get('status','UNKNOWN') for r in manifest)),'phase_complete':False,'rates_promoted':False,'global_plateau':False}
 put(OUT/'summary.json',jb(summary));print(jb(summary).decode())
if __name__=='__main__':main()
