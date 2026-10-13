import unittest

from src.phase1d.estimate_republic_europe_candidate_v3 import (
    first_event_observation,
    grouped_bootstrap_indices,
    is_ascertained,
    km_survival,
    supported,
    terminal_date,
    zero_event_survival_lower,
    zero_event_upper,
)


def row(**overrides):
    base = {
        "round_id": "r1",
        "canonical_company_id": "c1",
        "completion_date": "2020-01-01",
        "success_date": "",
        "closure_date": "",
        "terminal_event_midpoint_for_primary": "",
        "terminal_event_interval_start": "",
        "terminal_event_interval_end": "",
        "followup_months": "36",
    }
    base.update(overrides)
    return base


class RepublicEuropeEstimateV3Tests(unittest.TestCase):
    def test_success_before_later_terminal_is_first_success(self):
        obs = first_event_observation(row(success_date="2021-01-01", terminal_event_midpoint_for_primary="2022-01-01"), "success")
        self.assertEqual(obs.cause, "success")
        self.assertLess(obs.time, 24)

    def test_terminal_before_success_competes(self):
        obs = first_event_observation(row(success_date="2022-01-01", terminal_event_midpoint_for_primary="2021-01-01"), "success")
        self.assertEqual(obs.cause, "terminal_other")

    def test_nonterminal_success_does_not_end_closure_followup(self):
        obs = first_event_observation(row(success_date="2021-01-01", followup_months="48"), "closure")
        self.assertIsNone(obs.cause)
        self.assertEqual(obs.time, 48.0)

    def test_closure_is_typed_closure_event(self):
        obs = first_event_observation(row(closure_date="2021-01-01"), "closure")
        self.assertEqual(obs.cause, "closure")

    def test_terminal_date_uses_primary_midpoint(self):
        self.assertEqual(terminal_date(row(terminal_event_midpoint_for_primary="2021-06-01", terminal_event_interval_start="2021-01-01", terminal_event_interval_end="2021-12-01")), "2021-06-01")

    def test_km_survival_decreases_only_on_terminal_event(self):
        rows = [
            row(round_id="r1", canonical_company_id="a", terminal_event_midpoint_for_primary="2021-01-01", followup_months="12"),
            row(round_id="r2", canonical_company_id="b", followup_months="36"),
        ]
        self.assertAlmostEqual(km_survival(rows, 24), 0.5)

    def test_supported_includes_event_before_horizon(self):
        event = first_event_observation(row(success_date="2020-06-01", followup_months="6"), "success")
        self.assertTrue(supported(event, 12))
        censored = first_event_observation(row(followup_months="6"), "success")
        self.assertFalse(supported(censored, 12))

    def test_cluster_bootstrap_preserves_repeat_rounds(self):
        rows = [row(round_id="a1", canonical_company_id="a"), row(round_id="a2", canonical_company_id="a"), row(round_id="b1", canonical_company_id="b")]
        for indices in grouped_bootstrap_indices(rows, 20, 7):
            self.assertEqual(indices.count(0), indices.count(1))

    def test_zero_event_support_bounds(self):
        upper = zero_event_upper(100)
        lower = zero_event_survival_lower(100)
        self.assertAlmostEqual(upper + lower, 1.0)
        self.assertIsNone(zero_event_upper(0))

    def test_ascertainment_requires_followup_or_event(self):
        self.assertFalse(is_ascertained(row(followup_months="0")))
        self.assertTrue(is_ascertained(row(followup_months="1")))
        self.assertTrue(is_ascertained(row(followup_months="0", success_date="2020-01-01")))


if __name__ == "__main__":
    unittest.main()
