"""Independent synthetic review of operating numerical guards."""
import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'research'
sys.path[:0] = [str(ROOT / 'operating-uncertainty-guards-v0.1.0'),
                str(ROOT / 'explicit-history-statistics-v0.2.0')]
from aj_explicit_history import History, Transition, State
import statistical_reporting as raw
import aj_ij as raw_ij
import operating_uncertainty_guards as guarded


def boundary_histories():
    return tuple(History(f'r{i}', f'c{i}', State.PRE, 10,
                         (Transition(i + 1, State.PRE, State.POST),))
                 for i in range(5))


class IndependentOperatingReview(unittest.TestCase):
    def test_original_bug_and_guard_with_raw_point_and_draws_preserved(self):
        histories = boundary_histories()
        before = raw.operating_cluster_bootstrap(histories, 5, 100, 41)
        after = guarded.operating_cluster_bootstrap(histories, 5, 100, 41)
        self.assertIsNotNone(before.primary_interval)
        self.assertGreater(before.point, 1.0)
        self.assertEqual(after.point, before.point)
        self.assertEqual(after.draws, before.draws)
        self.assertEqual(after.completed_replicates, 100)
        self.assertIsNone(after.primary_interval)
        self.assertTrue(after.numerically_degenerate_distribution)

    def test_invalid_analytic_interval_withheld_scores_unchanged(self):
        histories = boundary_histories()
        before = raw_ij.aj_ij_diagnostic(histories, 5)
        after = guarded.aj_ij_diagnostic(histories, 5)
        self.assertGreater(before.normal_diagnostic_interval[0], before.normal_diagnostic_interval[1])
        self.assertIsNone(after.normal_diagnostic_interval)
        for name in ('mathematical_probabilities', 'round_gradients',
                     'company_gradients', 'covariance', 'operating_variance',
                     'operating_standard_error'):
            self.assertEqual(getattr(after, name), getattr(before, name))

    def test_interior_same_company_balance_is_not_false_precision(self):
        histories = tuple(h for i in range(5) for h in (
            History(f'op{i}', f'c{i}', State.PRE, 10,
                    (Transition(i + 1, State.PRE, State.POST),)),
            History(f'cl{i}', f'c{i}', State.PRE, 10,
                    (Transition(1, State.PRE, State.CLOSURE),)),
        ))
        report = guarded.operating_uncertainty_report(histories, 5,
                   disagreement_threshold=.1, n_boot=100, seed=41)
        self.assertAlmostEqual(report.primary.point, .5)
        self.assertIsNone(report.primary.primary_interval)
        self.assertIsNone(report.analytic.normal_diagnostic_interval)
        self.assertIsNone(report.material_disagreement)

    def test_non_degenerate_supported_case_is_identical(self):
        histories = (History('x', 'a', State.PRE, 10,
                              (Transition(1, State.PRE, State.CLOSURE),)),
                     History('y', 'b', State.PRE, 10),
                     History('z', 'c', State.PRE, 10))
        before = raw.operating_uncertainty_report(histories, 5,
                    disagreement_threshold=.1, n_boot=100, seed=41)
        after = guarded.operating_uncertainty_report(histories, 5,
                    disagreement_threshold=.1, n_boot=100, seed=41)
        self.assertEqual(after.primary.draws, before.primary.draws)
        self.assertEqual(after.primary.primary_interval, before.primary.primary_interval)
        self.assertEqual(after.analytic.normal_diagnostic_interval,
                         before.analytic.normal_diagnostic_interval)
        self.assertEqual(after.material_disagreement, before.material_disagreement)

    def test_no_run_status_and_unknown_draw_counts_preserved(self):
        for histories, n_boot in ((boundary_histories(), 0),
                                  ((History('x', 'a', State.PRE, 10),), 100)):
            before = raw.operating_cluster_bootstrap(histories, 5, n_boot)
            after = guarded.operating_cluster_bootstrap(histories, 5, n_boot)
            self.assertEqual(after.execution_status, before.execution_status)
            self.assertEqual(after.interval_status, before.interval_status)
            self.assertIsNone(after.undefined_draw_count)
            self.assertIsNone(after.numerically_degenerate_distribution)
            self.assertEqual(after.draws, ())

    def test_state_risk_gap_not_overridden_by_roundoff_disposition(self):
        histories = (History('x', 'a', State.PRE, 1),
                     History('y', 'b', State.PRE, 1))
        before = raw.operating_cluster_bootstrap(histories, 5, 20)
        after = guarded.operating_cluster_bootstrap(histories, 5, 20)
        self.assertEqual(after.interval_status, before.interval_status)
        self.assertEqual(after.draws, before.draws)
        self.assertIn('STATE_RISK_GAP', after.interval_status)

    def test_exact_degeneracy_keeps_exact_status(self):
        histories = (History('x', 'a', State.PRE, 10),
                     History('y', 'b', State.PRE, 10))
        report = guarded.operating_cluster_bootstrap(histories, 5, 20)
        self.assertTrue(report.degenerate_distribution)
        self.assertTrue(report.numerically_degenerate_distribution)
        self.assertEqual(report.interval_status, 'WITHHELD_DEGENERATE_BOOTSTRAP_DISTRIBUTION')

    def test_generator_consumed_once_and_input_tuple_preserved(self):
        histories = boundary_histories()
        expected = guarded.operating_uncertainty_report(histories, 5,
                     disagreement_threshold=.1, n_boot=20)
        actual = guarded.operating_uncertainty_report((h for h in histories), 5,
                     disagreement_threshold=.1, n_boot=20)
        self.assertEqual(actual, expected)
        self.assertEqual(histories, boundary_histories())


if __name__ == '__main__':
    unittest.main()
