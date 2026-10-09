import unittest

from src.phase1d.verifier_v3_repaired import republic_us_suppression_evidence


class RepublicUSSuppressionGateRepairTests(unittest.TestCase):
    def fixtures(self):
        coverage = {"status": "CENSUS_INCOMPLETE", "structured_search_unique": 108}
        probe = {"candidate_link_count": 400}
        recovery = {
            "census_status": "CENSUS_INCOMPLETE",
            "candidate_count": 0,
            "rates_promoted": False,
            "integrity_gates": {"passed": 12, "total": 12},
        }
        archive = {
            "candidate_rows": 144,
            "source_rows": 144,
            "census_status": "CENSUS_INCOMPLETE",
            "cohort_year_resolved": 0,
            "estimation_eligible": 0,
            "strong_company_ids": 0,
            "rates_promoted": False,
            "gates": {"passed": 15, "total": 15},
        }
        return coverage, probe, recovery, archive

    def test_complete_suppression_evidence_passes(self):
        passed, detail = republic_us_suppression_evidence(*self.fixtures())
        self.assertTrue(passed)
        self.assertEqual(detail["archive_candidate_rows"], 144)
        self.assertEqual(detail["archive_cohort_year_resolved"], 0)
        self.assertFalse(detail["recovery_rates_promoted"])

    def test_partial_archive_is_never_treated_as_rate_denominator(self):
        coverage, probe, recovery, archive = self.fixtures()
        archive["rates_promoted"] = True
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery, archive)
        self.assertFalse(passed)

    def test_archive_requires_zero_estimation_eligible_rows(self):
        coverage, probe, recovery, archive = self.fixtures()
        archive["estimation_eligible"] = 1
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery, archive)
        self.assertFalse(passed)

    def test_archive_integrity_failure_blocks_gate(self):
        coverage, probe, recovery, archive = self.fixtures()
        archive["gates"] = {"passed": 14, "total": 15}
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery, archive)
        self.assertFalse(passed)

    def test_native_recovery_integrity_failure_blocks_gate(self):
        coverage, probe, recovery, archive = self.fixtures()
        recovery["integrity_gates"] = {"passed": 11, "total": 12}
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery, archive)
        self.assertFalse(passed)

    def test_missing_native_recovery_blocks_gate(self):
        coverage, probe, _, archive = self.fixtures()
        passed, _ = republic_us_suppression_evidence(coverage, probe, None, archive)
        self.assertFalse(passed)

    def test_missing_archive_blocks_gate(self):
        coverage, probe, recovery, _ = self.fixtures()
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery, None)
        self.assertFalse(passed)

    def test_wrong_archive_size_blocks_expected_checkpoint(self):
        coverage, probe, recovery, archive = self.fixtures()
        archive["candidate_rows"] = 143
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery, archive)
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
