#!/usr/bin/env python3
"""Official RegCF discovery inventory only. Never equate filings to funded rounds."""
from __future__ import annotations
import io, json, re, time, zipfile
from urllib.parse import urljoin, urlparse
from collections import Counter
import requests
from bs4 import BeautifulSoup
from src.phase1d.capture_cp7_sources import ROOT, DATA, write_new, jbytes, now, digest
INDEX='https://www.sec.gov/data-research/sec-markets-data/crowdfunding-offerings-data-sets'

def main():
    out=DATA/'cp7'/'cycle-5-regulator-discovery'
    if out.exists():raise SystemExit('Refusing source inventory overwrite')
    out.mkdir(parents=True)
    write_new(out/'protocol.json',jbytes({'started_at':now(),'scope':'EXTERNAL_REGULATOR_DISCOVERY_ONLY','Jev_choice':'execute_separate_discovery_inventory','Jev_probability':1.0,'Jev_confidence':1.0,'rules':['RegCF is not allRegA/RegD.','FormCfiling is not a funded economic round.','Filing date is not first-live.','C-TR is not closure.','Coissuer/SPV identity needs separate validation.','No cohort, outcome, main branch, registry or prior promotion.'],'limits':{'seconds_between_requests':.6,'error_circuit_breaker':2,'max_archives':27,'max_archive_bytes':20000000,'max_uncompressed_archive_bytes':100000000}}))
    s=requests.Session();s.headers.update({'User-Agent':'VeraResearch/0.6.2 (arults; 109891188+arults@users.noreply.github.com)','Accept-Encoding':'gzip, deflate'})
    manifest=[];queue=[];errors=0
    try:
        r=s.get(INDEX,timeout=(10,30),allow_redirects=False)
        write_new(out/'sec-index-response.bin',r.content)
        index_record={'url':INDEX,'http_status':r.status_code,'sha256':digest(r.content),'received_at':now(),'source_path':str((out/'sec-index-response.bin').relative_to(ROOT))}
        write_new(out/'index-receipt.json',jbytes(index_record))
        if r.status_code!=200:raise RuntimeError('SEC index not publicly accessible; no bypass')
        soup=BeautifulSoup(r.content,'html.parser')
        for a in soup.find_all('a',href=True):
            label=a.get_text(' ',strip=True);m=re.fullmatch(r'(202[0-6])\s+Q([1-4])\s+CF',label,re.I)
            if not m:continue
            year,quarter=map(int,m.groups());url=urljoin(INDEX,a['href'])
            if year==2026 and quarter>3:continue
            if urlparse(url).hostname not in {'www.sec.gov','sec.gov'} or not urlparse(url).path.lower().endswith('.zip'):continue
            queue.append({'year':year,'quarter':quarter,'url':url,'label':f'{year}q{quarter}'})
        queue=sorted({(r['year'],r['quarter']):r for r in queue}.values(),key=lambda r:(r['year'],r['quarter']))
        write_new(out/'queue.json',jbytes(queue))
        if len(queue)>27:raise RuntimeError('unexpected archive count')
        for item in queue:
            row={**item,'attempted_at':now()}
            if errors>=2:
                row['status']='NOT_ATTEMPTED_ERROR_CIRCUIT_OPEN';manifest.append(row);continue
            try:
                time.sleep(.6);rr=s.get(item['url'],timeout=(10,40),allow_redirects=False);raw=rr.content
                row.update(http_status=rr.status_code,sha256=digest(raw),received_at=now(),bytes=len(raw))
                if len(raw)>20000000:raise ValueError('archive exceeds byte limit')
                ext='zip' if rr.status_code==200 and zipfile.is_zipfile(io.BytesIO(raw)) else 'response.bin'
                path=out/'archives'/f'{item["label"]}.{ext}';write_new(path,raw);row['source_path']=str(path.relative_to(ROOT))
                if ext!='zip':row['status']='HTTP_OR_ARCHIVE_ERROR';errors+=1
                else:
                    with zipfile.ZipFile(io.BytesIO(raw)) as z:
                        info=z.infolist()
                        if sum(i.file_size for i in info)>100000000:raise ValueError('uncompressed archive exceeds byte limit')
                        bad=z.testzip()
                        if bad:raise ValueError('ZIP CRC failed')
                        row['tables']=[{'name':i.filename,'uncompressed_bytes':i.file_size,'sha256':digest(z.read(i))} for i in info if not i.is_dir()]
                    row['status']='OFFICIAL_ARCHIVE_VERIFIED_DISCOVERY_ONLY'
            except Exception as e:errors+=1;row.update(status='REQUEST_OR_VALIDATION_ERROR',error=type(e).__name__+':'+str(e)[:300])
            manifest.append(row);write_new(out/'receipts'/f'{item["label"]}.json',jbytes(row))
    except Exception as e:
        write_new(out/'source-blocker.json',jbytes({'at':now(),'error':type(e).__name__+':'+str(e),'route':INDEX,'access_bypass_attempted':False}))
    write_new(out/'manifest-regulator.json',jbytes(manifest))
    summary={'completed_at':now(),'source_scope':'EXTERNAL_REGULATOR_DISCOVERY_ONLY','archives_discovered':len(queue),'archive_statuses':dict(Counter(r.get('status') for r in manifest)),'archives_verified':sum(r.get('status')=='OFFICIAL_ARCHIVE_VERIFIED_DISCOVERY_ONLY' for r in manifest),'all_expected_2020_2025_plus_2026Q1_Q3_archives_verified':len(manifest)==27 and all(r.get('status')=='OFFICIAL_ARCHIVE_VERIFIED_DISCOVERY_ONLY' for r in manifest),'platform_census_complete':False,'rates_promoted':False,'research_plateau':False}
    write_new(out/'summary.json',jbytes(summary));print(jbytes(summary).decode())
if __name__=='__main__':main()
