"""CP6 compatibility regression: no legacy call can claim research plateau."""
import unittest
from src.phase1d.plateau_verifier import compare_snapshots, main, safe_round_id


class Phase1DPlateauVerifierTests(unittest.TestCase):
    def test_legacy_empty_snapshot_does_not_authorize_plateau(self):
        result = compare_snapshots({}, {})
        self.assertFalse(result["plateau"])
        self.assertFalse(result["research_plateau"])

    def test_legacy_cli_cannot_overwrite_prior_snapshots(self):
        with self.assertRaises(SystemExit):
            main()

    def test_safe_identifier(self):
        self.assertEqual(safe_round_id("cp6-audit_1"), "cp6-audit_1")

    def test_path_traversal_rejected(self):
        for value in ["../a", "/a", "", "a" * 81]:
            with self.assertRaises(ValueError):
                safe_round_id(value)


if __name__ == "__main__":
    unittest.main()
