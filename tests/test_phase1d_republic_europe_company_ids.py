import unittest

from src.phase1d.build_republic_europe_cohort import (
    canonical_company_number,
    collision_plan,
    company_id,
)


class RepublicEuropeCompanyIdTests(unittest.TestCase):
    def test_leading_zero_numeric_ids_compare_equal(self):
        self.assertEqual(canonical_company_number("08007191"), "8007191")
        self.assertEqual(canonical_company_number("8007191"), "8007191")

    def test_unicode_soft_hyphen_and_punctuation_compare_equal(self):
        self.assertEqual(canonical_company_number("CHE-152.681.235"), "CHE152681235")
        self.assertEqual(canonical_company_number("CHE\u00ad152.681.235"), "CHE152681235")

    def test_raw_id_is_preserved_outside_canonical_key(self):
        cid, key, status = company_id("09464530", "Family Secret", set())
        self.assertEqual(cid, "reurope-company:9464530")
        self.assertEqual(key, "9464530")
        self.assertEqual(status, "CANONICAL_NUMBER")

    def test_formatting_equivalent_same_name_is_safe_merge(self):
        rows = [
            {"company_number": "08007191", "campaign_name": "Assetz Capital"},
            {"company_number": "8007191", "campaign_name": "Assetz Capital"},
        ]
        audit, blocked = collision_plan(rows)
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["status"], "FORMATTING_EQUIVALENT_MERGED")
        self.assertEqual(blocked, set())

    def test_conflicting_names_are_blocked_not_silently_merged(self):
        rows = [
            {"company_number": "00123", "campaign_name": "Alpha"},
            {"company_number": "123", "campaign_name": "Beta"},
        ]
        audit, blocked = collision_plan(rows)
        self.assertEqual(audit[0]["status"], "BLOCK_REVIEW")
        self.assertEqual(blocked, {"123"})
        a, _, status_a = company_id("00123", "Alpha", blocked)
        b, _, status_b = company_id("123", "Beta", blocked)
        self.assertNotEqual(a, b)
        self.assertEqual(status_a, "COLLISION_REVIEW_SEPARATE")
        self.assertEqual(status_b, "COLLISION_REVIEW_SEPARATE")

    def test_empty_number_uses_name_fallback(self):
        cid, key, status = company_id("", "Example Company", set())
        self.assertTrue(cid.startswith("reurope-name:"))
        self.assertEqual(key, "")
        self.assertEqual(status, "NAME_FALLBACK")


if __name__ == "__main__":
    unittest.main()
