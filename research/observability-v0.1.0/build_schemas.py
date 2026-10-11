"""Rebuild structural JSON schemas from the runtime vocabulary; stdlib only."""
import importlib.util
import json
from pathlib import Path
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('schema_runtime', BASE / 'vera_observability.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
ID = {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$'}
REF = {'type': 'string', 'pattern': '^(sha256:[a-f0-9]{64}|ver:[A-Za-z0-9][A-Za-z0-9_.:-]{0,119})$'}
def nullable(value):
    return {'anyOf': [value, {'type': 'null'}]}
def obj(fields):
    return {'type': 'object', 'additionalProperties': False, 'required': list(fields), 'properties': fields}
def enum(values):
    return {'type': 'string', 'enum': sorted(values)}
refs = obj({k: nullable(REF) for k in sorted(v.REF_KEYS)})
partial_refs = {'type': 'object', 'additionalProperties': False, 'properties': {k: nullable(REF) for k in sorted(v.REF_KEYS)}}
result = obj({'schema_version': {'const': v.EVAL_SCHEMA}, 'eval_id': ID,
    'component': enum(set(v.COMPONENTS) | {'system'}), 'span_id': nullable(ID),
    'status': enum(v.EVAL_STATUS), 'quality_axis': enum(v.AXES), 'scope': enum(v.SCOPES),
    'reviewer_basis': enum({'deterministic_check', 'synthetic_fixture', 'human_review', 'jev_structured'}),
    'refs': refs, 'evidence_ref': nullable(REF),
    'reason_code': enum({'NONE', 'EVIDENCE_MISSING', 'OUT_OF_SCOPE', 'DEPENDENCY_UNAVAILABLE', 'ASSERTION_FAILED', 'INSUFFICIENT_PROVENANCE'}),
    'jev': nullable(obj({'model_ref': REF, 'question_ref': REF, 'response_ref': REF,
                         'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'review_scope': enum(v.SCOPES)}))})
result.update({'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:vera:eval:1',
               'title': 'Vera structured evaluation 1',
               'description': 'Structural contract only. Runtime validation additionally enforces target, scope, provenance and chronology.'})
expected = obj({c: obj({'applicability': enum({'required', 'not_applicable'}), 'reason_code': nullable(enum(v.NA_REASONS))}) for c in v.COMPONENTS})
expected_evals = {'type': 'object', 'maxProperties': 1000, 'propertyNames': ID,
    'additionalProperties': obj({'component': enum(set(v.COMPONENTS) | {'system'}), 'quality_axis': enum(v.AXES), 'scope': enum(v.SCOPES)})}
link = {'type': 'string', 'maxLength': 180, 'pattern': '^[A-Za-z0-9][A-Za-z0-9_.-]*(/[A-Za-z0-9][A-Za-z0-9_.-]*)*\\.html$'}
fields = {
    'run_start': {'synthetic': {'type': 'boolean'}, 'expected_components': expected, 'expected_evals': expected_evals, 'refs': refs, 'metrics_ref': nullable(link), 'integration_scope': {'const': 'explicit_local_adapter'}},
    'run_resume': {'resumes_attempt_id': ID},
    'span_start': {'span_id': ID, 'parent_span_id': nullable(ID), 'component': enum(v.COMPONENTS), 'retry_of': nullable(ID), 'metrics_attempt_id': nullable(ID), 'refs': partial_refs},
    'span_end': {'span_id': ID, 'execution_status': enum(v.EXECUTION), 'error_code': enum(v.ERROR_CODES)},
    'eval_result': {'result': {'$ref': '#/$defs/eval'}},
    'run_end': {'execution_status': enum(v.EXECUTION - {'not_run'}), 'capture_status': enum({'complete', 'partial'})},
}
base = {'schema_version': {'const': v.SCHEMA}, 'event_id': ID, 'run_id': ID, 'attempt_id': ID,
        'seq': {'type': 'integer', 'minimum': 1, 'maximum': 2**53 - 1},
        'at': {'type': 'string', 'maxLength': 40, 'format': 'date-time'}}
trace = {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:vera:observability:1',
         'title': 'Vera append-only component event 1',
         'description': 'Use validate_event and aggregate for mandatory semantic, chronology and graph validation.',
         'oneOf': [obj({**base, 'kind': {'const': kind}, **extra}) for kind, extra in fields.items()],
         '$defs': {'eval': {k: value for k, value in result.items() if k not in {'$schema', '$id'}}}}
if __name__ == '__main__':
    (BASE / 'schemas').mkdir(exist_ok=True)
    for name, schema in [('eval', result), ('trace', trace)]:
        (BASE / 'schemas' / (name + '.schema.json')).write_text(json.dumps(schema, indent=2) + '\n')
