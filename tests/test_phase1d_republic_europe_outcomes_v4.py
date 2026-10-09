import unittest

from src.phase1d.rebuild_republic_europe_outcomes_v4 import (
    latest_positive_observations,
    migrate_row,
    months_between,
    terminal_date,
)


class RepublicEuropeOutcomeV4Tests(unittest.TestCase):
    def test_latest_positive_observation_wins(self):
        rows = [
            {"canonical_company_id": "c", "positive_operating_evidence": "true", "captured_at": "2025-01-01T00:00:00+00:00", "business_url": "a"},
            {"canonical_company_id": "c", "positive_operating_evidence": "true", "captured_at": "2026-01-01T00:00:00+00:00", "business_url": "b"},
            {"canonical_company_id": "c", "positive_operating_evidence": "false", "captured_at": "2027-01-01T00:00:00+00:00", "business_url": "x"},
        ]
        self.assertEqual(latest_positive_observations(rows)["c"]["date"], "2026-01-01")

    def test_nonterminal_row_is_extended_by_positive_evidence(self):
        row = {
            "round_id": "r", "canonical_company_id": "old", "campaign_name": "X", "platform": "republic_europe",
            "offering_year": "2020", "offering_year_status": "BOUNDED_YEAR", "primary_field": "saas_enterprise_software",
            "completion_date": "2020-01-01", "last_positive_date": "2021-01-01", "censor_date": "2021-01-01",
            "current_eligible_evidence": "false", "evidence_trace": "index_completion:2020-01-01",
            "closure_date": "", "terminal_event_midpoint_for_primary": "", "terminal_event_interval_end": "", "terminal_event_interval_start": "",
        }
        auth = {"canonical_company_id": "new", "campaign_name": "X", "platform": "republic_europe", "offering_year": "2020", "offering_year_status": "BOUNDED_YEAR", "primary_field": "saas_enterprise_software", "completion_date": "2020-01-01"}
        out, changed, extended = migrate_row(row, auth, {"new": {"date": "2026-10-09", "url": "u", "basis": "review"}})
        self.assertTrue(changed)
        self.assertTrue(extended)
        self.assertEqual(out["censor_date"], "2026-10-09")
        self.assertEqual(out["current_eligible_evidence"], "true")
        self.assertIn("secondary_market_current_eligible:2026-10-09:u", out["evidence_trace"])

    def test_terminal_row_is_never_reopened(self):
        row = {
            "round_id": "r", "canonical_company_id": "old", "completion_date": "2020-01-01",
            "last_positive_date": "2022-01-01", "censor_date": "2022-01-01", "current_eligible_evidence": "false",
            "evidence_trace": "x", "closure_date": "", "terminal_event_midpoint_for_primary": "2022-01-01",
            "terminal_event_interval_end": "2022-02-01", "terminal_event_interval_start": "2021-12-01",
        }
        auth = {"canonical_company_id": "new", "campaign_name": "X", "platform": "republic_europe", "offering_year": "2020", "offering_year_status": "BOUNDED_YEAR", "primary_field": "saas_enterprise_software", "completion_date": "2020-01-01"}
        out, _, extended = migrate_row(row, auth, {"new": {"date": "2026-10-09", "url": "u", "basis": "review"}})
        self.assertFalse(extended)
        self.assertEqual(out["censor_date"], "2022-01-01")
        self.assertEqual(out["current_eligible_evidence"], "false")

    def test_not_eligible_observations_are_excluded(self):
        rows = [{"canonical_company_id": "c", "positive_operating_evidence": "false", "captured_at": "2026-01-01", "business_url": "u"}]
        self.assertEqual(latest_positive_observations(rows), {})

    def test_terminal_date_precedence(self):
        row = {"closure_date": "2020-01-01", "terminal_event_midpoint_for_primary": "2021-01-01", "terminal_event_interval_end": "2022-01-01", "terminal_event_interval_start": "2019-01-01"}
        self.assertEqual(terminal_date(row), "2020-01-01")

    def test_followup_months_is_nonnegative_for_valid_dates(self):
        self.assertEqual(months_between("2020-01-01", "2020-01-01"), "0.000")
        self.assertGreater(float(months_between("2020-01-01", "2021-01-01")), 11.9)


if __name__ == "__main__":
    unittest.main()
