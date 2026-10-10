"""Explicit claim views over an unchanged full ledger, with fresh scope-bound review."""
import copy
import json
import datetime as dt
from pathlib import Path
from evidence import IMPLEMENTATION_VERSION,stable,sha,validate,base_report,source_snapshot,date,timestamp,safe_path

def claim_sources(claim):
    ids=[e['source_id'] for e in claim.get('evidence',[])]
    identity_ids=claim.get('identity',{}).get('evidence_source_ids',[])
    if not isinstance(identity_ids,list) or any(not isinstance(x,str) for x in identity_ids):raise ValueError('identity evidence IDs must be a string list')
    return set(ids+identity_ids)

RELATIONS={'dependency','contradiction','identity_context','temporal_context','same_transaction','irrelevant'}

def inspection_digest(inspection):
    if not isinstance(inspection,dict):raise ValueError('inspection must be an object')
    return sha(stable({k:v for k,v in inspection.items() if k!='review'}))

def section_adequate(source,claim_id,root=None):
    i=source.get('inspection') or {}
    if not isinstance(i,dict):return False,['INSPECTION_SCHEMA_INVALID']
    r=i.get('review') or {}
    if not isinstance(r,dict):return False,['INSPECTION_REVIEW_SCHEMA_INVALID']
    errors=[]
    if any(not isinstance(i.get(k,[]),list) for k in ('sections','excluded_sections','limitations','unresolved_material','claim_ids')) or not isinstance(r.get('adequate_claim_ids',[]),list):return False,['INSPECTION_LIST_SCHEMA_INVALID']
    if i.get('mode') not in {'full_document','relevant_sections'}:errors.append('INSPECTION_MODE_MISSING')
    if i.get('document_sha256')!=source.get('original_sha256'):errors.append('INSPECTION_DOCUMENT_HASH_MISMATCH')
    if root is not None:
        try:
            if sha(safe_path(root,i['document_reference']).read_bytes())!=i.get('document_sha256'):errors.append('INSPECTION_DOCUMENT_BYTES_MISMATCH')
        except (KeyError,TypeError,ValueError,OSError):errors.append('INSPECTION_DOCUMENT_UNAVAILABLE')
    sections=i.get('sections',[])
    if not isinstance(sections,list) or not sections or any(not isinstance(s,dict) or not s.get('locator') or not s.get('context') for s in sections):errors.append('INSPECTION_LOCATORS_OR_CONTEXT_MISSING')
    if 'excluded_sections' not in i or 'limitations' not in i:errors.append('INSPECTION_LIMITATIONS_MISSING')
    if i.get('qualifications_checked') is not True or i.get('cross_references_checked') is not True:errors.append('QUALIFICATIONS_OR_CROSS_REFERENCES_UNCHECKED')
    if i.get('unresolved_material'):errors.append('UNINSPECTED_MATERIAL_SECTION')
    if claim_id not in i.get('claim_ids',[]) or claim_id not in r.get('adequate_claim_ids',[]):errors.append('INSPECTION_CLAIM_UNREVIEWED')
    if not r.get('reviewer') or not r.get('rationale') or r.get('inspection_sha256')!=inspection_digest(i):errors.append('INSPECTION_REVIEW_STALE_OR_MISSING')
    return not errors,errors

def scope_digest(data):
    scope={k:v for k,v in data.get('research_scope',{}).items() if k!='review'}
    return sha(stable({'policy':data['policy'],'claims':data['claims'],'sources':data['sources'],'research_plan':data['research_plan'],'scope':scope}))

def context_closure(data):
    scope=data['research_scope']
    if not isinstance(scope,dict):raise ValueError('research_scope must be an object')
    if not isinstance(scope.get('selected_claim_ids'),list) or any(not isinstance(x,str) for x in scope['selected_claim_ids']):raise ValueError('selected_claim_ids must be a string list')
    if not isinstance(scope.get('context_links',[]),list) or any(not isinstance(x,dict) for x in scope.get('context_links',[])):raise ValueError('context_links must be an object list')
    if not isinstance(scope.get('route_dispositions',{}),dict):raise ValueError('route_dispositions must be an object')
    cm={c['id']:c for c in data['claims']};selected=set(scope.get('selected_claim_ids',[]));closure=set(selected);errors=[]
    if not selected or not selected<=set(cm):errors.append('INVALID_SELECTED_CLAIMS')
    links=scope.get('context_links',[])
    for link in links:
        if any(not isinstance(link.get(k),str) for k in ('from','to','relation')):raise ValueError('context link identifiers and relation must be strings')
        if link.get('from') not in cm or link.get('to') not in cm or link.get('relation') not in RELATIONS:errors.append('INVALID_CONTEXT_LINK')
        if not link.get('rationale'):errors.append('CONTEXT_RATIONALE_MISSING')
    changed=True
    while changed:
        before=set(closure)
        for cid in list(closure):
            c=cm.get(cid,{})
            if not isinstance(c.get('dependencies',[]),list) or any(not isinstance(x,str) for x in c.get('dependencies',[])):raise ValueError('dependencies must be a string list')
            targets=list(c.get('dependencies',[]))+[x['claim_id'] for x in c.get('contradictions',[])]
            targets += [x['to'] for x in links if x.get('from')==cid and x.get('relation')!='irrelevant']
            targets += [x['from'] for x in links if x.get('to')==cid and x.get('relation')=='contradiction']
            targets += [other['id'] for other in data['claims'] if any(x.get('claim_id')==cid for x in other.get('contradictions',[]))]
            for target in targets:
                if target not in cm:errors.append('MISSING_CONTEXT_DEPENDENCY:'+str(target))
                else:closure.add(target)
        for route in data['research_plan'].get('routes',[]):
            if route.get('result_class') in {'relevant_counterevidence','ambiguous'} and set(route.get('claim_ids',[]))&closure:
                for cid in route.get('claim_ids',[]):
                    if cid in cm:closure.add(cid)
                    else:errors.append('MISSING_ROUTE_CONTEXT:'+str(cid))
        changed=before!=closure
    # Every same-entity/shared-source candidate needs an explicit reviewed relevance edge.
    for cid in closure&set(cm):
        c=cm[cid];used={x['source_id'] for x in c['evidence']}
        for other in data['claims']:
            oid=other['id']
            if oid==cid:continue
            same=other['company_id']==c['company_id'] or bool(used&{x['source_id'] for x in other['evidence']})
            if same and not any({x.get('from'),x.get('to')}=={cid,oid} for x in links):errors.append('CONTEXT_RELEVANCE_UNREVIEWED:'+cid+':'+oid)
    return sorted(closure),sorted(set(errors))

def scoped_report(data,root,as_of,reviewer_registry=None):
    try:return _scoped_report(data,root,as_of,reviewer_registry)
    except (AttributeError,TypeError,KeyError,IndexError) as exc:
        raise ValueError("Malformed scoped metadata: "+str(exc)) from None

def _scoped_report(data,root,as_of,reviewer_registry=None):
    errors=validate(data,root)
    if errors:raise ValueError('\n'.join(errors))
    registry=reviewer_registry or {};scope=data['research_scope']
    if not isinstance(scope,dict) or (data.get('source_review') is not None and not isinstance(data.get('source_review'),dict)):raise ValueError('Scope and source review must be objects')
    selected=set(scope.get('selected_claim_ids',[]));closure,blocks=context_closure(data);review=data.get('source_review') or {}
    if review.get('scope_sha256')!=scope_digest(data):blocks.append('SCOPE_REVIEW_STALE_OR_MISSING')
    if set(review.get('claim_ids',[]))!=selected:blocks.append('SCOPE_REVIEW_SELECTED_MISMATCH')
    if set(review.get('context_claim_ids',[]))!=set(closure)-selected:blocks.append('SCOPE_REVIEW_CONTEXT_MISMATCH')
    for link in scope.get('context_links',[]):
        if link.get('reviewed_by')!=review.get('reviewer'):blocks.append('CONTEXT_REVIEWER_MISMATCH')
        if link.get('relation')=='contradiction' and ({link.get('from'),link.get('to')}&set(closure)):
            if link.get('status')!='resolved' or not link.get('resolution'):blocks.append('UNRESOLVED_CONTEXT_LINK:'+str(link.get('to')))
    if not review.get('timing_checked') or not review.get('inspection_scope_checked'):blocks.append('SCOPED_TIMING_OR_INSPECTION_UNREVIEWED')
    for c in data['claims']:
        if c['id'] in closure and any(x['status']=='open' for x in c['contradictions']):blocks.append('OPEN_CONTEXT_CONTRADICTION:'+c['id'])
    used={sid for c in data['claims'] if c['id'] in selected for sid in claim_sources(c)}
    for c in data['claims']:
        if c['id'] not in selected:continue
        for sid in claim_sources(c):
            found=[s for s in data['sources'] if s['id']==sid]
            if not found:blocks.append('IDENTITY_OR_EVIDENCE_SOURCE_MISSING:'+sid);continue
            s=found[0];ok,issues=section_adequate(s,c['id'],root)
            blocks.extend(s['id']+':'+x for x in issues)
            inspection=s.get('inspection') if isinstance(s.get('inspection'),dict) else {}
            ir=inspection.get('review') if isinstance(inspection.get('review'),dict) else {}
            if not ({'claim_verifier','source_verifier'}&set(registry.get(ir.get('reviewer'),[]))):blocks.append(s['id']+':INSPECTION_REVIEWER_UNAUTHORIZED')
    # Retain full ledger in output. Derive only an audit view, binding it to fresh full-scope review.
    expected_plan_policy=None
    if data['research_plan'].get('policy')!=data['policy']:
        h=scope.get('historical_plan_reassessment',{})
        try:
            good=isinstance(h,dict) and h.get('original_policy')==data['research_plan'].get('policy') and h.get('original_policy')=='vera.multisource.claim-policy.v1.0.0' and h.get('reviewed_under')==data['policy'] and h.get('reviewed_by')==review.get('reviewer') and bool(review.get('reviewer')) and h.get('same_selected_claim_scope') is True and set(h.get('selected_claim_ids',[]))==selected and bool(h.get('rationale'))
            good=good and h.get('retrospective_reassessment') is True and h.get('new_policy_prospectively_registered') is False
            good=good and sha(safe_path(root,h['original_plan_document_reference']).read_bytes())==h.get('original_plan_document_sha256')
            parent_bytes=safe_path(root,h['parent_dataset_reference']).read_bytes()
            good=good and sha(parent_bytes)==h.get('parent_dataset_sha256')
            good=good and h.get('original_policy_hash')=='21982e1c32472136cae3cbd208347734f985b2143c5758f177f7b328846c6df0' and h.get('reviewed_policy_hash')==sha((Path(__file__).parent/'POLICY.md').read_bytes())
            parent=json.loads(parent_bytes)
            good=good and sha(stable(parent['research_plan']))==h.get('original_plan_sha256')
            good=good and parent['research_plan'].get('policy')==data['research_plan'].get('policy') and parent['research_plan'].get('declared_at')==data['research_plan'].get('declared_at')
            old_claims={c['id']:c for c in parent['claims']};new_claims={c['id']:c for c in data['claims']}
            from precision_withdrawal import validate_withdrawal
            corrected=scope.get('precision_withdrawal',{}).get('claim_id') if isinstance(scope.get('precision_withdrawal',{}),dict) else None
            withdrawal_ok=validate_withdrawal(data,parent,root,registry,review) if corrected else False
            good=good and all(cid in old_claims and all(new_claims[cid].get(k)==old_claims[cid].get(k) for k in ('claim_type','company_id','round_id')) and (new_claims[cid].get('time')==old_claims[cid].get('time') or (cid==corrected and withdrawal_ok)) for cid in selected)
            if corrected and not withdrawal_ok:good=False
            equivalence=h.get('coverage_equivalence',{})
            required={'claim_scope','source_authority','identity_mapping','contradiction_search','timing_provenance','inspection_scope'}
            good=good and isinstance(equivalence,dict) and required<=set(equivalence) and all(isinstance(equivalence[k],dict) and equivalence[k].get('status')=='satisfied_for_selected_scope' and equivalence[k].get('basis') for k in required)
            if h.get('new_required_searches'):good=False
        except (KeyError,TypeError,ValueError,OSError):good=False
        if good:expected_plan_policy=h['original_policy']
        else:blocks.append('HISTORICAL_PLAN_REASSESSMENT_PENDING')
    full=copy.deepcopy(data);full.pop('research_scope',None);full['source_review']=None
    whole=base_report(full,root,as_of,registry)
    projection=copy.deepcopy(data);projection.pop('research_scope',None)
    projection['claims']=[c for c in projection['claims'] if c['id'] in selected]
    included=[];excluded=[];context_routes=[]
    dispositions=scope.get('route_dispositions',{})
    for route in data['research_plan'].get('routes',[]):
        disposition=dispositions.get(route['id'],{})
        if route['id'] in data['research_plan'].get('verifier_required_route_ids',[]) and (disposition.get('role')=='context_only' or disposition.get('material_for_selected') is False):blocks.append('VERIFIER_REQUIRED_ROUTE_DOWNGRADED:'+route['id'])
        if set(route.get('claim_ids',[]))&selected and disposition.get('role')=='context_only':
            context_routes.append(copy.deepcopy(route))
            if disposition.get('reviewed_by')!=review.get('reviewer') or not disposition.get('rationale'):blocks.append('CONTEXT_ROUTE_UNREVIEWED:'+route['id'])
            if route.get('result_class') in {'relevant_counterevidence','ambiguous'}:
                cr=route.get('counterevidence_disposition',{})
                if cr.get('status') not in {'resolved','narrow_scope_exclusion'} or not cr.get('rationale') or set(cr.get('claim_ids',[]))!=set(route.get('claim_ids',[])):blocks.append('UNRESOLVED_CONTEXT_ROUTE:'+route['id'])
            if route.get('status')=='searched':
                try:
                    from timing import bounds
                    low,high,_=bounds(route,'searched_at','search_timing',root)
                    review_low,review_high,_=bounds(review,'reviewed_at','review_timing',root)
                    if review_low is None or high>review_low:blocks.append('CONTEXT_REVIEW_ORDER_UNPROVEN:'+route['id'])
                except (ValueError,TypeError,KeyError,OSError,IndexError):blocks.append('CONTEXT_TIMING_UNPROVEN:'+route['id'])
        elif set(route.get('claim_ids',[]))&selected:
            derived=copy.deepcopy(route)
            if 'material_for_selected' in disposition:
                if disposition.get('reviewed_by')!=review.get('reviewer') or not disposition.get('rationale'):blocks.append('ROUTE_MATERIALITY_UNREVIEWED:'+route['id'])
                derived['material']=disposition['material_for_selected']
                derived['adequate_alternative_route_ids']=disposition.get('adequate_alternative_route_ids',[])
            included.append(derived)
        else:excluded.append({'route_id':route['id'],'reason':'Not a selected claim route; retained in full ledger/context report'})
    projection['research_plan']['routes']=included
    stopping=scope.get('stopping_assessment')
    if stopping:
        if stopping.get('reviewed_by')!=review.get('reviewer') or not stopping.get('rationale'):blocks.append('SCOPED_STOPPING_UNREVIEWED')
        elif stopping.get('kind')=='claim_sufficient':
            projection['research_plan']['stop_kind']='claim_sufficient'
            projection['research_plan']['stopping_rationale']=stopping['rationale']
    origin_groups={}
    for sid in sorted(used):
        assessment=review.get('origin_assessments',{}).get(sid,{})
        if not assessment.get('factual_origin_id') or not assessment.get('rationale') or assessment.get('kind') not in {'issuer_assertion','independent_reporting','official_finding'}:blocks.append('FACTUAL_ORIGIN_UNREVIEWED:'+sid)
        origin_groups[sid]=assessment.get('factual_origin_id')
    try:
        from timing import bounds
        review_low,review_high,_=bounds(review,'reviewed_at','review_timing',root)
        if review_high.astimezone(dt.timezone.utc).date()>as_of:blocks.append('SCOPED_REVIEW_POSTDATES_AS_OF')
    except (ValueError,TypeError,KeyError,OSError,IndexError):blocks.append('SCOPED_REVIEW_TIME_UNPROVEN')
    # A scope cannot copy blanket approval. Only after checking original scope hash may the
    # deterministic adapter bind the same review to the computed audit view for legacy checks.
    sr=copy.deepcopy(review)
    if review.get('scope_sha256')==scope_digest(data):
        from source_verifier import coverage_digest
        sr['plan_sha256']=sha(stable(projection['research_plan']));sr['coverage_sha256']=coverage_digest(projection)
    projection['source_review']=sr or None
    projected=base_report(projection,root,as_of,registry,context_claim_ids=closure,expected_plan_policy=expected_plan_policy)
    scoped_rows=projected['augmented_observations'];indexed={r['id']:r for r in scoped_rows}
    if blocks:
        for row in scoped_rows:row['release_status']='UNRELEASED_RESEARCH_OBSERVATION'
    rows=[indexed.get(row['id'],row) for row in whole['augmented_observations']]
    return {'implementation_version':IMPLEMENTATION_VERSION,'policy':data['policy'],'dataset':data['dataset'],'as_of':as_of.isoformat(),'as_of_convention':'End of specified day UTC for execution/availability; source-local event days preserved',
            'input_sha256':sha(stable(data)),'source_snapshot_sha256':source_snapshot(data),'scope_sha256':scope_digest(data),
            'scope':{'selected_claim_ids':sorted(selected),'effective_context_claim_ids':closure,'excluded_routes':excluded,'contextual_routes':context_routes,'reviewed_factual_origin_groups':origin_groups,'origin_count_scope':'Distinct reviewed origins across selected fact/identity scopes; not confirmations per event or calibrated independence','reviewed_origin_group_count':len({v for v in origin_groups.values() if v}),'blockers':sorted(set(blocks))},
            'scoped_source_coverage_audit':projected['source_coverage_audit'],'whole_batch_source_coverage_audit':whole['source_coverage_audit'],'original_operational_stop':data['research_plan'].get('stop_kind'),'original_plan_policy':data['research_plan'].get('policy'),'review_policy':data['policy'],'amended_policy_design':'Retrospective reassessment of historical plan; not prospectively registered under amended policy' if expected_plan_policy else 'Current-policy evaluation',
            'augmented_observations':rows,'full_ledger_preserved':True,'native_baseline':data['native_baseline'],'native_changes':0,'rates':None,'prior_promotions':0,
            'released_selected_claims':sum(r['release_status']=='RELEASED_RESEARCH_FINDING' for r in scoped_rows)}
