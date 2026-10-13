"""Source-bound native outcomes research. Candidate evidence, never rate promotion."""
from __future__ import annotations
import gzip,json,re
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup
from src.phase1d.capture_cp7_sources import ROOT, DATA, capture_group, write_new, jbytes, now, digest
from src.phase1d.analyze_cp7_empirical import capture_bytes, parse_republic_us, read_csv, write_csv_new

URLS=[('republic_us','https://republic.com/2021','new_native_annual_report_payout_evidence'),
 ('republic_us','https://republic.com/trusst','new_primary_campaign_not_in_prior120'),
 ('republic_us','https://republic.com/ring4','negative_control_2018_campaign_2021_principal_payout'),
 ('republic_us','https://republic.com/reg-cf-offerings','footer_all_companies_link_actual_scope_check'),
 ('wefunder','https://wefunder.com/feed/235158','search_discovered_CabinetM_dissolution_full_source_required')]

def normalize(text):return ' '.join(text.split())
def read_verified(record):
    if record.get('status')!='PUBLIC_CAPTURED_UNADJUDICATED' or record.get('http_status')!=200:return None
    raw=capture_bytes(ROOT,record)
    soup=BeautifulSoup(raw,'html.parser')
    for t in soup(['script','style','noscript']):t.decompose()
    text=normalize(soup.get_text(' ',strip=True))
    if len(text)<300 or any(t in text.lower() for t in ['verify you are human','verify you are a human','enable javascript to continue','checking your browser']):return None
    return raw,text

def derive(records):
    by={r['url']:r for r in records};loaded={}
    for u,r in by.items():
        content=read_verified(r)
        if content:loaded[u]=content
    report='https://republic.com/2021';observations=[];campaigns=[];checks={}
    for u in ['https://republic.com/trusst','https://republic.com/ring4']:
        if u in loaded:
            parsed=parse_republic_us(loaded[u][0],by[u])
            if parsed:campaigns.append(parsed)
    parsed_by={r['source_url']:r for r in campaigns}
    old=read_csv(DATA/'cp7/analysis-cp8-verified/republic_us_campaign_candidates.csv')
    old_urls={r['source_url'] for r in old}
    new=[r for r in campaigns if r['source_url'] not in old_urls]
    if report in loaded:
        text=loaded[report][1];h=by[report]['content_sha256']
        base={'source_url':report,'source_sha256':h,'source_capture_path':by[report]['capture_path'],
              'source_scope':'PLATFORM_REPORTED_NOT_INDEPENDENTLY_AUDITED','estimation_eligible':False,
              'exact_gross_moic':None,'exact_event_date':None,'closure_established':False,
              'cohort_offering_year':None,'census_complete':False}
        trusst=parsed_by.get('https://republic.com/trusst')
        if trusst and trusst['successful_close_date']=='2021-04-16' and re.search(r'Trusst was acquired by K Health',text,re.I) and re.search(r'annualized return of 102%',text,re.I):
            observations.append({**base,'id':'CP8-US-TRUSST-PAYOUT','company':'Trusst',
                'legal_name':trusst['legal_name_from_platform'],'campaign_url':trusst['source_url'],
                'campaign_source_sha256':trusst['source_content_sha256'],
                'event_type':'ACQUISITION_WITH_REPORTED_POSITIVE_INVESTOR_PAYOUT',
                'event_date_lower':'2021-04-17','event_date_upper':'2021-12-31',
                'date_precision':'BOUNDED_YEAR_WITH_APPROXIMATE_TWO_MONTH_RELATIVE_DESCRIPTION',
                'reported_annualized_return_pct':102,'reported_holding_period_return_pct':None,
                'qualifying_success_observation_candidate':True,
                'status':'PRIMARY_PAYOUT_OBSERVATION_VERIFIED_COHORT_AND_EXACT_RETURN_HELD',
                'holds':['first_live_date_missing','canonical_round_identity_review_pending','exact_acquisition_and_payout_dates_missing','annualization_method_and_cashflows_missing','historical_census_incomplete']})
        ring=parsed_by.get('https://republic.com/ring4')
        if ring and ring['successful_close_date']=='2018-11-03' and re.search(r'In May 2021, Ring4 investors were paid back their principal',text,re.I):
            observations.append({**base,'id':'CP8-US-RING4-CONTROL','company':'Ring4',
                'legal_name':ring['legal_name_from_platform'],'campaign_url':ring['source_url'],
                'campaign_source_sha256':ring['source_content_sha256'],
                'event_type':'ASSET_SALE_REPORTED_PRINCIPAL_REPAYMENT','event_date_lower':'2021-05-01','event_date_upper':'2021-05-31',
                'date_precision':'MONTH','reported_annualized_return_pct':None,'reported_holding_period_return_pct':None,
                'qualifying_success_observation_candidate':False,'status':'OUT_OF_TARGET_COHORT_NEGATIVE_CONTROL',
                'holds':['funded_campaign_closed2018_before_target_years','principal_repayment_not_profitable_exit','asset_sale_not_proof_of_company_closure']})
        if 'Boeing Ave Real Estate' in text and '27% return' in text and 'six months later' in text:
            observations.append({**base,'id':'CP8-US-BOEING-SCOPE-HOLD','company':'Boeing Ave Real Estate',
                'event_type':'PROPERTY_PROJECT_PAYOUT_SCOPE_REVIEW','reported_annualized_return_pct':None,
                'reported_holding_period_return_pct':27,'reported_holding_period_months':6,
                'qualifying_success_observation_candidate':False,'status':'NON_STARTUP_REAL_ESTATE_SCOPE_HOLD',
                'holds':['property_project_not_verified_startup_cohort','campaign_identity_and_dates_unresolved','do_not_pool_property_returns_with_startup_returns']})
    directory='https://republic.com/reg-cf-offerings'
    active_only=directory in loaded and 'Directory of all active Reg CF offerings'.lower() in loaded[directory][1].lower()
    report_scope={'source_url':report,'deals_launched_2021':226 if report in loaded and re.search(r'226\s+2021 deals launched',loaded[report][1],re.I) else None,
        'scope':'Republic Retail aggregate spans multiple entities/products/exemptions; not comparable to an incomplete historical RegCF campaign sample',
        'denominator_admissible':False}
    checks['all_observation_sources_hash_bound']=all(r['source_sha256']==by[r['source_url']]['content_sha256'] for r in observations)
    checks['no_annualized_return_relabelled_as_moic']=all(r['exact_gross_moic'] is None for r in observations)
    checks['no_close_year_substitution']=all(not r['offering_year'] for r in campaigns)
    checks['no_outcome_year_substitution']=all(r['cohort_offering_year'] is None for r in observations)
    checks['no_observation_used_for_rates']=all(not r['estimation_eligible'] for r in observations+campaigns)
    checks['ring4_not_new_2021_cohort']=all(not r['qualifying_success_observation_candidate'] for r in observations if r['company']=='Ring4')
    checks['no_asset_sale_auto_closure']=all(not r['closure_established'] for r in observations)
    checks['no_aggregate_denominator_promotion']=not report_scope['denominator_admissible']
    checks['candidate_urls_unique']=len({r['source_url'] for r in old+new})==len(old+new)
    summary={'version':'0.6.3-dev.research.1','scope':'source-bound candidate outcomes and discovery only','completed_at':now(),
        'public_pages_verified':len(loaded),'capture_status_counts':dict(Counter(r['status'] for r in records)),
        'new_campaign_pages_parsed':len(new),'all_campaign_candidates_after_union':len(old+new),
        'new_campaigns_closed2020_2025_not_offering_cohorts':sum('2020'<=r['successful_close_year_NOT_offering_year']<='2025' for r in new),
        'new_source_bound_observations':len(observations),'positive_payout_observation_candidates':sum(r['qualifying_success_observation_candidate'] for r in observations),
        'active_only_directory_confirmed':active_only,'annual_report_aggregate':report_scope,
        'four_historical_censuses_complete':False,'rates_promoted':False,'research_plateau':False,
        'source_availability_separate_from_checks':True,'checks_passed':sum(checks.values()),'checks_total':len(checks)}
    return summary,observations,old+new,checks

def main():
    out=DATA/'cp8/cycle-2-native-outcomes'
    if out.exists():raise SystemExit('Refusing checkpoint overwrite')
    out.mkdir(parents=True)
    queue=[dict(platform=p,url=u,reasons=[why]) for p,u,why in URLS]
    write_new(out/'protocol.json',jbytes({'started_at':now(),'queue':queue,'Jev_choice':'capture_native_outcomes_with_scoped_holds','Jev_probability':1.0,'Jev_confidence':1.0,'no_promotion':True,'no_access_bypass':True}))
    records=[]
    for platform in ['republic_us','wefunder']:
        records+=capture_group(platform,[r for r in queue if r['platform']==platform],out)
    write_new(out/'manifest.json',jbytes(records))
    summary,obs,candidates,checks=derive(records)
    write_new(out/'outcome_observations.json',jbytes(obs))
    write_csv_new(out/'republic_us_candidate_union.csv',candidates)
    write_new(out/'scientific_checks.json',jbytes(checks))
    write_new(out/'summary.json',jbytes(summary))
    assert all(checks.values()),checks
    print(jbytes(summary).decode())
if __name__=='__main__':main()
