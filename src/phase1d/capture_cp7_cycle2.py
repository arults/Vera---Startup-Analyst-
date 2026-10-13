#!/usr/bin/env python3
"""Follow feedback with distinct source work. No promotion, no overwrite."""
from __future__ import annotations
import concurrent.futures
from collections import Counter, defaultdict
from src.phase1d.capture_cp7_sources import DATA, csvrows, capture_group, write_new, jbytes, now
from src.phase1d.build_republic_europe_cohort import canonical_company_number

def main():
    out=DATA/'cp7'/'cycle-2'
    if out.exists():raise SystemExit('Refusing overwrite of cycle-2')
    later=csvrows(DATA/'cp2_republic_europe_rounds_raw.csv')
    keys={key for r in later if r['funded_year']=='2026' if (key:=canonical_company_number(r['company_number']))}
    prior=csvrows(DATA/'cp2_republic_europe_rounds_normalized.csv')
    queue=[{'url':r['campaign_url'],'platform':'republic_europe','reasons':['original_index_exact_valuation_identity_date_revalidation']} for r in prior if r['legal_company_number_canonical'] in keys]
    # Previously observed native URLs. Cycle1's 119 successful US campaign
    # captures establish materially changed access, not unchanged retries.
    for u in ['https://republic.com/companies/portfolio','https://republic.com/funded-ventures','https://republic.com/reg-cf-offerings','https://republic.com/investment-opportunities','https://republic.com/api/offerings/republic_note_public_deals','https://republic.com/blue']:
        queue.append({'url':u,'platform':'republic_us','reasons':['changed_access_after_119_successful_campaign_captures']})
    queue=sorted({r['url']:r for r in queue}.values(),key=lambda x:(x['platform'],x['url']))
    if not queue or any(not r['url'].startswith('https://') for r in queue):raise ValueError('invalid source queue')
    out.mkdir(parents=True)
    write_new(out/'queue.json',jbytes(queue))
    write_new(out/'feedback.json',jbytes({'created_at':now(),'prior_cycle':'cycle-1','critique':['Rounded valuation may cross1.5x threshold. Require exact values both sides.','Successful-close year is not offering year.','Changed US access warrants native-directory capture, not assumed completion.'],'Jev_precision_choice':'exact_prices_both_sides','Jev_precision_probability':1.0,'Jev_precision_confidence':1.0,'Jev_priority_probability':.97,'Jev_priority_confidence':.95}))
    by=defaultdict(list)
    for row in queue:by[row['platform']].append(row)
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(capture_group,p,q,out) for p,q in by.items()]
        for f in concurrent.futures.as_completed(futures):rows.extend(f.result())
    rows.sort(key=lambda x:(x['platform'],x['url']));write_new(out/'manifest.json',jbytes(rows))
    summary={'completed_at':now(),'queued':len(queue),'by_platform':{p:dict(Counter(r['status'] for r in rows if r['platform']==p)) for p in by},'rates_promoted':False,'census_complete':False,'research_plateau':False}
    write_new(out/'summary.json',jbytes(summary));print(jbytes(summary).decode())
if __name__=='__main__':main()
