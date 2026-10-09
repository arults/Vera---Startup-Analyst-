import unittest

from src.phase1d.verifier_v3_repaired import republic_us_suppression_evidence


class RepublicUSSuppressionGateRepairTests(unittest.TestCase):
    def fixtures(self):
        coverage = {"status": "CENSUS_INCOMPLETE", "structured_search_unique": 108}
        probe = {
            "candidate_link_count": 400,
            "json_summaries": [
                {"status": 200, "type": "dict"},
                {"status": 200, "type": "list", "length": 144},
            ],
        }
        recovery = {
            "census_status": "CENSUS_INCOMPLETE",
            "candidate_count": 0,
            "rates_promoted": False,
            "integrity_gates": {"passed": 12, "total": 12},
        }
        return coverage, probe, recovery

    def test_complete_suppression_evidence_passes(self):
        passed, detail = republic_us_suppression_evidence(*self.fixtures())
        self.assertTrue(passed)
        self.assertEqual(detail["largest_public_archive_list"], 144)
        self.assertFalse(detail["recovery_rates_promoted"])

    def test_partial_archive_is_never_treated_as_rate_denominator(self):
        coverage, probe, recovery = self.fixtures()
        recovery["rates_promoted"] = True
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery)
        self.assertFalse(passed)

    def test_integrity_failure_blocks_gate(self):
        coverage, probe, recovery = self.fixtures()
        recovery["integrity_gates"] = {"passed": 11, "total": 12}
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery)
        self.assertFalse(passed)

    def test_missing_native_recovery_blocks_gate(self):
        coverage, probe, _ = self.fixtures()
        passed, _ = republic_us_suppression_evidence(coverage, probe, None)
        self.assertFalse(passed)

    def test_wrong_archive_size_blocks_expected_checkpoint(self):
        coverage, probe, recovery = self.fixtures()
        probe["json_summaries"][1]["length"] = 143
        passed, _ = republic_us_suppression_evidence(coverage, probe, recovery)
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
