#!/usr/bin/env python3
"""Vera's payload-free, stdlib-only, explicitly scoped run telemetry.

No network, provider SDK, global agent interception, or scientific-output changes.
See README.md for coverage, exclusive-attribution and adapter requirements.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import html
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import threading
import uuid

SCHEMA = 'vera.run-metrics/1'
MODES = {'SCREEN', 'STANDARD', 'DEEP'}
STATES = {'completed', 'cancelled', 'failed', 'blocked'}
CAPTURE = {'complete', 'partial', 'unavailable'}
BASE = {'schema_version', 'event_id', 'run_id', 'at', 'type'}
FIELDS = {
    'run_start': {'company_id', 'analysis_mode', 'cache_state', 'synthetic', 'collection_source'},
    'run_resume': set(),
    'run_end': {'status', 'capture_status', 'data_cutoff', 'final_response_included'},
    'worker_start': {'worker_id', 'parent_worker_id'},
    'attempt_start': {'attempt_id', 'worker_id', 'kind', 'name', 'parent_attempt_id', 'provider', 'model', 'model_version', 'provider_request_id', 'dispatch_role', 'usage_scope'},
    'attempt_end': {'attempt_id', 'status', 'token_usage', 'cost', 'prices'},
    'memory_sample': {'worker_id', 'process_id', 'scope', 'peak_rss_bytes', 'context_tokens', 'storage_bytes', 'method', 'platform', 'measurement_start', 'measurement_end'},
}
TOKEN_FIELDS = ('uncached_input_tokens', 'cached_input_tokens', 'output_tokens')
TOKEN_METRICS = (*TOKEN_FIELDS, 'total_input_tokens', 'total_tokens')
RATE_FIELDS = ('uncached_input_per_million', 'cached_input_per_million', 'output_per_million')
_ID = re.compile(r'[A-Za-z0-9_.:/@+ -]{1,160}\Z')


class MetricsError(ValueError):
    """Rejected malformed or contradictory telemetry; never silently repaired."""


def label(value, field, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise MetricsError(f'{field}: expected a short payload-free identifier')


def enum(value, choices, field):
    if not isinstance(value, str) or value not in choices:
        raise MetricsError(f'{field}: unsupported value')


def count(value, field):
    if value is not None and (type(value) is not int or not 0 <= value <= 9223372036854775807):
        raise MetricsError(f'{field}: expected null or nonnegative integer')


def decimal(value, field):
    # Decimal strings preserve invoice precision. Floats and booleans are rejected.
    if not isinstance(value, str):
        raise MetricsError(f'{field}: expected decimal string')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise MetricsError(f'{field}: invalid decimal') from exc
    if not result.is_finite() or result < 0 or result.adjusted() > 30 or result.as_tuple().exponent < -30:
        raise MetricsError(f'{field}: expected bounded finite nonnegative decimal')
    return result


def timestamp(value):
    if not isinstance(value, str):
        raise MetricsError('at: timestamp required')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise MetricsError('at: invalid ISO timestamp') from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise MetricsError('at: timezone is required')
    return result.astimezone(timezone.utc)


def obj(value, allowed, field):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise MetricsError(f'{field}: invalid object or unsupported fields')


def tokens(usage):
    if usage is None:
        return dict.fromkeys(TOKEN_METRICS)
    obj(usage, {'input_tokens', 'cached_input_tokens', 'output_tokens', 'input_includes_cached', 'source'}, 'token_usage')
    for key in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
        count(usage.get(key), key)
    if type(usage.get('input_includes_cached')) is not bool:
        raise MetricsError('token_usage: explicit input_includes_cached required')
    label(usage.get('source'), 'token_usage.source')
    inp, cached = usage.get('input_tokens'), usage.get('cached_input_tokens')
    if usage['input_includes_cached'] and inp is not None and cached is not None and cached > inp:
        raise MetricsError('cached input exceeds inclusive input')
    uncached = inp
    if usage['input_includes_cached']:
        uncached = inp - cached if inp is not None and cached is not None else None
    total_input = inp if usage['input_includes_cached'] else (inp + cached if inp is not None and cached is not None else None)
    output = usage.get('output_tokens')
    return {'uncached_input_tokens': uncached, 'cached_input_tokens': cached, 'output_tokens': output, 'total_input_tokens': total_input, 'total_tokens': total_input + output if total_input is not None and output is not None else None}


def validate_event(event):
    obj(event, BASE | set.union(*FIELDS.values()), 'event')
    if event.get('schema_version') != SCHEMA:
        raise MetricsError('unsupported schema_version')
    kind = event.get('type')
    enum(kind, FIELDS, 'type')
    if set(event) - BASE - FIELDS[kind]:
        raise MetricsError(f'{kind}: unsupported fields')
    for key in ('event_id', 'run_id'):
        label(event.get(key), key)
    timestamp(event.get('at'))
    if kind == 'run_start':
        label(event.get('company_id'), 'company_id')
        enum(event.get('analysis_mode'), MODES, 'analysis_mode')
        enum(event.get('cache_state'), {'cold', 'warm', 'mixed', 'unknown'}, 'cache_state')
        enum(event.get('collection_source'), {'adapter', 'manual', 'command_boundary', 'fixture'}, 'collection_source')
        if type(event.get('synthetic')) is not bool:
            raise MetricsError('synthetic: explicit boolean required')
    elif kind == 'run_end':
        enum(event.get('status'), STATES, 'status')
        enum(event.get('capture_status'), CAPTURE, 'capture_status')
        if timestamp(event.get('data_cutoff')) > timestamp(event['at']):
            raise MetricsError('data_cutoff cannot follow run_end')
        if type(event.get('final_response_included')) is not bool:
            raise MetricsError('final_response_included: boolean required')
    elif kind == 'worker_start':
        label(event.get('worker_id'), 'worker_id')
        label(event.get('parent_worker_id'), 'parent_worker_id', True)
    elif kind == 'attempt_start':
        for key in ('attempt_id', 'worker_id', 'name'):
            label(event.get(key), key)
        for key in ('parent_attempt_id', 'provider', 'model', 'model_version', 'provider_request_id'):
            label(event.get(key), key, True)
        enum(event.get('kind'), {'model', 'tool', 'jev'}, 'kind')
        enum(event.get('dispatch_role', 'leaf'), {'leaf', 'wrapper'}, 'dispatch_role')
        if event.get('usage_scope') != 'exclusive':
            raise MetricsError('only exclusive attempt usage/cost is supported; no rollups')
    elif kind == 'attempt_end':
        label(event.get('attempt_id'), 'attempt_id')
        enum(event.get('status'), STATES, 'status')
        tokens(event.get('token_usage'))
        cost, prices = event.get('cost'), event.get('prices')
        if cost is not None and prices is not None:
            raise MetricsError('cost and prices are mutually exclusive billing bases')
        if cost is not None:
            obj(cost, {'currency', 'amount', 'complete', 'basis', 'price_version'}, 'cost')
            validate_currency(cost.get('currency'))
            decimal(cost.get('amount'), 'cost.amount')
            if type(cost.get('complete')) is not bool:
                raise MetricsError('cost.complete: boolean required')
            enum(cost.get('basis'), {'invoice', 'provider_reported', 'estimate', 'explicit_no_charge'}, 'cost.basis')
            label(cost.get('price_version'), 'cost.price_version', True)
            if cost['basis'] == 'explicit_no_charge' and decimal(cost['amount'], 'amount') != 0:
                raise MetricsError('explicit_no_charge requires zero')
        if prices is not None:
            obj(prices, {'currency', 'price_version', 'source', *RATE_FIELDS}, 'prices')
            validate_currency(prices.get('currency'))
            label(prices.get('price_version'), 'prices.price_version')
            label(prices.get('source'), 'prices.source')
            for key in RATE_FIELDS:
                if prices.get(key) is not None:
                    decimal(prices[key], key)
    elif kind == 'memory_sample':
        for key in ('worker_id', 'process_id'):
            label(event.get(key), key)
        enum(event.get('scope'), {'process_lifetime', 'run_isolated_process'}, 'scope')
        enum(event.get('method'), {'getrusage_ru_maxrss', 'provider_reported', 'os_sample', 'fixture'}, 'method')
        label(event.get('platform'), 'platform')
        if event.get('measurement_start') is not None and timestamp(event['measurement_start']) > timestamp(event['at']):
            raise MetricsError('measurement interval starts after observation')
        if timestamp(event.get('measurement_end')) != timestamp(event['at']):
            raise MetricsError('measurement_end must match observation timestamp')
        for key in ('peak_rss_bytes', 'context_tokens', 'storage_bytes'):
            count(event.get(key), key)
    return event


def validate_currency(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Z]{3}', value):
        raise MetricsError('currency: explicit three-letter code required')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def read_events(paths):
    output = []
    for path in paths:
        with Path(path).open(encoding='utf-8') as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(MetricsError(f'invalid number {x}')))
                    output.append(validate_event(event))
                except (ValueError, TypeError) as exc:
                    raise MetricsError(f'{path}:{line_number}: {exc}') from exc
    return output


def exclusive_cost(end, kind=None):
    if end is None:
        return {'currency': None, 'known_subtotal': None, 'complete': False, 'basis': 'unavailable', 'known_components': 0, 'expected_components': 1, 'price_version': None}
    cost, prices = end.get('cost'), end.get('prices')
    if cost is not None:
        return {'currency': cost['currency'], 'known_subtotal': str(decimal(cost['amount'], 'amount')), 'complete': cost['complete'], 'basis': cost['basis'], 'known_components': 1, 'expected_components': 1 if cost['complete'] else None, 'price_version': cost.get('price_version')}
    if prices is None:
        return exclusive_cost(None)
    usage = tokens(end.get('token_usage'))
    amounts = []
    for key, rate in zip(TOKEN_FIELDS, RATE_FIELDS):
        # An observed zero category costs zero even if its rate is unknown.
        if usage[key] == 0:
            amounts.append(Decimal(0))
        elif usage[key] is not None and prices.get(rate) is not None:
            amounts.append(Decimal(usage[key]) * decimal(prices[rate], rate) / Decimal(1000000))
    return {'currency': prices['currency'], 'known_subtotal': str(sum(amounts, Decimal(0))) if amounts else None, 'complete': len(amounts) == 3 and kind != 'jev', 'basis': 'estimate', 'known_components': len(amounts), 'expected_components': 4 if kind == 'jev' else 3, 'price_version': prices['price_version']}


def coverage(values, expected, capture_complete):
    known = [v for v in values if v is not None]
    # Empty known values are unknown, except a certified empty population.
    subtotal = sum(known) if known else (0 if expected == 0 and capture_complete else None)
    return {'known_subtotal': subtotal, 'known_count': len(known), 'expected_count': expected,
            'complete': capture_complete and len(known) == expected,
            'status': 'complete' if capture_complete and len(known) == expected else ('partial' if known else 'unavailable')}


def aggregate(events):
    """Merge unordered shards; IDs are idempotency keys. Conflicts fail closed."""
    unique, duplicates = {}, 0
    for item in events:
        validate_event(item)
        old = unique.get(item['event_id'])
        if old is not None:
            if canonical(old) != canonical(item):
                raise MetricsError('conflicting event_id')
            duplicates += 1
        unique[item['event_id']] = item
    by_run = {}
    provider_requests = {}
    for item in unique.values():
        if item['type'] == 'attempt_start' and item.get('provider_request_id') is not None:
            key = (item.get('provider'), item['provider_request_id'])
            owner = (item['run_id'], item['attempt_id'])
            if key in provider_requests and provider_requests[key] != owner:
                raise MetricsError('provider request has multiple run/attempt owners; keep shared work unallocated')
            provider_requests[key] = owner
        by_run.setdefault(item['run_id'], []).append(item)
    rows = [_run(run_id, items) for run_id, items in sorted(by_run.items())]
    return {'schema_version': SCHEMA, 'runs': rows, 'groups': group_runs(rows), 'duplicate_event_count': duplicates,
            'warning': 'Observed ledger only. No global runtime interception, inferred usage, or scientific approval.'}


def _identity_payload(event):
    return {k: v for k, v in event.items() if k != 'event_id'}


def _one(mapping, key, event):
    if key in mapping and _identity_payload(mapping[key]) != _identity_payload(event):
        raise MetricsError(f'conflicting identity: {key}')
    mapping[key] = event


def _run(run_id, items):
    starts = [e for e in items if e['type'] == 'run_start']
    if len(starts) != 1:
        raise MetricsError('each run needs exactly one run_start')
    start = starts[0]
    first = timestamp(start['at'])
    # Lifecycle order is by absolute time, independent of shard ordering.
    lifecycle = sorted([e for e in items if e['type'] in {'run_start', 'run_end', 'run_resume'}], key=lambda e: timestamp(e['at']))
    if len({timestamp(e['at']) for e in lifecycle}) != len(lifecycle):
        raise MetricsError('ambiguous equal lifecycle timestamps')
    open_run, last_end, resume_count = False, None, 0
    intervals, interval_start = [], None
    for e in lifecycle:
        if e['type'] in {'run_start', 'run_resume'}:
            if open_run or (e['type'] == 'run_resume' and last_end is None):
                raise MetricsError('invalid start/resume transition')
            open_run, interval_start = True, timestamp(e['at'])
            resume_count += e['type'] == 'run_resume'
        else:
            if not open_run:
                raise MetricsError('end without an open run')
            open_run, last_end = False, e
            intervals.append((interval_start, timestamp(e['at'])))
    if open_run:
        intervals.append((interval_start, None))
    workers, attempts, ends, memories = {}, {}, {}, []
    for e in items:
        if timestamp(e['at']) < first:
            raise MetricsError('event predates run')
        if e['type'] not in {'run_start', 'run_end', 'run_resume'}:
            if not any(lo <= timestamp(e['at']) and (hi is None or timestamp(e['at']) <= hi) for lo, hi in intervals):
                raise MetricsError('event outside active run interval')
        if e['type'] == 'worker_start':
            _one(workers, e['worker_id'], e)
        elif e['type'] == 'attempt_start':
            _one(attempts, e['attempt_id'], e)
        elif e['type'] == 'attempt_end':
            _one(ends, e['attempt_id'], e)
        elif e['type'] == 'memory_sample':
            memories.append(e)
    for worker_id, e in workers.items():
        seen, p = {worker_id}, e.get('parent_worker_id')
        while p is not None:
            if p not in workers or p in seen:
                raise MetricsError('missing worker parent or worker cycle')
            if timestamp(workers[p]['at']) > timestamp(e['at']):
                raise MetricsError('worker predates parent')
            seen.add(p)
            p = workers[p].get('parent_worker_id')
    if set(ends) - set(attempts):
        raise MetricsError('attempt_end without attempt_start')
    requests = {}
    for attempt_id, e in attempts.items():
        if e.get('provider_request_id') is not None:
            if not e.get('provider'):
                raise MetricsError('provider_request_id needs provider')
            request_key = (e['provider'], e['provider_request_id'])
            if request_key in requests and requests[request_key] != attempt_id:
                raise MetricsError('provider request reused under another attempt_id; deduplicate at source')
            requests[request_key] = attempt_id
        if e['worker_id'] not in workers or timestamp(workers[e['worker_id']]['at']) > timestamp(e['at']):
            raise MetricsError('attempt needs an existing worker')
        end = ends.get(attempt_id)
        if end and timestamp(end['at']) < timestamp(e['at']):
            raise MetricsError('negative attempt duration')
        if e['kind'] == 'tool' and end and (end.get('token_usage') is not None or end.get('prices') is not None):
            raise MetricsError('tool wrapper cannot duplicate model token usage; record model child')
        seen, p = {attempt_id}, e.get('parent_attempt_id')
        while p is not None:
            if p not in attempts or p in seen:
                raise MetricsError('missing attempt parent or cycle')
            parent = attempts[p]
            if timestamp(parent['at']) > timestamp(e['at']):
                raise MetricsError('attempt predates parent')
            seen.add(p)
            p = parent.get('parent_attempt_id')
    final = None if open_run else last_end
    complete_capture = final is not None and final['capture_status'] == 'complete' and final['final_response_included']
    if final and timestamp(final['data_cutoff']) < first:
        raise MetricsError('data_cutoff predates run')
    if final and any(timestamp(e['at']) > timestamp(final['data_cutoff']) for e in items if e['type'] not in {'run_end'}):
        raise MetricsError('event follows declared data cutoff')
    if complete_capture and set(attempts) != set(ends):
        raise MetricsError('complete capture cannot leave open attempts')
    token_attempts = [e for e in attempts.values() if e['kind'] in {'model', 'jev'}]
    token_metrics = {key: coverage([tokens(ends.get(e['attempt_id'], {}).get('token_usage'))[key] for e in token_attempts], len(token_attempts), complete_capture) for key in TOKEN_METRICS}
    costs = [exclusive_cost(ends.get(e['attempt_id']), e['kind']) for e in attempts.values()]
    currencies = sorted({c['currency'] for c in costs if c['currency'] is not None})
    cost_rows = []
    for currency in currencies:
        same = [c for c in costs if c['currency'] == currency]
        values = [Decimal(c['known_subtotal']) for c in same if c['known_subtotal'] is not None]
        all_complete = complete_capture and len(same) == len(costs) and all(c['complete'] for c in same)
        cost_rows.append({'currency': currency, 'known_subtotal': str(sum(values, Decimal(0))) if values else None,
                          'complete_total': str(sum(values, Decimal(0))) if all_complete else None,
                          'complete': all_complete, 'known_attempts': len(values), 'expected_attempts': len(costs),
                          'basis': sorted({c['basis'] for c in same}), 'price_versions': sorted({c['price_version'] for c in same if c['price_version']})})
    memory_rows = {}
    for e in memories:
        if e['worker_id'] not in workers or timestamp(workers[e['worker_id']]['at']) > timestamp(e['at']):
            raise MetricsError('memory needs an existing worker')
        key = (e['process_id'], e['scope'], e['method'], e['platform'])
        row = memory_rows.setdefault(key, {'process_id': e['process_id'], 'scope': e['scope'], 'method': e['method'], 'platform': e['platform'], 'measurement_start': e.get('measurement_start'), 'measurement_end': e['measurement_end'], 'worker_ids': [], 'peak_rss_bytes': None, 'context_tokens_max': None, 'storage_bytes_max': None})
        if timestamp(e['measurement_end']) > timestamp(row['measurement_end']):
            row['measurement_end'] = e['measurement_end']
        if e.get('measurement_start') is not None and (row['measurement_start'] is None or timestamp(e['measurement_start']) < timestamp(row['measurement_start'])):
            row['measurement_start'] = e['measurement_start']
        if e['worker_id'] not in row['worker_ids']:
            row['worker_ids'].append(e['worker_id'])
        for source, dest in [('peak_rss_bytes', 'peak_rss_bytes'), ('context_tokens', 'context_tokens_max'), ('storage_bytes', 'storage_bytes_max')]:
            if e.get(source) is not None:
                row[dest] = max(row[dest] or 0, e[source])
    for row in memory_rows.values():
        row['worker_ids'].sort()
    memory_list = [memory_rows[k] for k in sorted(memory_rows)]
    run_peak_values = [m['peak_rss_bytes'] for m in memory_list if m['scope'] == 'run_isolated_process' and m['peak_rss_bytes'] is not None]
    # Max process peak is NOT simultaneous aggregate memory or a sum of peaks.
    leaf_tools = [a for a in attempts.values() if a['kind'] in {'tool', 'jev'} and a.get('dispatch_role', 'leaf') == 'leaf']
    distinct_tools = sorted({a['name'] for a in leaf_tools})
    durations = [(timestamp(ends[k]['at']) - timestamp(a['at'])).total_seconds() for k, a in attempts.items() if k in ends]
    return {'run_id': run_id, 'company_id': start['company_id'], 'analysis_mode': start['analysis_mode'], 'cache_state': start['cache_state'], 'synthetic': start['synthetic'],
            'started_at': start['at'], 'ended_at': final['at'] if final else None,
            'status': final['status'] if final else 'running', 'collection_source': start['collection_source'], 'data_cutoff': final['data_cutoff'] if final else None, 'final_response_included': final['final_response_included'] if final else False, 'capture_status': final['capture_status'] if final else 'partial',
            'resumes': resume_count, 'worker_count': len(workers), 'attempt_count': len(attempts),
            'tool_attempt_count': sum(a['kind'] in {'tool', 'jev'} and a.get('dispatch_role', 'leaf') == 'leaf' for a in attempts.values()),
            'wrapper_attempt_count': sum(a.get('dispatch_role', 'leaf') == 'wrapper' for a in attempts.values()),
            'model_attempt_count': len(token_attempts), 'open_attempt_count': len(attempts) - len(ends),
            'attempt_status_counts': {s: sum(e['status'] == s for e in ends.values()) for s in sorted(STATES)},
            'wall_seconds': (timestamp(final['data_cutoff']) - first).total_seconds() if final else None,
            'closure_wall_seconds': (timestamp(final['at']) - first).total_seconds() if final else None,
            'tool_calls': {'observed_attempts': len(leaf_tools), 'known_subtotal': len(leaf_tools) if leaf_tools or complete_capture else None, 'complete': complete_capture, 'status': 'complete' if complete_capture else ('partial' if leaf_tools else 'unavailable'), 'distinct_tools': distinct_tools, 'distinct_tool_count': len(distinct_tools) if leaf_tools or complete_capture else None},
            'summed_attempt_seconds': sum(durations) if durations else (0 if complete_capture and not attempts else None),
            'tokens': token_metrics, 'costs': cost_rows, 'cost_unknown_attempts': sum(c['known_subtotal'] is None for c in costs),
            'cost_complete': bool(costs) and complete_capture and all(c['complete'] for c in costs) and len(currencies) == 1,
            'memory': {'processes': memory_list, 'max_observed_isolated_process_peak_rss_bytes': max(run_peak_values) if run_peak_values else None,
                       'simultaneous_total_peak_rss_bytes': None, 'workers_with_rss': len({w for m in memory_list if m['peak_rss_bytes'] is not None for w in m['worker_ids']}), 'expected_workers': len(workers),
                       'note': 'Process-lifetime peaks may predate run. Never sum process peaks; context tokens and storage are separate.'},
            'attempts': [{'attempt_id': k, 'worker_id': a['worker_id'], 'kind': a['kind'], 'name': a['name'], 'parent_attempt_id': a.get('parent_attempt_id'), 'provider': a.get('provider'), 'model': a.get('model'), 'model_version': a.get('model_version'), 'provider_request_id': a.get('provider_request_id'), 'dispatch_role': a.get('dispatch_role', 'leaf'), 'status': ends[k]['status'] if k in ends else 'running', 'cost': exclusive_cost(ends.get(k), a['kind'])} for k, a in sorted(attempts.items())]}


def _stat(values, total=None):
    ordered = sorted(values)
    def percentile(q):
        if not ordered:
            return None
        index = (len(ordered) - 1) * q
        low, high = math.floor(index), math.ceil(index)
        return ordered[low] + (ordered[high] - ordered[low]) * (index - low)
    return {'n': len(values), 'missing_count': (total - len(values)) if total is not None else None,
            'mean': statistics.fmean(values) if values else None, 'min': min(values) if values else None,
            'max': max(values) if values else None, 'median': percentile(.5), 'p90': percentile(.9), 'p95': percentile(.95),
            'percentile_method': 'linear interpolation; descriptive only'}


def group_runs(rows):
    grouped = {}
    for row in rows:
        models = tuple(sorted({(a.get('provider') or 'unknown', a.get('model') or 'unknown', a.get('model_version') or 'unknown') for a in row['attempts'] if a['kind'] in {'model', 'jev'}}))
        key = (row['analysis_mode'], row['cache_state'], row['status'], row['synthetic'], row['collection_source'], row['final_response_included'], models)
        grouped.setdefault(key, []).append(row)
    result = []
    for (mode, cache, state, synthetic, collection, final_included, models), group in sorted(grouped.items()):
        n = len(group)
        metrics = {key: _stat([r['tokens'][key]['known_subtotal'] for r in group if r['tokens'][key]['complete']], n) for key in TOKEN_METRICS}
        metrics['wall_seconds'] = _stat([r['wall_seconds'] for r in group if r['wall_seconds'] is not None], n)
        metrics['tool_calls'] = _stat([r['tool_calls']['known_subtotal'] for r in group if r['tool_calls']['complete']], n)
        metrics['distinct_tool_count'] = _stat([r['tool_calls']['distinct_tool_count'] for r in group if r['tool_calls']['complete']], n)
        cost_metrics = []
        # Invoice, provider-reported and estimated values are not pooled together.
        keys = sorted({(c['currency'], tuple(c['basis']), tuple(c['price_versions'])) for r in group for c in r['costs']})
        for currency, basis, versions in keys:
            values = [Decimal(c['complete_total']) for r in group for c in r['costs'] if c['complete'] and (c['currency'], tuple(c['basis']), tuple(c['price_versions'])) == (currency, basis, versions)]
            eligible = sum(any((c['currency'], tuple(c['basis']), tuple(c['price_versions'])) == (currency, basis, versions) for c in r['costs']) for r in group)
            unknown = sum(not r['costs'] for r in group)
            cost_metrics.append({'currency': currency, 'basis': list(basis), 'price_versions': list(versions), 'n': len(values), 'eligible_n': eligible, 'missing_count': eligible - len(values), 'unknown_provenance_count': unknown, 'excluded_incompatible_count': n - eligible - unknown, 'mean': str(sum(values) / Decimal(len(values))) if values else None})
        memory_metrics = []
        memory_keys = sorted({(m['scope'], m['method'], m['platform']) for r in group for m in r['memory']['processes']})
        for scope, method, platform in memory_keys:
            values = []
            for r in group:
                observed = [m['peak_rss_bytes'] for m in r['memory']['processes'] if (m['scope'], m['method'], m['platform']) == (scope, method, platform) and m['peak_rss_bytes'] is not None]
                if observed:
                    values.append(max(observed))
            eligible = sum(any((m['scope'], m['method'], m['platform']) == (scope, method, platform) for m in r['memory']['processes']) for r in group)
            unknown = sum(not r['memory']['processes'] for r in group)
            memory_metrics.append({'scope': scope, 'method': method, 'platform': platform, 'measure': 'max observed process peak; not simultaneous total', 'eligible_n': eligible, 'unknown_provenance_count': unknown, 'excluded_incompatible_count': n - eligible - unknown, **_stat(values, eligible)})
        result.append({'analysis_mode': mode, 'cache_state': cache, 'status': state, 'synthetic': synthetic,
                       'collection_source': collection, 'final_response_included': final_included,
                       'model_set': [dict(zip(('provider', 'model', 'model_version'), model)) for model in models],
                       'n_runs': n, 'metrics': metrics, 'costs': cost_metrics, 'memory_peak_groups': memory_metrics})
    return result


def _display_metric(metric):
    value = metric['known_subtotal']
    if value is None:
        return f"unknown (0/{metric['expected_count']})"
    return f"{value} ({metric['known_count']}/{metric['expected_count']}; {metric['status']})"


def render_table(report):
    headers = ['Company / run', 'Mode / cache / collection', 'Data cutoff', 'Status / capture / final response', 'Input uncached', 'Input cached', 'Output', 'Total tokens', 'Tools / distinct / all attempts', 'Wall to cutoff seconds', 'Cost', 'Memory']
    rows = []
    for r in report['runs']:
        costs = '; '.join(f"{c['currency']} {c['known_subtotal'] if c['known_subtotal'] is not None else 'unknown'} ({('complete ' if c['complete'] else 'known subtotal only; ')+','.join(c['basis'])})" for c in r['costs']) or 'unknown'
        memories = r['memory']['processes']
        memory = '; '.join(f"{m['process_id']}: {m['peak_rss_bytes'] if m['peak_rss_bytes'] is not None else 'unknown'} B RSS ({m['scope']}; {m['method']}; {m['platform']}); context {m['context_tokens_max']}; storage {m['storage_bytes_max']} B" for m in memories) or 'unknown'
        rows.append([r['company_id']+' / '+r['run_id'], r['analysis_mode']+' / '+r['cache_state']+' / '+r['collection_source'], r['data_cutoff'] or 'unknown', r['status']+' / '+r['capture_status']+' / '+('included' if r['final_response_included'] else 'excluded'), *[_display_metric(r['tokens'][k]) for k in (*TOKEN_FIELDS, 'total_tokens')], f"{r['tool_calls']['known_subtotal'] if r['tool_calls']['known_subtotal'] is not None else 'unknown'} / {r['tool_calls']['distinct_tool_count'] if r['tool_calls']['distinct_tool_count'] is not None else 'unknown'} / {r['attempt_count']} observed ({r['tool_calls']['status']})", str(r['wall_seconds']) if r['wall_seconds'] is not None else 'unknown', costs, memory])
    def safe(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |'] + ['| '+' | '.join(map(safe, row))+' |' for row in rows])+'\n'


def render_html(report):
    # Static escaped HTML, no JavaScript or external resources.
    table = render_table(report).splitlines()
    body = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Vera run metrics</title><style>body{font:15px system-ui;margin:2rem;color:#17212b}table{border-collapse:collapse;width:100%}th,td{text-align:left;border:1px solid #ccd6dd;padding:.6rem;vertical-align:top}th{background:#e8f1f3}pre{white-space:pre-wrap}h1{font-size:1.7rem}</style><h1>Vera run metrics</h1><p>Operational telemetry only. Unknown values are not zero. Synthetic and live runs are grouped separately.</p><div style="overflow-x:auto"><table>'
    for i, line in enumerate(table):
        if i == 1:
            continue
        tag = 'th' if i == 0 else 'td'
        body += '<tr>'+''.join(f'<{tag}>'+html.escape(x.strip())+f'</{tag}>' for x in line.strip('|').split('|'))+'</tr>'
    body += '</table></div><h2>Matched groups and measured sample sizes</h2><pre>'+html.escape(json.dumps(report['groups'], indent=2))+'</pre><p>'+html.escape(report['warning'])+'</p></html>\n'
    return body


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


class Ledger:
    """One writer per file. Workers use separate files; merge by IDs on report.

    Thread-safe within one Ledger instance. No multiprocess append guarantee.
    Existing corrupt/truncated files are rejected, never silently truncated.
    """
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.seen = {e['event_id']: e for e in read_events([self.path])} if self.path.exists() else {}
        # Detect historical conflicts too.
        if self.path.exists():
            seen = {}
            for e in read_events([self.path]):
                if e['event_id'] in seen and canonical(seen[e['event_id']]) != canonical(e):
                    raise MetricsError('existing conflicting event_id')
                seen[e['event_id']] = e

    def emit(self, event):
        validate_event(event)
        with self.lock:
            if event['event_id'] in self.seen:
                if canonical(event) != canonical(self.seen[event['event_id']]):
                    raise MetricsError('conflicting event_id')
                return False
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Do not serialize prompts, tool arguments, responses or exception text.
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(canonical(event)+'\n')
                stream.flush()
                os.fsync(stream.fileno())
            self.seen[event['event_id']] = json.loads(canonical(event))
            return True


class RunRecorder:
    """Adapters must explicitly supply real provider usage and known billing."""
    def __init__(self, ledger, run_id, worker_id='coordinator'):
        self.ledger = ledger
        self.run_id = run_id
        self.worker_id = worker_id

    def event(self, event_type, *, at=None, event_id=None, **fields):
        e = {'schema_version': SCHEMA, 'event_id': event_id or str(uuid.uuid4()), 'run_id': self.run_id, 'at': at or now(), 'type': event_type, **fields}
        self.ledger.emit(e)
        return e

    def start(self, company_id, analysis_mode, cache_state='unknown', synthetic=False, collection_source='adapter', **stamp):
        self.event('run_start', company_id=company_id, analysis_mode=analysis_mode, cache_state=cache_state, synthetic=synthetic, collection_source=collection_source, **stamp)
        self.worker(self.worker_id)
        return self

    def worker(self, worker_id, parent_worker_id=None, **stamp):
        self.event('worker_start', worker_id=worker_id, parent_worker_id=parent_worker_id, **stamp)

    def resume(self, **stamp):
        self.event('run_resume', **stamp)

    def finish(self, status='completed', capture_status='partial', final_response_included=False, data_cutoff=None, **stamp):
        at = stamp.pop('at', None) or now()
        self.event('run_end', status=status, capture_status=capture_status, data_cutoff=data_cutoff or at, final_response_included=final_response_included, at=at, **stamp)

    @contextmanager
    def attempt(self, kind, name, *, attempt_id=None, parent_attempt_id=None, provider=None, model=None, model_version=None, provider_request_id=None, dispatch_role='leaf'):
        attempt_id = attempt_id or str(uuid.uuid4())
        self.event('attempt_start', attempt_id=attempt_id, worker_id=self.worker_id, kind=kind, name=name, parent_attempt_id=parent_attempt_id, provider=provider, model=model, model_version=model_version, provider_request_id=provider_request_id, dispatch_role=dispatch_role, usage_scope='exclusive')
        result = {'token_usage': None, 'cost': None, 'prices': None}
        try:
            yield result
        except BaseException as exc:
            status = 'cancelled' if isinstance(exc, (KeyboardInterrupt, SystemExit)) else 'failed'
            self.event('attempt_end', attempt_id=attempt_id, status=status, **result)
            raise
        else:
            self.event('attempt_end', attempt_id=attempt_id, status='completed', **result)

    def sample_process(self, *, context_tokens=None, storage_bytes=None):
        peak = None
        try:
            import resource
            value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform.startswith('linux'):
                peak = int(value * 1024)
            elif sys.platform == 'darwin':
                peak = int(value)
        except (ImportError, OSError, ValueError):
            pass
        at = now()
        return self.event('memory_sample', at=at, worker_id=self.worker_id, process_id=f'{os.getpid()}', scope='process_lifetime', peak_rss_bytes=peak, context_tokens=context_tokens, storage_bytes=storage_bytes, method='getrusage_ru_maxrss', platform=sys.platform, measurement_start=None, measurement_end=at)


def write_report(report, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'metrics.json').write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')
    (output / 'metrics.md').write_text(render_table(report), encoding='utf-8')
    (output / 'dashboard.html').write_text(render_html(report), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    report = sub.add_parser('report', help='Validate and merge ledger shards; always print table')
    report.add_argument('ledgers', nargs='+')
    report.add_argument('--output-dir')
    append = sub.add_parser('append', help='Append one validated, payload-free JSON event')
    append.add_argument('--ledger', required=True)
    append.add_argument('--event-file', required=True)
    run = sub.add_parser('run-command', help='Observe a command boundary only; inner usage is unknown')
    run.add_argument('--ledger', required=True)
    run.add_argument('--run-id', required=True)
    run.add_argument('--company-id', required=True)
    run.add_argument('--mode', choices=sorted(MODES), required=True)
    run.add_argument('--cache-state', choices=['cold', 'warm', 'mixed', 'unknown'], default='unknown')
    run.add_argument('--synthetic', action='store_true')
    run.add_argument('--output-dir', required=True)
    run.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.command == 'report':
            result = aggregate(read_events(args.ledgers))
            if args.output_dir:
                write_report(result, args.output_dir)
            print(render_table(result), end='')
            return 0
        if args.command == 'append':
            event = json.loads(Path(args.event_file).read_text(encoding='utf-8'))
            Ledger(args.ledger).emit(event)
            return 0
        command = args.args[1:] if args.args[:1] == ['--'] else args.args
        if not command:
            raise MetricsError('run-command needs a command after --')
        ledger = Ledger(args.ledger)
        if any(e['run_id'] == args.run_id for e in ledger.seen.values()):
            raise MetricsError('run-command requires a new run_id; use adapter resume for a resumed run')
        recorder = RunRecorder(ledger, args.run_id).start(args.company_id, args.mode, args.cache_state, args.synthetic, 'command_boundary')
        status, code = 'failed', 1
        attempt_id = str(uuid.uuid4())
        recorder.event('attempt_start', attempt_id=attempt_id, worker_id=recorder.worker_id, kind='tool', name='local-command', parent_attempt_id=None, provider=None, model=None, dispatch_role='wrapper', usage_scope='exclusive')
        try:
            # No shell; inherited stdio preserves command outputs. Arguments not logged.
            code = subprocess.run(command, check=False).returncode
            status = 'completed' if code == 0 else ('cancelled' if code < 0 else 'failed')
        except KeyboardInterrupt:
            status, code = 'cancelled', 130
        except OSError:
            status, code = 'failed', 127
        finally:
            recorder.event('attempt_end', attempt_id=attempt_id, status=status, token_usage=None, cost=None, prices=None)
            recorder.sample_process()
            recorder.finish(status, 'partial')
            result = aggregate(read_events([args.ledger]))
            write_report(result, args.output_dir)
            print(render_table(result), end='')
        return code if code >= 0 else 128 - code
    except (MetricsError, OSError, json.JSONDecodeError) as exc:
        print(f'metrics error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
