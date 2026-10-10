"""Synthetic scenario-specific landmark support; real repository imports.

Run from repo root:
    python -m unittest discover -s tests -p test_reporting_scenario_support.py

Primary support is not scenario support. A scenario shifts only its declared
terminal endpoint; it cannot borrow the primary midpoint as a censor cap or as
proof of follow-up. Complete modeled absorption remains a legitimate exception.
"""
import copy
import unittest

from src.phase1d import estimate_republic_europe_candidate_v3 as reporting


START_STATUS = "operating_survival_terminal_start_status"
END_STATUS = "operating_survival_terminal_end_status"


def row(subject, end, closure="", interval=None):
    result = dict(round_id=subject, canonical_company_id=subject,
                  platform="republic_europe", offering_year="2020",
                  offering_year_status="BOUNDED_YEAR", primary_field="saas_enterprise_software",
                  completion_date="2020-01-01", censor_date=end,
                  followup_months=str(reporting.months("2020-01-01", end)),
                  success_date="", closure_date=closure,
                  terminal_event_interval_start="", terminal_event_interval_end="",
                  terminal_event_midpoint_for_primary="")
    if interval:
        result.update(terminal_event_interval_start=interval[0],
                      terminal_event_midpoint_for_primary=interval[1],
                      terminal_event_interval_end=interval[2])
    return result


def source_fixture():
    return [row("A", "2021-07-02", interval=("2020-02-01", "2021-07-02", "2022-12-01")),
            row("B", "2020-03-01")]


def cell(rows, horizon=12):
    return next(r for r in reporting.rq1_rows(rows)
                if r["offering_year"] == 2020 and r["horizon_months"] == horizon)


class TestReportingScenarioSupport(unittest.TestCase):
    def test_unsupported_start_blanked_without_suppressing_primary_or_end(self):
        rows = source_fixture()
        original = copy.deepcopy(rows)
        result = cell(rows)
        self.assertEqual(result["estimable"], "true")
        self.assertEqual(result["operating_survival"], "1")
        self.assertEqual(result["operating_survival_terminal_start"], "")
        self.assertEqual(result[START_STATUS], "UNSUPPORTED_HORIZON")
        self.assertEqual(result["operating_survival_terminal_end"], "1")
        self.assertEqual(result[END_STATUS], "SUPPORTED")
        self.assertEqual(rows, original)

    def test_all_terminal_scenario_absorption_remains_supported(self):
        rows = [row("A", "2021-07-02", interval=("2020-02-01", "2021-07-02", "2022-12-01"))]
        result = cell(rows)
        self.assertEqual(result["operating_survival_terminal_start"], "0")
        self.assertEqual(result[START_STATUS], "SUPPORTED")
        self.assertEqual(result["operating_survival_terminal_end"], "1")
        self.assertEqual(result[END_STATUS], "SUPPORTED")

    def test_censor_then_scenario_absorption_remains_supported(self):
        rows = source_fixture()
        rows[1] = row("B", "2020-01-15")
        result = cell(rows)
        self.assertEqual(result["operating_survival_terminal_start"], "0")
        self.assertEqual(result[START_STATUS], "SUPPORTED")

    def test_primary_unestimable_does_not_claim_scenarios_were_evaluated(self):
        result = cell([row("A", "2020-02-01"), row("B", "2020-03-01")])
        self.assertEqual(result["estimable"], "false")
        for value, status in [("operating_survival_terminal_start", START_STATUS),
                              ("operating_survival_terminal_end", END_STATUS)]:
            self.assertEqual(result[value], "")
            self.assertEqual(result[status], "NOT_EVALUATED_PRIMARY_UNESTIMABLE")

    def test_exact_horizon_and_later_horizon_use_scenario_own_risk_history(self):
        rows = [row("A", "2020-02-01", closure="2020-02-01"), row("B", "2021-01-01")]
        exact = reporting.months("2020-01-01", "2021-01-01")
        for mode in ["start", "end"]:
            self.assertEqual(reporting.supported_survival_scenario(rows, exact, mode), (0.5, "SUPPORTED"))
            self.assertEqual(reporting.supported_survival_scenario(rows, exact + 1, mode),
                             (None, "UNSUPPORTED_HORIZON"))

    def test_supported_no_terminal_scenarios_are_unchanged(self):
        result = cell([row("A", "2022-01-01")])
        for value, status in [("operating_survival_terminal_start", START_STATUS),
                              ("operating_survival_terminal_end", END_STATUS)]:
            self.assertEqual(result[value], "1")
            self.assertEqual(result[status], "SUPPORTED")

    def test_empty_and_invalid_scenario_mode(self):
        self.assertEqual(reporting.supported_survival_scenario([], 12, "start"),
                         (None, "UNSUPPORTED_HORIZON"))
        with self.assertRaises(ValueError):
            reporting.supported_survival_scenario([], 12, "mid")


if __name__ == "__main__":
    unittest.main()
