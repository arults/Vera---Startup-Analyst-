#!/usr/bin/env python3
"""Real exact-price audit with append-only durable source checkpoints."""
from __future__ import annotations
import argparse, json, subprocess
from collections import defaultdict, Counter
from src.phase1d.capture_cp7_sources import ROOT, DATA, csvrows, capture_group, write_new, jbytes, now
from src.phase1d.build_republic_europe_cohort import canonical_company_number

def persist(out):
    rel=str(out.relative_to(ROOT))
    subprocess.run(['git','add','--',rel],cwd=ROOT,check=True)
    diff=subprocess.check_output(['git','diff','--cached','--name-status'],cwd=ROOT,text=True)
    if not diff.strip():return
    if any(not line.startswith('A\t'+rel+'/') for line in diff.splitlines()):raise RuntimeError('Refusing non-additive or out-of-scope commit')
    subprocess.run(['git','commit','-m','CP7 cycle 3: durable exact-price source checkpoint; no rate promotion'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:phase-1d'],cwd=ROOT,check=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--persist',action='store_true');args=parser.parse_args()
    out=DATA/'cp7'/'cycle-3'
    if out.exists():raise SystemExit('Refusing overwrite; inspect durable batches before choosing a new resume ID')
    groups=defaultdict(list)
    for r in csvrows(DATA/'cp2_republic_europe_rounds_raw.csv'):
        if '2020'<=r['funded_year']<='2026' and r['funded_date']<='2026-10-09' and (key:=canonical_company_number(r['company_number'])):groups[key].append(r)
    repeat=[r for rr in groups.values() if len(rr)>1 for r in rr]
    prior=[]
    for cycle in ['cycle-1','cycle-2']:prior.extend(json.loads((DATA/'cp7'/cycle/'manifest.json').read_text()))
    captured={r['url'] for r in prior if r['status']=='PUBLIC_CAPTURED_UNADJUDICATED' and r['http_status']==200}
    queue=sorted([{'url':r['candidate_url'],'platform':'republic_europe','reasons':['systematic_exact_price_audit_after_revvies_rounded_false_positive']} for r in repeat if r['candidate_url'] not in captured],key=lambda r:r['url'])
    out.mkdir(parents=True)
    write_new(out/'queue.json',jbytes(queue))
    write_new(out/'feedback.json',jbytes({'created_at':now(),'repeat_groups':sum(len(rr)>1 for rr in groups.values()),'repeat_campaigns':len(repeat),'new_capture_queue':len(queue),'critique':'Revvies exact ratio1.4946025187 fails1.5 although rounded displays imply1.5. Audit all repeat-round valuations, not only new candidates.','Jev_audit_choice':'audit_all_repeat_rounds','Jev_audit_probability':1.0,'Jev_audit_confidence':1.0,'Jev_versioned_correction_probability':.98,'Jev_versioned_correction_confidence':.96,'Jev_plateau_yes_probability':.26,'empirical_plateau':False}))
    if args.persist:persist(out)
    rows=[];errors=0
    for offset in range(0,len(queue),40):
        part=queue[offset:offset+40];batch=out/f'batch-{offset//40+1:04d}'
        batch.mkdir()
        if errors>=5:
            result=[{**r,'attempted_at':now(),'status':'NOT_ATTEMPTED_DOMAIN_CIRCUIT_OPEN','http_status':None,'reason':'five earlier blocked/error responses; no retry'} for r in part]
        else:result=capture_group('republic_europe',part,batch)
        errors+=sum(r['status'] in {'REQUEST_ERROR','HTTP_ERROR_OR_REDIRECT','ACCESS_OR_LOGIN_PAGE'} for r in result)
        rows.extend(result);write_new(batch/'manifest.json',jbytes(result))
        write_new(batch/'receipt.json',jbytes({'completed_at':now(),'offset':offset,'batch_rows':len(result),'cumulative_rows':len(rows),'errors_cumulative':errors,'rates_promoted':False}))
        if args.persist:persist(out)
    write_new(out/'manifest.json',jbytes(rows))
    summary={'completed_at':now(),'queued':len(queue),'status_counts':dict(Counter(r['status'] for r in rows)),'rates_promoted':False,'census_complete':False,'research_plateau':False}
    write_new(out/'summary.json',jbytes(summary))
    if args.persist:persist(out)
    print(jbytes(summary).decode())
if __name__=='__main__':main()
