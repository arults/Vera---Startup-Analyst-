"""CP8 official published SEC archives: discovery only, immutable and fail-closed.
The official index was read on 2026-10-09 via the web research tool. It lists
2020Q1--2025Q4 and 2026Q1--Q2, NOT 2026Q3. Direct links to 2020Q1,
2025Q4 and 2026Q2 were independently followed. Remaining paths use the same
published naming convention and are validated as ZIPs, never assumed captured.
RegCF filings are not all-platform censuses, funded rounds, or outcome proof.
"""
from __future__ import annotations
import csv, io, json, time, zipfile
from collections import Counter
from pathlib import Path
import requests
from src.phase1d.capture_cp7_sources import ROOT, DATA, write_new, jbytes, now, digest
INDEX='https://www.sec.gov/data-research/sec-markets-data/crowdfunding-offerings-data-sets'
BASE='https://www.sec.gov/files/dera/data/crowdfunding-offerings-data-sets/'

def published_quarters():
    return [(y,q) for y in range(2020,2026) for q in range(1,5)]+[(2026,1),(2026,2)]

def archive_tables(raw):
    if len(raw)>20_000_000 or not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ValueError('not a bounded ZIP archive')
    result=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist()
        if len(infos)>40 or sum(i.file_size for i in infos)>100_000_000:
            raise ValueError('unsafe archive size or entry count')
        if z.testzip(): raise ValueError('archive CRC error')
        for item in infos:
            if item.is_dir(): continue
            if Path(item.filename).is_absolute() or '..' in Path(item.filename).parts:
                raise ValueError('unsafe member path')
            body=z.read(item)
            table={'name':item.filename,'sha256':digest(body),'bytes':len(body)}
            if item.filename.lower().endswith(('.tsv','.csv','.txt')):
                text=body.decode('utf-8-sig')
                delimiter='\t' if '\t' in text.split('\n',1)[0] else ','
                rows=list(csv.reader(io.StringIO(text),delimiter=delimiter))
                table.update(header=rows[0] if rows else [],data_rows=max(0,len(rows)-1))
            result.append(table)
    return result

def coverage(manifest):
    have={(r['year'],r['quarter']) for r in manifest if r.get('status')=='OFFICIAL_ARCHIVE_VERIFIED_DISCOVERY_ONLY'}
    target={(y,q) for y in range(2020,2026) for q in range(1,5)}
    published=set(published_quarters())
    return {'target_quarters_verified':len(have&target),'target_quarters_required':24,
            'all_target_filing_archives_verified':target<=have,
            'published_quarters_verified':len(have&published),'published_quarters_required':26,
            'all_published_filing_archives_verified':published<=have,
            'unpublished_followup_quarters':['2026Q3'],
            'platform_census_complete':False,'rates_promoted':False,'research_plateau':False}

def main():
    out=DATA/'cp8'/'cycle-1-published-archives'
    if out.exists(): raise SystemExit('Refusing checkpoint overwrite')
    out.mkdir(parents=True)
    queue=[{'year':y,'quarter':q,'url':BASE+f'{y}q{q}_cf.zip',
            'url_provenance':'DIRECT_LINK_FOLLOWED' if (y,q) in {(2020,1),(2025,4),(2026,2)} else 'PUBLISHED_LABEL_AND_PATH_CONVENTION_REQUIRES_FETCH'} for y,q in published_quarters()]
    # Try two directly witnessed files first; never evade an access denial.
    queue.sort(key=lambda r:(0 if (r['year'],r['quarter'])==(2025,4) else 1 if (r['year'],r['quarter'])==(2026,2) else 2,r['year'],r['quarter']))
    write_new(out/'protocol.json',jbytes({'started_at':now(),'source_index':INDEX,
        'index_evidence':'Web tool opened official index 2026-10-09, source turn751014view0, lines23-65; three direct archive links followed.',
        'scope':'EXTERNAL_REGULATOR_DISCOVERY_ONLY','max_consecutive_errors':2,'minimum_request_spacing_seconds':1,
        'Jev_choice':'published_archives_plus_reconciled_cp7','Jev_probability':1.0,'Jev_confidence':1.0,
        'rules':['RegCF is not RegA/RegD.','A Form C is not confirmed funding.','Filing date is not first-live.','C-TR is not company closure.','No promotion, no main merge, no access bypass.']}))
    write_new(out/'queue.json',jbytes(queue))
    s=requests.Session();s.headers.update({'User-Agent':'VeraResearch/0.6.3 (arults; 109891188+arults@users.noreply.github.com)','Accept-Encoding':'gzip, deflate'})
    manifest=[];consecutive_errors=0
    for item in queue:
        row={**item,'attempted_at':None}
        if consecutive_errors>=2:
            row['status']='NOT_ATTEMPTED_SOURCE_CIRCUIT_OPEN';manifest.append(row);continue
        row['attempted_at']=now()
        try:
            time.sleep(1)
            with s.get(item['url'],timeout=(10,35),allow_redirects=False,stream=True) as response:
                chunks=[];size=0
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size>20_000_000: raise ValueError('response exceeds byte limit')
                    chunks.append(chunk)
                raw=b''.join(chunks)
                row.update(http_status=response.status_code,bytes=len(raw),sha256=digest(raw),received_at=now())
                if response.status_code!=200:
                    row['status']='HTTP_ERROR_NO_BYPASS';consecutive_errors+=1;extension='response.bin'
                else:
                    row['tables']=archive_tables(raw);extension='zip';consecutive_errors=0
                    row['status']='OFFICIAL_ARCHIVE_VERIFIED_DISCOVERY_ONLY'
                path=out/'archives'/f'{item["year"]}q{item["quarter"]}.{extension}'
                write_new(path,raw);row['source_path']=str(path.relative_to(ROOT))
        except (requests.RequestException,ValueError,zipfile.BadZipFile,UnicodeError) as exc:
            consecutive_errors+=1;row.update(status='REQUEST_OR_VALIDATION_ERROR',error=type(exc).__name__+':'+str(exc)[:300])
        manifest.append(row)
        write_new(out/'receipts'/f'{item["year"]}q{item["quarter"]}.json',jbytes(row))
    write_new(out/'manifest.json',jbytes(manifest))
    summary={**coverage(manifest),'completed_at':now(),'status_counts':dict(Counter(r['status'] for r in manifest)),'access_bypass_attempted':False}
    write_new(out/'summary.json',jbytes(summary));print(jbytes(summary).decode())
if __name__=='__main__':main()
