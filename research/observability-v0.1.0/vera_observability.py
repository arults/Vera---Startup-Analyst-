#!/usr/bin/env python3
"""Explicit, payload-free local Vera traces. No network or host interception.

This module observes execution and evaluation evidence; it never estimates research
accuracy, calibration, tokens, cost, or memory. Pair with vera_metrics by run_id.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import threading
import uuid

SCHEMA = 'vera.observability/1'
EVAL_SCHEMA = 'vera.eval/1'
REPORT_SCHEMA = 'vera.observability-report/1'
COMPONENTS = ('prompt', 'identity', 'planning', 'research', 'retrieval',
              'sourcing_verifier', 'analysis', 'model', 'jev', 'report', 'persistence')
REF_KEYS = {'input', 'artifact', 'model', 'prompt', 'rubric', 'dataset', 'config', 'code'}
EXECUTION = {'completed', 'failed', 'blocked', 'not_run', 'cancelled'}
EVAL_STATUS = {'pass', 'fail', 'blocked', 'not_run', 'incomplete'}
AXES = {'engineering', 'research'}
SCOPES = {'component', 'full_system', 'generic_method', 'synthetic_contract'}
ERROR_CODES = {'NONE', 'UNCLASSIFIED_EXCEPTION', 'TIMEOUT', 'DEPENDENCY_UNAVAILABLE',
               'INVALID_INPUT', 'IO_FAILURE', 'CANCELLED', 'ASSERTION_FAILED', 'EXPLICIT_BLOCK'}
NA_REASONS = {'NOT_USED_BY_DECLARED_MODE', 'NO_MODEL_REQUEST_REQUIRED',
              'NO_JEV_REVIEW_REQUIRED', 'NO_PERSISTENCE_REQUIRED', 'FIXTURE_OUT_OF_SCOPE'}
BASE = {'schema_version', 'event_id', 'run_id', 'attempt_id', 'seq', 'at', 'kind'}
FIELDS = {
    'run_start': {'synthetic', 'expected_components', 'expected_evals', 'refs', 'metrics_ref', 'integration_scope'},
    'run_resume': {'resumes_attempt_id'},
    'span_start': {'span_id', 'parent_span_id', 'component', 'retry_of', 'metrics_attempt_id', 'refs'},
    'span_end': {'span_id', 'execution_status', 'error_code'},
    'eval_result': {'result'},
    'run_end': {'execution_status', 'capture_status'},
}
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}\Z')
_REF = re.compile(r'(?:sha256:[a-f0-9]{64}|ver:[A-Za-z0-9][A-Za-z0-9_.:-]{0,119})\Z')
LINK_WARNING = 'Production company-analysis host integration is missing. Explicit local adapters only.'
QUALITY_WARNING = 'Engineering and synthetic checks do not establish research accuracy, calibration, or prior promotion.'


class TraceError(ValueError):
    """Payload-free validation failure."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def content_ref(data):
    """Hash caller-selected bytes. Never persist the bytes or a secret-bearing path."""
    if not isinstance(data, bytes):
        raise TraceError('HASH_REQUIRES_BYTES')
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def identifier(value, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise TraceError('INVALID_IDENTIFIER')


def enum(value, allowed):
    if not isinstance(value, str) or value not in allowed:
        raise TraceError('INVALID_ENUM')


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise TraceError('INVALID_FIELDS')


def timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise TraceError('INVALID_TIMESTAMP')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise TraceError('INVALID_TIMESTAMP') from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TraceError('TIMESTAMP_REQUIRES_TIMEZONE')
    return parsed.astimezone(timezone.utc)


def reference(value, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise TraceError('INVALID_REFERENCE')


def references(value, complete_keys=False):
    if not isinstance(value, dict) or set(value) - REF_KEYS or (complete_keys and set(value) != REF_KEYS):
        raise TraceError('INVALID_PROVENANCE_FIELDS')
    for item in value.values():
        reference(item, nullable=True)


def local_link(value):
    """A relative file beneath the dashboard directory; never URL or traversal."""
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 180 or not value.endswith('.html'):
        raise TraceError('UNSAFE_METRICS_LINK')
    if not all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', part) and part not in {'.', '..'}
               for part in value.split('/')):
        raise TraceError('UNSAFE_METRICS_LINK')
    return value


def validate_eval(result):
    exact(result, {'schema_version', 'eval_id', 'component', 'span_id', 'status', 'quality_axis',
                   'scope', 'reviewer_basis', 'refs', 'evidence_ref', 'reason_code', 'jev'})
    if result['schema_version'] != EVAL_SCHEMA:
        raise TraceError('UNSUPPORTED_EVAL_SCHEMA')
    identifier(result['eval_id'])
    enum(result['component'], set(COMPONENTS) | {'system'})
    identifier(result['span_id'], nullable=True)
    enum(result['status'], EVAL_STATUS)
    enum(result['quality_axis'], AXES)
    enum(result['scope'], SCOPES)
    enum(result['reviewer_basis'], {'deterministic_check', 'synthetic_fixture', 'human_review', 'jev_structured'})
    references(result['refs'], complete_keys=True)
    reference(result['evidence_ref'], nullable=True)
    enum(result['reason_code'], {'NONE', 'EVIDENCE_MISSING', 'OUT_OF_SCOPE', 'DEPENDENCY_UNAVAILABLE',
                                 'ASSERTION_FAILED', 'INSUFFICIENT_PROVENANCE'})
    if result['status'] in {'pass', 'fail'}:
        if result['evidence_ref'] is None or any(v is None for v in result['refs'].values()):
            raise TraceError('EVALUATION_REQUIRES_PROVENANCE')
        if result['status'] == 'pass' and result['reason_code'] != 'NONE':
            raise TraceError('PASS_WITH_FAILURE_REASON')
    if result['status'] in {'blocked', 'not_run', 'incomplete'} and result['reason_code'] == 'NONE':
        raise TraceError('MISSING_EVAL_REASON')
    if result['quality_axis'] == 'research' and result['scope'] in {'generic_method', 'synthetic_contract'}:
        raise TraceError('GENERIC_OR_SYNTHETIC_IS_NOT_RESEARCH_QUALITY')
    if result['scope'] == 'component' and (result['span_id'] is None or result['component'] == 'system'):
        raise TraceError('COMPONENT_EVAL_REQUIRES_SPAN')
    if result['scope'] == 'full_system' and (result['component'] != 'system' or result['span_id'] is not None):
        raise TraceError('SYSTEM_EVAL_REQUIRES_SYSTEM_TARGET')
    if result['reviewer_basis'] == 'synthetic_fixture' and result['quality_axis'] != 'engineering':
        raise TraceError('SYNTHETIC_IS_NOT_RESEARCH_QUALITY')
    if result['reviewer_basis'] == 'jev_structured':
        jev = result['jev']
        exact(jev, {'model_ref', 'question_ref', 'response_ref', 'confidence', 'review_scope'})
        for key in ('model_ref', 'question_ref', 'response_ref'):
            reference(jev[key])
        confidence = jev['confidence']
        if type(confidence) not in {int, float} or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise TraceError('INVALID_JEV_CONFIDENCE')
        enum(jev['review_scope'], SCOPES)
        if jev['review_scope'] != result['scope']:
            raise TraceError('JEV_SCOPE_MISMATCH')
        if result['quality_axis'] == 'research' and result['scope'] in {'generic_method', 'synthetic_contract'}:
            raise TraceError('GENERIC_JEV_IS_NOT_RESEARCH_QUALITY')
    elif result['jev'] is not None:
        raise TraceError('UNEXPECTED_JEV_METADATA')


def validate_event(event):
    if not isinstance(event, dict):
        raise TraceError('EVENT_REQUIRES_OBJECT')
    kind = event.get('kind')
    enum(kind, FIELDS)
    exact(event, BASE | FIELDS[kind])
    if event['schema_version'] != SCHEMA:
        raise TraceError('UNSUPPORTED_TRACE_SCHEMA')
    for key in ('event_id', 'run_id', 'attempt_id'):
        identifier(event[key])
    if type(event['seq']) is not int or not 1 <= event['seq'] <= 2**53 - 1:
        raise TraceError('INVALID_SEQUENCE')
    timestamp(event['at'])
    if kind == 'run_start':
        if type(event['synthetic']) is not bool:
            raise TraceError('SYNTHETIC_REQUIRES_BOOLEAN')
        enum(event['integration_scope'], {'explicit_local_adapter'})
        exact(event['expected_components'], COMPONENTS)
        for spec in event['expected_components'].values():
            exact(spec, {'applicability', 'reason_code'})
            enum(spec['applicability'], {'required', 'not_applicable'})
            if spec['applicability'] == 'required':
                if spec['reason_code'] is not None:
                    raise TraceError('UNEXPECTED_NA_REASON')
            else:
                enum(spec['reason_code'], NA_REASONS)
                if spec['reason_code'] == 'FIXTURE_OUT_OF_SCOPE' and not event['synthetic']:
                    raise TraceError('SYNTHETIC_NA_IN_LIVE_RUN')
        if not isinstance(event['expected_evals'], dict) or len(event['expected_evals']) > 1000:
            raise TraceError('INVALID_EVAL_MANIFEST')
        for eval_id, spec in event['expected_evals'].items():
            identifier(eval_id)
            exact(spec, {'component', 'quality_axis', 'scope'})
            enum(spec['component'], set(COMPONENTS) | {'system'})
            enum(spec['quality_axis'], AXES)
            enum(spec['scope'], SCOPES)
        references(event['refs'], complete_keys=True)
        local_link(event['metrics_ref'])
    elif kind == 'run_resume':
        identifier(event['resumes_attempt_id'])
    elif kind == 'span_start':
        for key in ('span_id', 'parent_span_id', 'retry_of', 'metrics_attempt_id'):
            identifier(event[key], nullable=key != 'span_id')
        enum(event['component'], COMPONENTS)
        references(event['refs'])
    elif kind == 'span_end':
        identifier(event['span_id'])
        enum(event['execution_status'], EXECUTION)
        enum(event['error_code'], ERROR_CODES)
        if (event['execution_status'] == 'completed') != (event['error_code'] == 'NONE'):
            raise TraceError('STATUS_ERROR_CONTRADICTION')
    elif kind == 'eval_result':
        validate_eval(event['result'])
    elif kind == 'run_end':
        enum(event['execution_status'], EXECUTION - {'not_run'})
        enum(event['capture_status'], {'complete', 'partial'})
    return event


def read_events(path):
    path = Path(path)
    events = []
    if not path.exists():
        return events
    # A torn final write is evidence of incomplete capture. Refuse to repair it silently.
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if not line.endswith('\n') or len(line) > 1_000_000:
                raise TraceError('TRUNCATED_OR_OVERSIZE_EVENT')
            try:
                event = json.loads(line)
            except (ValueError, TypeError):
                raise TraceError('MALFORMED_EVENT_JSON') from None
            events.append(validate_event(event))
    return events


def _unique(events):
    seen = {}
    duplicates = 0
    for event in events:
        validate_event(event)
        event_id = event['event_id']
        if event_id in seen:
            if canonical(seen[event_id]) != canonical(event):
                raise TraceError('CONFLICTING_EVENT_ID')
            duplicates += 1
        else:
            seen[event_id] = event
    return list(seen.values()), duplicates


def _cycles(nodes, key):
    for start in nodes:
        seen, current = set(), start
        while current in nodes:
            if current in seen:
                return True
            seen.add(current)
            current = nodes[current].get(key)
    return False


def aggregate(events):
    unique, duplicates = _unique(events)
    grouped = {}
    for event in unique:
        grouped.setdefault(event['run_id'], []).append(event)
    return {'schema_version': REPORT_SCHEMA, 'duplicate_deliveries': duplicates,
            'integration_warning': LINK_WARNING, 'quality_warning': QUALITY_WARNING,
            'observation_status': 'observed' if grouped else 'not_run',
            'runs': [_aggregate_run(run_id, items) for run_id, items in sorted(grouped.items())]}


def _aggregate_run(run_id, items):
    items = sorted(items, key=lambda item: item['seq'])
    issues = []
    def issue(code, event=None):
        item = {'code': code, 'event_id': event['event_id'] if event else None}
        if item not in issues:
            issues.append(item)
    if [e['seq'] for e in items] != list(range(1, len(items) + 1)):
        issue('SEQUENCE_GAP_OR_COLLISION')
    if any(timestamp(a['at']) > timestamp(b['at']) for a, b in zip(items, items[1:])):
        issue('NONMONOTONIC_TIMESTAMP')
    starts = [e for e in items if e['kind'] == 'run_start']
    manifest = starts[0] if len(starts) == 1 else None
    if manifest is None:
        issue('MISSING_OR_DUPLICATE_RUN_START')
    elif items[0] != manifest:
        issue('RUN_START_NOT_FIRST', manifest)
    spans, ends, evals, run_ends = {}, {}, {}, []
    current_attempt, known_attempts, closed = None, set(), False
    previous_end = None
    for event in items:
        kind, attempt = event['kind'], event['attempt_id']
        if kind == 'run_start':
            current_attempt = attempt
            known_attempts.add(attempt)
        elif kind == 'run_resume':
            if attempt in known_attempts or event['resumes_attempt_id'] != current_attempt:
                issue('INVALID_RESUME_LINK', event)
            if previous_end and previous_end['execution_status'] == 'completed':
                issue('RESUME_AFTER_COMPLETED', event)
            current_attempt, closed, previous_end = attempt, False, None
            known_attempts.add(attempt)
        elif attempt != current_attempt:
            # Span ends can close abandoned spans after resuming only through a fresh retry;
            # rewriting an older attempt would conceal partial capture.
            issue('ATTEMPT_CORRELATION_MISMATCH', event)
        if closed and kind not in {'run_resume', 'run_start'}:
            issue('EVENT_AFTER_RUN_END', event)
        if kind == 'span_start':
            sid = event['span_id']
            if sid in spans:
                issue('DUPLICATE_SPAN_START', event)
            else:
                spans[sid] = event
            if manifest and manifest['expected_components'][event['component']]['applicability'] == 'not_applicable':
                issue('OBSERVED_COMPONENT_DECLARED_NA', event)
        elif kind == 'span_end':
            sid = event['span_id']
            if sid in ends:
                issue('DUPLICATE_SPAN_END', event)
            else:
                ends[sid] = event
        elif kind == 'eval_result':
            result = event['result']
            if result['eval_id'] in evals:
                issue('DUPLICATE_EVAL_RESULT', event)
            else:
                evals[result['eval_id']] = event
        elif kind == 'run_end':
            run_ends.append(event)
            closed, previous_end = True, event
    for sid, start in spans.items():
        end = ends.get(sid)
        parent = spans.get(start['parent_span_id'])
        if start['parent_span_id'] is not None:
            if parent is None:
                issue('ORPHAN_PARENT_SPAN', start)
            elif parent['seq'] >= start['seq'] or parent['attempt_id'] != start['attempt_id']:
                issue('INVALID_PARENT_ORDER_OR_ATTEMPT', start)
            elif parent['span_id'] in ends and (ends[parent['span_id']]['seq'] < start['seq'] or (end and ends[parent['span_id']]['seq'] < end['seq'])):
                issue('CHILD_OUTLIVES_PARENT', end)
        if end:
            if end['seq'] <= start['seq'] or end['attempt_id'] != start['attempt_id']:
                issue('INVALID_SPAN_END_ORDER_OR_ATTEMPT', end)
        retry = spans.get(start['retry_of'])
        if start['retry_of'] is not None:
            if retry is None:
                issue('ORPHAN_RETRY', start)
            elif retry['seq'] >= start['seq'] or retry['component'] != start['component']:
                issue('INVALID_RETRY_ORDER_OR_COMPONENT', start)
            elif start['retry_of'] not in ends and retry['attempt_id'] == start['attempt_id']:
                issue('RETRY_OF_OPEN_SPAN_WITHOUT_RESUME', start)
            elif start['retry_of'] in ends and ends[start['retry_of']]['execution_status'] == 'completed':
                issue('RETRY_OF_COMPLETED_SPAN', start)
            elif start['retry_of'] in ends and ends[start['retry_of']]['seq'] >= start['seq']:
                issue('RETRY_BEFORE_FAILURE', start)
    for sid, end in ends.items():
        if sid not in spans:
            issue('ORPHAN_SPAN_END', end)
    for key in ('parent_span_id', 'retry_of'):
        if _cycles(spans, key):
            issue('SPAN_GRAPH_CYCLE')
    retry_children = {}
    for sid, start in spans.items():
        if start['retry_of'] is not None:
            retry_children.setdefault(start['retry_of'], []).append(sid)
    if any(len(value) > 1 for value in retry_children.values()):
        issue('AMBIGUOUS_RETRY_BRANCH')
    terminal_spans = {sid: start for sid, start in spans.items() if sid not in retry_children}
    components = {}
    for component in COMPONENTS:
        spec = manifest['expected_components'][component] if manifest else {'applicability': 'required', 'reason_code': None}
        all_ids = [sid for sid, start in spans.items() if start['component'] == component]
        ids = [sid for sid in all_ids if sid in terminal_spans]
        states = [ends[sid]['execution_status'] if sid in ends else 'incomplete' for sid in ids]
        if spec['applicability'] == 'not_applicable' and not all_ids:
            status = 'not_applicable'
        elif not states:
            status = 'unobserved'
        else:
            status = next((s for s in ('incomplete', 'failed', 'cancelled', 'blocked', 'not_run') if s in states), 'completed')
        components[component] = {'status': status, 'applicability': spec['applicability'],
                                 'reason_code': spec['reason_code'], 'span_ids': all_ids,
                                 'recovered_attempts': len(all_ids) - len(ids)}
    required = [c for c, spec in components.items() if spec['applicability'] == 'required']
    observed = [c for c in required if components[c]['status'] != 'unobserved']
    executed = [c for c in required if components[c]['status'] == 'completed']
    eval_rows = []
    expected_evals = manifest['expected_evals'] if manifest else {}
    for eval_id in sorted(set(expected_evals) | set(evals)):
        event = evals.get(eval_id)
        expected = expected_evals.get(eval_id)
        if event is None:
            eval_rows.append({'eval_id': eval_id, **expected, 'status': 'not_run', 'observed': False,
                              'reviewer_basis': None, 'evidence_ref': None, 'refs': None, 'jev': None})
            continue
        result = event['result']
        if expected is None:
            issue('UNDECLARED_EVALUATION', event)
        elif any(result[key] != expected[key] for key in ('component', 'quality_axis', 'scope')):
            issue('EVAL_MANIFEST_SCOPE_MISMATCH', event)
        sid = result['span_id']
        if sid is not None:
            if sid not in spans:
                issue('ORPHAN_EVAL_SPAN', event)
            elif result['component'] != spans[sid]['component']:
                issue('EVAL_COMPONENT_MISMATCH', event)
            elif sid not in ends or ends[sid]['seq'] >= event['seq']:
                issue('EVAL_BEFORE_SPAN_END', event)
        if manifest:
            if manifest['synthetic'] and result['quality_axis'] == 'research':
                issue('SYNTHETIC_RUN_CANNOT_ESTABLISH_RESEARCH_QUALITY', event)
            effective_refs = dict(manifest['refs'])
            if sid in spans:
                effective_refs.update(spans[sid]['refs'])
            for key in REF_KEYS:
                if result['refs'][key] != effective_refs[key]:
                    issue('EVAL_PROVENANCE_MISMATCH', event)
        eval_rows.append({**result, 'observed': True})
    last_end = run_ends[-1] if run_ends and run_ends[-1]['attempt_id'] == current_attempt else None
    claimed = last_end['execution_status'] if last_end else 'incomplete'
    component_complete = len(executed) == len(required)
    all_evals_observed = all(row['observed'] for row in eval_rows)
    provenance_complete = bool(manifest) and all(v is not None for v in manifest['refs'].values()) and all(v is not None for start in spans.values() for v in start['refs'].values())
    missing_span_ends = set(spans) - set(ends)
    # Every terminal claim is checked against its own prefix. Later resume/evidence
    # cannot retroactively repair a false earlier completion/capture claim.
    for end in run_ends:
        before = [e for e in items if e['seq'] < end['seq']]
        prior_spans = {e['span_id']: e for e in before if e['kind'] == 'span_start'}
        prior_ends = {e['span_id']: e for e in before if e['kind'] == 'span_end'}
        prior_retries = {e['retry_of'] for e in before if e['kind'] == 'span_start' and e['retry_of']}
        prior_terminals = {sid: start for sid, start in prior_spans.items() if sid not in prior_retries}
        prior_evals = {e['result']['eval_id'] for e in before if e['kind'] == 'eval_result'}
        completed_components = set()
        observed_components = {start['component'] for start in prior_spans.values()}
        for component in required:
            ids = [sid for sid, start in prior_terminals.items() if start['component'] == component]
            if ids and all(sid in prior_ends and prior_ends[sid]['execution_status'] == 'completed' for sid in ids):
                completed_components.add(component)
        if end['execution_status'] == 'completed' and set(required) - completed_components:
            issue('CONTRADICTORY_EXECUTION_COMPLETE', end)
        if end['capture_status'] == 'complete':
            prefix_provenance = bool(manifest) and all(v is not None for v in manifest['refs'].values()) and all(v is not None for start in prior_spans.values() for v in start['refs'].values())
            if set(required) - observed_components or set(prior_spans) - set(prior_ends) or set(expected_evals) - prior_evals or not prefix_provenance:
                issue('CONTRADICTORY_CAPTURE_COMPLETE', end)
    if issues:
        health = 'invalid'
    elif not last_end or last_end['capture_status'] != 'complete' or missing_span_ends or not provenance_complete or not all_evals_observed or any(c['status'] in {'unobserved', 'incomplete'} for c in components.values()):
        health = 'partial'
    else:
        health = 'healthy'
    if issues and claimed == 'completed':
        execution = 'incomplete'
    else:
        execution = claimed
    quality = {}
    for axis in sorted(AXES):
        rows = [row for row in eval_rows if row['quality_axis'] == axis]
        # Generic method advice is tracked, but never certifies the implementation/system.
        decisive = [row for row in rows if row['scope'] != 'generic_method']
        if axis == 'research' and manifest and manifest['synthetic']:
            decisive = []
        if not decisive:
            state = 'not_evaluated'
        elif any(row['status'] == 'fail' for row in decisive):
            state = 'failed'
        elif any(row['status'] in {'blocked', 'not_run', 'incomplete'} for row in decisive):
            state = 'incomplete'
        elif issues:
            state = 'unverified'
        else:
            state = 'passed_declared_checks'
        quality[axis] = {'status': state, 'declared': len(decisive),
                         'observed': sum(row['observed'] for row in decisive),
                         'scope': sorted(set(row['scope'] for row in decisive))}
    return {'run_id': run_id, 'synthetic': manifest['synthetic'] if manifest else None,
            'telemetry_health': health, 'execution_outcome': execution, 'claimed_execution': claimed,
            'quality': quality, 'coverage': {'required': len(required), 'observed': len(observed),
                                          'completed': len(executed), 'fraction': len(observed) / len(required) if required else None},
            'provenance_status': 'complete' if provenance_complete else 'incomplete',
            'refs': manifest['refs'] if manifest else None, 'components': components,
            'evaluations': eval_rows, 'issues': issues, 'attempt_ids': sorted(known_attempts),
            'metrics_ref': manifest['metrics_ref'] if manifest else None,
            'metrics_correlation': {'status': 'not_checked'},
            'spans': [{'start': start, 'end': ends.get(sid)} for sid, start in spans.items()],
            'missing_span_end_ids': sorted(missing_span_ends), 'event_count': len(items)}


class Ledger:
    """Durable append-only ledger, one owner instance per file.

    Thread-safe within this instance. Do not share a file between writer processes.
    Use separate run files, aggregate afterwards. No silent torn-write recovery.
    """
    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink():
            raise TraceError('SYMLINK_LEDGER_NOT_ALLOWED')
        self.lock = threading.RLock()
        self.events, _ = _unique(read_events(self.path))

    def emit(self, event):
        validate_event(event)
        with self.lock:
            for previous in self.events:
                if previous['event_id'] == event['event_id']:
                    if canonical(previous) != canonical(event):
                        raise TraceError('CONFLICTING_EVENT_ID')
                    return False
            self.path.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0)
            fd = os.open(self.path, flags, 0o600)
            try:
                data = (canonical(event) + '\n').encode('utf-8')
                with os.fdopen(fd, 'ab', closefd=False) as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                os.close(fd)
            self.events.append(json.loads(canonical(event)))
            return True

    def next_sequence(self, run_id):
        return max((e['seq'] for e in self.events if e['run_id'] == run_id), default=0) + 1


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def classify_exception(exc):
    # Never stringify exceptions: messages commonly contain prompts, paths, and secrets.
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return 'CANCELLED'
    if isinstance(exc, TimeoutError):
        return 'TIMEOUT'
    if isinstance(exc, OSError):
        return 'IO_FAILURE'
    if isinstance(exc, AssertionError):
        return 'ASSERTION_FAILED'
    if isinstance(exc, ValueError):
        return 'INVALID_INPUT'
    return 'UNCLASSIFIED_EXCEPTION'


def component_manifest():
    return {name: {'applicability': 'required', 'reason_code': None} for name in COMPONENTS}


class RunRecorder:
    """Explicit runtime hooks. This is not automatically installed in any LLM host."""
    def __init__(self, ledger, run_id, attempt_id='attempt-1'):
        identifier(run_id)
        identifier(attempt_id)
        self.ledger, self.run_id, self.attempt_id = ledger, run_id, attempt_id

    def event(self, kind, *, at=None, event_id=None, **fields):
        with self.ledger.lock:
            event = {'schema_version': SCHEMA, 'event_id': event_id or str(uuid.uuid4()),
                     'run_id': self.run_id, 'attempt_id': self.attempt_id,
                     'seq': self.ledger.next_sequence(self.run_id), 'at': at or now(),
                     'kind': kind, **fields}
            self.ledger.emit(event)
            return event

    def start(self, refs, *, synthetic=False, expected_components=None, expected_evals=None, metrics_ref=None):
        if any(e['run_id'] == self.run_id for e in self.ledger.events):
            raise TraceError('RUN_ALREADY_EXISTS_USE_RESUME')
        return self.event('run_start', synthetic=synthetic,
                          expected_components=component_manifest() if expected_components is None else expected_components,
                          expected_evals=expected_evals or {}, refs=refs, metrics_ref=metrics_ref,
                          integration_scope='explicit_local_adapter')

    def resume(self, new_attempt_id):
        identifier(new_attempt_id)
        previous = self.attempt_id
        self.attempt_id = new_attempt_id
        try:
            event = self.event('run_resume', resumes_attempt_id=previous)
        except BaseException:
            self.attempt_id = previous
            raise
        return event

    @contextmanager
    def span(self, component, *, span_id=None, parent_span_id=None, retry_of=None,
             metrics_attempt_id=None, refs=None):
        sid = span_id or str(uuid.uuid4())
        self.event('span_start', span_id=sid, parent_span_id=parent_span_id, component=component,
                   retry_of=retry_of, metrics_attempt_id=metrics_attempt_id, refs=refs or {})
        result = {'execution_status': 'completed', 'error_code': 'NONE'}
        try:
            yield result
        except BaseException as exc:
            code = classify_exception(exc)
            self.event('span_end', span_id=sid, execution_status='cancelled' if code == 'CANCELLED' else 'failed', error_code=code)
            raise
        else:
            self.event('span_end', span_id=sid, **result)

    def evaluation(self, result):
        return self.event('eval_result', result=result)

    def finish(self, execution_status='completed', capture_status='partial'):
        # Validate before publishing a terminal claim. Raw imported events are still
        # checked independently by aggregate(). Incomplete runs may be failed/blocked.
        with self.ledger.lock:
            candidate = {'schema_version': SCHEMA, 'event_id': str(uuid.uuid4()), 'run_id': self.run_id,
                         'attempt_id': self.attempt_id, 'seq': self.ledger.next_sequence(self.run_id),
                         'at': now(), 'kind': 'run_end', 'execution_status': execution_status,
                         'capture_status': capture_status}
            report = aggregate(self.ledger.events + [candidate])
            row = next(row for row in report['runs'] if row['run_id'] == self.run_id)
            if row['telemetry_health'] == 'invalid':
                raise TraceError('TERMINAL_CLAIM_CONTRADICTS_EVIDENCE')
            self.ledger.emit(candidate)
            return candidate


def render_dashboard(report):
    esc = lambda value: html.escape(str(value), quote=True)
    out = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
           '<title>Vera local observability</title><style>body{font:15px system-ui;background:#0e1726;color:#e6edf5;max-width:1200px;margin:auto;padding:24px}h1,h2{letter-spacing:-.03em}a{color:#94d8ff}.warning{padding:16px;border:1px solid #a87d3a;background:#30281f;border-radius:10px}section,details{margin:16px 0;padding:16px;background:#172438;border-radius:10px}summary{cursor:pointer;font-weight:600}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #35465f}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#c9d8e8}.scroll{overflow-x:auto}.bad{color:#ffaeae}.muted{color:#b8c5d6}.cards{display:flex;flex-wrap:wrap;gap:10px}.card{flex:1;padding:14px;background:#203149;border-radius:8px;min-width:130px}</style>',
           '<h1>Vera · local observability</h1>',
           '<p class="warning">' + esc(report.get('integration_warning', LINK_WARNING)) + '<br>' + esc(report.get('quality_warning', QUALITY_WARNING)) + '</p>',
           '<p class="muted">Payload-free append-only traces. Expand a component or evaluation to inspect its evidence. No network requests or scripts.</p>']
    for row in report.get('runs', []):
        out.append('<section><h2>' + esc(row['run_id']) + (' · SYNTHETIC' if row.get('synthetic') else '') + '</h2>')
        out.append('<div class="cards">' + ''.join('<div class="card">' + esc(label) + '<br><strong>' + esc(value) + '</strong></div>' for label, value in (
            ('Telemetry', row['telemetry_health']), ('Execution', row['execution_outcome']),
            ('Engineering checks', row['quality']['engineering']['status']), ('Research quality', row['quality']['research']['status']),
            ('Observed components', str(row['coverage']['observed']) + '/' + str(row['coverage']['required'])))) + '</div>')
        try:
            link = local_link(row.get('metrics_ref'))
        except TraceError:
            link = None
        if link:
            out.append('<p><a href="' + esc(link) + '">Open linked run metrics</a> · correlation: ' + esc(row.get('metrics_correlation', {}).get('status', 'not_checked')) + '<br>Attempt coverage: ' + esc(row.get('metrics_correlation', {}).get('coverage_status', 'not_checked')) + '; report content: ' + esc(row.get('metrics_correlation', {}).get('report_content_verification', 'not_checked')) + '</p>')
        out.append('<p>Provenance: ' + esc(row['provenance_status']) + '. Attempts: ' + esc(', '.join(row['attempt_ids'])) + '</p>')
        for component, status in row['components'].items():
            out.append('<details><summary>' + esc(component) + ' · ' + esc(status['status']) + '</summary>')
            out.append('<pre>' + esc(json.dumps(status, indent=2)) + '</pre>')
            for span in row['spans']:
                if span['start']['component'] == component:
                    out.append('<pre>' + esc(json.dumps(span, indent=2)) + '</pre>')
            out.append('</details>')
        out.append('<details><summary>Evaluation evidence (' + esc(len(row['evaluations'])) + ')</summary>')
        for result in row['evaluations']:
            out.append('<details><summary>' + esc(result['eval_id']) + ' · ' + esc(result['status']) + ' · ' + esc(result['scope']) + '</summary><pre>' + esc(json.dumps(result, indent=2)) + '</pre></details>')
        out.append('</details><details><summary>Diagnostics and provenance</summary><pre>' + esc(json.dumps({'issues': row['issues'], 'refs': row['refs']}, indent=2)) + '</pre></details></section>')
    out.append('</html>\n')
    return ''.join(out)


def correlate_metrics(report, metrics_events, metrics_report, output_dir, expected_dashboard=None):
    """Validate shared run/attempt IDs and the local metrics report destination.

    Call only after the metrics package has validated/aggregated its own events.
    No metrics totals are copied or recomputed here.
    """
    metric_rows = {row['run_id']: row for row in metrics_report['runs']}
    metric_starts = {e['run_id']: e for e in metrics_events if e['type'] == 'run_start'}
    attempts = {(e['run_id'], e['attempt_id']) for e in metrics_events if e['type'] == 'attempt_start'}
    for row in report['runs']:
        declared = [span['start']['metrics_attempt_id'] for span in row['spans'] if span['start']['metrics_attempt_id'] is not None]
        refs = set(declared)
        run_attempts = {aid for rid, aid in attempts if rid == row['run_id']}
        matched = len(refs & run_attempts)
        unreferenced = sorted(run_attempts - refs)
        missing = sorted(refs - run_attempts)
        duplicate_refs = sorted(aid for aid in refs if declared.count(aid) > 1)
        same_run = row['run_id'] in metric_rows and row['run_id'] in metric_starts
        same_synthetic = same_run and metric_starts[row['run_id']]['synthetic'] == row['synthetic']
        link = local_link(row['metrics_ref'])
        target = (Path(output_dir) / link).resolve() if link else None
        link_exists = target is not None and target.is_relative_to(Path(output_dir).resolve()) and target.is_file()
        report_content_matches = bool(link_exists and expected_dashboard is not None and target.read_bytes() == expected_dashboard)
        valid_link = link_exists and (expected_dashboard is None or report_content_matches)
        status = 'matched' if same_run and same_synthetic and not missing and not duplicate_refs and valid_link else 'mismatch'
        if status == 'matched' and unreferenced:
            status = 'matched_declared_refs'
        row['metrics_correlation'] = {'status': status, 'referenced_attempts': len(refs),
                                      'matched_attempts': matched, 'total_metrics_attempts': len(run_attempts),
                                      'unreferenced_attempt_ids': unreferenced, 'missing_attempt_ids': missing,
                                      'duplicate_attribution_ids': duplicate_refs,
                                      'coverage_status': 'complete' if not unreferenced and not missing and not duplicate_refs else 'partial',
                                      'local_report_exists': link_exists,
                                      'report_content_verification': 'verified_generated_bytes' if report_content_matches else 'existence_only' if link_exists and expected_dashboard is None else 'unverified'}
        if status == 'matched_declared_refs' and row['telemetry_health'] == 'healthy':
            row['telemetry_health'] = 'partial'
        if status == 'mismatch':
            row['issues'].append({'code': 'METRICS_CORRELATION_MISMATCH', 'event_id': None})
            row['telemetry_health'] = 'invalid'
            if row['execution_outcome'] == 'completed':
                row['execution_outcome'] = 'incomplete'
    return report


def write_report(report, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'observability.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (output / 'dashboard.html').write_text(render_dashboard(report))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = aggregate(read_events(args.ledger))
        write_report(report, args.output_dir)
    except (TraceError, OSError):
        print('Observability input/output invalid; no successful report claimed.')
        return 2
    return 1 if not report['runs'] or any(row['telemetry_health'] == 'invalid' for row in report['runs']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
