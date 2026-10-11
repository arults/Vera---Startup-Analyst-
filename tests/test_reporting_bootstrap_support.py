"""Caller safeguard controls. Fixtures are synthetic; no private ledger is bundled."""
import copy
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.phase1c.estimators import percentile_interval
from src.phase1d import estimate_republic_europe_candidate_v3 as c


def row(name, followup=24, *, company=None, success='', closure=''):
    return dict(round_id=name, canonical_company_id=company or name,
                completion_date='2020-01-01', followup_months=str(followup),
                offering_year='2020', offering_year_status='BOUNDED_YEAR',
                primary_field='synthetic', success_date=success, closure_date=closure)


def sparse_rows(endpoint='success'):
    event = {endpoint + '_date': '2020-02-01'}
    first = row('a', 1.1)
    first.update(event)
    return [first, row('b', 6), row('c', 24)]


class CallerBootstrapSupportTests(unittest.TestCase):
    def test_seed71_retains_257_unsupported_finite_draws(self):
        rows = sparse_rows()
        report = c.bootstrap_cif(rows, 'success', 12, 71, return_report=True)
        self.assertEqual(report['full_sample_support_status'], 'SUPPORTED')
        self.assertEqual(report['point'], 1/3)
        self.assertEqual(report['unsupported_draw_count'], 257)
        self.assertEqual(report['supported_draw_count'], 743)
        self.assertEqual(report['defined_draw_count'], 1000)
        self.assertEqual(report['undefined_draw_count'], 0)
        self.assertEqual(report['not_run_draw_count'], 0)
        self.assertEqual(report['interval_status'], 'WITHHELD_UNSUPPORTED_BOOTSTRAP_DRAWS')
        self.assertIsNone(report['primary_interval'])
        expected = c.grouped_bootstrap_indices(rows, 1000, 71)
        self.assertEqual([d['source_row_indices'] for d in report['draws']], expected)
        self.assertEqual([d['index'] for d in report['draws']], list(range(1000)))
        self.assertTrue(all(d['mathematical_value'] is not None for d in report['draws']))
        self.assertEqual(c.bootstrap_cif(rows, 'success', 12, 71), (1/3, None, None))

    def test_closure_and_survival_own_history_support(self):
        rows = sparse_rows('closure')
        for report in [c.bootstrap_cif(rows, 'closure', 12, 71, return_report=True),
                       c.bootstrap_survival(rows, 12, 71, return_report=True)]:
            self.assertEqual(report['unsupported_draw_count'], 257)
            self.assertIsNone(report['primary_interval'])
        success_only = sparse_rows()
        survival = c.bootstrap_survival(success_only, 12, 71, return_report=True)
        # A success does not absorb the collapsed-terminal operating endpoint.
        self.assertGreater(survival['unsupported_draw_count'], 257)

    def test_full_sample_gap_withholds(self):
        report = c.bootstrap_cif(sparse_rows()[:2], 'success', 12, 71, return_report=True)
        self.assertEqual(report['full_sample_support_status'], 'UNSUPPORTED_HORIZON')
        self.assertEqual(report['interval_status'], 'WITHHELD_FULL_SAMPLE_STATE_RISK_GAP')
        self.assertEqual(report['completed_replicates'], 1000)

    def test_complete_absorption_supports_later_landmark(self):
        rows = [row('a', 2, success='2020-02-01'), row('b', 2, success='2020-02-01')]
        report = c.bootstrap_cif(rows, 'success', 60, 71, return_report=True)
        self.assertEqual(report['unsupported_draw_count'], 0)
        self.assertEqual(report['interval_status'], 'WITHHELD_DEGENERATE_BOOTSTRAP_DISTRIBUTION')
        self.assertEqual(report['degenerate_draw_count'], 1000)
        self.assertEqual(report['point'], 1)

    def test_legacy_discrete_quantiles_not_linear(self):
        rows = [row('a', 24, success='2020-02-01'), row('b'), row('c')]
        with patch.object(c, 'BOOTSTRAPS', 7):
            report = c.bootstrap_cif(rows, 'success', 12, 71, return_report=True)
        values = [d['mathematical_value'] for d in report['draws']]
        self.assertEqual(report['primary_interval'], percentile_interval(values))
        self.assertNotIn('linear', report['percentile_convention'])
        self.assertEqual(report['unsupported_draw_count'], 0)
        self.assertEqual(report['interval_status'], 'PERCENTILE_BOOTSTRAP_INTERVAL_NO_NOMINAL_COVERAGE_GUARANTEE')

    def test_fully_supported_km_quantiles_are_legacy(self):
        rows = [row('a', 24, closure='2020-02-01'), row('b'), row('c')]
        with patch.object(c, 'BOOTSTRAPS', 19):
            report = c.bootstrap_survival(rows, 12, 71, return_report=True)
            values = [c.km_survival([rows[i] for i in indices], 12)
                      for indices in c.grouped_bootstrap_indices(rows, 19, 71)]
        self.assertEqual(report['primary_interval'], percentile_interval(values))
        self.assertEqual(report['point'], c.km_survival(rows, 12))

    def test_undefined_draw_retained_and_not_conditioned_away(self):
        rows = [row('a', success='2020-02-01'), row('b'), row('c')]
        original = c.cif_at_horizon
        calls = 0
        def sometimes_undefined(*args):
            nonlocal calls
            calls += 1
            return float('nan') if calls == 3 else original(*args)
        with patch.object(c, 'BOOTSTRAPS', 9), patch.object(c, 'cif_at_horizon', side_effect=sometimes_undefined):
            report = c.bootstrap_cif(rows, 'success', 12, 71, return_report=True)
        self.assertEqual(len(report['draws']), 9)
        self.assertEqual(report['undefined_draw_count'], 1)
        self.assertEqual(report['defined_draw_count'], 8)
        self.assertIsNone(report['draws'][1]['mathematical_value'])
        self.assertIn('nonfinite_bootstrap_statistic', report['draws'][1]['failure_reason'])
        self.assertEqual(report['interval_status'], 'WITHHELD_UNDEFINED_BOOTSTRAP_DRAWS')
        self.assertIsNone(report['primary_interval'])
        self.assertIsNone(report['degenerate_distribution'])

    def test_arithmetic_draw_error_retained(self):
        rows = [row('a', closure='2020-02-01'), row('b')]
        original = c.km_survival
        calls = 0
        def fail_once(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ArithmeticError('synthetic-draw-failure')
            return original(*args)
        with patch.object(c, 'BOOTSTRAPS', 5), patch.object(c, 'km_survival', side_effect=fail_once):
            report = c.bootstrap_survival(rows, 12, 71, return_report=True)
        self.assertEqual(report['undefined_draw_count'], 1)
        self.assertEqual(len(report['draws']), 5)
        self.assertEqual(report['draws'][0]['failure_reason'], 'ArithmeticError:synthetic-draw-failure')

    def test_empty_and_single_company_do_not_simulate(self):
        for rows in [[], [row('a')], [row('a', company='x'), row('b', company='x')]]:
            report = c.bootstrap_survival(rows, 12, 71, return_report=True)
            self.assertEqual(report['execution_status'], 'NOT_RUN_INSUFFICIENT_COMPANY_CLUSTERS')
            self.assertEqual(report['draws'], [])
            self.assertEqual(report['not_run_draw_count'], 1000)
            self.assertIsNone(report['unsupported_draw_count'])
            self.assertIsNone(report['primary_interval'])

    def test_zero_and_one_requested_replicates(self):
        for count, status in [(0, 'WITHHELD_BOOTSTRAP_NOT_RUN'), (1, 'WITHHELD_FEWER_THAN_TWO_REPLICATES')]:
            with patch.object(c, 'BOOTSTRAPS', count):
                report = c.bootstrap_survival([row('a'), row('b')], 12, 71, return_report=True)
            self.assertEqual(report['interval_status'], status)
            self.assertEqual(report['completed_replicates'], count)

    def test_bad_bootstrap_arguments_fail_cleanly(self):
        for value in [-1, .5, True, '1000', None]:
            with patch.object(c, 'BOOTSTRAPS', value), self.assertRaises(ValueError):
                c.bootstrap_survival([row('a'), row('b')], 12, 71, return_report=True)
        for value in [-1, float('nan'), float('inf'), True, None, '12']:
            with self.assertRaises(ValueError):
                c.bootstrap_survival([row('a')], value, 71, return_report=True)
        for value in [True, None, 1.5, '71']:
            with self.assertRaises(ValueError):
                c.bootstrap_survival([row('a')], 12, value, return_report=True)
        with self.assertRaises(ValueError):
            c.bootstrap_cif([row('a')], 'typo', 12, 71, return_report=True)

    def test_cluster_rounds_and_repeated_multiplicity_preserved(self):
        rows = [row('a1', company='a'), row('a2', company='a'), row('b')]
        with patch.object(c, 'BOOTSTRAPS', 30):
            report = c.bootstrap_survival(rows, 12, 71, return_report=True)
        self.assertTrue(any(d['source_row_indices'] == [0, 1, 0, 1] for d in report['draws']))
        for draw in report['draws']:
            indices = draw['source_row_indices']
            self.assertEqual(indices.count(0), indices.count(1))
            self.assertEqual(draw['source_round_ids'], [rows[i]['round_id'] for i in indices])
            self.assertEqual(draw['source_company_ids_by_row'], [rows[i]['canonical_company_id'] for i in indices])

    def test_pure_repeatable_rq1_and_zero_events_are_not_run(self):
        rows = [row('a'), row('b')]
        before = copy.deepcopy(rows)
        first_audit, second_audit = {}, {}
        first = c.rq1_rows(rows, bootstrap_audit=first_audit)
        second = c.rq1_rows(rows, bootstrap_audit=second_audit)
        self.assertEqual(first, second)
        self.assertEqual(first_audit, second_audit)
        self.assertEqual(rows, before)
        self.assertEqual(len(first), 24)
        self.assertEqual(len(first_audit), 72)
        self.assertEqual(first[0]['success_bootstrap_execution_status'], 'NOT_RUN_ZERO_OBSERVED_EVENTS')
        self.assertEqual(first[0]['success_bootstrap_not_run_draw_count'], 1000)
        self.assertEqual(first[3]['success_bootstrap_execution_status'], 'NOT_RUN_PRIMARY_UNESTIMABLE')
        self.assertNotIn('success_bootstrap_draws_json', first[0])

    def test_portable_hashed_sidecar_retains_nulls_and_all_draws(self):
        rows = sparse_rows()
        with patch.object(c, 'BOOTSTRAPS', 21):
            report = c.bootstrap_cif(rows, 'success', 12, 71, return_report=True)
        reports = {'republic_europe/2020/12/success': report}
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = c.write_bootstrap_audit(Path(a), reports, {'fixture': 'synthetic'})
            second = c.write_bootstrap_audit(Path(b), reports, {'fixture': 'synthetic'})
            self.assertEqual(first, second)
            manifest_path = Path(a) / first['bootstrap_audit_manifest']
            self.assertEqual(c.sha(manifest_path), first['bootstrap_audit_manifest_sha256'])
            manifest = json.loads(manifest_path.read_text())
            artifact = Path(a) / manifest['artifact']['relative_path']
            self.assertEqual(c.sha(artifact), manifest['artifact']['sha256'])
            with gzip.open(artifact, 'rt') as f:
                restored = json.loads(f.readline())
                self.assertEqual(f.read(), '')
            self.assertEqual(restored['report']['draws'], report['draws'])
            self.assertEqual(restored['report_id'], 'republic_europe/2020/12/success')
            self.assertEqual(manifest['reports'][restored['report_id']]['line_1based'], 1)
            self.assertNotIn(a, manifest_path.read_text())
            self.assertFalse(manifest['empirical_failure_claim'])

    def test_rq1_unsupported_bootstrap_does_not_suppress_point(self):
        rows = sparse_rows()
        with patch.object(c, 'BOOTSTRAPS', 100):
            output = c.rq1_rows(rows)
        first = output[0]
        self.assertEqual(first['estimable'], 'true')
        self.assertEqual(first['success_cif'], c.fmt(1/3))
        self.assertEqual(first['success_ci_lower'], '')
        self.assertEqual(first['success_ci_upper'], '')
        self.assertEqual(first['success_bootstrap_interval_status'], 'WITHHELD_UNSUPPORTED_BOOTSTRAP_DRAWS')
        self.assertEqual(first['promotion_status'], 'CANDIDATE_ONLY')

    def test_invalid_rq1_replicates_rejected_even_empty_cells(self):
        for value in [-1, .5, True, None]:
            with patch.object(c, 'BOOTSTRAPS', value), self.assertRaises(ValueError):
                c.rq1_rows([])

    def test_sidecar_noop_and_content_change_preserves_old_artifacts(self):
        with patch.object(c, 'BOOTSTRAPS', 5):
            report = c.bootstrap_survival([row('a'), row('b')], 12, 71, return_report=True)
        reports = {'synthetic/12/survival': report}
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            first = c.write_bootstrap_audit(out, reports, {'fixture': 'synthetic'})
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in out.iterdir()}
            self.assertEqual(first, c.write_bootstrap_audit(out, reports, {'fixture': 'synthetic'}))
            self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in out.iterdir()})
            newer = copy.deepcopy(reports)
            newer['synthetic/12/survival']['seed'] = 72
            c.write_bootstrap_audit(out, newer, {'fixture': 'synthetic'})
            self.assertEqual(len(list(out.iterdir())), 4)
            for name, snapshot in before.items():
                self.assertEqual(snapshot, ((out/name).read_bytes(), (out/name).stat().st_mtime_ns))

    def test_bad_sidecar_json_does_not_create_or_clobber_files(self):
        with patch.object(c, 'BOOTSTRAPS', 5):
            report = c.bootstrap_survival([row('a'), row('b')], 12, 71, return_report=True)
        reports = {'synthetic/12/survival': report}
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            c.write_bootstrap_audit(out, reports, {'fixture': 'synthetic'})
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in out.iterdir()}
            bad = copy.deepcopy(reports)
            bad['synthetic/12/survival']['draws'][0]['mathematical_value'] = float('nan')
            with self.assertRaises(ValueError):
                c.write_bootstrap_audit(out, bad, {'fixture': 'synthetic'})
            self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in out.iterdir()})
            for bad_id in ['/absolute/path', '../escape', 'x/../escape', '']:
                with self.assertRaises(ValueError):
                    c.write_bootstrap_audit(out, {bad_id: report}, {})

    def test_conflicting_content_address_is_rejected_without_overwrite(self):
        with patch.object(c, 'BOOTSTRAPS', 5):
            report = c.bootstrap_survival([row('a'), row('b')], 12, 71, return_report=True)
        reports = {'synthetic/12/survival': report}
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            binding = c.write_bootstrap_audit(out, reports, {})
            target = out/binding['bootstrap_audit_artifact']
            target.write_bytes(b'conflicting artifact')
            before = {p.name: p.read_bytes() for p in out.iterdir()}
            with self.assertRaisesRegex(ValueError, 'bootstrap_audit_artifact_conflict'):
                c.write_bootstrap_audit(out, reports, {})
            self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()})

    def test_every_rq1_report_id_and_seed_resolve_in_audit(self):
        with patch.object(c, 'BOOTSTRAPS', 11):
            audit = {}
            output = c.rq1_rows(sparse_rows(), bootstrap_audit=audit)
        for item in output:
            for endpoint, offset in [('success', 11), ('closure', 23), ('survival', 37)]:
                report_id = item[f'{endpoint}_bootstrap_report_id']
                self.assertIn(report_id, audit)
                self.assertEqual(audit[report_id]['seed'], item['offering_year'] * 1000 + item['horizon_months'] + offset)
                self.assertEqual(audit[report_id]['endpoint'], endpoint)
                self.assertEqual(audit[report_id]['horizon'], item['horizon_months'])

    def test_main_connects_compact_csv_to_private_sidecar(self):
        from contextlib import ExitStack, redirect_stdout
        fixtures = [row(f'synthetic-{i}', success='2020-02-01' if i < 10 else '') for i in range(952)]
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            out = Path(directory)
            paths = {'DATA': out, 'LEDGER': out/'synthetic-ledger.csv',
                     'PRIOR': out/'absent-prior.csv', 'RQ1': out/'rq1.csv',
                     'RQ2': out/'rq2.csv', 'SUMMARY': out/'summary.json',
                     'MANIFEST': out/'run-manifest.json'}
            c.write_csv(paths['LEDGER'], fixtures, list(fixtures[0]))
            for name, value in paths.items():
                stack.enter_context(patch.object(c, name, value))
            stack.enter_context(patch.object(c, 'BOOTSTRAPS', 7))
            with redirect_stdout(io.StringIO()):
                c.main()
            output = c.read_csv(paths['RQ1'])
            self.assertEqual(len(output), 24)
            binding = json.loads(paths['MANIFEST'].read_text())['bootstrap_audit']
            audit_manifest = json.loads((out/binding['bootstrap_audit_manifest']).read_text())
            for item in output:
                for key, value in binding.items():
                    self.assertEqual(item[key], value)
                for endpoint in ('success', 'closure', 'survival'):
                    self.assertIn(item[f'{endpoint}_bootstrap_report_id'], audit_manifest['reports'])
            self.assertLess(paths['RQ1'].stat().st_size, 50000)
            self.assertNotIn('draws_json', paths['RQ1'].read_text())
            self.assertEqual(c.sha(out/binding['bootstrap_audit_manifest']), binding['bootstrap_audit_manifest_sha256'])
            self.assertEqual(c.sha(out/binding['bootstrap_audit_artifact']), binding['bootstrap_audit_artifact_sha256'])
