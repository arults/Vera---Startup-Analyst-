import json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class TestReferenceClassRegistry(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((ROOT/"reference_classes/wefunder_2020_operating_survival.json").read_text())
        self.summary=json.loads((ROOT/"data/survival_sensitivity_summary.json").read_text())
        self.verifier=json.loads((ROOT/"evidence/verifier/CP3_full_verifier.json").read_text())

    def test_promoted_version_and_scope(self):
        self.assertEqual(self.registry["vera_version"],"0.4.0")
        self.assertEqual(self.registry["status"],"PROMOTED_LIMITED_REFERENCE_CLASS")
        self.assertEqual(self.registry["promoted_horizon"]["years"],5)
        self.assertFalse(self.registry["applicability"]["direct_substitution_for_company_success_probability"])

    def test_five_year_values_match_frozen_outputs(self):
        p=self.registry["promoted_horizon"]["primary"]
        s=self.summary["primary_5y"]
        self.assertAlmostEqual(p["kaplan_meier_survival"],s["survival"],places=12)
        self.assertAlmostEqual(p["ci95_lower"],s["ci95_lower"],places=12)
        self.assertAlmostEqual(p["ci95_upper"],s["ci95_upper"],places=12)
        self.assertEqual(p["at_risk"],s["at_risk"])

    def test_late_bound_values_match_frozen_outputs(self):
        p=self.registry["promoted_horizon"]["late_bound_sensitivity"]
        s=self.summary["late_bound_5y"]
        self.assertAlmostEqual(p["kaplan_meier_survival"],s["survival"],places=12)
        self.assertEqual(p["at_risk"],s["at_risk"])

    def test_input_hashes_match_verifier(self):
        prov=self.registry["provenance"]
        self.assertEqual(prov["manifest_sha256"],self.verifier["inputs"]["manifest_sha256"])
        self.assertEqual(prov["outcomes_sha256"],self.verifier["inputs"]["outcomes_sha256"])
        self.assertEqual(self.verifier["promotion_gate"],"PASS")

    def test_six_year_not_promoted(self):
        self.assertIn("six_year_reason",self.registry["not_promoted"])
        self.assertNotIn("six_year",self.registry["promoted_horizon"])
        self.assertLess(self.registry["not_promoted"]["six_year_jev_yes_probability"],0.5)

if __name__=="__main__":
    unittest.main()
