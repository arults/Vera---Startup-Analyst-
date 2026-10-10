"""Local observation-only projection; no semantic adjudication or estimator interface."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from datetime import date, datetime

SCHEMA = 'vera.followup-diagnostic.input.v0.2'
ATTRIBUTION = {'reviewed_attribution', 'pending', 'held'}
OPERATING = {'operating_point', 'operating_period', 'non_operating_context', 'unresolved_predicate', 'unresolved_time', 'invalid_time'}
RELATIONS = {'same_platform_native', 'other_platform_graph_aware', 'outside', 'unresolved'}
APPLICABILITY = {'supported', 'unresolved', 'inapplicable'}
MISSING = {'not_searched', 'searched_no_relevant_result', 'tool_failure', 'auth_required', 'unavailable', 'not_reported', 'ambiguous', 'not_applicable'}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def exact_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('date must be YYYY-MM-DD')
    return date.fromisoformat(value)

def aware_instant(value):
    if not isinstance(value, str):
        raise ValueError('instant must be string')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('instant requires timezone')
    return parsed

def nonblank(value):
    return isinstance(value, str) and bool(value.strip())

def artifact_reference_complete(ref):
    return (nonblank(ref.get('artifact_path')) and '\x00' not in ref['artifact_path']
            and isinstance(ref.get('artifact_sha256'), str)
            and bool(re.fullmatch(r'[0-9a-f]{64}', ref['artifact_sha256'])))

def reference_complete(ref):
    return (nonblank(ref.get('id')) and nonblank(ref.get('artifact_path'))
            and isinstance(ref.get('artifact_sha256'), str)
            and bool(re.fullmatch(r'[0-9a-f]{64}', ref['artifact_sha256']))
            and isinstance(ref.get('claim_payload_sha256'), str)
            and bool(re.fullmatch(r'[0-9a-f]{64}', ref['claim_payload_sha256'])))

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def point_window(day, entry, cutoff):
    """Separate boundary relations: entry=cutoff retains both equalities."""
    try:
        e, c = exact_date(entry), exact_date(cutoff)
        require(e <= c, 'entry after cutoff')
    except (ValueError, TypeError):
        return {'entry_relation': 'unresolved', 'cutoff_relation': 'unresolved', 'window_status': 'unresolved'}
    return {'entry_relation': 'before_entry' if day < e else 'at_entry' if day == e else 'after_entry',
            'cutoff_relation': 'before_cutoff' if day < c else 'at_cutoff' if day == c else 'after_cutoff',
            'window_status': 'pre_entry_context' if day < e else 'after_window' if day > c else 'within_closed_window'}

def period_window(start, end, entry, cutoff):
    try:
        e, c = exact_date(entry), exact_date(cutoff)
        require(e <= c, 'entry after cutoff')
    except (ValueError, TypeError):
        return {'window_status': 'unresolved', 'endpoint_observation_inferred': False}
    return {'window_status': 'pre_entry_context' if end < e else 'after_window' if start > c else 'overlaps_window',
            'endpoint_observation_inferred': False}

def project(document):
    """Project explicit supplied dispositions; never infer them from prose or tags."""
    before = canonical(document)
    require(isinstance(document, dict) and document.get('schema') == SCHEMA, 'schema mismatch')
    require(type(document.get('synthetic')) is bool, 'synthetic flag required')
    cutoffs = document.get('cutoffs')
    require(isinstance(cutoffs, dict), 'cutoffs object required')
    exact_date(cutoffs['evidence_report_cutoff'])
    if cutoffs.get('historical_availability_cutoff') not in (None, 'not_requested'):
        aware_instant(cutoffs['historical_availability_cutoff'])
    records = document.get('observations')
    require(isinstance(records, list), 'observations list required')
    bindings = document.get('input_bindings', [])
    require(isinstance(bindings, list), 'input_bindings must be list')
    diagnostic_holds = ['EVIDENCE_REPORT_CONSISTENCY_NOT_EVALUATED', 'DEPENDENCY_FILE_VERIFICATION_NOT_PERFORMED']
    if not bindings: diagnostic_holds.append('DEPENDENCY_FILES_NOT_BOUND')
    output = []; ids = set()
    for r in records:
        require(isinstance(r, dict), 'observation object required')
        rid = r.get('id'); require(isinstance(rid, str) and rid and rid not in ids, 'invalid/duplicate observation id'); ids.add(rid)
        payload = r['original_claim']; require(digest(canonical(payload)) == r['claim_payload_sha256'], 'claim payload digest mismatch')
        axes = r['supplied_dispositions']; require(isinstance(axes, dict), 'dispositions object required')
        require(axes['source_attribution'] in ATTRIBUTION, 'invalid attribution disposition')
        interpretation = axes['operating_interpretation']; require(interpretation in OPERATING, 'invalid operating disposition')
        scope = axes['native_scope']; require(isinstance(scope, dict) and scope.get('relation') in RELATIONS, 'invalid native scope')
        for key in ('source_original_platform', 'indexed_platform', 'original_host', 'archive_host', 'mapping_review_ref'):
            require(key in scope, 'missing scope field:'+key)
        state = axes['independent_state_applicability']; require(state in APPLICABILITY, 'invalid state applicability')
        rounds = axes['index_round_applicability']; require(isinstance(rounds, list), 'round applicability list required')
        require(nonblank(r.get('round_mapping_reason')), 'round mapping rationale required')
        require(isinstance(r.get('review_refs'), list) and all(isinstance(x, dict) for x in r['review_refs']), 'review refs list required')
        missing = r.get('missingness', {}); require(isinstance(missing, dict) and all(v in MISSING for v in missing.values()), 'invalid missingness')
        holds = r.get('supplied_holds', []); require(isinstance(holds, list) and all(isinstance(x, str) for x in holds), 'holds must be strings')
        holds = list(holds)
        if not r['review_refs']: holds.append('REVIEW_BINDING_NOT_SUPPLIED')
        if any(not reference_complete(ref) for ref in r['review_refs']):
            holds.append('REVIEW_REFERENCE_INCOMPLETE')
        if not any(reference_complete(ref) for ref in r['review_refs']):
            holds.append('NO_COMPLETE_REVIEW_REFERENCE')
        for review in r['review_refs']:
            if review.get('claim_payload_sha256') not in (None, r['claim_payload_sha256']):
                holds.append('STALE_REVIEW_REFERENCE')
        # This projector never authenticates reviewers or upgrades supplied judgments.
        holds.append('PROJECTOR_DOES_NOT_AUTHENTICATE_REVIEW_AUTHORITY')
        if not rounds: holds.append('ROUND_MAPPING_UNRESOLVED')
        if scope['relation'] != 'unresolved' and not scope['mapping_review_ref']: holds.append('NATIVE_SCOPE_MAPPING_UNBOUND')
        if state == 'unresolved': holds.append('INDEPENDENT_STATE_MAPPING_UNRESOLVED')
        time = r.get('source_observed_time'); require(isinstance(time, dict), 'source_observed_time object required')
        validated_time = None
        try:
            if interpretation == 'operating_point':
                require(time.get('kind') == 'point', 'point interpretation requires point time')
                require(nonblank(time.get('basis')), 'point time basis missing')
                validated_time = exact_date(time.get('on'))
            elif interpretation == 'operating_period':
                require(time.get('kind') == 'activity_period', 'period interpretation requires period time')
                require(nonblank(time.get('basis')), 'period time basis missing')
                start, end = exact_date(time.get('start')), exact_date(time.get('end'))
                require(start <= end, 'reversed activity bounds'); validated_time = (start, end)
        except (ValueError, TypeError):
            interpretation = 'invalid_time'; holds.append('INVALID_OPERATING_TIME'); validated_time = None
        dates = r.get('source_dates'); require(isinstance(dates, dict), 'source_dates object required')
        for field in ('publication_date', 'as_of_date'):
            if dates.get(field) is not None: exact_date(dates[field])
        for field in ('retrieved_at', 'reviewed_at'):
            if dates.get(field) is not None: aware_instant(dates[field])
        relations = []
        round_ids = set()
        for rr in rounds:
            require(isinstance(rr, dict) and isinstance(rr.get('round_id'), str) and rr['round_id'], 'round id required')
            require(rr['round_id'] not in round_ids, 'duplicate round mapping'); round_ids.add(rr['round_id'])
            require(rr.get('disposition') in APPLICABILITY and nonblank(rr.get('rationale')), 'invalid round applicability')
            if interpretation == 'operating_point' and validated_time is not None:
                relation = point_window(validated_time, rr.get('entry_date'), cutoffs.get('analytical_extraction_cutoff'))
            elif interpretation == 'operating_period' and validated_time is not None:
                relation = period_window(*validated_time, rr.get('entry_date'), cutoffs.get('analytical_extraction_cutoff'))
            else: relation = {'window_status': 'not_computable_from_operating_time'}
            relations.append({'round_id': rr['round_id'], **relation})
        output.append({'id': rid, 'original_claim': copy.deepcopy(payload), 'claim_payload_sha256': r['claim_payload_sha256'],
            'supplied_dispositions': copy.deepcopy(axes), 'operating_time_diagnostic': interpretation,
            'source_observed_time': copy.deepcopy(time), 'source_dates': copy.deepcopy(dates),
            'review_reference_structure': [reference_complete(ref) for ref in r['review_refs']],
            'review_artifact_files_verified': False,
            'source_date_fields_missing': [field for field in ('publication_date', 'as_of_date', 'retrieved_at', 'reviewed_at') if dates.get(field) is None],
            'review_refs': copy.deepcopy(r['review_refs']), 'round_mapping_reason': r['round_mapping_reason'],
            'window_relations': relations, 'missingness': copy.deepcopy(missing), 'holds': sorted(set(holds)),
            'native_censor_date': None, 'estimator_enabled': False, 'estimation_eligible': False})
    require(canonical(document) == before, 'input mutation')
    return {'schema': 'vera.followup-diagnostic.output.v0.2', 'synthetic': document['synthetic'],
        'projection_only': True, 'authority_validation_performed': False,
        'supplied_dispositions_are_not_new_adjudications': True,
        'cutoffs': copy.deepcopy(cutoffs), 'historical_availability_evaluated': False,
        'evidence_report_consistency_evaluated': False,
        'diagnostic_holds': diagnostic_holds,
        'dependency_binding_diagnostic': {'declared_count': len(bindings), 'filesystem_verification_performed': False,
            'verified_dependency_hashes': {}, 'coverage_completeness_evaluated': False},
        'observations': output, 'native_censor_date': None, 'estimator_enabled': False, 'estimation_eligible': False}

def run(input_path, output_path):
    """Only new diagnostic output is written; all bound paths are explicit in input."""
    src = Path(input_path).resolve(); requested_dest = Path(output_path)
    require(not requested_dest.exists() and not requested_dest.is_symlink(), 'output must be a new path, not a symlink')
    dest = requested_dest.resolve()
    require(not dest.exists(), 'output must be a new path')
    raw = src.read_bytes(); doc = json.loads(raw); snapshots = {src: raw}
    bindings = doc.get('input_bindings', [])
    require(isinstance(bindings, list), 'input_bindings must be list')
    for binding in bindings:
        require(isinstance(binding, dict) and isinstance(binding.get('path'), str), 'invalid input binding')
        bound = (src.parent / binding['path']).resolve(); contents = bound.read_bytes()
        require(digest(contents) == binding.get('sha256'), 'bound input digest mismatch')
        snapshots[bound] = contents
    require(dest not in snapshots, 'output aliases input')
    try:
        result = project(doc)
    finally:
        require(all(path.read_bytes() == contents for path, contents in snapshots.items()), 'input bytes changed during diagnostic')
    verified = {str(path): digest(contents) for path, contents in snapshots.items() if path != src}
    result['dependency_binding_diagnostic'].update(filesystem_verification_performed=bool(verified), verified_dependency_hashes=verified)
    if verified:
        result['diagnostic_holds'].remove('DEPENDENCY_FILE_VERIFICATION_NOT_PERFORMED')
    for observation in result['observations']:
        refs = observation['review_refs']
        all_verified = bool(refs) and all(artifact_reference_complete(ref) and verified.get(str((src.parent / ref['artifact_path']).resolve())) == ref['artifact_sha256'] for ref in refs)
        observation['review_artifact_files_verified'] = all_verified
        if not all_verified:
            observation['holds'].append('REVIEW_ARTIFACT_FILES_NOT_VERIFIED')
    result['input_hashes'] = {str(path): digest(contents) for path, contents in snapshots.items()}
    encoded = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    with dest.open('x', encoding='utf-8') as stream:
        stream.write(encoded)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); run(args.input, args.output)

if __name__ == '__main__': main()
