#!/usr/bin/env python3
"""Replay local contract cases, never a live-company or calibration benchmark."""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile

_vo_spec = importlib.util.spec_from_file_location('vera_observability_local', Path(__file__).with_name('vera_observability.py'))
vo = importlib.util.module_from_spec(_vo_spec)
_vo_spec.loader.exec_module(vo)

BENCHMARK_SCHEMA = 'vera.synthetic-benchmark/1'
EVALUATOR_REF = 'ver:contract-harness-1'
IMPLEMENTATION_REF = vo.content_ref(Path(__file__).with_name('vera_observability.py').read_bytes())
EVALUATOR_SOURCE_REF = vo.content_ref(Path(__file__).read_bytes())
CASES = [
    {'case_id': 'complete', 'scenario': 'complete', 'expected_health': 'healthy', 'expected_execution': 'completed', 'expected_engineering': 'passed_declared_checks'},
    {'case_id': 'missing-component', 'scenario': 'missing_component', 'expected_health': 'partial', 'expected_execution': 'blocked', 'expected_engineering': 'passed_declared_checks'},
    {'case_id': 'tool-exception', 'scenario': 'tool_exception', 'expected_health': 'healthy', 'expected_execution': 'failed', 'expected_engineering': 'passed_declared_checks'},
    {'case_id': 'retry', 'scenario': 'retry', 'expected_health': 'healthy', 'expected_execution': 'completed', 'expected_engineering': 'passed_declared_checks'},
    {'case_id': 'resume-after-crash', 'scenario': 'resume', 'expected_health': 'partial', 'expected_execution': 'completed', 'expected_engineering': 'passed_declared_checks'},
    {'case_id': 'missing-evaluation', 'scenario': 'missing_eval', 'expected_health': 'partial', 'expected_execution': 'completed', 'expected_engineering': 'incomplete'},
    {'case_id': 'failed-evaluation', 'scenario': 'failed_eval', 'expected_health': 'healthy', 'expected_execution': 'completed', 'expected_engineering': 'failed'},
    {'case_id': 'generic-jev-only', 'scenario': 'generic_jev', 'expected_health': 'healthy', 'expected_execution': 'completed', 'expected_engineering': 'not_evaluated'},
]
DATASET_REF = vo.content_ref(vo.canonical(CASES).encode())


def fixture_refs(case_id, config_ref='ver:synthetic-config-1'):
    return {'input': vo.content_ref(('synthetic-input:' + case_id).encode()),
            'artifact': 'ver:synthetic-artifact-1', 'model': 'ver:deterministic-no-llm-1',
            'prompt': 'ver:synthetic-prompt-1', 'rubric': 'ver:synthetic-contract-rubric-1',
            'dataset': DATASET_REF, 'config': config_ref, 'code': IMPLEMENTATION_REF}


def eval_result(refs, *, status='pass', generic_jev=False):
    return {'schema_version': vo.EVAL_SCHEMA, 'eval_id': 'contract-check', 'component': 'system',
            'span_id': None, 'status': status, 'quality_axis': 'engineering',
            'scope': 'generic_method' if generic_jev else 'synthetic_contract',
            'reviewer_basis': 'jev_structured' if generic_jev else 'synthetic_fixture',
            'refs': dict(refs), 'evidence_ref': vo.content_ref(b'synthetic deterministic equality: sum(2,3)==5'),
            'reason_code': 'ASSERTION_FAILED' if status == 'fail' else 'NONE',
            'jev': {'model_ref': 'ver:synthetic-jev-standin-1', 'question_ref': vo.content_ref(b'synthetic-method-question'),
                    'response_ref': vo.content_ref(b'synthetic-response-not-a-service-call'), 'confidence': 1.0,
                    'review_scope': 'generic_method'} if generic_jev else None}


def load_metrics(path):
    # Explicit caller-selected local source file; never download/install an adapter.
    spec = importlib.util.spec_from_file_location('vera_metrics_adapter', Path(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_case(case, output, *, config_ref='ver:synthetic-config-1', metrics=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    run_id = 'synthetic-' + case['case_id']
    refs = fixture_refs(case['case_id'], config_ref)
    scenario = case['scenario']
    trace_path = output / 'trace.jsonl'
    if trace_path.exists():
        raise vo.TraceError('BENCHMARK_OUTPUT_ALREADY_EXISTS')
    scope = 'generic_method' if scenario == 'generic_jev' else 'synthetic_contract'
    expected_evals = {'contract-check': {'component': 'system', 'quality_axis': 'engineering', 'scope': scope}}
    recorder = vo.RunRecorder(vo.Ledger(trace_path), run_id)
    recorder.start(refs, synthetic=True, expected_evals=expected_evals,
                   metrics_ref='metrics/dashboard.html' if metrics else None)
    mr = None
    if metrics:
        mr = metrics.RunRecorder(metrics.Ledger(output / 'metrics.jsonl'), run_id)
        mr.start('synthetic-company', 'STANDARD', cache_state='cold', synthetic=True, collection_source='fixture')
    actual = 0
    for component in vo.COMPONENTS:
        if component == 'research' and scenario == 'missing_component':
            continue
        if component == 'retrieval' and scenario in {'tool_exception', 'retry'}:
            try:
                with recorder.span(component, span_id='retrieval-first', metrics_attempt_id='retrieval-first' if mr else None):
                    if mr:
                        with mr.attempt('tool', 'synthetic-retrieval', attempt_id='retrieval-first'):
                            raise TimeoutError('DO_NOT_LOG_SYNTHETIC_SECRET')
                    else:
                        raise TimeoutError('DO_NOT_LOG_SYNTHETIC_SECRET')
            except TimeoutError:
                pass
            if scenario == 'tool_exception':
                continue
            with recorder.span(component, span_id='retrieval-retry', retry_of='retrieval-first', metrics_attempt_id='retrieval-retry' if mr else None):
                if mr:
                    with mr.attempt('tool', 'synthetic-retrieval', attempt_id='retrieval-retry'):
                        actual += 1
                else:
                    actual += 1
            continue
        if component == 'retrieval' and scenario == 'resume':
            recorder.event('span_start', span_id='retrieval-interrupted', parent_span_id=None,
                           component=component, retry_of=None, metrics_attempt_id=None, refs={})
            recorder.finish('blocked', 'partial')
            if mr:
                mr.finish('blocked', 'partial')
                mr.resume()
            recorder = vo.RunRecorder(vo.Ledger(trace_path), run_id, 'attempt-1')
            recorder.resume('attempt-2')
            with recorder.span(component, span_id='retrieval-resumed', retry_of='retrieval-interrupted'):
                actual += 1
            continue
        metrics_attempt = component + '-dispatch' if component in {'model', 'jev', 'retrieval'} and mr else None
        with recorder.span(component, span_id=component + '-span', metrics_attempt_id=metrics_attempt):
            if metrics_attempt:
                kind = 'tool' if component == 'retrieval' else component
                with mr.attempt(kind, 'synthetic-' + component, attempt_id=metrics_attempt):
                    # Local deterministic stand-ins execute for real. They make no
                    # provider call and therefore report no invented tokens/cost.
                    actual += sum((2, 3))
            else:
                actual += 1
    if scenario != 'missing_eval':
        # The negative case changes the expected answer, so this is an actual
        # failed assertion over deterministic work rather than a fabricated label.
        expected_answer = 6 if scenario == 'failed_eval' else 5
        observed_answer = sum((2, 3))
        result = eval_result(refs, status='pass' if observed_answer == expected_answer else 'fail', generic_jev=scenario == 'generic_jev')
        result['evidence_ref'] = vo.content_ref(vo.canonical({'actual': observed_answer, 'expected': expected_answer}).encode())
        recorder.evaluation(result)
    execution = 'blocked' if scenario == 'missing_component' else 'failed' if scenario == 'tool_exception' else 'completed'
    capture = 'partial' if scenario in {'missing_component', 'missing_eval', 'resume'} else 'complete'
    recorder.finish(execution, capture)
    if mr:
        mr.sample_process()
        # Local stand-ins have no provider usage. Partial metrics remain explicit.
        mr.finish(execution, capture_status='partial', final_response_included=False)
        metrics_report = metrics.aggregate(metrics.read_events([output / 'metrics.jsonl']))
        metrics.write_report(metrics_report, output / 'metrics')
    report = vo.aggregate(vo.read_events(trace_path))
    if mr:
        vo.correlate_metrics(report, metrics.read_events([output / 'metrics.jsonl']), metrics_report, output, expected_dashboard=metrics.render_html(metrics_report).encode('utf-8'))
    vo.write_report(report, output)
    row = report['runs'][0]
    checks = {
        'telemetry_health': row['telemetry_health'] == case['expected_health'],
        'execution_outcome': row['execution_outcome'] == case['expected_execution'],
        'engineering_quality': row['quality']['engineering']['status'] == case['expected_engineering'],
        'research_not_claimed': row['quality']['research']['status'] == 'not_evaluated',
        'local_work_executed': actual > 0,
    }
    return {'case_id': case['case_id'], 'input_ref': refs['input'], 'config_ref': refs['config'],
            'rubric_ref': refs['rubric'], 'model_ref': refs['model'], 'prompt_ref': refs['prompt'],
            'checks': checks, 'passed': all(checks.values()), 'telemetry_health': row['telemetry_health'],
            'execution_outcome': row['execution_outcome'], 'engineering_quality': row['quality']['engineering']['status'],
            'research_quality': row['quality']['research']['status'], 'run_id': run_id,
            'metrics_correlation': row['metrics_correlation']['status']}


def run_benchmark(output, *, config_ref='ver:synthetic-config-1', metrics_module=None):
    vo.reference(config_ref)
    metrics = load_metrics(metrics_module) if metrics_module else None
    rows = [run_case(case, Path(output) / case['case_id'], config_ref=config_ref, metrics=metrics) for case in CASES]
    report = {'schema_version': BENCHMARK_SCHEMA, 'synthetic': True, 'dataset_ref': DATASET_REF,
              'evaluator_ref': EVALUATOR_REF, 'evaluator_source_ref': EVALUATOR_SOURCE_REF,
              'implementation_ref': IMPLEMENTATION_REF, 'config_ref': config_ref, 'cases': rows,
              'passed': all(row['passed'] for row in rows), 'metrics_adapter': 'connected_local' if metrics else 'not_run',
              'research_quality': 'not_evaluated', 'warning': vo.QUALITY_WARNING}
    (Path(output) / 'benchmark.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def compare(baseline, candidate, *, allow_config_change=False):
    for report in (baseline, candidate):
        if report.get('schema_version') != BENCHMARK_SCHEMA or report.get('synthetic') is not True:
            raise vo.TraceError('UNSUPPORTED_BENCHMARK')
    for key in ('dataset_ref', 'evaluator_ref', 'evaluator_source_ref', 'metrics_adapter'):
        if baseline[key] != candidate[key]:
            raise vo.TraceError('UNMATCHED_BENCHMARK_BASIS')
    changed = baseline['config_ref'] != candidate['config_ref']
    if changed and not allow_config_change:
        raise vo.TraceError('UNMATCHED_CONFIG_REQUIRES_EXPLICIT_COMPARISON')
    maps = []
    for report in (baseline, candidate):
        mapping = {row['case_id']: row for row in report['cases']}
        if len(mapping) != len(report['cases']):
            raise vo.TraceError('DUPLICATE_BENCHMARK_CASE')
        if report.get('metrics_adapter') not in {'connected_local', 'not_run'}:
            raise vo.TraceError('INVALID_METRICS_ADAPTER_STATUS')
        expected_correlation = 'matched' if report['metrics_adapter'] == 'connected_local' else 'not_checked'
        if any(row.get('metrics_correlation') != expected_correlation for row in report['cases']):
            raise vo.TraceError('METRICS_ADAPTER_STATUS_CONTRADICTION')
        if type(report.get('passed')) is not bool or report['passed'] != all(row.get('passed') is True for row in report['cases']):
            raise vo.TraceError('CONTRADICTORY_REPORT_PASS')
        maps.append(mapping)
    before, after = maps
    if set(before) != set(after) or not before:
        raise vo.TraceError('UNMATCHED_CASE_SET')
    comparisons = []
    for case_id in sorted(before):
        a, b = before[case_id], after[case_id]
        for key in ('input_ref', 'rubric_ref', 'model_ref', 'prompt_ref'):
            if a[key] != b[key]:
                raise vo.TraceError('UNMATCHED_CASE_BASIS')
        if a['config_ref'] != baseline['config_ref'] or b['config_ref'] != candidate['config_ref']:
            raise vo.TraceError('CASE_CONFIG_CONTRADICTION')
        expected_checks = {'telemetry_health', 'execution_outcome', 'engineering_quality', 'research_not_claimed', 'local_work_executed'}
        if set(a['checks']) != expected_checks or set(b['checks']) != expected_checks:
            raise vo.TraceError('UNMATCHED_CHECK_SET')
        if any(type(value) is not bool for value in list(a['checks'].values()) + list(b['checks'].values())):
            raise vo.TraceError('INVALID_CHECK_RESULT')
        if type(a['passed']) is not bool or type(b['passed']) is not bool or a['passed'] != all(a['checks'].values()) or b['passed'] != all(b['checks'].values()):
            raise vo.TraceError('CONTRADICTORY_BENCHMARK_PASS')
        regressions = [name for name in a['checks'] if a['checks'][name] and not b['checks'][name]]
        comparisons.append({'case_id': case_id, 'regressions': regressions, 'baseline_passed': a['passed'], 'candidate_passed': b['passed']})
    return {'schema_version': 'vera.synthetic-comparison/1', 'synthetic': True,
            'matched_cases': len(comparisons), 'config_changed': changed,
            'baseline_config_ref': baseline['config_ref'], 'candidate_config_ref': candidate['config_ref'],
            'baseline_implementation_ref': baseline['implementation_ref'], 'candidate_implementation_ref': candidate['implementation_ref'],
            'regressions': sum(len(row['regressions']) for row in comparisons), 'cases': comparisons,
            'research_quality': 'not_evaluated', 'warning': vo.QUALITY_WARNING}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run')
    run.add_argument('--output-dir', type=Path, required=True)
    run.add_argument('--config-ref', default='ver:synthetic-config-1')
    run.add_argument('--metrics-module', type=Path)
    match = commands.add_parser('compare')
    match.add_argument('baseline', type=Path)
    match.add_argument('candidate', type=Path)
    match.add_argument('--allow-config-change', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'run':
            report = run_benchmark(args.output_dir, config_ref=args.config_ref, metrics_module=args.metrics_module)
            print(json.dumps({'passed': report['passed'], 'cases': len(report['cases']), 'research_quality': 'not_evaluated'}))
            return 0 if report['passed'] else 1
        report = compare(json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text()), allow_config_change=args.allow_config_change)
        print(json.dumps(report, indent=2))
        return 1 if report['regressions'] else 0
    except (vo.TraceError, OSError, ValueError, KeyError):
        print('Benchmark input/output or comparison basis invalid.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
