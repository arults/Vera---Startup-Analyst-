"""Narrow customer observations. Does not infer issuer outcomes or event dates."""
import datetime
import hashlib
import re
from pathlib import Path

CUSTOMER_TYPES = frozenset({'customer_project_observation', 'customer_product_use'})
EXTENSION = 'vera.multisource.customer-observations.v1'
EXCLUDED = ('issuer_survival', 'issuer_operating_activity', 'financing', 'investor_return',
            'state_transition', 'point_censor_date', 'estimation_eligible', 'numeric_prior_eligible')

def calendar_date(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):
        raise ValueError('customer report/correction date requires YYYY-MM-DD')
    return datetime.date.fromisoformat(value)

def policy_hash():
    return hashlib.sha256(Path(__file__).with_name('CUSTOMER_OBSERVATIONS.md').read_bytes()).hexdigest()

def customer_errors(data):
    errors=[]
    sm={s['id']:s for s in data.get('sources',[])}
    for c in data.get('claims',[]):
        cid=c.get('id'); is_customer=c.get('claim_type') in CUSTOMER_TYPES
        def check(ok,msg):
            if not ok: errors.append(f'{cid}: {msg}')
        if not is_customer:
            check(not any(k in c for k in ('customer_subject','customer_scope')), 'customer contract cannot be retyped as issuer outcome')
            continue
        try:
            check(c.get('customer_scope')==EXTENSION, 'customer extension required')
            subject=c['customer_subject']
            check(isinstance(subject,dict) and all(isinstance(subject.get(k),str) and subject[k].strip() for k in ('customer_id','customer_name','project_or_product','site','relationship_basis')), 'customer subject incomplete')
            check(subject.get('company_id')==c['company_id'], 'customer company linkage mismatch')
            # This initial narrow version admits unknown event time only. Explicit event
            # observations need a separately designed provenance contract, not guessing.
            t=c['time']
            check(t.get('kind')=='unknown', 'customer event time must remain unknown in this extension')
            check(not any(t.get(k) is not None for k in ('on','start','end','event_time','event_timezone','censor_date')), 'report date cannot populate event or censor fields')
            check(bool(t.get('basis')), 'unknown event basis missing')
            for key in EXCLUDED:
                check(c.get(key) in (None,False) and c.get('value',{}).get(key) in (None,False) if isinstance(c.get('value'),dict) else c.get(key) in (None,False), 'customer outcome promotion forbidden: '+key)
            for e in c['evidence']:
                s=sm[e['source_id']]; a=e.get('customer_attribution',{})
                check(isinstance(a,dict), 'customer attribution must be an object')
                check(a.get('customer_id')==subject['customer_id'] and a.get('company_id')==c['company_id'] and a.get('project_or_product')==subject['project_or_product'] and a.get('site')==subject['site'], 'customer evidence linkage mismatch')
                check(all(isinstance(a.get(k),str) and a[k].strip() for k in ('original_witness','factual_origin_id','competence_rationale','relationship_disclosures','correction_disposition')), 'customer authority/origin qualifications incomplete')
                check(a.get('origin_role')=='customer_or_project_party', 'issuer or anonymous assertion is not customer testimony')
                check(a.get('report_date')==s.get('publication_date') and bool(a.get('report_date')), 'report date must equal known source publication date')
                calendar_date(a['report_date'])
                check(a.get('report_date_basis')=='source_publication_only', 'report date semantics must remain publication only')
                if 'report_date' in t:
                    check(t['report_date']==a['report_date'], 'claim report date differs from source-specific report date')
                check(a.get('event_time') is None, 'customer testimony event time is unknown')
        except (KeyError,TypeError,ValueError,AttributeError) as exc:
            errors.append(f'{cid}: invalid customer contract: {exc}')
    return errors

def customer_reasons(c,sources,as_of):
    if c.get('claim_type') not in CUSTOMER_TYPES:return []
    reasons=[]
    predicate=c.get('predicate_review') or {}
    if not all(predicate.get(k) is True for k in ('customer_scope_checked','unknown_event_time_checked','corrections_conflicts_checked')):
        reasons.append('CUSTOMER_SCOPE_SEMANTICS_UNREVIEWED')
    if predicate.get('extension_policy_sha256')!=policy_hash():reasons.append('CUSTOMER_POLICY_REVIEW_PENDING')
    for e in c.get('evidence',[]):
        s=sources[e['source_id']]
        if e['stance']=='supports' and s['source_type'] not in {'customer_project_report','independent_reporting'}:
            reasons.append('UNQUALIFIED_CUSTOMER_SUPPORT_SOURCE')
        correction=s.get('correction')
        if correction:
            try:
                if calendar_date(correction['date'])>as_of: reasons.append('CUSTOMER_CORRECTION_POSTDATES_AS_OF')
            except (KeyError,TypeError,ValueError):reasons.append('CUSTOMER_CORRECTION_DATE_UNRESOLVED')
        if e['stance']=='supports' and s['source_type']=='customer_project_report' and s.get('relationship')!='customer_project_party':
            reasons.append('PRIMARY_CUSTOMER_RELATIONSHIP_UNQUALIFIED')
    return reasons

def customer_release_blockers(data):
    claims=[c for c in data['claims'] if c['claim_type'] in CUSTOMER_TYPES]
    if not claims:return []
    review=data.get('source_review') or {}
    required={c['collector'] for c in claims}|{r['reviewer'] for c in claims for r in c['reviews']}|{review.get('reviewer'),review.get('researcher')}
    acknowledged={a.get('actor') for a in data.get('rollout',{}).get('acknowledgements',[]) if a.get('customer_extension')==EXTENSION and a.get('customer_extension_sha256')==policy_hash() and a.get('acknowledged_at')}
    blockers=[]
    if any(review.get('reviewer')==c['collector'] or any(r['reviewer']==review.get('reviewer') for r in c['reviews']) for c in claims):
        blockers.append('CUSTOMER_REVIEWERS_NOT_DISTINCT')
    if (required-{None})-acknowledged:blockers.append('CUSTOMER_POLICY_ACKNOWLEDGEMENTS_MISSING')
    if review.get('customer_extension_sha256')!=policy_hash() or set(review.get('customer_claim_ids',[]))!={c['id'] for c in claims} or review.get('customer_authority_and_temporal_scope_checked') is not True:
        blockers.append('CUSTOMER_SOURCE_SCOPE_REVIEW_PENDING')
    return blockers

def customer_output(c):
    if c.get('claim_type') not in CUSTOMER_TYPES:return {}
    return {'customer_scope':EXTENSION,'customer_subject':c['customer_subject'],
            'report_dates':[{'source_id':e['source_id'],'report_date':e['customer_attribution']['report_date'],'semantics':'source_publication_only','event_time':None,'original_witness':e['customer_attribution']['original_witness'],'factual_origin_id':e['customer_attribution']['factual_origin_id']} for e in c['evidence']],
            'excluded_inferences':list(EXCLUDED),'issuer_survival':None,'issuer_operating_activity':None,'financing':None,'investor_return':None}
