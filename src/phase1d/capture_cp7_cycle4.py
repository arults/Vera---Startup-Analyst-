#!/usr/bin/env python3
"""New native census routes. Public data only; no access bypass or rate promotion."""
from __future__ import annotations
import concurrent.futures, gzip, hashlib, json, math, re, time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlencode
from collections import Counter
import requests
from bs4 import BeautifulSoup
from src.phase1d.capture_cp7_sources import DATA, ROOT, write_new, jbytes, now, digest

def save(out,label,url,status,raw,extra=None):
    key=digest(raw);p=out/'captures'/f'{key}.bin.gz'
    packed=gzip.compress(raw,mtime=0)
    if not p.exists():write_new(p,packed)
    row={'label':label,'url':url,'http_status':status,'received_at':now(),'raw_sha256':key,'gzip_sha256':digest(packed),'capture_path':str(p.relative_to(ROOT)),**(extra or {})}
    write_new(out/'receipts'/f'{label}.json',jbytes(row));return row

def crowdcube(out):
    s=requests.Session();s.headers['User-Agent']='VeraResearch/0.6.2 public historical investment research'
    receipts=[];candidates={};expected=None;failed=0
    for page in range(1,85):
        url='https://www.crowdcube.com/companies'+(f'?page={page}' if page>1 else '')
        try:
            r=s.get(url,timeout=(10,20),allow_redirects=False)
            row=save(out,f'crowdcube-{page:03d}',url,r.status_code,r.content)
            soup=BeautifulSoup(r.content,'html.parser');title=soup.title.get_text(' ',strip=True) if soup.title else ''
            challenge=bool(re.search(r'just a moment|verify you are human|access denied',title,re.I))
            if r.status_code!=200 or challenge:
                row['result']='ACCESS_BLOCKED_OR_HTTP_ERROR';failed+=1
            else:
                links=[]
                for a in soup.find_all('a',href=True):
                    dest=urljoin(url,a['href']);p=urlparse(dest)
                    if p.hostname not in {'www.crowdcube.com','crowdcube.com'}:continue
                    if re.fullmatch(r'/companies/[^/]+/?',p.path):
                        dest=dest.split('?')[0].rstrip('/');candidates[dest]={'company_profile_url':dest,'directory_page':page,'source_sha256':row['raw_sha256'],'candidate_only':True};links.append(dest)
                    m=re.search(r'(?:\?|&)page=(\d+)',dest)
                    if m:expected=max(expected or 0,int(m.group(1)))
                row.update(result='PUBLIC_DIRECTORY_PARSED',company_links=len(set(links)),advertised_max_page=expected)
                if not links:failed+=1
            receipts.append(row)
        except requests.RequestException as e:
            failed+=1;receipts.append({'label':f'crowdcube-{page:03d}','url':url,'http_status':None,'result':'REQUEST_ERROR','error':str(e)[:300]})
        if failed>=3:break
        if expected and page>=expected:break
        time.sleep(.7)
    write_new(out/'crowdcube_directory_candidates.json',jbytes(list(candidates.values())))
    return {'attempts':receipts,'candidate_profiles':len(candidates),'advertised_max_page':expected,'census_complete':False,'limitation':'Company directory is not a full economic-round census; blocked/missing pages and historical campaign terms remain unresolved.'}

def wefunder(out):
    from playwright.sync_api import sync_playwright
    receipts=[];profiles={};requests_count=0;blocked=0
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context();page=context.new_page()
        try:
            resp=page.goto('https://wefunder.com/explore',wait_until='domcontentloaded',timeout=45000)
            page.wait_for_timeout(3000)
            raw=page.content().encode();save(out,'wefunder-public-landing',page.url,resp.status if resp else None,raw)
            title=page.title()
            if (resp and resp.status in {401,403,429}) or re.search(r'just a moment|verify you are human|access denied',title,re.I):
                return {'attempts':[],'status':'PUBLIC_LANDING_BLOCKED_NO_BYPASS','census_complete':False}
            # Fields and endpoint are present in the preserved native API capture.
            # Per-year filtering must be verified against every returned timestamp.
            for year in range(2020,2026):
                low=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp());high=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp())
                params={'index':'Company_sorted_by_funding_closed_at_asc','tagFilters':'[]','page':'0','hitsPerPage':'1000','filters':f'fundingClosedAtSeconds >= {low} AND fundingClosedAtSeconds < {high}','vipOverride':'false','capCompanyCount':'false'}
                for page_no in range(6):
                    params['page']=str(page_no);url='https://wefunder.com/-/companies/explore?'+urlencode(params);label=f'wefunder-{year}-{page_no:02d}'
                    try:
                        rr=context.request.get(url,timeout=30000);raw=rr.body();row=save(out,label,url,rr.status,raw);requests_count+=1
                        try:body=json.loads(raw)
                        except (ValueError,UnicodeDecodeError):body={}
                        companies=body.get('companies') if isinstance(body,dict) else None
                        if rr.status!=200 or not isinstance(companies,list):
                            blocked+=1;row['result']='HTTP_OR_SCHEMA_ERROR';receipts.append(row);break
                        valid=all(isinstance(c.get('fundingClosedAtSeconds'),(int,float)) and low<=c['fundingClosedAtSeconds']<high for c in companies)
                        public=[c for c in companies if c.get('ownerPublished') and not c.get('privacySearch') and not c.get('privacyInviteOnly') and not c.get('deleted') and not c.get('adminRejected')]
                        before=len(profiles)
                        for c in public:profiles[str(c['id'])]=c
                        row.update(result='BOUNDED_PUBLIC_PROFILE_CANDIDATES' if valid else 'FILTER_NOT_VERIFIED_DO_NOT_ENUMERATE',returned_rows=len(companies),public_rows=len(public),new_public_profiles=len(profiles)-before,advertised_total=body.get('nbHits'),advertised_pages=body.get('nbPages'),filter_verified=valid)
                        receipts.append(row)
                        if not valid:break
                        if page_no>0 and len(profiles)==before:break
                        if len(companies)<1000 or page_no+1>=max(1,int(body.get('nbPages') or 1)):break
                    except Exception as e:
                        blocked+=1;receipts.append({'label':label,'url':url,'result':'REQUEST_ERROR','error':type(e).__name__+':'+str(e)[:200]});break
                    time.sleep(.5)
                if blocked>=3:break
            # Only public, owner-published candidates are exposed in derived output.
            write_new(out/'wefunder_public_profiles.json',jbytes(list(profiles.values())))
        finally:browser.close()
    return {'attempts':receipts,'public_profile_count':len(profiles),'request_count':requests_count,'census_complete':False,'limitation':'Profiles/latest-close filters do not enumerate every economic round or failed launch; first-live/round terms still require admissible evidence.'}

def main():
    out=DATA/'cp7'/'cycle-4'
    if out.exists():raise SystemExit('Refusing cycle4 overwrite')
    out.mkdir(parents=True)
    write_new(out/'feedback.json',jbytes({'created_at':now(),'prior_cycles':['cycle-1','cycle-2','cycle-3'],'action':'Native Crowdcube directory and Wefunder observed public API year-sliced collection','Jev_choice':'crowdcube_native_and_wefunder_public_api','Jev_probability':1.0,'Jev_confidence':1.0,'guard':'No authentication, CAPTCHA solving, proxies, stealth, VIP access, or access-control bypass. Stop bounded errors; metadata remains candidates.'}))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fs={pool.submit(crowdcube,out):'crowdcube',pool.submit(wefunder,out):'wefunder'};summary={}
        for f in concurrent.futures.as_completed(fs):
            platform=fs[f]
            try:summary[platform]=f.result()
            except Exception as e:summary[platform]={'status':'TASK_ERROR','error':type(e).__name__+':'+str(e),'census_complete':False}
    summary.update(completed_at=now(),rates_promoted=False,research_plateau=False)
    write_new(out/'summary.json',jbytes(summary));print(jbytes(summary).decode())
if __name__=='__main__':main()
