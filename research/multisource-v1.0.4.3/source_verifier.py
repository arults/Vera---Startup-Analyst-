"""Bounded search sufficiency. Structural validation cannot certify source truth."""
from evidence import POLICY, sha, stable, timestamp, date
from pathlib import Path

VERDICTS={'SUFFICIENT_FOR_NARROW_CLAIM','INCOMPLETE_MATERIAL_ROUTE','EXHAUSTED_WITH_UNKNOWNS','ACCESS_BLOCKED'}
FAMILIES={'native_platform','direct_party','legal_regulatory','independent_reporting'}
PURPOSES={'primary','contradiction','alternative'}

def coverage_digest(data):
    return sha(stable({k:data.get(k) for k in ('research_plan','sources','claims','policy')}))

def audit(data,root=None,expected_plan_policy=None):
    plan=data.get('research_plan',{}); blockers=[]; warnings=[]
    claims=data.get('claims',[]);sources=data.get('sources',[]);review=data.get('source_review')
    sm={s['id']:s for s in sources}; routes=plan.get('routes',[])
    if plan.get('policy')!=(expected_plan_policy or POLICY): blockers.append('WRONG_SEARCH_POLICY')
    try:
        from timing import bounds
        declared_low,_,_=bounds(plan,'declared_at','declared_timing',root)
        if declared_low is None or plan.get('retrospective_import'): blockers.append('PROSPECTIVE_PLAN_NOT_ESTABLISHED')
    except (KeyError,TypeError,ValueError,OSError,IndexError): blockers.append('PROSPECTIVE_PLAN_NOT_ESTABLISHED')
    if not plan.get('search_cutoff'): blockers.append('SEARCH_CUTOFF_MISSING')
    if len({r.get('id') for r in routes})!=len(routes): blockers.append('DUPLICATE_ROUTE')
    entities={x.get('company_id'):x for x in plan.get('entities',[])}
    exceptions=set((review or {}).get('approved_exception_route_ids',[]))
    for c in claims:
        cid=c['id'];entity=entities.get(c['company_id'],{})
        aliases=set(entity.get('aliases',[]))
        if not aliases or not entity.get('identity_basis'): blockers.append(cid+':ENTITY_ALIASES_UNDECLARED')
        relevant=[r for r in routes if cid in r.get('claim_ids',[]) and c['company_id'] in r.get('company_ids',[]) and c['claim_type'] in r.get('claim_types',[])]
        if not relevant: blockers.append(cid+':NO_ENTITY_SPECIFIC_ROUTES')
        for purpose in sorted(PURPOSES):
            if not any(r.get('purpose')==purpose for r in relevant): blockers.append(cid+':MISSING_'+purpose.upper()+'_ROUTE')
        for family in sorted(FAMILIES):
            if not any(r.get('source_family')==family for r in relevant): blockers.append(cid+':MISSING_FAMILY_'+family)
        covered=set(a for r in relevant if r.get('status')=='searched' for a in r.get('aliases_searched',[]))
        if aliases-covered: blockers.append(cid+':ALIASES_NOT_SEARCHED')
        if not any(r.get('status')=='searched' and r.get('source_family')!='native_platform' for r in relevant): blockers.append(cid+':OUTSIDE_SOURCES_NOT_SEARCHED')
        for purpose in ('primary','contradiction'):
            if not any(r.get('status')=='searched' and r.get('purpose')==purpose for r in relevant): blockers.append(cid+':NO_COMPLETED_'+purpose.upper()+'_ROUTE')
    for r in routes:
        status=r.get('status');rid=str(r.get('id','missing'))
        if status not in {'searched','blocked','unperformed','not_applicable'}: blockers.append(rid+':INVALID_STATUS')
        if status=='unperformed': blockers.append(rid+':UNPERFORMED_MATERIAL_ROUTE')
        if status in {'blocked','not_applicable'} and not r.get('reason'): blockers.append(rid+':MISSING_REASON')
        if status=='not_applicable' and rid not in exceptions: blockers.append(rid+':EXCEPTION_UNREVIEWED')
        if status=='blocked':
            warnings.append(rid+':ACCESS_BLOCKED')
            alternatives=[a for a in routes if a.get('id') in r.get('adequate_alternative_route_ids',[]) and a.get('status')=='searched' and all(set(r.get(k,[]))<=set(a.get(k,[])) for k in ('claim_ids','company_ids','claim_types')) and r.get('purpose')==a.get('purpose')]
            if r.get('material',True) or rid not in exceptions or not alternatives: blockers.append(rid+':MATERIAL_ACCESS_BLOCK')
        if status=='searched':
            if not all(r.get(k) for k in ('query','result','source_family','receipt','aliases_searched','time_scope')) or not (r.get('searched_at') or r.get('search_timing')): blockers.append(rid+':INCOMPLETE_SEARCH_RECEIPT')
            if r.get('result_class') in {'relevant_counterevidence','ambiguous'}:
                disposition=r.get('counterevidence_disposition',{})
                if not disposition.get('claim_ids') or set(disposition.get('claim_ids',[]))!=set(r.get('claim_ids',[])) or not disposition.get('rationale'):
                    blockers.append(rid+':COUNTEREVIDENCE_DISPOSITION_MISSING')
                if (review or {}).get('verdict')=='SUFFICIENT_FOR_NARROW_CLAIM' and disposition.get('status') not in {'resolved','narrow_scope_exclusion'}:
                    blockers.append(rid+':UNRESOLVED_COUNTEREVIDENCE')
            if r.get('result_class') not in {'relevant_positive','relevant_counterevidence','no_relevant_result','ambiguous'}: blockers.append(rid+':RESULT_CLASS_MISSING')
            if r.get('time_scope')!='unrestricted' and not r.get('time_scope_rationale'): blockers.append(rid+':UNJUSTIFIED_DATE_RESTRICTION')
            if r.get('grouped_query') and not r.get('per_entity_result_review'): blockers.append(rid+':GROUPED_QUERY_UNREVIEWED')
            try:
                from timing import bounds
                low,high,_=bounds(r,'searched_at','search_timing',root)
                plow,phigh,_=bounds(plan,'declared_at','declared_timing',root)
                if low is None: blockers.append(rid+':SEARCH_START_NOT_ESTABLISHED')
                elif low<phigh: blockers.append(rid+':PLAN_SEARCH_ORDER_UNPROVEN')
                if high.astimezone(__import__('datetime').timezone.utc).date()>date(plan['search_cutoff']): blockers.append(rid+':SEARCH_POSTDATES_CUTOFF')
            except (KeyError,TypeError,ValueError,OSError,IndexError): blockers.append(rid+':INVALID_SEARCH_TIME')
        if not set(r.get('source_ids',[]))<=set(sm): blockers.append(rid+':UNKNOWN_SOURCE')
    if not plan.get('stopping_rationale'): blockers.append('NO_STOPPING_RATIONALE')
    if plan.get('stop_kind') not in {'claim_sufficient','exhausted_unknowns','access_blocked','budget_exhausted'}: blockers.append('STOP_KIND_MISSING')
    if not review: blockers.append('INDEPENDENT_SOURCE_REVIEW_PENDING')
    else:
        if review.get('reviewer')==review.get('researcher') or not review.get('reviewer') or not review.get('researcher'): blockers.append('SOURCE_REVIEW_NOT_INDEPENDENT')
        if review.get('plan_sha256')!=sha(stable(plan)) or review.get('coverage_sha256')!=coverage_digest(data): blockers.append('STALE_SOURCE_REVIEW')
        if not review.get('origin_families_checked') or not review.get('depth_checked'): blockers.append('SOURCE_DEPTH_OR_INDEPENDENCE_UNREVIEWED')
        if review.get('verdict') not in VERDICTS: blockers.append('INVALID_SOURCE_VERDICT')
        expected_stops={'EXHAUSTED_WITH_UNKNOWNS':{'exhausted_unknowns'},'ACCESS_BLOCKED':{'access_blocked'}}
        if review.get('verdict') in expected_stops and plan.get('stop_kind') not in expected_stops[review['verdict']]: blockers.append('VERDICT_STOP_MISMATCH')
        if not review.get('rationale'): blockers.append('SOURCE_REVIEW_RATIONALE_MISSING')
        if set(review.get('claim_ids',[]))!=set(c['id'] for c in claims): blockers.append('SOURCE_REVIEW_SCOPE_MISMATCH')
        try:
            from timing import bounds
            reviewed,review_end,_=bounds(review,'reviewed_at','review_timing',root)
            if reviewed is None: blockers.append('REVIEW_START_NOT_ESTABLISHED')
            for r in routes:
                if r.get('status')=='searched':
                    low,high,_=bounds(r,'searched_at','search_timing',root)
                    if reviewed is None or high>reviewed: blockers.append('REVIEW_SEARCH_ORDER_UNPROVEN')
        except (KeyError,TypeError,ValueError,OSError,IndexError): blockers.append('INVALID_SOURCE_REVIEW_TIME')
    used={x['source_id'] for c in claims for x in c.get('evidence',[])}
    for sid in used:
        source=sm.get(sid,{})
        from scoped_review import section_adequate
        linked=[c['id'] for c in claims if any(e['source_id']==sid for e in c.get('evidence',[]))]
        if not source.get('original_body_inspected') and not all(section_adequate(source,cid)[0] for cid in linked): blockers.append(sid+':FULL_BODY_NOT_INSPECTED')
        if not source.get('origin_rationale') or not source.get('upstream_urls'): blockers.append(sid+':ORIGIN_PROVENANCE_MISSING')
    if review and review.get('verdict')=='SUFFICIENT_FOR_NARROW_CLAIM':
        if plan.get('stop_kind')!='claim_sufficient': blockers.append('OPERATIONAL_STOP_NOT_SUFFICIENT')
    policy_sha256=sha(Path(__file__).with_name('POLICY.md').read_bytes())
    acknowledgements=data.get('rollout',{}).get('acknowledgements',[])
    required={c['collector'] for c in claims} | {r['reviewer'] for c in claims for r in c.get('reviews',[])}
    if review: required|={review.get('reviewer'),review.get('researcher')}
    acknowledged={a['actor'] for a in acknowledgements if a.get('policy')==POLICY and a.get('policy_sha256')==policy_sha256 and a.get('acknowledged_at')}
    missing=sorted(x for x in required-acknowledged if x)
    if missing: blockers.append('POLICY_ACKNOWLEDGEMENTS_MISSING')
    return {'policy_sha256':policy_sha256,'status':'INCOMPLETE_MATERIAL_ROUTE' if blockers else review['verdict'],'blockers':sorted(set(blockers)), 'access_warnings':warnings,
            'operational_stop':plan.get('stop_kind'),'missing_policy_acknowledgements':missing,'route_count':len(routes),
            'origin_family_count':len({s.get('origin_family') for s in sources}),
            'claim_truth_certified':False,'receipt_content_authenticated':False,'reviewer_identity_authenticated':False,'research_conclusion_authorized':False,'calibrated_probability':None}
