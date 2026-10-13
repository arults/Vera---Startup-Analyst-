"""Landmark support regressions using real modules and synthetic records only.

Run from the repository root:
    python -m unittest discover -s tests -p test_reporting_horizon_support.py

An early observed event supports that subject, but must not extend an unresolved
censored tail indefinitely. Complete modeled first-event absorption is the
exception: no remaining modeled event-free mass needs extrapolation. This does
not identify the real outcome of a censored subject or validate source evidence.
"""
import copy
import unittest

from src.phase1c.estimators import CompetingRiskObservation
from src.phase1d import estimate_republic_europe_candidate_v3 as reporting


def observation(subject, time, cause=None):
    return CompetingRiskObservation(subject, subject, time, cause)


def synthetic_row(subject, end, closure="", success=""):
    start = "2020-01-01"
    return dict(
        round_id=subject, canonical_company_id=f"company-{subject}",
        platform="republic_europe", offering_year="2020",
        offering_year_status="BOUNDED_YEAR", primary_field="saas_enterprise_software",
        completion_date=start, censor_date=end,
        followup_months=str(reporting.months(start, end)),
        success_date=success, closure_date=closure,
        terminal_event_interval_start="", terminal_event_interval_end="",
        terminal_event_midpoint_for_primary="",
    )


def selected_cell(rows, horizon=60):
    return next(cell for cell in reporting.rq1_rows(rows)
                if cell["offering_year"] == 2020 and cell["horizon_months"] == horizon)


class TestReportingHorizonSupport(unittest.TestCase):
    def test_early_event_does_not_support_unresolved_tail(self):
        rows = [synthetic_row("a", "2020-02-01", closure="2020-02-01"),
                synthetic_row("b", "2020-03-01")]
        original = copy.deepcopy(rows)
        cell = selected_cell(rows)
        # Keep the informative early event and visible cell, but suppress points.
        self.assertEqual(cell["n_rounds"], 2)
        self.assertEqual(cell["n_supported_to_horizon"], 1)
        self.assertEqual(cell["closure_events_observed"], 1)
        self.assertEqual(cell["estimable"], "false")
        self.assertEqual(cell["promotion_status"], "CANDIDATE_ONLY")
        for field in ("success_cif", "closure_cif", "operating_survival",
                      "success_ci_lower", "success_ci_upper", "closure_ci_lower",
                      "closure_ci_upper", "survival_ci_lower", "survival_ci_upper",
                      "operating_survival_terminal_start", "operating_survival_terminal_end"):
            with self.subTest(field=field):
                self.assertEqual(cell[field], "")
        self.assertEqual(rows, original)

    def test_all_terminal_absorbing_tail_remains_estimable(self):
        rows = [synthetic_row("a", "2020-02-01", closure="2020-02-01"),
                synthetic_row("b", "2020-03-01", closure="2020-03-01")]
        cell = selected_cell(rows)
        self.assertEqual(cell["estimable"], "true")
        self.assertEqual(cell["operating_survival"], "0")
        self.assertEqual(cell["closure_cif"], "1")

    def test_censor_then_complete_modeled_absorption_is_not_rejected(self):
        rows = [synthetic_row("a", "2020-02-01"),
                synthetic_row("b", "2020-03-01", closure="2020-03-01")]
        cell = selected_cell(rows)
        self.assertEqual(cell["estimable"], "true")
        self.assertEqual(cell["operating_survival"], "0")
        # This is modeled absorption, not proof of a's unobserved actual outcome.

    def test_no_events_without_horizon_support_suppress(self):
        cell = selected_cell([synthetic_row("a", "2020-02-01"),
                              synthetic_row("b", "2020-03-01")])
        self.assertEqual(cell["estimable"], "false")
        self.assertEqual(cell["operating_survival"], "")

    def test_observed_support_with_no_events_retains_point(self):
        cell = selected_cell([synthetic_row("a", "2021-02-01")], horizon=12)
        self.assertEqual(cell["estimable"], "true")
        self.assertEqual(cell["operating_survival"], "1")

    def test_success_absorption_alone_does_not_support_other_estimands(self):
        # Success is nonterminal for independent operation. A first-success CIF
        # can have complete absorption while closure/survival still lack support.
        rows = [synthetic_row("a", "2020-03-01", success="2020-02-01"),
                synthetic_row("b", "2020-03-01", success="2020-02-01")]
        cell = selected_cell(rows)
        self.assertEqual(cell["estimable"], "false")
        self.assertEqual(cell["success_cif"], "")
        self.assertEqual(cell["operating_survival"], "")

    def test_helper_exact_horizon_support(self):
        observations = [observation("a", 1, "terminal"), observation("b", 12)]
        self.assertTrue(reporting.landmark_supported(observations, 12))
        self.assertFalse(reporting.landmark_supported(observations, 60))

    def test_helper_distinguishes_competing_absorption_from_residual_mass(self):
        self.assertTrue(reporting.landmark_supported(
            [observation("a", 1, "success"), observation("b", 2, "closure")], 60))
        self.assertFalse(reporting.landmark_supported(
            [observation("a", 1, "success"), observation("b", 2)], 60))

    def test_helper_empty_and_no_event_cases(self):
        self.assertFalse(reporting.landmark_supported([], 12))
        self.assertFalse(reporting.landmark_supported([observation("a", 2)], 12))
        self.assertTrue(reporting.landmark_supported([observation("a", 12)], 12))

    def test_original_reporting_grid_and_inputs_remain_visible(self):
        rows = [synthetic_row("a", "2020-03-01")]
        original = copy.deepcopy(rows)
        cells = reporting.rq1_rows(rows)
        self.assertEqual(len(cells), 24)
        self.assertEqual(sum(cell["offering_year"] == 2020 for cell in cells), 4)
        self.assertTrue(all(cell["promotion_status"] == "CANDIDATE_ONLY" for cell in cells))
        self.assertEqual(rows, original)


if __name__ == "__main__":
    unittest.main()
