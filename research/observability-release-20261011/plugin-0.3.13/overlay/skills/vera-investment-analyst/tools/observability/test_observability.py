from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vo = load('vo_test', 'vera_observability.py')
bench = load('benchmark_test', 'synthetic_benchmark.py')


def events():
    with tempfile.TemporaryDirectory() as tmp:
        refs = bench.fixture_refs('unit')
        recorder = vo.RunRecorder(vo.Ledger(Path(tmp) / 'trace.jsonl'), 'test-run')
        recorder.start(refs, synthetic=True, expected_evals={'contract-check': {'component': 'system', 'quality_axis': 'engineering', 'scope': 'synthetic_contract'}})
        for component in vo.COMPONENTS:
            with recorder.span(component, span_id=component + '-span'):
                sum((2, 3))
        recorder.evaluation(bench.eval_result(refs))
        recorder.finish('completed', 'complete')
        return recorder.ledger.events


def row(es):
    return vo.aggregate(es)['runs'][0]


def resequence(es):
    for i, event in enumerate(es, 1):
        event['seq'] = i
    return es


def issues(es):
    return {issue['code'] for issue in row(es)['issues']}


class SchemaTests(unittest.TestCase):
    def test_happy_path(self):
        r = row(events())
        self.assertEqual(r['telemetry_health'], 'healthy')
        self.assertEqual(r['coverage']['completed'], 11)
        self.assertEqual(r['execution_outcome'], 'completed')
        self.assertEqual(r['quality']['research']['status'], 'not_evaluated')

    def test_unknown_event_payload_rejected(self):
        es = events()
        es[0]['prompt_text'] = 'SECRET'
        with self.assertRaisesRegex(vo.TraceError, 'INVALID_FIELDS'):
            row(es)

    def test_unknown_ref_payload_rejected(self):
        es = events()
        es[0]['refs']['secret'] = 'do-not-log'
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_raw_ref_rejected(self):
        es = events()
        es[0]['refs']['input'] = 'confidential arbitrary prose'
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_schema_version_rejected(self):
        es = events()
        es[0]['schema_version'] = 'vera.observability/2'
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_sequence_boolean_rejected(self):
        es = events()
        es[0]['seq'] = True
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_timestamp_requires_zone(self):
        es = events()
        es[0]['at'] = '2026-10-11T10:00:00'
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_hash_stable(self):
        self.assertEqual(vo.content_ref(b'test'), vo.content_ref(b'test'))
        self.assertNotEqual(vo.content_ref(b'test'), vo.content_ref(b'test2'))
        with self.assertRaises(vo.TraceError):
            vo.content_ref('test')

    def test_identifier_rejects_payload_and_markup(self):
        for text in ['<script>alert(1)</script>', 'raw prose', 'a@b.com', 'https://example.com', '', 'x' * 121]:
            with self.subTest(text=text), self.assertRaises(vo.TraceError):
                vo.identifier(text)

    def test_na_reason_required(self):
        es = events()
        es[0]['expected_components']['jev'] = {'applicability': 'not_applicable', 'reason_code': None}
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_all_components_required_in_manifest(self):
        es = events()
        del es[0]['expected_components']['jev']
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_valid_na_is_not_pass(self):
        es = events()
        es[0]['expected_components']['jev'] = {'applicability': 'not_applicable', 'reason_code': 'NO_JEV_REVIEW_REQUIRED'}
        es = [e for e in es if e.get('span_id') != 'jev-span']
        r = row(resequence(es))
        self.assertEqual(r['telemetry_health'], 'healthy')
        self.assertEqual(r['components']['jev']['status'], 'not_applicable')
        self.assertEqual(r['coverage']['required'], 10)

    def test_observed_na_invalid(self):
        es = events()
        es[0]['expected_components']['jev'] = {'applicability': 'not_applicable', 'reason_code': 'NO_JEV_REVIEW_REQUIRED'}
        self.assertIn('OBSERVED_COMPONENT_DECLARED_NA', issues(es))

    def test_span_failure_requires_code(self):
        es = events()
        es[2]['execution_status'] = 'failed'
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_unknown_error_code_rejected(self):
        es = events()
        es[2]['error_code'] = 'SECRET_IN_ERROR'
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_sensitive_error_text_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'traces.jsonl'
            recorder = vo.RunRecorder(vo.Ledger(path), 'sensitive')
            recorder.start(bench.fixture_refs('sensitive'), synthetic=True)
            with self.assertRaises(RuntimeError):
                with recorder.span('retrieval'):
                    raise RuntimeError('VERY_PRIVATE_TOKEN_123 <script>')
            self.assertNotIn('VERY_PRIVATE_TOKEN', path.read_text())
            self.assertNotIn('<script>', path.read_text())
            self.assertEqual(recorder.ledger.events[-1]['error_code'], 'UNCLASSIFIED_EXCEPTION')

    def test_cancellation_records_and_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = vo.RunRecorder(vo.Ledger(Path(tmp) / 'traces.jsonl'), 'cancel')
            recorder.start(bench.fixture_refs('cancel'), synthetic=True)
            with self.assertRaises(KeyboardInterrupt):
                with recorder.span('retrieval'):
                    raise KeyboardInterrupt()
            self.assertEqual(recorder.ledger.events[-1]['execution_status'], 'cancelled')

    def test_unknown_provenance_partial(self):
        es = events()
        es[0]['refs']['model'] = None
        es = [e for e in es if e['kind'] != 'eval_result']
        es[-1]['capture_status'] = 'partial'
        r = row(resequence(es))
        self.assertEqual(r['provenance_status'], 'incomplete')
        self.assertEqual(r['telemetry_health'], 'partial')


class IntegrityTests(unittest.TestCase):
    def test_identical_duplicate_idempotent(self):
        es = events()
        report = vo.aggregate(es + [deepcopy(es[2])])
        self.assertEqual(report['duplicate_deliveries'], 1)
        self.assertEqual(report['runs'][0]['telemetry_health'], 'healthy')

    def test_conflicting_duplicate_fails(self):
        es = events()
        duplicate = deepcopy(es[2])
        duplicate['span_id'] = 'other'
        with self.assertRaisesRegex(vo.TraceError, 'CONFLICTING_EVENT_ID'):
            row(es + [duplicate])

    def test_duplicate_semantic_start_invalid(self):
        es = events()
        duplicate = deepcopy(es[1])
        duplicate['event_id'] = 'second-start'
        es.insert(2, duplicate)
        self.assertIn('DUPLICATE_SPAN_START', issues(resequence(es)))

    def test_duplicate_semantic_end_invalid(self):
        es = events()
        duplicate = deepcopy(es[2])
        duplicate['event_id'] = 'second-end'
        es.insert(3, duplicate)
        self.assertIn('DUPLICATE_SPAN_END', issues(resequence(es)))

    def test_missing_event_sequence_detected(self):
        es = events()
        del es[2]
        self.assertIn('SEQUENCE_GAP_OR_COLLISION', issues(es))

    def test_sequence_collision_detected(self):
        es = events()
        es[2]['seq'] = es[1]['seq']
        self.assertIn('SEQUENCE_GAP_OR_COLLISION', issues(es))

    def test_missing_component_never_completed(self):
        es = events()
        es = [e for e in es if e.get('span_id') != 'retrieval-span']
        r = row(resequence(es))
        self.assertEqual(r['components']['retrieval']['status'], 'unobserved')
        self.assertEqual(r['execution_outcome'], 'incomplete')
        self.assertIn('CONTRADICTORY_EXECUTION_COMPLETE', {i['code'] for i in r['issues']})

    def test_orphan_end(self):
        es = events()
        es[2]['span_id'] = 'unknown'
        self.assertIn('ORPHAN_SPAN_END', issues(es))

    def test_orphan_parent(self):
        es = events()
        es[1]['parent_span_id'] = 'missing'
        self.assertIn('ORPHAN_PARENT_SPAN', issues(es))

    def test_parent_cycle(self):
        es = events()
        es[1]['parent_span_id'] = 'identity-span'
        es[3]['parent_span_id'] = 'prompt-span'
        self.assertIn('SPAN_GRAPH_CYCLE', issues(es))

    def test_child_after_parent_closed(self):
        es = events()
        es[3]['parent_span_id'] = 'prompt-span'
        self.assertIn('CHILD_OUTLIVES_PARENT', issues(es))

    def test_valid_nested_spans(self):
        es = events()
        prompt_end = es.pop(2)
        es[2]['parent_span_id'] = 'prompt-span'
        es.insert(4, prompt_end)
        # Use same valid timestamp for reordered synthetic events.
        for event in es:
            event['at'] = '2026-10-11T10:00:00Z'
        self.assertEqual(row(resequence(es))['telemetry_health'], 'healthy')

    def test_retry_cycle(self):
        es = events()
        es[1]['retry_of'] = 'prompt-span'
        self.assertIn('SPAN_GRAPH_CYCLE', issues(es))

    def test_retry_of_completed(self):
        es = events()
        es[3]['retry_of'] = 'prompt-span'
        es[3]['component'] = 'prompt'
        self.assertIn('RETRY_OF_COMPLETED_SPAN', issues(es))

    def test_orphan_retry(self):
        es = events()
        es[1]['retry_of'] = 'unknown'
        self.assertIn('ORPHAN_RETRY', issues(es))

    def test_event_after_end(self):
        es = events()
        duplicate = deepcopy(es[1])
        duplicate['event_id'], duplicate['span_id'] = 'late', 'late-span'
        duplicate['at'] = es[-1]['at']
        es.append(duplicate)
        self.assertIn('EVENT_AFTER_RUN_END', issues(resequence(es)))

    def test_missing_run_start(self):
        es = events()[1:]
        self.assertIn('MISSING_OR_DUPLICATE_RUN_START', issues(resequence(es)))

    def test_missing_run_end_partial(self):
        r = row(events()[:-1])
        self.assertEqual(r['telemetry_health'], 'partial')
        self.assertEqual(r['execution_outcome'], 'incomplete')

    def test_attempt_mismatch(self):
        es = events()
        es[2]['attempt_id'] = 'wrong-attempt'
        self.assertIn('ATTEMPT_CORRELATION_MISMATCH', issues(es))

    def test_nonmonotonic_clock(self):
        es = events()
        es[-1]['at'] = '2000-01-01T00:00:00Z'
        self.assertIn('NONMONOTONIC_TIMESTAMP', issues(es))

    def test_valid_retry_retains_failed_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = bench.run_case(bench.CASES[3], tmp)
            report = row(vo.read_events(Path(tmp) / 'trace.jsonl'))
            self.assertTrue(result['passed'])
            self.assertEqual(report['components']['retrieval']['recovered_attempts'], 1)
            self.assertTrue(any(s['end'] and s['end']['execution_status'] == 'failed' for s in report['spans']))

    def test_resumed_missing_span_end_stays_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            bench.run_case(bench.CASES[4], tmp)
            es = vo.read_events(Path(tmp) / 'trace.jsonl')
            self.assertEqual(row(es)['telemetry_health'], 'partial')
            self.assertEqual(row(es)['execution_outcome'], 'completed')
            es[-1]['capture_status'] = 'complete'
            self.assertIn('CONTRADICTORY_CAPTURE_COMPLETE', issues(es))

    def test_invalid_resume_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            bench.run_case(bench.CASES[4], tmp)
            es = vo.read_events(Path(tmp) / 'trace.jsonl')
            next(e for e in es if e['kind'] == 'run_resume')['resumes_attempt_id'] = 'unknown'
            self.assertIn('INVALID_RESUME_LINK', issues(es))

    def test_sdk_rejects_false_complete_before_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = vo.RunRecorder(vo.Ledger(Path(tmp) / 'traces.jsonl'), 'partial')
            recorder.start(bench.fixture_refs('partial'), synthetic=True)
            before = len(recorder.ledger.events)
            with self.assertRaises(vo.TraceError):
                recorder.finish('completed', 'complete')
            self.assertEqual(len(recorder.ledger.events), before)


class EvaluationTests(unittest.TestCase):
    def test_missing_eval_not_pass(self):
        es = events()
        es = [e for e in es if e['kind'] != 'eval_result']
        es[-1]['capture_status'] = 'partial'
        r = row(resequence(es))
        self.assertEqual(r['quality']['engineering']['status'], 'incomplete')
        self.assertEqual(r['evaluations'][0]['status'], 'not_run')
        self.assertEqual(r['execution_outcome'], 'completed')

    def test_failed_eval_not_execution_failure(self):
        es = events()
        result = es[-2]['result']
        result['status'], result['reason_code'] = 'fail', 'ASSERTION_FAILED'
        r = row(es)
        self.assertEqual(r['quality']['engineering']['status'], 'failed')
        self.assertEqual(r['execution_outcome'], 'completed')
        self.assertEqual(r['telemetry_health'], 'healthy')

    def test_eval_pass_needs_artifact_and_evidence(self):
        for key in ['evidence_ref', 'refs']:
            es = events()
            if key == 'refs':
                es[-2]['result']['refs']['artifact'] = None
            else:
                es[-2]['result'][key] = None
            with self.subTest(key=key), self.assertRaises(vo.TraceError):
                row(es)

    def test_stale_provenance_cannot_pass(self):
        for key in vo.REF_KEYS:
            es = events()
            es[-2]['result']['refs'][key] = 'ver:stale'
            with self.subTest(key=key):
                self.assertIn('EVAL_PROVENANCE_MISMATCH', issues(es))
                self.assertEqual(row(es)['quality']['engineering']['status'], 'unverified')

    def test_component_eval_requires_span(self):
        es = events()
        es[-2]['result']['scope'] = 'component'
        es[-2]['result']['component'] = 'analysis'
        with self.assertRaises(vo.TraceError):
            row(es)

    def test_component_eval_effective_refs(self):
        es = events()
        es[0]['expected_evals']['contract-check'] = {'component': 'analysis', 'scope': 'component', 'quality_axis': 'engineering'}
        start = next(e for e in es if e.get('span_id') == 'analysis-span' and e['kind'] == 'span_start')
        start['refs']['artifact'] = 'ver:analysis-artifact-2'
        result = es[-2]['result']
        result.update(component='analysis', span_id='analysis-span', scope='component')
        self.assertIn('EVAL_PROVENANCE_MISMATCH', issues(es))
        result['refs']['artifact'] = 'ver:analysis-artifact-2'
        self.assertEqual(row(es)['telemetry_health'], 'healthy')

    def test_eval_orphan_span(self):
        es = events()
        es[-2]['result']['span_id'] = 'missing'
        self.assertIn('ORPHAN_EVAL_SPAN', issues(es))

    def test_eval_scope_mismatch(self):
        es = events()
        es[-2]['result']['scope'] = 'generic_method'
        self.assertIn('EVAL_MANIFEST_SCOPE_MISMATCH', issues(es))

    def test_undeclared_eval(self):
        es = events()
        es[-2]['result']['eval_id'] = 'other-eval'
        self.assertIn('UNDECLARED_EVALUATION', issues(es))

    def test_duplicate_eval(self):
        es = events()
        duplicate = deepcopy(es[-2])
        duplicate['event_id'] = 'extra-eval'
        es.insert(-1, duplicate)
        self.assertIn('DUPLICATE_EVAL_RESULT', issues(resequence(es)))

    def test_generic_jev_does_not_pass_system(self):
        es = events()
        es[0]['expected_evals']['contract-check']['scope'] = 'generic_method'
        es[-2]['result'] = bench.eval_result(es[0]['refs'], generic_jev=True)
        self.assertEqual(row(es)['quality']['engineering']['status'], 'not_evaluated')

    def test_jev_scope_and_confidence_limits(self):
        for value in [float('nan'), float('inf'), -0.1, 1.1, True]:
            result = bench.eval_result(bench.fixture_refs('unit'), generic_jev=True)
            result['jev']['confidence'] = value
            with self.subTest(value=value), self.assertRaises(vo.TraceError):
                vo.validate_eval(result)
        result = bench.eval_result(bench.fixture_refs('unit'), generic_jev=True)
        result['jev']['review_scope'] = 'full_system'
        with self.assertRaises(vo.TraceError):
            vo.validate_eval(result)

    def test_generic_or_synthetic_research_forbidden_all_bases(self):
        for basis in ['human_review', 'deterministic_check', 'synthetic_fixture']:
            for scope in ['synthetic_contract', 'generic_method']:
                result = bench.eval_result(bench.fixture_refs('unit'))
                result.update(reviewer_basis=basis, quality_axis='research', scope=scope)
                with self.subTest(basis=basis, scope=scope), self.assertRaises(vo.TraceError):
                    vo.validate_eval(result)

    def test_synthetic_run_cannot_establish_research(self):
        es = events()
        es[0]['expected_evals']['contract-check'].update(quality_axis='research', scope='full_system')
        es[-2]['result'].update(quality_axis='research', scope='full_system', reviewer_basis='human_review')
        self.assertIn('SYNTHETIC_RUN_CANNOT_ESTABLISH_RESEARCH_QUALITY', issues(es))
        self.assertEqual(row(es)['quality']['research']['status'], 'not_evaluated')

    def test_live_declared_research_check_is_bounded(self):
        es = events()
        es[0]['synthetic'] = False
        es[0]['expected_evals']['contract-check'].update(quality_axis='research', scope='full_system')
        es[-2]['result'].update(quality_axis='research', scope='full_system', reviewer_basis='human_review')
        r = row(es)
        self.assertEqual(r['quality']['research']['status'], 'passed_declared_checks')
        self.assertNotIn('calibrated', json.dumps(r))

    def test_blocked_and_notrun_require_reason(self):
        for status in ['blocked', 'not_run', 'incomplete']:
            result = bench.eval_result(bench.fixture_refs('unit'))
            result['status'] = status
            with self.subTest(status=status), self.assertRaises(vo.TraceError):
                vo.validate_eval(result)
            result['reason_code'] = 'EVIDENCE_MISSING'
            vo.validate_eval(result)


class PersistenceAndDashboardTests(unittest.TestCase):
    def test_append_reopen_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'trace.jsonl'
            ledger = vo.Ledger(path)
            for event in events()[:2]:
                ledger.emit(event)
            before = path.read_bytes()
            reopened = vo.Ledger(path)
            reopened.emit(events()[2])
            self.assertTrue(path.read_bytes().startswith(before))

    def test_ledger_duplicate_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'trace.jsonl'
            ledger = vo.Ledger(path)
            event = events()[0]
            self.assertTrue(ledger.emit(event))
            before = path.read_bytes()
            self.assertFalse(ledger.emit(event))
            self.assertEqual(before, path.read_bytes())

    def test_truncated_tail_not_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'trace.jsonl'
            path.write_text('{"secret":"DO_NOT_PRINT"')
            before = path.read_bytes()
            with self.assertRaisesRegex(vo.TraceError, 'TRUNCATED_OR_OVERSIZE_EVENT'):
                vo.Ledger(path)
            self.assertEqual(before, path.read_bytes())

    def test_malformed_json_not_echoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'trace.jsonl'
            path.write_text('SENSITIVE_PAYLOAD\n')
            with self.assertRaises(vo.TraceError) as error:
                vo.read_events(path)
            self.assertNotIn('SENSITIVE_PAYLOAD', str(error.exception))

    def test_symlink_ledger_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, target = Path(tmp) / 'link.jsonl', Path(tmp) / 'target'
            target.write_text('')
            path.symlink_to(target)
            with self.assertRaises(vo.TraceError):
                vo.Ledger(path)

    def test_owner_only_file_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'trace.jsonl'
            vo.Ledger(path).emit(events()[0])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_html_escaping_defense_in_depth(self):
        report = vo.aggregate(events())
        report['runs'][0]['run_id'] = '<script>alert("x")</script>'
        report['runs'][0]['refs']['input'] = '<img src=x onerror=alert(1)>'
        output = vo.render_dashboard(report)
        self.assertNotIn('<script>', output)
        self.assertNotIn('<img src=x', output)
        self.assertIn('&lt;script&gt;', output)
        self.assertIn('Content-Security-Policy', output)
        self.assertIn('<details>', output)

    def test_metrics_links_safe_only(self):
        self.assertEqual(vo.local_link('metrics/report.html'), 'metrics/report.html')
        for value in ['https://evil.example/x.html', '//evil/x.html', '../private.html', '/private.html', 'a/../x.html', 'x%2fsecret.html', 'javascript:x.html', 'x.html?secret=1', 'x\\y.html', '.hidden.html']:
            with self.subTest(value=value), self.assertRaises(vo.TraceError):
                vo.local_link(value)

    def test_dashboard_rejects_unsafe_injected_link(self):
        report = vo.aggregate(events())
        report['runs'][0]['metrics_ref'] = 'javascript:alert(1).html'
        self.assertNotIn('javascript:', vo.render_dashboard(report))

    def test_no_model_payload_capture_fields(self):
        es = events()
        text = vo.canonical(es)
        for forbidden in ['prompt_text', 'response_text', 'api_key', 'password', 'exception_message', 'traceback']:
            self.assertNotIn('"' + forbidden + '"', text)

    def test_thread_safe_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = vo.RunRecorder(vo.Ledger(Path(tmp) / 'thread.jsonl'), 'thread-run')
            recorder.start(bench.fixture_refs('thread'), synthetic=True)
            def record(i):
                with recorder.span('retrieval', span_id='retrieval-' + str(i)):
                    sum((i, 1))
            threads = [threading.Thread(target=record, args=(i,)) for i in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            es = recorder.ledger.events
            self.assertEqual([e['seq'] for e in es], list(range(1, 18)))


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.report = bench.run_benchmark(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_synthetic_cases_pass(self):
        self.assertTrue(self.report['passed'])
        self.assertEqual(len(self.report['cases']), 8)
        self.assertEqual(self.report['research_quality'], 'not_evaluated')

    def test_replay_matched_configs(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = bench.run_benchmark(tmp)
        result = bench.compare(self.report, candidate)
        self.assertEqual(result['regressions'], 0)
        self.assertEqual(result['matched_cases'], 8)

    def test_mismatched_dataset_rejected(self):
        changed = deepcopy(self.report)
        changed['dataset_ref'] = 'ver:other-dataset'
        with self.assertRaises(bench.vo.TraceError):
            bench.compare(self.report, changed)

    def test_mismatched_cases_rejected(self):
        changed = deepcopy(self.report)
        changed['cases'].pop()
        with self.assertRaises(bench.vo.TraceError):
            bench.compare(self.report, changed)

    def test_mismatched_config_requires_explicit_optin(self):
        changed = deepcopy(self.report)
        changed['config_ref'] = 'ver:other-config'
        for case in changed['cases']:
            case['config_ref'] = changed['config_ref']
        with self.assertRaises(bench.vo.TraceError):
            bench.compare(self.report, changed)
        self.assertTrue(bench.compare(self.report, changed, allow_config_change=True)['config_changed'])

    def test_mismatched_case_provenance_rejected(self):
        for key in ['input_ref', 'model_ref', 'prompt_ref', 'rubric_ref']:
            changed = deepcopy(self.report)
            changed['cases'][0][key] = 'ver:changed'
            with self.subTest(key=key), self.assertRaises(bench.vo.TraceError):
                bench.compare(self.report, changed)

    def test_regression_localized(self):
        changed = deepcopy(self.report)
        changed['cases'][0]['checks']['research_not_claimed'] = False
        changed['cases'][0]['passed'] = False
        changed['passed'] = False
        report = bench.compare(self.report, changed)
        self.assertEqual(report['regressions'], 1)
        self.assertEqual(report['cases'][0]['regressions'], ['research_not_claimed'])

    def test_contradictory_pass_rejected(self):
        changed = deepcopy(self.report)
        changed['cases'][0]['checks']['research_not_claimed'] = False
        with self.assertRaises(bench.vo.TraceError):
            bench.compare(self.report, changed)

    def test_duplicate_case_rejected(self):
        changed = deepcopy(self.report)
        changed['cases'].append(deepcopy(changed['cases'][0]))
        with self.assertRaises(bench.vo.TraceError):
            bench.compare(self.report, changed)

    def test_unknown_check_is_not_comparable(self):
        changed = deepcopy(self.report)
        changed['cases'][0]['checks']['new-check'] = True
        with self.assertRaises(bench.vo.TraceError):
            bench.compare(self.report, changed)

    def test_fixture_output_not_overwritten(self):
        with self.assertRaises(bench.vo.TraceError):
            bench.run_benchmark(self.tmp.name)

class AdditionalRegressionTests(unittest.TestCase):
    def test_empty_ledger_unobserved(self):
        self.assertEqual(vo.aggregate([])['observation_status'], 'not_run')

    def test_empty_benchmark_checks_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = bench.run_benchmark(tmp)
        for case in report['cases']:
            case['checks'] = {}
        with self.assertRaises(bench.vo.TraceError):
            bench.compare(report, report)

    def test_nonboolean_benchmark_pass_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = bench.run_benchmark(tmp)
        report['passed'] = 1
        with self.assertRaises(bench.vo.TraceError):
            bench.compare(report, report)

    def test_partial_span_provenance_affects_health(self):
        es = events()
        es[1]['refs']['input'] = None
        es[-1]['capture_status'] = 'partial'
        self.assertEqual(row(es)['provenance_status'], 'incomplete')
        self.assertEqual(row(es)['telemetry_health'], 'partial')

    def test_complete_claim_cannot_be_repaired_retroactively(self):
        es = events()
        evaluation = es.pop(-2)
        premature = es[-1]
        premature['execution_status'] = 'blocked'
        resume = {k: premature[k] for k in vo.BASE}
        resume.update(event_id='resume-new', kind='run_resume', attempt_id='attempt-2', resumes_attempt_id='attempt-1')
        es.append(resume)
        evaluation.update(attempt_id='attempt-2', at=resume['at'])
        es.append(evaluation)
        end = deepcopy(premature)
        end.update(event_id='new-end', attempt_id='attempt-2', execution_status='completed')
        es.append(end)
        self.assertIn('CONTRADICTORY_CAPTURE_COMPLETE', issues(resequence(es)))

    def test_local_metrics_correlation_counts_unreferenced(self):
        report = vo.aggregate(events())
        report['runs'][0]['metrics_ref'] = 'metrics/dashboard.html'
        me = [{'type': 'run_start', 'run_id': 'test-run', 'synthetic': True},
              {'type': 'attempt_start', 'run_id': 'test-run', 'attempt_id': 'untraced'}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'metrics/dashboard.html'
            path.parent.mkdir()
            path.write_bytes(b'synthetic-html')
            vo.correlate_metrics(report, me, {'runs': [{'run_id': 'test-run'}]}, tmp, expected_dashboard=b'synthetic-html')
        status = report['runs'][0]['metrics_correlation']
        self.assertEqual(status['status'], 'matched_declared_refs')
        self.assertEqual(status['unreferenced_attempt_ids'], ['untraced'])
        self.assertEqual(status['report_content_verification'], 'verified_generated_bytes')
        self.assertEqual(report['runs'][0]['telemetry_health'], 'partial')

    def test_stale_metrics_dashboard_invalid(self):
        report = vo.aggregate(events())
        report['runs'][0]['metrics_ref'] = 'metrics/dashboard.html'
        me = [{'type': 'run_start', 'run_id': 'test-run', 'synthetic': True}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'metrics/dashboard.html'
            path.parent.mkdir()
            path.write_bytes(b'stale-html')
            vo.correlate_metrics(report, me, {'runs': [{'run_id': 'test-run'}]}, tmp, expected_dashboard=b'new-html')
        self.assertEqual(report['runs'][0]['metrics_correlation']['status'], 'mismatch')
        self.assertEqual(report['runs'][0]['telemetry_health'], 'invalid')

    def test_schema_artifacts_match_generator(self):
        generated = load('schemas_test', 'build_schemas.py')
        base = Path(__file__).parent / 'schemas'
        self.assertEqual(json.loads((base / 'trace.schema.json').read_text()), generated.trace)
        self.assertEqual(json.loads((base / 'eval.schema.json').read_text()), generated.result)


if __name__ == '__main__':
    unittest.main()
