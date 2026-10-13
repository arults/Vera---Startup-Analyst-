"""Synthetic regression and exact-rational checks, never empirical calibration."""
from dataclasses import fields, replace
from fractions import Fraction
import math
import random
import unittest
from unittest.mock import patch

from aj_explicit_history import History as H, Transition as T, State as S
import aj_ij as frozen_ij
import statistical_reporting as frozen
from exact_reference import weighted_occupancy
import operating_uncertainty_guards as guarded


def all_operating(n=5):
    return [H(str(i), str(i), S.PRE, n + 1, (T(i + 1, S.PRE, S.POST),))
            for i in range(n)]


def balanced_companies(n=5):
    return [H(f'{i}:{kind}', str(i), S.PRE, n + 1, (T(i + 1, S.PRE, end),))
            for i in range(n) for kind, end in [('alive', S.POST), ('dead', S.CLOSURE)]]


def mixture():
    return [H(str(i), str(i), S.PRE, 5, (T(1, S.PRE, S.CLOSURE),) if i < 4 else ())
            for i in range(10)]


class OperatingNumericalGuardTests(unittest.TestCase):
    def assert_raw_preserved(self, original, result, changed):
        for field in fields(original):
            if field.name not in changed:
                self.assertEqual(getattr(original, field.name), getattr(result, field.name), field.name)

    def test_reproduces_and_guards_inverted_boundary_interval(self):
        histories = all_operating()
        self.assertEqual(weighted_occupancy(histories, 5)[1], Fraction(1))
        old_b = frozen.operating_cluster_bootstrap(histories, 5, 100, 73)
        old_a = frozen_ij.aj_ij_diagnostic(histories, 5)
        self.assertGreater(old_b.point, 1)
        self.assertGreater(old_b.primary_interval[1], 1)
        self.assertGreater(old_a.normal_diagnostic_interval[0], old_a.normal_diagnostic_interval[1])
        result = guarded.operating_uncertainty_report(histories, 5, n_boot=100, seed=73,
                                                     disagreement_threshold=.05)
        self.assertIsNone(result.primary.primary_interval)
        self.assertIsNone(result.analytic.normal_diagnostic_interval)
        self.assertTrue(result.primary.numerically_degenerate_distribution)
        self.assertFalse(result.primary.degenerate_distribution)
        self.assertEqual(result.primary.interval_status, 'WITHHELD_NUMERICALLY_DEGENERATE_BOOTSTRAP_DISTRIBUTION')
        self.assertEqual(result.analytic.interval_status, 'WITHHELD_BOUNDARY_OR_ZERO_IJ_VARIANCE_NOT_INFORMATIVE_COVERAGE')
        self.assertEqual(result.comparison_status, 'NOT_COMPARABLE_INTERVAL_UNAVAILABLE')
        self.assertIsNone(result.material_disagreement)
        self.assertIsNone(result.endpoint_max_absolute_difference)
        self.assert_raw_preserved(old_b, result.primary, {'primary_interval', 'interval_status'})
        self.assert_raw_preserved(old_a, result.analytic, {'normal_diagnostic_interval', 'interval_status'})

    def test_interior_company_constant_distribution_is_numerically_degenerate(self):
        histories = balanced_companies()
        self.assertEqual(weighted_occupancy(histories, 5)[1], Fraction(1, 2))
        old = frozen.operating_cluster_bootstrap(histories, 5, 100, 73)
        self.assertIsNotNone(old.primary_interval)
        result = guarded.operating_uncertainty_report(histories, 5, n_boot=100, seed=73,
                                                     disagreement_threshold=.05)
        self.assertTrue(result.primary.numerically_degenerate_distribution)
        self.assertIsNone(result.primary.primary_interval)
        self.assertIsNone(result.analytic.normal_diagnostic_interval)
        for draw in result.primary.draws:
            self.assertAlmostEqual(draw.mathematical_value, .5)
        self.assertEqual(result.primary.draws, old.draws)

    def test_non_degenerate_distribution_only_clips_roundoff_bounds(self):
        histories = all_operating() + [H('dead', 'dead', S.CLOSURE, 6)]
        old = frozen.operating_cluster_bootstrap(histories, 5, 1000, 73)
        self.assertGreater(old.primary_interval[1], 1)
        result = guarded.operating_cluster_bootstrap(histories, 5, 1000, 73)
        self.assertFalse(result.numerically_degenerate_distribution)
        self.assertEqual(result.primary_interval, (old.primary_interval[0], 1.0))
        self.assertGreater(max(d.mathematical_value for d in result.draws), 1)
        self.assert_raw_preserved(old, result, {'primary_interval'})

    def test_regular_interior_report_is_identical_on_original_fields(self):
        histories = mixture()
        old = frozen.operating_uncertainty_report(histories, 3, n_boot=200, seed=73,
                                                  disagreement_threshold=.05)
        result = guarded.operating_uncertainty_report(histories, 3, n_boot=200, seed=73,
                                                       disagreement_threshold=.05)
        self.assert_raw_preserved(old.primary, result.primary, set())
        self.assert_raw_preserved(old.analytic, result.analytic, set())
        self.assertFalse(result.primary.numerically_degenerate_distribution)
        for key in ('comparison_status', 'material_disagreement', 'endpoint_max_absolute_difference'):
            self.assertEqual(getattr(old, key), getattr(result, key))

    def test_mixed_initial_terminal_mass_without_transitions_stays_informative(self):
        histories = [H('a1', 'A', S.PRE, 5), H('a2', 'A', S.PRE, 5), H('b1', 'B', S.CLOSURE, 5)]
        result = guarded.operating_cluster_bootstrap(histories, 3, 40, 3)
        self.assertTrue(result.zero_terminal_transitions)
        self.assertFalse(result.numerically_degenerate_distribution)
        self.assertIsNotNone(result.primary_interval)
        self.assertEqual({len(d.source_round_ids) for d in result.draws}, {2, 3, 4})

    def test_exact_degenerate_status_stays_distinct(self):
        histories = [H('a', 'A', S.PRE, 5), H('b', 'B', S.PRE, 5)]
        result = guarded.operating_cluster_bootstrap(histories, 3, 20, 0)
        self.assertTrue(result.degenerate_distribution)
        self.assertTrue(result.numerically_degenerate_distribution)
        self.assertEqual(result.interval_status, 'WITHHELD_DEGENERATE_BOOTSTRAP_DISTRIBUTION')

    def test_complete_terminal_absorption_withheld_at_zero(self):
        histories = [H('a', 'A', S.PRE, 5, (T(1, S.PRE, S.CLOSURE),)),
                     H('b', 'B', S.SUCCESS_EXIT, 5)]
        result = guarded.operating_uncertainty_report(histories, 3, n_boot=30,
                                                       disagreement_threshold=.05)
        self.assertEqual(result.primary.point, 0)
        self.assertEqual(result.primary.full_sample_support_status, 'COMPLETE_MODELED_ABSORPTION')
        self.assertIsNone(result.primary.primary_interval)
        self.assertIsNone(result.analytic.normal_diagnostic_interval)

    def test_not_run_stays_null_not_numerical_degeneracy(self):
        for histories, count in ((mixture(), 0), ([H('a', 'A', S.PRE, 4)], 20)):
            with self.subTest(count=count):
                result = guarded.operating_cluster_bootstrap(histories, 2, count)
                self.assertIsNone(result.numerically_degenerate_distribution)
                self.assertIsNone(result.undefined_draw_count)
                self.assertIsNone(result.unsupported_draw_count)
                self.assertEqual(result.draws, ())
                self.assertIsNone(result.primary_interval)

    def test_single_draw_keeps_fewer_replicates_precedence(self):
        result = guarded.operating_cluster_bootstrap(mixture(), 3, 1, 8)
        self.assertTrue(result.numerically_degenerate_distribution)
        self.assertEqual(result.interval_status, 'WITHHELD_FEWER_THAN_TWO_REPLICATES')

    def test_full_sample_unsupported_precedes_degeneracy(self):
        histories = [H('a', 'A', S.PRE, 1), H('b', 'B', S.PRE, 1)]
        result = guarded.operating_cluster_bootstrap(histories, 3, 20)
        self.assertTrue(result.numerically_degenerate_distribution)
        self.assertEqual(result.interval_status, 'WITHHELD_FULL_SAMPLE_STATE_RISK_GAP')

    def test_unsupported_draws_remain_unfiltered(self):
        histories = [H('a', 'A', S.PRE, 1, (T(1, S.PRE, S.CLOSURE),)),
                     H('b', 'B', S.PRE, 2), H('c', 'C', S.PRE, 4)]
        old = frozen.operating_cluster_bootstrap(histories, 3, 100, 11)
        result = guarded.operating_cluster_bootstrap(histories, 3, 100, 11)
        self.assert_raw_preserved(old, result, set())
        self.assertGreater(result.unsupported_draw_count, 0)
        self.assertEqual(result.interval_status, 'WITHHELD_UNSUPPORTED_BOOTSTRAP_DRAWS')

    def test_undefined_draw_keeps_all_draws_and_unknown_degeneracy(self):
        original = frozen.at_horizon
        calls = 0
        def interrupted(histories, horizon):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise ValueError('synthetic_undefined')
            return original(histories, horizon)
        with patch.object(frozen, 'at_horizon', interrupted):
            result = guarded.operating_cluster_bootstrap(mixture(), 3, 20)
        self.assertEqual(len(result.draws), 20)
        self.assertEqual(result.undefined_draw_count, 1)
        self.assertIsNone(result.numerically_degenerate_distribution)
        self.assertEqual(result.interval_status, 'WITHHELD_UNDEFINED_BOOTSTRAP_DRAWS')

    def test_materially_invalid_point_is_rejected_never_clipped(self):
        real = frozen.operating_cluster_bootstrap(mixture(), 3, 10)
        landmark = frozen.at_horizon(mixture(), 3)
        for bad in (-.01, 1.01, float('nan'), float('inf')):
            with self.subTest(bad=bad), patch.object(guarded, '_frozen_bootstrap', return_value=replace(real, point=bad)):
                with self.assertRaisesRegex(ValueError, 'operating_point_outside_roundoff_probability_bounds'):
                    guarded.operating_cluster_bootstrap(mixture(), 3, 10)
            with self.subTest(analytic_bad=bad), patch.object(guarded, 'at_horizon',
                    return_value=replace(landmark, independent_operating_probability=bad)):
                with self.assertRaisesRegex(ValueError, 'operating_point_outside_roundoff_probability_bounds'):
                    guarded.aj_ij_diagnostic(mixture(), 3)

    def test_materially_invalid_draw_is_rejected_never_clipped(self):
        real = frozen.operating_cluster_bootstrap(mixture(), 3, 10)
        for bad in (-.01, 1.01, float('nan'), float('inf')):
            bad_draw = replace(real.draws[0], mathematical_value=bad)
            bad_report = replace(real, draws=(bad_draw,) + real.draws[1:])
            with self.subTest(bad=bad), patch.object(guarded, '_frozen_bootstrap', return_value=bad_report):
                with self.assertRaisesRegex(ValueError, 'operating_bootstrap_draw_outside_roundoff_probability_bounds'):
                    guarded.operating_cluster_bootstrap(mixture(), 3, 10)

    def test_invalid_configuration_rejected(self):
        for count in (-1, True, 1.1):
            with self.assertRaises(ValueError): guarded.operating_cluster_bootstrap(mixture(), 3, count)
        for seed in (True, '1', 1.1):
            with self.assertRaises(ValueError): guarded.operating_cluster_bootstrap(mixture(), 3, 10, seed)
        for confidence in (0, 1, True, float('nan')):
            with self.assertRaises(ValueError): guarded.aj_ij_diagnostic(mixture(), 3, confidence)
        with self.assertRaises(ValueError):
            guarded.operating_uncertainty_report(mixture(), 3, disagreement_threshold=-.1)

    def test_extreme_confidence_level_preserved(self):
        level = math.nextafter(1, 0)
        result = guarded.operating_uncertainty_report(mixture(), 3, n_boot=40,
            confidence_level=level, disagreement_threshold=.05)
        self.assertEqual(result.analytic.normal_diagnostic_interval, (0, 1))
        self.assertEqual(result.primary.confidence_level, level)

    def test_input_order_invariance_and_no_mutation(self):
        histories = balanced_companies()
        before = list(histories)
        a = guarded.operating_uncertainty_report(histories, 5, n_boot=40, seed=3, disagreement_threshold=.05)
        b = guarded.operating_uncertainty_report(list(reversed(histories)), 5, n_boot=40, seed=3, disagreement_threshold=.05)
        self.assertEqual(histories, before)
        self.assertEqual(a.primary.primary_interval, b.primary.primary_interval)
        self.assertEqual(a.analytic, b.analytic)
        self.assertEqual([d.sampled_company_ids for d in a.primary.draws],
                         [d.sampled_company_ids for d in b.primary.draws])

    def test_constant_operating_sweep_exact_reference(self):
        for size in range(2, 25):
            for make, expected in ((all_operating, Fraction(1)), (balanced_companies, Fraction(1, 2))):
                with self.subTest(size=size, expected=expected):
                    histories = make(size)
                    self.assertEqual(weighted_occupancy(histories, size)[1], expected)
                    result = guarded.operating_uncertainty_report(histories, size,
                        n_boot=40, seed=73, disagreement_threshold=.05)
                    self.assertTrue(result.primary.numerically_degenerate_distribution)
                    self.assertIsNone(result.primary.primary_interval)
                    self.assertIsNone(result.analytic.normal_diagnostic_interval)

    def test_randomized_exact_rational_values_and_independent_company_draws(self):
        rng = random.Random(12102026)
        case_count = draw_count = 0
        for trial in range(30):
            histories = []
            for i in range(rng.randint(3, 8)):
                initial = rng.choice(list(S))
                state = initial
                end = rng.randint(0, 6)
                transitions = []
                for time in range(end + 1):
                    if state in (S.PRE, S.POST) and rng.random() < .3:
                        destination = rng.choice([S.SUCCESS_EXIT, S.ACQUISITION_UNKNOWN, S.CLOSURE]
                                                 + ([S.POST] if state == S.PRE else []))
                        transitions.append(T(time, state, destination))
                        state = destination
                histories.append(H(str(i), str(i // 2), initial, end, tuple(transitions)))
            for horizon in (0, 2, 7):
                result = guarded.operating_uncertainty_report(histories, horizon,
                    n_boot=12, seed=trial, disagreement_threshold=.05)
                exact, operating = weighted_occupancy(histories, horizon)
                self.assertAlmostEqual(result.primary.point, float(operating), places=13)
                for state, value in exact.items():
                    self.assertAlmostEqual(result.analytic.mathematical_probabilities[state], float(value), places=13)
                raw_a = frozen_ij.aj_ij_diagnostic(histories, horizon)
                self.assert_raw_preserved(raw_a, result.analytic, {'normal_diagnostic_interval', 'interval_status'})
                companies = sorted({h.company_id for h in histories})
                sampler = random.Random(trial)
                for draw in result.primary.draws:
                    selected = tuple(sampler.choice(companies) for _ in companies)
                    rows = [h for company in selected for h in histories if h.company_id == company]
                    self.assertEqual(draw.sampled_company_ids, selected)
                    self.assertEqual(draw.source_round_ids, tuple(h.round_id for h in rows))
                    self.assertAlmostEqual(draw.mathematical_value,
                                           float(weighted_occupancy(rows, horizon)[1]), places=13)
                    draw_count += 1
                for interval in (result.primary.primary_interval, result.analytic.normal_diagnostic_interval):
                    if interval is not None:
                        self.assertLessEqual(0, interval[0])
                        self.assertLessEqual(interval[0], interval[1])
                        self.assertLessEqual(interval[1], 1)
                case_count += 1
        print(f'Independent synthetic exact-rational cases: {case_count}; reconstructed company draws: {draw_count}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
