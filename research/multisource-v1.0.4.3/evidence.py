"""Vera additive evidence ledger. Standard library only; never edits native data."""
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

IMPLEMENTATION_VERSION = '1.0.4.3-customer-local'
POLICY = 'vera.multisource.claim-policy.v1.1.0'
SCHEMA = 'vera.multisource.evidence.v1'
# Authority is specific to the assertion; eligibility is not certification of truth.
ALLOW = {
 'acquisition_completed': {'buyer_announcement', 'issuer_announcement', 'regulatory_filing', 'court_order'},
 'asset_acquisition': {'buyer_announcement','issuer_announcement','transaction_document','regulatory_filing'},
 'acquisition_intent': {'buyer_announcement', 'issuer_announcement', 'regulatory_filing'},
 'control_transfer': {'regulatory_filing', 'court_order', 'transaction_document'},
 'operational_autonomy_reported': {'buyer_announcement', 'issuer_announcement'},
 'operating_activity': {'platform_issuer_report', 'issuer_announcement', 'regulatory_filing'},
 'product_activity': {'official_product_artifact', 'platform_issuer_report', 'issuer_announcement'},
 'legal_active': {'official_registry'}, 'legal_dissolution': {'official_registry', 'court_order'},
 'bankruptcy_petition': {'court_petition'}, 'final_liquidation': {'court_order'},
 'business_cessation': {'platform_issuer_report', 'issuer_announcement', 'court_order', 'regulatory_filing'},
 'reporting_termination': {'regulatory_filing'},
 'priced_equity': {'transaction_document', 'regulatory_filing', 'platform_issuer_report'},
 'safe_cap': {'transaction_document', 'regulatory_filing', 'platform_issuer_report'},
 'shareholder_consideration': {'transaction_document', 'regulatory_filing', 'court_order'},
 'realized_investor_return': {'transaction_document', 'regulatory_filing', 'court_order'},
 'transaction_enterprise_value': {'buyer_announcement', 'transaction_document', 'regulatory_filing'},
}
# Independent reporting is admissible as attributed secondary assertion, never upgraded to official fact.
for _types in ALLOW.values(): _types.add('independent_reporting')
ALLOW['database_reported_lead']={'specialist_database'}
from customer_observations import CUSTOMER_TYPES, customer_errors, customer_reasons, customer_release_blockers, customer_output
for _customer_type in CUSTOMER_TYPES:
    ALLOW[_customer_type] = {'customer_project_report', 'independent_reporting'}
KINDS = {'point', 'activity_period', 'event_interval', 'upper_bound', 'unknown'}
MISSING = {'not_searched','searched_no_relevant_result','tool_failure','auth_required','unavailable','not_reported','ambiguous','not_applicable'}

def stable(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def source_snapshot(data):
    return sha(stable(data['sources']))

def digest_claim(claim):
    # Reviews bind all substantive claim fields, not a mutable claim ID.
    return sha(stable({k:v for k,v in claim.items() if k != 'reviews'}))

def date(s):
    return dt.date.fromisoformat(s)

def timestamp(s):
    if not isinstance(s,str) or not s:
        raise ValueError('timestamp missing or not a string; exact time must not be invented')
    t = dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('timestamp requires timezone')
    return t

def safe_path(root, name):
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()) or Path(name).is_absolute():
        raise ValueError('path escapes package')
    return p

def public_url(url):
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password: return False
    safe={'id','cik','companynumber','company_number','accession','action','type','dateb','owner','count','page','output','documentid'}
    for key,value in parse_qsl(u.query,keep_blank_values=True):
        if key.lower() not in safe or not re.fullmatch(r'[A-Za-z0-9_.:/ -]{0,160}',value): return False
    if any(word in u.fragment.lower() for word in ('access_token','auth','session','signature','password','secret','api_key')): return False
    return not u.fragment or bool(re.fullmatch(r'[A-Za-z0-9_=.-]{1,120}',u.fragment))

def validate(data, root, context_claim_ids=()):
    """Fail closed on malformed evidence; semantic insufficiency is a reported hold."""
    errors = []
    def require(condition, message):
        if not condition: errors.append(message)
    require(data.get('schema') == SCHEMA, 'schema mismatch')
    require(data.get('policy') == POLICY, 'policy mismatch')
    require(data.get('dataset') == 'augmented_research_only', 'dataset separation required')
    require(data.get('estimator_enabled') is False and data.get('prior_promotion_enabled') is False, 'promotion forbidden')
    sources = data.get('sources',[]); claims = data.get('claims',[])
    for rows, label in [(sources,'source'),(claims,'claim')]:
        require(len({r.get('id') for r in rows}) == len(rows), f'duplicate {label} ID')
    sm = {s['id']:s for s in sources}
    cm = {c['id']:c for c in claims}
    for s in sources:
        try:
            for key in ('id','url','publisher','source_type','origin_family','relationship','capture','capture_sha256','original_sha256','capture_scope','original_body_inspected','origin_rationale','upstream_urls','retrieved_at','retrieval_missingness','publication_date','as_of_date'):
                require(key in s, f'{s["id"]}: missing {key}')
            u = urlsplit(s['url'])
            require(public_url(s['url']), f'{s["id"]}: unsafe/noncanonical URL')
            raw = safe_path(root,s['capture']).read_bytes()
            require(sha(raw) == s['capture_sha256'], f'{s["id"]}: capture hash mismatch')
            require(bool(re.fullmatch('[0-9a-f]{64}',s['original_sha256'])), f'{s["id"]}: original hash invalid')
            if s['retrieved_at']: timestamp(s['retrieved_at'])
            else: require(s['retrieval_missingness'] in MISSING, f'{s["id"]}: missing retrieval reason')
            for field in ('publication_date','as_of_date'):
                if s[field]: date(s[field])
        except (KeyError,ValueError,OSError,TypeError) as exc: errors.append(f'source invalid: {exc}')
    for c in claims:
        try:
            for key in ('id','company_id','round_id','claim_type','assertion','value','time','identity','evidence','contradictions','missingness','collector','reviews','predicate_review'):
                require(key in c, f'{c["id"]}: missing {key}')
            require(c['claim_type'] in ALLOW, f'{c["id"]}: unsupported claim type')
            t = c['time']; require(t['kind'] in KINDS, f'{c["id"]}: invalid temporal kind')
            if t['kind'] == 'point': date(t['on']); require(bool(t.get('basis')), f'{c["id"]}: event time basis missing')
            if t['kind'] in {'activity_period','event_interval'}:
                require(date(t['start']) <= date(t['end']), f'{c["id"]}: reversed interval')
            if t['kind'] == 'upper_bound': date(t['end'])
            if t['kind'] == 'activity_period': require(c['claim_type'] in {'operating_activity','product_activity'}, f'{c["id"]}: activity period not transition interval')
            require(bool(c['evidence']), f'{c["id"]}: evidence required')
            for e in c['evidence']:
                s = sm[e['source_id']]
                text = safe_path(root,s['capture']).read_text()
                require(bool(e['excerpt']) and e['excerpt'] in text, f'{c["id"]}: excerpt absent from capture')
                require(e['stance'] in {'supports','contradicts'}, f'{c["id"]}: invalid stance')
                require(bool(e['locator']), f'{c["id"]}: locator missing')
            for conflict in c['contradictions']:
                require((conflict['claim_id'] in cm or conflict['claim_id'] in context_claim_ids) and conflict['claim_id'] != c['id'], f'{c["id"]}: invalid contradiction target')
                require(conflict['status'] in {'open','resolved'}, f'{c["id"]}: contradiction status invalid')
                if conflict['status'] == 'resolved': require(bool(conflict.get('resolution')), f'{c["id"]}: missing conflict resolution')
            for key,value in c['missingness'].items(): require(value in MISSING, f'{c["id"]}: invalid missingness {key}')
            for review in c['reviews']:
                require(review['reviewer'] != c['collector'], f'{c["id"]}: self-review forbidden')
                require(review['decision'] in {'accept','hold','reject'}, f'{c["id"]}: invalid review')
                require(review['claim_sha256'] == digest_claim(c), f'{c["id"]}: stale review')
                require(review.get('source_snapshot_sha256') == source_snapshot(data), f'{c["id"]}: stale source-bound review')
                require(bool(review['rationale']) and bool(review['identity_checked']), f'{c["id"]}: incomplete review')
                timestamp(review['reviewed_at'])
        except (KeyError,ValueError,OSError,TypeError) as exc: errors.append(f'claim invalid: {exc}')
    errors.extend(customer_errors(data))
    return errors

def adjudicate(c, sources, as_of):
    """Internal semantic projection; callers must use report() for validated release decisions."""
    reasons=customer_reasons(c, sources, as_of); support=[sources[e['source_id']] for e in c['evidence'] if e['stance']=='supports']
    valid=[s for s in support if s['source_type'] in ALLOW[c['claim_type']]]
    if (c.get('predicate_review') or {}).get('supported_claim_type') != c['claim_type'] or not (c.get('predicate_review') or {}).get('rationale'):
        reasons.append('PREDICATE_NOT_REVIEWED')
    if not valid: reasons.append('NO_CLAIM_APPROPRIATE_AUTHORITY')
    if any(s['source_type']=='independent_reporting' and not s.get('editorial_authority_rationale') for s in support): reasons.append('SECONDARY_AUTHORITY_UNASSESSED')
    from scoped_review import section_adequate
    if any(not s.get('original_body_inspected') and not section_adequate(s,c['id'])[0] for s in support): reasons.append('FULL_BODY_NOT_INSPECTED')
    if any(not s.get('origin_rationale') for s in support): reasons.append('ORIGIN_INDEPENDENCE_UNASSESSED')
    i=c['identity']; strong=[x for x in i.get('strong_ids',[]) if isinstance(x,dict) and x.get('kind') in {'CIK','LEI','company_registration_number'} and x.get('value') and x.get('provenance')]; medium=i.get('medium_identifiers',[])
    if not strong and len({x['kind'] for x in medium if x.get('value') and x.get('provenance')}) < 2: reasons.append('IDENTITY_UNRESOLVED')
    if i.get('mapping_review_status') != 'verified': reasons.append('IDENTITY_REVIEW_PENDING')
    if i.get('scope') != 'security_issuer_verified' and c['claim_type'] in {'control_transfer','shareholder_consideration','realized_investor_return','priced_equity'}: reasons.append('SECURITY_ISSUER_CHAIN_UNVERIFIED')
    if any(e['stance']=='contradicts' for e in c['evidence']) or any(x['status']=='open' for x in c['contradictions']): reasons.append('OPEN_CONTRADICTION')
    reviews=c['reviews']
    if not any(r['decision']=='accept' for r in reviews): reasons.append('INDEPENDENT_REVIEW_PENDING')
    if any(timestamp(r['reviewed_at']).astimezone(dt.timezone.utc).date()>as_of for r in reviews): reasons.append('CLAIM_REVIEW_POSTDATES_AS_OF')
    if any(r['decision'] in {'reject','hold'} for r in reviews): reasons.append('REVIEW_DISAGREEMENT')
    # Unknown dates do not erase a narrow source assertion; downstream transitions stay blocked.
    ages=[]
    for s in support:
        ages.append({'source_id':s['id'],'retrieval_age_days':(as_of-timestamp(s['retrieved_at']).astimezone(dt.timezone.utc).date()).days if s['retrieved_at'] else None,
                     'publication_age_days':(as_of-date(s['publication_date'])).days if s['publication_date'] else None,
                     'source_as_of_age_days':(as_of-date(s['as_of_date'])).days if s['as_of_date'] else None,
                     'retrieval_missingness':s['retrieval_missingness']})
    for s in support:
        if any(s.get(k) and date(s[k])>as_of for k in ('publication_date','as_of_date')): reasons.append('SOURCE_POSTDATES_AS_OF')
    t=c['time']
    if any(t.get(k) and date(t[k])>as_of for k in ('on','start','end')): reasons.append('EVENT_POSTDATES_AS_OF')
    if any(x['retrieval_age_days'] is not None and x['retrieval_age_days']<0 for x in ages): reasons.append('FUTURE_RETRIEVAL')
    return {**customer_output(c), 'id':c['id'],'company_id':c['company_id'],'round_id':c['round_id'],'claim_type':c['claim_type'],
            'status':'HELD' if reasons else 'ACCEPTED_ATTRIBUTED_OBSERVATION','evidence_tier':('DISCOVERY' if c['claim_type']=='database_reported_lead' else 'SECONDARY_ATTRIBUTED' if valid and all(s['source_type']=='independent_reporting' for s in valid) else 'PRIMARY_ATTRIBUTED'),'reasons':reasons,
            'time':c['time'],'original_source_urls':[s['url'] for s in support],
            'source_families':sorted({s['origin_family'] for s in support}),
            'publisher_count':len({s['publisher'] for s in support}),
            'declared_origin_family_count':len({s['origin_family'] for s in support}),
            'freshness':ages,'unknowns':c['missingness'],
            'native_source_scope_only':bool(valid) and all(s['source_type']=='platform_issuer_report' for s in support),
            'state_transition':None,'point_censor_date':None,'estimation_eligible':False,'numeric_prior_eligible':False}

def report(data, root, as_of, reviewer_registry=None):
    if data.get('research_scope'):
        from scoped_review import scoped_report
        return scoped_report(data,root,as_of,reviewer_registry)
    return base_report(data,root,as_of,reviewer_registry)

def base_report(data, root, as_of, reviewer_registry=None, context_claim_ids=(), expected_plan_policy=None):
    errors=validate(data,root,context_claim_ids)
    if errors: raise ValueError('\n'.join(errors))
    sm={s['id']:s for s in data['sources']}
    rows=[adjudicate(c,sm,as_of) for c in data['claims']]
    from source_verifier import audit
    coverage=audit(data,root=root,expected_plan_policy=expected_plan_policy)
    if data.get('research_plan',{}).get('search_cutoff') and date(data['research_plan']['search_cutoff'])>as_of:
        coverage['blockers'].append('SEARCH_CUTOFF_POSTDATES_AS_OF')
    if data.get('source_review',{} ) and data['source_review'].get('reviewed_at') and timestamp(data['source_review']['reviewed_at']).astimezone(dt.timezone.utc).date()>as_of:
        coverage['blockers'].append('SOURCE_REVIEW_POSTDATES_AS_OF')
    coverage['blockers'].extend(customer_release_blockers(data))
    if coverage['blockers']: coverage['status']='INCOMPLETE_MATERIAL_ROUTE'
    registry=reviewer_registry or {}
    for c,r in zip(data['claims'],rows):
        claim_trusted=any(x['decision']=='accept' and 'claim_verifier' in registry.get(x['reviewer'],[]) for x in c['reviews'])
        sr=data.get('source_review') or {}
        source_trusted='source_verifier' in registry.get(sr.get('reviewer'),[])
        r['release_status']='RELEASED_RESEARCH_FINDING' if r['status']=='ACCEPTED_ATTRIBUTED_OBSERVATION' and claim_trusted and source_trusted and coverage['status']=='SUFFICIENT_FOR_NARROW_CLAIM' and r['evidence_tier']!='DISCOVERY' else 'UNRELEASED_RESEARCH_OBSERVATION'
        r['reviewer_authority_checked']={'claim':claim_trusted,'source':source_trusted}
        r['known_by_retrieval']=max((timestamp(s['retrieved_at']) for s in sm.values() if s['id'] in [e['source_id'] for e in c['evidence']] and s['retrieved_at']),default=None)
        if r['known_by_retrieval']: r['known_by_retrieval']=r['known_by_retrieval'].astimezone(dt.timezone.utc).isoformat()
        if any(not sm[e['source_id']]['retrieved_at'] for e in c['evidence']): r['known_by_retrieval']=None
    return {'implementation_version':IMPLEMENTATION_VERSION,'source_coverage_audit':coverage,'policy':POLICY,'dataset':data['dataset'],'input_sha256':sha(stable(data)),'as_of':as_of.isoformat(),
            'native_baseline':data['native_baseline'],'native_changes':0,'augmented_observations':rows,
            'accepted_attributed_observations':sum(r['status']=='ACCEPTED_ATTRIBUTED_OBSERVATION' for r in rows),
            'held_observations':sum(r['status']=='HELD' for r in rows),'rates':None,'prior_promotions':0,
            'warning':'Research observations only. Native state and denominator unchanged. No estimator implemented; source counts are not outcome counts.'}

def main():
    p=argparse.ArgumentParser(); p.add_argument('input',type=Path);p.add_argument('--as-of',required=True);p.add_argument('--output',type=Path)
    p.add_argument('--reviewer-registry',type=Path,help='Operator-controlled reviewer-to-role registry; not embedded in evidence input')
    a=p.parse_args(); result=report(json.loads(a.input.read_text()),a.input.resolve().parent,date(a.as_of),json.loads(a.reviewer_registry.read_text()) if a.reviewer_registry else None); text=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if a.output:
        # Never silently replace a report: immutable content-addressed runs.
        a.output.mkdir(parents=True,exist_ok=True); dest=a.output/(sha(text.encode())+'.json')
        if not dest.exists(): dest.write_text(text)
        print(dest)
    else: print(text,end='')
if __name__=='__main__': main()
