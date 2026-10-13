"""Second substantive CP9 collection: new public documents and full posts.
No authentication, hidden form extraction, inferred exits or numerical promotion.
"""
from __future__ import annotations
import gzip,json,re,os
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from . import capture_cp9_evidence as cap
ROOT=cap.ROOT
BASE=ROOT/'data/phase1d/cp9'
OUT=BASE/'cycle-2-documents-posts'

def public_visible(raw:bytes)->str:
    soup=BeautifulSoup(raw,'html.parser')
    for tag in list(soup.select('script,style,noscript,form,textarea,input,select,[hidden],.u-hidden')):tag.decompose()
    for tag in list(soup.find_all(style=True)):
        if re.search(r'display\s*:\s*none|visibility\s*:\s*hidden',tag.get('style',''),re.I):tag.decompose()
    body=soup.body or soup
    return body.get_text('\n',strip=True)

def get_documents(queue):
    c=cap.PublicClient('native-documents');candidates=[]
    for item in queue:
        r,raw=c.get(item)
        if raw is None:continue
        pdf=raw.startswith(b'%PDF-')
        kind='PUBLIC_PDF_CAPTURE_NOT_YET_CONTENT_VERIFIED' if pdf else 'PUBLIC_DOCUMENT_RESPONSE_REQUIRES_CONTENT_TYPE_REVIEW'
        if not pdf and 'html' in r.get('content_type',''):
            text=public_visible(raw)
            if re.search(r'log in to (?:view|access|download)|sign in to (?:view|access|download)',text,re.I):kind='LOGIN_REQUIRED_NOT_ADMITTED'
        candidates.append({**item,'source_path':r['source_path'],'source_sha256':r['raw_sha256'],'final_url':r['final_url'],'content_type':r['content_type'],'bytes':r['bytes'],'pdf_magic_verified':pdf,'status':kind,'identity_admitted':False,'economic_round_admitted':False,'estimation_eligible':False})
    cap.put(OUT/'document_candidates.json',cap.jb(candidates));return c.records

def get_posts(queue):
    c=cap.PublicClient('native-full-posts');candidates=[]
    for item in queue:
        r,raw=c.get(item)
        if raw is None:continue
        soup=BeautifulSoup(raw,'html.parser');text=public_visible(raw)
        title=soup.title.get_text(' ',strip=True) if soup.title else ''
        canonical=soup.find('link',rel='canonical');canonical=canonical.get('href') if canonical else None
        og=soup.find('meta',attrs={'property':'og:title'});og=og.get('content') if og else None
        normalized=lambda x:' '.join(re.sub(r'[^\w ]',' ',x.lower()).split())
        title_seen=normalized(item['title']) in normalized(text)
        login_wall=bool(re.search(r'log in to (?:read|view) this (?:update|post)|sign in to (?:read|view) this (?:update|post)|only (?:available|visible) to investors',text,re.I))
        path=OUT/'visible_text'/f"{r['raw_sha256']}.txt"
        if not path.exists():cap.put(path,text.encode())
        candidates.append({**item,'source_path':r['source_path'],'source_sha256':r['raw_sha256'],'text_path':str(path.relative_to(ROOT)),'text_sha256':cap.sha(text.encode()),'final_url':r['final_url'],'page_title':title,'og_title':og,'canonical_url':canonical,'expected_title_visible':title_seen,'login_wall_detected':login_wall,'text_chars':len(text),'status':'PUBLIC_PAGE_CAPTURE_REQUIRES_POST_REGION_AND_EVENT_ADJUDICATION' if not login_wall else 'ACCESS_GATED_NOT_ADMITTED','publication_date_is_not_event_date':True,'verified_operating_evidence':False,'verified_terminal_event':False,'estimation_eligible':False})
    cap.put(OUT/'full_post_candidates.json',cap.jb(candidates));return c.records

def main():
    if OUT.exists():raise SystemExit('Refusing checkpoint overwrite')
    OUT.mkdir(parents=True)
    cap.OUT=OUT
    # This old native CDN is explicitly linked on the public Republic campaign pages.
    original_safe=cap.safe
    def native_safe(url):
        p=urlparse(url)
        return original_safe(url) or (p.scheme=='https' and p.hostname=='uploads.republic.co' and not p.username and not p.password)
    cap.safe=native_safe
    before={str(p.relative_to(ROOT)):cap.sha(p.read_bytes()) for p in (ROOT/'data').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
    cap.put(OUT/'preserved_before.json',cap.jb(before))
    cap.put(OUT/'protocol.json',cap.jb({'started_at':cap.now(),'source_commit':os.getenv('GITHUB_SHA'),'version':'0.6.4-dev.research.2','route':'Exact public document links and full post links from hash-bound campaign/timeline HTML; no guessed endpoints or authentication.','Jev_choice':'decode_verify_then_new_public_documents_and_posts','Jev_selection_probability':1.0,'Jev_confidence':1.0,'scope':'Second substantive collection; JSON replay correction is not a separate research iteration.','rules':['Two-error source circuit. No SEC retries.','Hidden forms and textareas excluded from text extraction.','Native dates preserve first-live vs completion; 2019 campaigns remain controls.','Public previews/full text require issuer, event, chronology, security and cohort adjudication.','No C-TR closure inference, no acquisition keyword classifier promotion, no numerical priors or global plateau.']}))
    docs=json.loads((BASE/'cycle-1-issuer-history-updates/public_document_queue.json').read_text())
    posts=json.loads((BASE/'cycle-1-reconciled/public_post_followup_queue.json').read_text())
    # Bind follow-up URLs to immutable previous-cycle evidence, not free-form task text.
    for item in docs+posts:
        if not cap.safe(item['url']):raise ValueError('source URL outside verified public allowlist')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(get_documents,docs),pool.submit(get_posts,posts)]
        manifest=[r for f in futures for r in f.result()]
    cap.put(OUT/'manifest.json',cap.jb(manifest))
    intact=all((ROOT/p).is_file() and cap.sha((ROOT/p).read_bytes())==h for p,h in before.items())
    if not intact:raise AssertionError('Earlier data changed')
    dc=json.loads((OUT/'document_candidates.json').read_text());pc=json.loads((OUT/'full_post_candidates.json').read_text())
    summary={'completed_at':cap.now(),'version':'0.6.4-dev.research.2','prior_data_files_preserved':len(before),'all_prior_data_unchanged':intact,'document_urls_queued':len(docs),'full_post_urls_queued':len(posts),'document_responses_captured':len(dc),'pdf_magic_verified_not_content_verified':sum(r['pdf_magic_verified'] for r in dc),'full_post_responses_captured':len(pc),'expected_titles_visible':sum(r['expected_title_visible'] for r in pc),'login_walls_detected':sum(r['login_wall_detected'] for r in pc),'source_status_counts':dict(Counter(r['source_group']+':'+r['status'] for r in manifest)),'new_sources_not_yet_outcome_adjudicated':True,'rates_promoted':False,'census_complete':False,'research_plateau':False}
    cap.put(OUT/'summary.json',cap.jb(summary));print(cap.jb(summary).decode())
if __name__=='__main__':main()
