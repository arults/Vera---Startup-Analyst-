import unittest

from src.phase1d.plateau_verifier import compare_snapshots


def state(value=0.5, label="stable", digest="a"):
    return {
        "dimensions": {"x": value, "y": 0.2},
        "labels": {"status": label},
        "source_hashes": {"artifact": digest},
    }


class Phase1DPlateauVerifierTests(unittest.TestCase):
    def test_identical_state_is_plateau(self):
        result = compare_snapshots(state(), state())
        self.assertTrue(result["plateau"])
        self.assertEqual(result["improvements_over_threshold"], [])

    def test_exactly_point_zero_five_improvement_is_plateau(self):
        result = compare_snapshots(state(0.5), state(0.55))
        self.assertTrue(result["plateau"])

    def test_improvement_above_threshold_breaks_plateau(self):
        result = compare_snapshots(state(0.5), state(0.551))
        self.assertFalse(result["plateau"])
        self.assertEqual(result["improvements_over_threshold"], ["x"])

    def test_score_decrease_does_not_break_plateau(self):
        result = compare_snapshots(state(0.5), state(0.4))
        self.assertTrue(result["plateau"])

    def test_material_label_flip_breaks_plateau(self):
        result = compare_snapshots(state(label="a"), state(label="b"))
        self.assertFalse(result["plateau"])
        self.assertIn("status", result["material_label_flips"])

    def test_source_hash_change_breaks_plateau(self):
        result = compare_snapshots(state(digest="a"), state(digest="b"))
        self.assertFalse(result["plateau"])
        self.assertIn("artifact", result["source_hash_changes"])

    def test_missing_dimension_breaks_plateau(self):
        before = state()
        after = state()
        del after["dimensions"]["y"]
        result = compare_snapshots(before, after)
        self.assertFalse(result["plateau"])
        self.assertEqual(result["missing_dimensions"], ["y"])


if __name__ == "__main__":
    unittest.main()
