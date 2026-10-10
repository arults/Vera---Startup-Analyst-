"""Conservative, receipt-bound execution timing; never manufacture exact timestamps."""
import json
import datetime as dt
from evidence import timestamp, safe_path, sha

def pointer(obj,path):
    if not path.startswith('/'): raise ValueError('JSON pointer required')
    for key in path[1:].split('/'):
        key=key.replace('~1','/').replace('~0','~')
        if not isinstance(obj,(dict,list)):raise ValueError('pointer crosses scalar')
        obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj

def evidence_value(root,entry):
    if not isinstance(entry,dict):raise ValueError('timing evidence must be an object')
    raw=safe_path(root,entry['evidence_reference']).read_bytes()
    if sha(raw)!=entry.get('evidence_sha256'):raise ValueError('timing receipt hash mismatch')
    return pointer(json.loads(raw),entry['evidence_pointer'])

def bounds(obj,exact_key,timing_key,root=None):
    if not isinstance(obj,dict):raise ValueError('timing container must be an object')
    exact=timestamp(obj[exact_key]) if obj.get(exact_key) is not None else None
    supplied=obj.get(timing_key)
    if supplied is None:
        if exact is not None:return exact,exact,'exact'
        raise ValueError('timing missing')
    if not isinstance(supplied,dict):raise ValueError('timing must be an object')
    t=supplied;kind=t.get('kind')
    if kind not in {'observed_window','completed_by'}:raise ValueError('timing missing')
    if root is None:raise ValueError('receipt root required for timing window')
    if kind=='observed_window' and t.get('lower_evidence') is not None:
        actual=[evidence_value(root,t['lower_evidence']),evidence_value(root,t['upper_evidence'])]
    else:actual=evidence_value(root,t)
    if kind=='observed_window':
        if actual!=[t.get('lower'),t.get('upper')]:raise ValueError('window not in receipt')
        low,high=timestamp(t['lower']),timestamp(t['upper'])
        if low>high:raise ValueError('reversed window')
        if exact is not None and not low<=exact<=high:raise ValueError('exact time contradicts window')
        return (exact,exact,'consistent_exact_and_window') if exact is not None else (low,high,kind)
    if actual!=t.get('upper'):raise ValueError('completed-by bound not in receipt')
    high=timestamp(t['upper'])
    if exact is not None and exact>high:raise ValueError('exact time contradicts completed-by bound')
    return (exact,exact,'consistent_exact_and_bound') if exact is not None else (None,high,kind)

def utc(value):return value.astimezone(dt.timezone.utc).isoformat()

def availability(lower,upper,cutoff):
    """Evidence acquisition, not first public availability."""
    if cutoff>=upper:return 'KNOWN_BY_UPPER_BOUND'
    if lower is not None and cutoff<lower:return 'NOT_YET_ESTABLISHED'
    return 'ACQUISITION_TIME_UNCERTAIN'
