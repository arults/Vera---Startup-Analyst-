#!/usr/bin/env python3
"""Reproducible CP7 empirical audit. New output directories only; no prior promotion.

Raw platform pages are evidence. Search/profile rows are discovery, not denominators.
The follow-on event definition is the frozen comparable pre-money >=1.5x convention,
not investor return, and 2026 is follow-up only for the unchanged 2020-2025 cohort.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, io, json, re
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup, NavigableString
from src.phase1d.build_republic_europe_cohort import canonical_company_number, collision_plan, round_id
from src.phase1d.normalize_republic_europe import parse_date, MONTHS
from src.phase1d.estimate_republic_europe_candidate_v3 import rq1_rows, rq2_rows, first_event_observation

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/phase1d'
CUTOFF='2026-10-09'

def digest(raw: bytes) -> str:return hashlib.sha256(raw).hexdigest()
def read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def json_bytes(value: object) -> bytes:return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def write_new(path: Path,raw: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(raw)
def write_csv_new(path: Path,rows: list[dict],fields: list[str]|None=None) -> None:
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,extrasaction='raise');w.writeheader();w.writerows(rows)
    write_new(path,out.getvalue().encode())
def canonical_url(url: str) -> str:
    p=urlparse(url);return f'{p.scheme}://{p.netloc.lower()}{p.path.rstrip("/")}'
def text_from_html(raw: bytes) -> tuple[BeautifulSoup,str]:
    soup=BeautifulSoup(raw,'html.parser')
    for tag in soup(['script','style','noscript']):tag.decompose()
    return soup,soup.get_text('\n',strip=True)
def value_after(text: str,label: str) -> str:
    m=re.search(re.escape(label)+r'\s*\n\s*([^\n]+)',text,re.I)
    return m.group(1).strip() if m else ''
def exact_money(text: str) -> tuple[str,str]:
    m=re.fullmatch(r'\s*([£€$])([0-9][0-9,]*(?:\.[0-9]+)?)\s*',text)
    if not m:return '',''
    value=Decimal(m.group(2).replace(',',''))
    if not value.is_finite() or value<=0:return '',''
    return {'£':'GBP','€':'EUR','$':'USD'}[m.group(1)],str(value)
def terminal_lower(row: dict) -> str:
    return row.get('closure_date') or row.get('terminal_event_interval_start') or row.get('terminal_event_midpoint_for_primary') or row.get('terminal_event_interval_end') or ''
def full_precision_months(start: str,end: str) -> str:
    days=(date.fromisoformat(end)-date.fromisoformat(start)).days
    if days<0:raise ValueError('negative follow-up interval')
    return format(Decimal(days)/Decimal('30.4375'),'.12f')

def capture_bytes(root: Path,record: dict) -> bytes:
    path=(root/record['capture_path']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('source path outside repository')
    compressed=path.read_bytes()
    if digest(compressed)!=record['capture_gzip_sha256']:raise ValueError('compressed source hash mismatch')
    raw=gzip.decompress(compressed)
    if digest(raw)!=record['content_sha256']:raise ValueError('raw source hash mismatch')
    if record.get('text_path'):
        tp=(root/record['text_path']).resolve()
        if not tp.is_relative_to(root.resolve()):raise ValueError('text path outside repository')
        if digest(gzip.decompress(tp.read_bytes()))!=record['text_sha256']:raise ValueError('text hash mismatch')
    return raw

def parse_republic_europe(raw: bytes,record: dict) -> dict:
    soup,text=text_from_html(raw)
    funded=re.search(rf'\bFunded\s+(\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}})\b',text,re.I)
    funded_date=parse_date(funded.group(1)) if funded else ''
    company_number=value_after(text,'Company number')
    investment=re.search(r'Investment summary\s+Type\s+([^\n]+)',text,re.I)
    instrument=investment.group(1).strip() if investment else ''
    exact_raw=value_after(text,'Valuation rounded from')
    cur,valuation=exact_money(exact_raw)
    basis='FULLY_DILUTED_PRE_MONEY' if 'fully-diluted pre-money valuation' in text.lower() else ''
    popup=soup.select_one('#valuation_popup')
    direct=' '.join(str(c).strip() for c in popup.children if isinstance(c,NavigableString)) if popup else ''
    dom_money=re.findall(r'[£€$][0-9][0-9,]*(?:\.[0-9]+)?',direct)
    dom_cur,dom_value=exact_money(dom_money[0]) if len(dom_money)==1 else ('','')
    id_th=soup.find('th',string=lambda s:bool(s and s.strip()=='Company number'))
    id_td=id_th.find_next_sibling('td') if id_th else None
    dom_id=id_td.get_text(' ',strip=True) if id_td else ''
    raised=re.search(r'([£€$][0-9][0-9,]*(?:\.[0-9]+)?)\s+from\s+([0-9,]+)\s+investors',text)
    amount_currency,amount=exact_money(raised.group(1)) if raised else ('','')
    h1=soup.find('h1')
    result={
        'url':record['url'],'final_url':record.get('final_url',''),'round_id':round_id(record['url']),
        'campaign_name':h1.get_text(' ',strip=True) if h1 else '',
        'company_number':company_number,'company_key':canonical_company_number(company_number),
        'funded_date':funded_date,'instrument_type':instrument,
        'exact_pre_money_currency':cur,'exact_pre_money_valuation':valuation,
        'exact_pre_money_text':exact_raw,'valuation_basis':basis,
        'raised_currency':amount_currency,'raised_amount':amount,'investors':raised.group(2).replace(',','') if raised else '',
        'content_sha256':record['content_sha256'],'capture_path':record['capture_path'],
        'received_at':record.get('received_at',''),
        'dom_valuation_matches':bool(valuation and valuation==dom_value and cur==dom_cur),
        'dom_identity_matches':bool(company_number and company_number==dom_id),
        'source_valid':bool(record['http_status']==200 and record['status']=='PUBLIC_CAPTURED_UNADJUDICATED'
            and urlparse(record['url']).hostname=='europe.republic.com'
            and canonical_url(record['url'])==canonical_url(record.get('final_url',''))
            and funded_date and funded_date<=CUTOFF and company_number and instrument
            and 'Investment summary' in text and 'Business overview' in text),
    }
    return result

def bind_source(source: dict,expected: dict) -> dict:
    r=dict(source);issues=[]
    if not r['source_valid']:issues.append('NOT_VERIFIED_CAMPAIGN')
    if r['company_key']!=canonical_company_number(expected['company_number']):issues.append('LEGAL_ID_CHANGED')
    if r['funded_date']!=expected['funded_date']:issues.append('FUNDED_DATE_CHANGED')
    if r['instrument_type'].casefold()!=expected['investment_type'].casefold():issues.append('INSTRUMENT_CHANGED')
    if not r['dom_identity_matches']:issues.append('DOM_ID_DISAGREEMENT')
    if r['instrument_type'].casefold()=='equity' and (not r['exact_pre_money_valuation'] or not r['dom_valuation_matches']):issues.append('EXACT_VALUATION_UNVERIFIED')
    r['binding_issues']='|'.join(issues);r['binding_valid']=not issues
    r['old_display_valuation']=expected['pre_money_valuation'];r['old_display_currency']=expected['pre_money_currency']
    return r

def qualification(index: dict,later: dict,terminal: str='') -> tuple[bool,str,str]:
    if not index.get('binding_valid') or not later.get('binding_valid'):return False,'HELD_SOURCE_BINDING',''
    if not index.get('company_key') or index['company_key']!=later.get('company_key'):return False,'IDENTITY_MISMATCH',''
    if later['funded_date']<=index['funded_date']:return False,'NOT_LATER',''
    if later['funded_date']>CUTOFF:return False,'AFTER_CUTOFF',''
    if terminal and later['funded_date']>=terminal:return False,'TERMINAL_CONFLICT_OR_UNCERTAIN_INTERVAL',''
    if index['instrument_type'].casefold()!='equity' or later['instrument_type'].casefold()!='equity':return False,'NONCOMPARABLE_INSTRUMENT',''
    if not index['exact_pre_money_currency'] or index['exact_pre_money_currency']!=later['exact_pre_money_currency']:return False,'CURRENCY_MISMATCH',''
    if index['valuation_basis']!='FULLY_DILUTED_PRE_MONEY' or later['valuation_basis']!=index['valuation_basis']:return False,'BASIS_UNVERIFIED',''
    try:a,b=Decimal(index['exact_pre_money_valuation']),Decimal(later['exact_pre_money_valuation'])
    except (InvalidOperation,TypeError):return False,'EXACT_VALUATION_MISSING',''
    if not a.is_finite() or not b.is_finite() or a<=0 or b<=0:return False,'INVALID_VALUATION',''
    ratio=b/a
    return (ratio>=Decimal('1.5'),'QUALIFIED' if ratio>=Decimal('1.5') else 'BELOW_1_5',format(ratio,'.12f'))

def parse_republic_us(raw: bytes,record: dict) -> dict|None:
    soup,text=text_from_html(raw)
    if not re.fullmatch(r'/[A-Za-z0-9._-]+',urlparse(record['url']).path):return None
    m=re.search(r'Successfully funded and closed\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',text,re.I)
    close=datetime.strptime(m.group(1),'%B %d, %Y').date().isoformat() if m else ''
    header=re.search(r'\$([0-9,]+(?:\.[0-9]+)?)\s+Raised\s+([0-9,]+)\s+Investors\s+Successfully funded and closed',text,re.I)
    legal=value_after(text,'Legal Name')
    title=soup.title.get_text(' ',strip=True).replace(' — Republic','') if soup.title else ''
    ciks=set()
    for a in soup.find_all('a',href=True):
        p=urlparse(a['href'])
        if p.hostname not in {'www.sec.gov','sec.gov'}:continue
        for key,vals in parse_qs(p.query).items():
            if key.upper()=='CIK':ciks.update(str(int(v)) for v in vals if v.isdigit())
        mm=re.search(r'/Archives/edgar/data/(\d+)/',p.path)
        if mm:ciks.add(str(int(mm.group(1))))
    canonical=soup.find('link',rel='canonical')
    canonical_link=canonical.get('href','') if canonical else ''
    if canonical_link and urlparse(canonical_link).hostname not in {'republic.com','www.republic.com'}:canonical_link=''
    if not legal and not close:return None
    return {'source_url':record['url'],'final_url':record.get('final_url',''),'canonical_link':canonical_link,
        'campaign_name':title,'legal_name_from_platform':legal,'successful_close_date':close,
        'successful_close_year_NOT_offering_year':close[:4],
        'raised_amount_usd':header.group(1).replace(',','') if header else '',
        'investors':header.group(2).replace(',','') if header else '',
        'security_type':value_after(text,'Type of security'),
        'filing_cik_from_platform_links':'|'.join(sorted(ciks)),
        'linked_cik_status':'SINGLE_LINKED_CIK_PENDING_ENTITY_VALIDATION' if len(ciks)==1 else 'MULTIPLE_CIKS_HELD' if ciks else 'MISSING',
        'source_content_sha256':record['content_sha256'],'capture_path':record['capture_path'],
        'first_live_date':'','offering_year':'','canonical_company_id':'','economic_round_id':'',
        'estimation_eligible':False,'census_complete':False,
        'status':'SOURCE_VERIFIED_FIELDS_COHORT_AND_ECONOMIC_ROUND_HELD',
        'limitations':'Close is not first-live; linked CIK needs issuer/coissuer resolution; directory/search selection is incomplete; capture date is not survival evidence'}

def recover_wefunder_preserved() -> tuple[list[dict],dict]:
    path=DATA/'cp1_wefunder_explore_probe.json';data=json.loads(path.read_text())
    capture=next(r for r in data['captures'] if r.get('probe_label')=='enum_no_tags_nocap')
    companies=capture['body']['companies'];rows=[];excluded=Counter()
    for c in companies:
        reason=''
        if c.get('privacyInviteOnly'):reason='INVITE_ONLY'
        elif c.get('privacySearch'):reason='SEARCH_PRIVACY_REQUIRES_PUBLIC_CAMPAIGN_CONFIRMATION'
        elif c.get('deleted') or c.get('adminRejected'):reason='DELETED_OR_REJECTED'
        elif not c.get('ownerPublished'):reason='NOT_OWNER_PUBLISHED'
        if reason:excluded[reason]+=1;continue
        events=c.get('postFundingEvents') or []
        for number,event in enumerate(events):
            timestamp=event.get('timestamp') or '';closed=timestamp[:10]
            try:date.fromisoformat(closed)
            except ValueError:continue
            if not '2020-01-01'<=closed<='2025-12-31':continue
            rows.append({'source_native_company_id':str(c['id']),'company_name':c.get('name',''),'legal_name':c.get('legalName') or '',
                'source_profile_url':'https://wefunder.com/'+(c.get('url') or c.get('slug') or ''),
                'source_event_ordinal':number,'post_funding_event_timestamp':timestamp,'event_currency':event.get('currency',''),
                'event_amount':str(event.get('rawFundedAmount','')),'source_public_timestamp_seconds':c.get('fundingPublicAtSeconds'),
                'source_profile_latest_closed_seconds':c.get('fundingClosedAtSeconds'),
                'first_live_date':'','offering_year':'','economic_round_id':'','estimation_eligible':False,
                'source_archive_sha256':digest(path.read_bytes()),'source_native_query':capture['url'],
                'status':'PUBLIC_PROFILE_EVENT_CANDIDATE_ONLY','limitation':'Company profile and postFundingEvent do not establish full round terms, unique economic round, or first-live date; no survival/closure inference'})
    summary={'source_profile_rows':len(companies),'advertised_index_total':capture['body']['nbHits'],
        'visible_listed_prior_rows':149,'privacy_or_publication_hold_counts':dict(excluded),
        'public_profile_event_candidates_2020_2025':len(rows),'public_profile_companies_with_2020_2025_events':len({r['source_native_company_id'] for r in rows}),
        'new_live_observations':0,'mode':'PRESERVED_NATIVE_SOURCE_RECOVERY','census_complete':False,'estimation_eligible':0,
        'limitation':'985 profiles were retained, not a complete5132-index enumeration; candidates preserve missing round identity and first-live dates.'}
    return rows,summary

def run(output: Path,estimates: bool=True) -> dict:
    if output.exists():raise ValueError('refuse output overwrite')
    if not output.resolve().is_relative_to((DATA/'cp7').resolve()):raise ValueError('output outside CP7')
    preserved={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in DATA.rglob('*') if p.is_file() and not p.is_relative_to(DATA/'cp7')}
    records=[]
    for cycle in ['cycle-1','cycle-2','cycle-3']:
        manifest=DATA/'cp7'/cycle/'manifest.json'
        records.extend(json.loads(manifest.read_text()))
    captures={};us=[];parsed=[];hash_checked=0
    for record in records:
        if record.get('capture_path'):raw=capture_bytes(ROOT,record);hash_checked+=1
        else:continue
        if record['status']!='PUBLIC_CAPTURED_UNADJUDICATED' or record['http_status']!=200:continue
        if record['platform']=='republic_europe':
            p=parse_republic_europe(raw,record)
            if p['funded_date']:captures[record['url']]=p;parsed.append(p)
        elif record['platform']=='republic_us':
            p=parse_republic_us(raw,record)
            if p:us.append(p)
    raw_rows=read_csv(DATA/'cp2_republic_europe_rounds_raw.csv')
    raw_map={r['candidate_url']:r for r in raw_rows if '2020'<=r['funded_year']<='2026' and r['funded_date']<=CUTOFF}
    collision_rows,blocked=collision_plan(list(raw_map.values()))
    bound={u:bind_source(p,raw_map[u]) for u,p in captures.items() if u in raw_map}
    by_key=defaultdict(list)
    for r in raw_map.values():
        key=canonical_company_number(r['company_number'])
        if key and key not in blocked:by_key[key].append(r)
    needed={r['candidate_url'] for rr in by_key.values() if len(rr)>1 for r in rr}
    missing=sorted(needed-set(bound))
    invalid={u:r['binding_issues'] for u,r in bound.items() if u in needed and not r['binding_valid']}
    if missing or invalid:raise ValueError(json.dumps({'repeat_source_audit_incomplete':True,'missing':missing,'invalid':invalid},sort_keys=True))
    norm=read_csv(DATA/'cp2_republic_europe_rounds_normalized.csv');norm_by_id={r['round_id']:r for r in norm}
    old=read_csv(DATA/'cp3_republic_europe_outcome_ledger_v4.csv');new=[];pairs=[];changes=[]
    for baseline in old:
        row=dict(baseline);n=norm_by_id[row['round_id']];key=n['legal_company_number_canonical'];url=n['campaign_url']
        candidates=[r for r in by_key.get(key,[]) if r['funded_date']>n['completion_date']] if key and n['company_id_normalization_status']=='CANONICAL_NUMBER' else []
        index=bound.get(url);successes=[];funded=[]
        for raw_later in sorted(candidates,key=lambda r:(r['funded_date'],r['candidate_url'])):
            event=bound[raw_later['candidate_url']]
            yes,reason,ratio=qualification(index,event,terminal_lower(row))
            if event['binding_valid'] and (not terminal_lower(row) or event['funded_date']<terminal_lower(row)):funded.append(event)
            pairs.append({'index_round_id':row['round_id'],'index_url':url,'later_round_id':event['round_id'],'later_url':event['url'],
                'company_key':key,'index_date':n['completion_date'],'later_date':event['funded_date'],
                'index_exact_valuation':index['exact_pre_money_valuation'],'later_exact_valuation':event['exact_pre_money_valuation'],
                'index_currency':index['exact_pre_money_currency'],'later_currency':event['exact_pre_money_currency'],
                'index_instrument':index['instrument_type'],'later_instrument':event['instrument_type'],
                'index_old_display_value':index['old_display_valuation'],'later_old_display_value':event['old_display_valuation'],
                'exact_ratio':ratio,'qualified':yes,'decision':reason,
                'index_source_sha256':index['content_sha256'],'later_source_sha256':event['content_sha256'],
                'later_in_2026_followup_only':event['funded_date'].startswith('2026')})
            if yes:successes.append((event,ratio))
        if row['success_type'] not in {'','qualified_priced_followon'}:raise ValueError('unreviewed non-priced success type')
        row.update(success_date='',success_type='',success_valuation_multiple='',success_evidence_url='',success_evidence_sha256='')
        if successes:
            event,ratio=successes[0];row.update(success_date=event['funded_date'],success_type='qualified_priced_followon',success_valuation_multiple=ratio,
                success_evidence_url=event['url'],success_evidence_sha256=event['content_sha256'])
        if not terminal_lower(row) and funded:
            latest=max(event['funded_date'] for event in funded)
            if latest>row['last_positive_date']:row['last_positive_date']=latest;row['censor_date']=max(row['censor_date'],latest)
        row['followup_months']=full_precision_months(row['completion_date'],row['censor_date'])
        row['priced_followon_audit_scope']='ALL_NATIVE_REPEAT_ROUNDS_THROUGH_2026_10_09'
        row['prior_version']='cp3_republic_europe_outcome_ledger_v4.csv'
        if row['success_date']!=baseline['success_date'] or row['last_positive_date']!=baseline['last_positive_date']:row['evidence_trace']+='|cp7_exact_price_followup_audit'
        changes.append({'round_id':row['round_id'],'campaign_name':row['campaign_name'],'offering_year':row['offering_year'],
            'old_success_date':baseline['success_date'],'new_success_date':row['success_date'],
            'old_multiple':baseline['success_valuation_multiple'],'new_multiple':row['success_valuation_multiple'],
            'old_last_positive':baseline['last_positive_date'],'new_last_positive':row['last_positive_date'],
            'new_success_source':row['success_evidence_url']})
        new.append(row)
    changed=[r for r in changes if any(r[a]!=r[b] for a,b in [('old_success_date','new_success_date'),('old_multiple','new_multiple'),('old_last_positive','new_last_positive')])]
    oracle_errors=[]
    for row in new:
        n=norm_by_id[row['round_id']];idx=bound.get(n['campaign_url']);expected=[]
        if idx and idx['instrument_type'].lower()=='equity' and idx['binding_valid']:
            for ev in bound.values():
                if ev['company_key']!=idx['company_key'] or not ev['binding_valid'] or ev['instrument_type'].lower()!='equity':continue
                if not idx['funded_date']<ev['funded_date']<=CUTOFF:continue
                if terminal_lower(row) and ev['funded_date']>=terminal_lower(row):continue
                if idx['exact_pre_money_currency']!=ev['exact_pre_money_currency'] or not idx['exact_pre_money_currency']:continue
                if idx['valuation_basis']!='FULLY_DILUTED_PRE_MONEY' or ev['valuation_basis']!=idx['valuation_basis']:continue
                if Decimal(ev['exact_pre_money_valuation'])*2>=Decimal(idx['exact_pre_money_valuation'])*3:expected.append(ev['funded_date'])
        expected_date=min(expected) if expected else ''
        if row['success_date']!=expected_date:oracle_errors.append({'round_id':row['round_id'],'expected':expected_date,'actual':row['success_date']})
    duplicate_groups=defaultdict(list)
    for row in us:
        key=(row['filing_cik_from_platform_links'],row['legal_name_from_platform'],row['successful_close_date'],row['raised_amount_usd'])
        if all(key):duplicate_groups[key].append(row['source_url'])
    duplicate_hints=[urls for urls in duplicate_groups.values() if len(urls)>1]
    wf,wf_summary=recover_wefunder_preserved()
    added=[r for r in changed if not r['old_success_date'] and r['new_success_date']]
    removed=[r for r in changed if r['old_success_date'] and not r['new_success_date']]
    time_changed=[r for r in changed if r['old_success_date'] and r['new_success_date'] and r['old_success_date']!=r['new_success_date']]
    extended=[r for r in changed if r['new_last_positive']>r['old_last_positive']]
    checks={
        'all_capture_hashes_verified':hash_checked>0,
        'all_repeat_sources_captured':not missing,
        'all_repeat_sources_bound_to_raw_identity_date_instrument':not invalid,
        'all_equity_exact_values_independently_dom_verified':all(r['dom_valuation_matches'] for u,r in bound.items() if u in needed and r['instrument_type'].lower()=='equity'),
        'all_repeat_legal_ids_independently_dom_verified':all(r['dom_identity_matches'] for u,r in bound.items() if u in needed),
        'strong_id_collision_gates':not blocked,
        'cohort_cardinality_unchanged':len(new)==len(old)==952,
        'cohort_ids_unchanged':{r['round_id'] for r in new}=={r['round_id'] for r in old},
        'cohort_years_unchanged':[(r['round_id'],r['offering_year'],r['offering_year_status']) for r in new]==[(r['round_id'],r['offering_year'],r['offering_year_status']) for r in old],
        'no_2026_cohort_added':all(r['completion_date'][:4]!='2026' for r in new),
        'independent_all_pairs_oracle_agrees':not oracle_errors,
        'old_terminal_rows_not_reopened':all(n['last_positive_date']==o['last_positive_date'] and n['censor_date']==o['censor_date'] for n,o in zip(new,old) if terminal_lower(o)),
        'closure_labels_unchanged_without_new_evidence':all(n['closure_date']==o['closure_date'] for n,o in zip(new,old)),
        'all_successes_within_supported_followup':all(first_event_observation(r,'success').cause=='success' for r in new if r['success_date']),
        'no_event_after_cutoff':all(not r['success_date'] or r['success_date']<=CUTOFF for r in new),
        'followup_nondecreasing':all(n['last_positive_date']>=o['last_positive_date'] for n,o in zip(new,old)),
        'us_close_dates_not_misassigned_as_first_live':all(not r['offering_year'] and not r['first_live_date'] for r in us),
        'us_candidates_not_rate_eligible':all(not r['estimation_eligible'] and not r['census_complete'] for r in us),
        'wf_profile_events_not_rate_eligible':all(not r['estimation_eligible'] for r in wf),
        'all_pre_cp7_data_files_preserved':all(digest((ROOT/p).read_bytes())==h for p,h in preserved.items()),
    }
    summary={'version':'0.6.2-dev.empirical.1','scope':'candidate only; unchanged2020-2025 cohorts; followup through2026-10-09',
        'source_capture_records':len(records),'content_hashes_verified':hash_checked,
        'republic_europe':{'repeat_groups':sum(len(rr)>1 for rr in by_key.values()),'repeat_campaigns_exhaustively_price_reviewed':len(needed),
            'later_pairs_evaluated':len(pairs),'index_rows':len(new),'year_eligible_rows':sum(r['offering_year_status']=='BOUNDED_YEAR' for r in new),
            'old_qualifying_successes_all':sum(bool(r['success_date']) for r in old),'new_qualifying_successes_all':sum(bool(r['success_date']) for r in new),
            'old_qualifying_successes_year_eligible':sum(bool(r['success_date']) for r in old if r['offering_year_status']=='BOUNDED_YEAR'),
            'new_qualifying_successes_year_eligible':sum(bool(r['success_date']) for r in new if r['offering_year_status']=='BOUNDED_YEAR'),
            'new_success_labels':len(added),'removed_rounded_success_labels':len(removed),'first_success_dates_changed':len(time_changed),
            'old_labeled_successes_ignored_by_rounded_censor':sum(bool(r['success_date']) and first_event_observation(r,'success').cause!='success' for r in old),
            'new_labeled_successes_ignored_by_censor':sum(bool(r['success_date']) and first_event_observation(r,'success').cause!='success' for r in new),
            'followup_rows_extended':len(extended),'followup_companies_extended':len({r['canonical_company_id'] for r in new if r['round_id'] in {x['round_id'] for x in extended}}),
            'confirmed_closures':sum(bool(r['closure_date']) for r in new),
            'source_precision_changes':len(changed),'all_pairs_oracle_errors':oracle_errors},
        'republic_us':{'campaign_pages_parsed':len(us),'explicit_successful_close_dates':sum(bool(r['successful_close_date']) for r in us),
            'close_year_2020_2025_NOT_cohort':sum('2020'<=r['successful_close_year_NOT_offering_year']<='2025' for r in us),
            'single_linked_CIK_pending_identity_review':sum(r['linked_cik_status'].startswith('SINGLE') for r in us),
            'potential_duplicate_alias_groups':duplicate_hints,'census_complete':False,'estimation_eligible':0},
        'wefunder':wf_summary,'startengine':{'census_complete':False},'crowdcube':{'census_complete':False},
        'rates_promoted':False,'research_plateau':False,
        'limitations':['Exact-price universe does not exhaust acquisitions, IPOs, shutdowns or operating evidence.','Zero confirmed closures is not zero closures.','Successful-funded discovery is selection-biased; no cross-platform prior can be promoted.','Four historical censuses remain incomplete.']}
    output.mkdir(parents=True)
    write_csv_new(output/'republic_europe_verified_campaign_prices.csv',list(bound.values()))
    write_csv_new(output/'republic_europe_all_later_exact_pair_audit.csv',pairs)
    write_csv_new(output/'republic_europe_outcome_ledger_v5.csv',new)
    write_csv_new(output/'republic_europe_changes.csv',changed)
    write_csv_new(output/'republic_us_campaign_candidates.csv',us)
    write_csv_new(output/'wefunder_public_profile_event_candidates.csv',wf)
    write_new(output/'preserved_pre_cp7_data_hashes.json',json_bytes(preserved))
    if estimates:
        rq1=rq1_rows(new);rq2=rq2_rows(new)
        write_csv_new(output/'republic_europe_rq1_candidate_v4.csv',rq1)
        write_csv_new(output/'republic_europe_rq2_candidate_v4.csv',rq2)
        prior_rq1=read_csv(DATA/'cp4_republic_europe_rq1_candidate_v3.csv')
        prior_map={(r['offering_year'],r['horizon_months']):r for r in prior_rq1}
        deltas=[]
        for r in rq1:
            before=prior_map[(str(r['offering_year']),str(r['horizon_months']))]
            for metric in ['success_cif','closure_cif','operating_survival']:
                if r[metric] and before[metric]:deltas.append({'offering_year':r['offering_year'],'horizon_months':r['horizon_months'],'metric':metric,'before':before[metric],'after':r[metric],'absolute_delta':abs(float(r[metric])-float(before[metric]))})
        summary['comparison_to_prior_candidate_v3']={'largest_change':max(deltas,key=lambda r:r['absolute_delta']) if deltas else None,'comparison_rows':len(deltas),'interpretation':'candidate change is not a promoted startup-specific probability; no empirical plateau'}
        write_csv_new(output/'candidate_v3_to_v4_comparison.csv',deltas)
        summary['candidate_estimates']={'rq1_cells':len(rq1),'rq1_low_information':sum(r['low_information']=='true' for r in rq1),'rq2_reportable':sum(r['report']=='true' for r in rq2),'rates_promoted':False}
        checks['candidate_rates_not_promoted']=all(r['promotion_status']=='CANDIDATE_ONLY' for r in rq1)
    report={'passed':sum(checks.values()),'total':len(checks),'checks':checks,'rates_promoted':False,'research_plateau':False}
    write_new(output/'scientific_verifier.json',json_bytes(report))
    write_new(output/'summary.json',json_bytes(summary))
    write_new(output/'manifest.json',json_bytes({'created_at':datetime.now(timezone.utc).isoformat(),'outputs':{p.name:digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()},'baseline_data_preserved_files':len(preserved)}))
    if not all(checks.values()):raise ValueError('scientific verifier failed: '+json.dumps(report))
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='data/phase1d/cp7/analysis-verified-v1');parser.add_argument('--skip-estimates',action='store_true');args=parser.parse_args()
    print(json.dumps(run(ROOT/args.output,not args.skip_estimates),indent=2,sort_keys=True))
