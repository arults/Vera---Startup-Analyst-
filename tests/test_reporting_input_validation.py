"""Reporting guards, using real repository imports and synthetic fixtures.

Run: python -m unittest discover -s tests -p test_reporting_input_validation.py
Optional exact legacy-column replay with explicit additive diagnostics: set VERA_REPORTING_REPLAY_LEDGER,
VERA_REPORTING_REPLAY_RQ1 and VERA_REPORTING_REPLAY_RQ2 to an authorized
952-row ledger and its archived baseline CSVs. No data files are bundled here.
"""
import csv
import io
import os
import unittest
from pathlib import Path

from src.phase1c.reporting import (
    CellStats, lost_followup_sensitivity, pool_adjacent_years,
    rq1_cell_decision, rq2_field_cell_decision,
)
from src.phase1d.estimate_republic_europe_candidate_v3 import (
    followup_time, is_ascertained, km_survival, rq1_rows, rq2_rows,
)


def synthetic_rows(followup='1'):
    return [dict(round_id=f'synthetic-{i}', canonical_company_id=f'company-{i}',
                 offering_year_status='BOUNDED_YEAR', offering_year='2022',
                 primary_field='synthetic', followup_months=followup,
                 completion_date='2022-01-01',
                 success_date='2022-02-01' if i < 5 else '') for i in range(30)]


class TestReportingInputValidation(unittest.TestCase):
    def test_invalid_counts(self):
        for bad in [-1, -.1, .5, float('nan'), float('inf'), -float('inf'), True, '30', None]:
            calls = [lambda: rq1_cell_decision(bad, 5), lambda: rq1_cell_decision(30, bad),
                     lambda: rq2_field_cell_decision(bad, 5, .8), lambda: rq2_field_cell_decision(30, bad, .8),
                     lambda: CellStats(2022, bad, 5, 0), lambda: CellStats(2022, 30, bad, 0),
                     lambda: CellStats(2022, 30, 5, bad), lambda: lost_followup_sensitivity(bad, 0, 30),
                     lambda: lost_followup_sensitivity(5, bad, 30), lambda: lost_followup_sensitivity(5, 0, bad)]
            for index, call in enumerate(calls):
                with self.subTest(value=repr(bad), entry=index), self.assertRaises(ValueError):
                    call()

    def test_invalid_coverage_and_impossible_components(self):
        for bad in [float('nan'), float('inf'), -float('inf'), -.01, 1.01, None, '.8', True]:
            with self.subTest(value=repr(bad)), self.assertRaises(ValueError):
                rq2_field_cell_decision(30, 5, bad)
        for n, ascertained in [(30, 31), (0, 1)]:
            with self.assertRaises(ValueError):
                CellStats(2022, n, 5, ascertained)
        with self.assertRaises(ValueError):
            pool_adjacent_years(2022, [CellStats(2022, 30, 5, 30), CellStats(2021, 0, 0, 1)])

    def test_valid_gates_and_count_semantics(self):
        small = rq1_cell_decision(12, 2)
        self.assertTrue(small.report)
        self.assertTrue(small.low_information)
        self.assertEqual(small.reasons, ('n_lt_30', 'events_lt_5'))
        self.assertFalse(rq1_cell_decision(0, 0).report)
        self.assertEqual(rq2_field_cell_decision(30, 5, .79).reasons, ('ascertainment_lt_80pct',))
        for coverage in [.8, 1]:
            self.assertTrue(rq2_field_cell_decision(30, 5, coverage).report)
        self.assertFalse(rq2_field_cell_decision(29, 5, 1).report)
        self.assertFalse(rq2_field_cell_decision(30, 4, 1).report)
        # Generic informative counts may describe multiple state transitions.
        self.assertTrue(rq2_field_cell_decision(30, 40, .8).report)
        self.assertTrue(rq2_field_cell_decision(30.0, 5.0, .8).report)
        self.assertEqual(lost_followup_sensitivity(5, 3, 30),
                         dict(optimistic_rate=5/30, adverse_rate=8/30, lost_followup_share=3/30))

    def test_pooling_threshold_and_maturity(self):
        pooled = pool_adjacent_years(2022, [CellStats(2022, 18, 3, 16), CellStats(2021, 20, 3, 18)])
        self.assertTrue(pooled.report)
        self.assertEqual(pooled.years, (2021, 2022))
        young = pool_adjacent_years(2025, [CellStats(2025, 10, 1, 10), CellStats(2024, 10, 1, 10),
                                          CellStats(2023, 100, 50, 100)])
        self.assertTrue(young.suppressed)
        self.assertEqual(young.years, (2024, 2025))
        self.assertFalse(young.crossed_maturity_boundary)
        self.assertTrue(pool_adjacent_years(2022, [CellStats(2022, 30, 5, 24)]).report)
        self.assertFalse(pool_adjacent_years(2022, [CellStats(2022, 30, 5, 23)]).report)
        self.assertFalse(pool_adjacent_years(2022, [CellStats(2022, 0, 0, 0)]).report)

    def test_invalid_followup_rejected_by_real_callers(self):
        for bad in ['nan', 'NaN', 'inf', '-inf', '-1', 'broken', True, {}, float('inf')]:
            row = synthetic_rows(bad)[0]
            for helper in [followup_time, is_ascertained]:
                with self.subTest(value=repr(bad), helper=helper.__name__), self.assertRaises(ValueError):
                    helper(row)
            for caller in [rq1_rows, rq2_rows]:
                with self.subTest(value=repr(bad), caller=caller.__name__), self.assertRaises(ValueError):
                    caller(synthetic_rows(bad))
            with self.assertRaises(ValueError):
                km_survival([dict(row, closure_date='2022-02-01')], 12)

    def test_reversed_dates_even_with_supplied_followup(self):
        for raw in ['1', '', None]:
            row = dict(followup_months=raw, completion_date='2022-02-01', censor_date='2022-01-01')
            for helper in [followup_time, is_ascertained]:
                with self.assertRaises(ValueError):
                    helper(row)

    def test_date_types_and_existing_iso_syntax(self):
        for field in ['completion_date', 'censor_date']:
            for bad in [False, 0, [], {}, True, 1, 'invalid']:
                for helper in [followup_time, is_ascertained]:
                    with self.subTest(field=field, value=repr(bad)), self.assertRaises(ValueError):
                        helper({'followup_months': '1', field: bad})
            for value in [None, '', '2022-01-01', '20220101', '2022-W01-1']:
                row = {'followup_months': '1', field: value}
                self.assertEqual(followup_time(row), 1)
                self.assertTrue(is_ascertained(row))

    def test_missingness_is_preserved(self):
        for row in [{}, {'followup_months': None}, {'followup_months': ''}, {'followup_months': '0'}]:
            original = dict(row)
            self.assertEqual(followup_time(row), 0)
            self.assertFalse(is_ascertained(row))
            self.assertEqual(row, original)
        row = dict(followup_months='', completion_date='2022-01-01', censor_date='2022-02-01')
        self.assertGreater(followup_time(row), 0)
        # Deliberately preserve the existing blank-followup ascertainment convention.
        self.assertFalse(is_ascertained(row))
        self.assertTrue(is_ascertained(dict(followup_months='', success_date='2022-02-01')))
        self.assertTrue(any(row['report'] == 'true' for row in rq2_rows(synthetic_rows())))
        self.assertFalse(any(row['report'] == 'true' for row in rq2_rows(synthetic_rows('0'))))

    @unittest.skipUnless(all(os.environ.get(name) for name in (
        'VERA_REPORTING_REPLAY_LEDGER', 'VERA_REPORTING_REPLAY_RQ1', 'VERA_REPORTING_REPLAY_RQ2')),
        'Optional authorized ledger and archived CSVs not supplied')
    def test_optional_exact_952_row_replay(self):
        with Path(os.environ['VERA_REPORTING_REPLAY_LEDGER']).open(newline='', encoding='utf-8') as stream:
            ledger = list(csv.DictReader(stream))
        self.assertEqual(len(ledger), 952)
        for caller, expected_cells, variable in [(rq1_rows, 24, 'VERA_REPORTING_REPLAY_RQ1'),
                                                  (rq2_rows, 60, 'VERA_REPORTING_REPLAY_RQ2')]:
            rows = caller(ledger)
            self.assertEqual(len(rows), expected_cells)
            expected_bytes = Path(os.environ[variable]).read_bytes()
            baseline_reader = csv.DictReader(io.StringIO(expected_bytes.decode('utf-8'), newline=''))
            baseline_rows = list(baseline_reader)
            legacy_fields = baseline_reader.fieldnames
            self.assertEqual(len(baseline_rows), expected_cells)
            if caller is rq1_rows:
                # Intentional additive diagnostics: keep the exact archived
                # legacy schema/order/values, and check new fields separately.
                diagnostics = {
                    'operating_survival_terminal_start_status',
                    'operating_survival_terminal_end_status',
                }
                bootstrap_fields = {
                    f'{endpoint}_bootstrap_{field}'
                    for endpoint in ('success', 'closure', 'survival')
                    for field in ('execution_status', 'interval_status', 'requested_replicates',
                                  'completed_replicates', 'seed', 'supported_draw_count',
                                  'unsupported_draw_count', 'defined_draw_count', 'undefined_draw_count',
                                  'not_run_draw_count', 'degenerate_draw_count', 'degenerate_distribution',
                                  'report_id')
                }
                all_diagnostics = diagnostics | bootstrap_fields
                self.assertEqual(set(rows[0]), set(legacy_fields) | all_diagnostics)
                added_fields = all_diagnostics - set(legacy_fields)
                self.assertEqual([key for key in rows[0] if key not in added_fields], legacy_fields)
                for current, archived in zip(rows, baseline_rows):
                    self.assertEqual(set(current), set(legacy_fields) | all_diagnostics)
                    # This specific archived replay has no unsupported scenario
                    # within a primary-estimable cell; synthetic tests cover it.
                    expected_status = ('SUPPORTED' if archived['estimable'] == 'true'
                                       else 'NOT_EVALUATED_PRIMARY_UNESTIMABLE')
                    for field in diagnostics:
                        self.assertEqual(current[field], expected_status)
                comparison_rows = [{key: row[key] for key in legacy_fields} for row in rows]
            else:
                self.assertEqual(list(rows[0]), legacy_fields)
                comparison_rows = rows
            buf = io.StringIO(newline='')
            writer = csv.DictWriter(buf, fieldnames=legacy_fields)
            writer.writeheader()
            writer.writerows(comparison_rows)
            self.assertEqual(buf.getvalue().encode('utf-8'), expected_bytes)


if __name__ == '__main__':
    unittest.main()
