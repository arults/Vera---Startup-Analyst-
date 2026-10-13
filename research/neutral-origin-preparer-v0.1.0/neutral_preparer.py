"""Unadopted, estimator-disconnected hypothetical neutral preparation candidate."""
import copy
from datetime import date

STATUSES = {'TRUE', 'FALSE', 'UNKNOWN'}
class InvalidInput(ValueError): pass

def status(value):
    if type(value) is not str or value not in STATUSES: raise InvalidInput('Expected TRUE/FALSE/UNKNOWN enum')
    return value

def day(value):
    if type(value) is not str or len(value)!=10: raise InvalidInput('Exact ISO day required within date interval')
    try: parsed=date.fromisoformat(value)
    except (ValueError,TypeError) as exc: raise InvalidInput('Invalid date') from exc
    if parsed.isoformat()!=value: raise InvalidInput('Noncanonical date')
    return value

def span(value):
    if type(value) is str: return (day(value),day(value))
    if type(value) is not dict or set(value)!={'earliest','latest'}: raise InvalidInput('Date requires exact day or bounded interval')
    lo,hi=day(value['earliest']),day(value['latest'])
    if lo>hi: raise InvalidInput('Reversed interval')
    return lo,hi

def relative(event_date,origin):
    if origin is None: return 'ORIGIN_UNRESOLVED'
    lo,hi=span(event_date); ol,oh=span(origin)
    if hi<ol:return 'BEFORE'
    if lo>oh:return 'AFTER'
    return 'ORDER_UNRESOLVED'

def unique(records,label):
    ids=[r.get('id') for r in records]
    if any(type(x) is not str or not x for x in ids): raise InvalidInput(label+' requires nonempty IDs')
    if len(set(ids))!=len(ids): raise InvalidInput(label+' duplicate IDs')

def prepare(f):
    original=copy.deepcopy(f)
    f=copy.deepcopy(f)
    unique(f['closes'],'close'); unique(f['events'],'event'); unique(f['entry_assertions'],'entry assertion')
    for record in f['closes']+f['events']+f['entry_assertions']:
        if type(record.get('provenance')) is not dict or not record['provenance']: raise InvalidInput('Nonempty assertion provenance required')
    f['closes'].sort(key=lambda x:x['id']); f['events'].sort(key=lambda x:x['id']); f['entry_assertions'].sort(key=lambda x:x['id'])
    if type(f['offering_year']) is not int: raise InvalidInput('Offering year must be integer')
    limit=day(f['admin_limit']); round_position=status(f['round_position_status']); ledger_complete=status(f['close_ledger_complete'])
    for c in f['closes']:
        span(c['date'])
        for k in ('completed','position_produced','aggregate_complete'):status(c[k])
    for e in f['events']:
        span(e['date'])
        for k in ('terminal','success','closure','affirmative_operation'):status(e[k])
        if 'reported' in e:span(e['reported'])
    for a in f['entry_assertions']:
        span(a['date']); status(a['independent'])
    if f.get('operating_last_positive') is not None: span(f['operating_last_positive'])
    if round_position=='FALSE' and any(c['completed']=='TRUE' and c['position_produced']=='TRUE' for c in f['closes']):
        raise InvalidInput('Round position status contradicts completed position-producing close')
    results={}
    for scenario in ('A','B'):
        reasons=[]; origin=None; origin_ids=[]
        if scenario=='A':
            required=('completed','position_produced')
            confirmed=[c for c in f['closes'] if all(c[k]=='TRUE' for k in required)]
            possible=[c for c in f['closes'] if all(c[k]!='FALSE' for k in required) and any(c[k]=='UNKNOWN' for k in required)]
            if not confirmed:reasons.append('NO_QUALIFIED_FIRST_POSITION_CLOSE')
            else:
                # A first close can be chosen only if its entire date support precedes others.
                ordered=sorted(confirmed,key=lambda c:span(c['date'])[0]); first=ordered[0]
                if any(span(c['date'])[0]<=span(first['date'])[1] for c in ordered[1:]):reasons.append('FIRST_CLOSE_ORDER_UNRESOLVED')
                elif any(span(c['date'])[0]<=span(first['date'])[1] for c in possible):reasons.append('EARLIER_POSSIBLE_CLOSE_UNRESOLVED')
                else:origin=first['date'];origin_ids=[first['id']]
        else:
            required=('completed','aggregate_complete')
            confirmed=[c for c in f['closes'] if all(c[k]=='TRUE' for k in required)]
            possible=[c for c in f['closes'] if all(c[k]!='FALSE' for k in required) and any(c[k]=='UNKNOWN' for k in required)]
            if round_position!='TRUE':reasons.append('AGGREGATE_POSITION_PRODUCTION_UNRESOLVED' if round_position=='UNKNOWN' else 'NO_AGGREGATE_POSITION')
            if len(confirmed)!=1:reasons.append('AGGREGATE_COMPLETION_MISSING_OR_CONFLICTING')
            if possible:reasons.append('POSSIBLE_AGGREGATE_COMPLETION_UNRESOLVED')
            if not reasons:
                final=confirmed[0]
                known_positions=[c for c in f['closes'] if c['completed']=='TRUE' and c['position_produced']=='TRUE']
                if any(relative(c['date'],final['date'])=='AFTER' for c in known_positions):
                    reasons.append('POSITION_CLOSE_AFTER_AGGREGATE_COMPLETION_REQUIRES_REVIEW')
                else:origin=final['date'];origin_ids=[final['id']]
        if scenario=='A' and ledger_complete!='TRUE':
            origin=None;origin_ids=[];reasons.append('FIRST_CLOSE_LEDGER_COMPLETENESS_UNRESOLVED')
        relations={e['id']:relative(e['date'],origin) for e in f['events']}
        baseline='ORIGIN_UNRESOLVED' if origin is None else 'ENTRY_UNKNOWN'
        asserted=any(a['date']==origin and a['independent']=='TRUE' for a in f['entry_assertions']) if origin else False
        denied=any(a['date']==origin and a['independent']=='FALSE' for a in f['entry_assertions']) if origin else False
        prior=[e for e in f['events'] if e['terminal']=='TRUE' and relations[e['id']]=='BEFORE']
        ambiguous=[e for e in f['events'] if e['terminal']!='FALSE' and relations[e['id']] in ('BEFORE','ORDER_UNRESOLVED') and not(e['terminal']=='TRUE' and relations[e['id']]=='BEFORE')]
        if origin:
            if asserted and denied:baseline='ENTRY_CONFLICT'
            elif prior:baseline='ENTRY_CONFLICT' if asserted else 'KNOWN_NONINDEPENDENT'
            elif denied:baseline='KNOWN_NONINDEPENDENT_ASSERTION'
            elif ambiguous:baseline='ENTRY_ORDER_OR_TERMINAL_STATUS_UNRESOLVED'
            elif asserted:baseline='INDEPENDENT_ASSERTION_SUPPLIED'
        if asserted and denied:reasons.append('CONTRADICTORY_INDEPENDENT_ENTRY_ASSERTIONS')
        if ambiguous:reasons.append('MATERIAL_TERMINAL_ORDER_OR_STATUS_UNRESOLVED')
        if prior and asserted:reasons.append('INDEPENDENCE_ASSERTION_CONFLICTS_WITH_PRIOR_TERMINAL')
        results[scenario]={'candidate_origin':origin,'origin_close_ids':origin_ids,'origin_reasons':reasons,'entry_disposition':baseline,'relations':relations}
    window={}
    for e in f['events']:
        lo,hi=span(e['date']); window[e['id']]='WITHIN' if hi<=limit else 'AFTER' if lo>limit else 'BOUNDARY_UNRESOLVED'
    return {'input_record':original,'status':'UNADOPTED_HYPOTHETICAL_CANDIDATE','scenarios':results,'close_ledger':f['closes'],'event_ledger':f['events'],
            'entry_assertions':f['entry_assertions'],'offering_year':f['offering_year'],'operating_last_positive':f.get('operating_last_positive'),
            'within_admin_window':window,'index_relative_success_qualification':'NOT_EVALUATED','analytical_endpoint_eligibility':'NOT_EVALUATED',
            'post_success_operating_state':'NOT_INFERRED','primary_origin_selected':False}

def validate_output(f,output):
    if prepare(f)!=output: raise InvalidInput('Derived output differs from neutral preparation contract')
    return True
