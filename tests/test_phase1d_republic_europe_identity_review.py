import unittest

from src.phase1d.build_republic_europe_identity_review import (
    candidate_rows,
    company_index,
    explicit_aliases,
    jaccard,
    norm_name,
    norm_slug,
)


class RepublicEuropeIdentityReviewTests(unittest.TestCase):
    def test_legal_suffixes_are_removed(self):
        self.assertEqual(norm_name("Acme Holdings Limited"), "acme")

    def test_round_suffix_is_removed_from_slug(self):
        self.assertEqual(norm_slug("aduna1"), "aduna")
        self.assertEqual(norm_slug("laundryheap5"), "laundryheap")

    def test_explicit_former_aliases_are_preserved(self):
        aliases = explicit_aliases("Keel (formerly Frost)")
        self.assertIn("keel", aliases)
        self.assertIn("frost", aliases)

    def test_token_similarity_is_bounded(self):
        self.assertEqual(jaccard("Acme Limited", "Acme Holdings Ltd"), 1.0)
        self.assertEqual(jaccard("Acme", "Unrelated"), 0.0)

    def test_slug_and_alias_create_review_candidate_not_match(self):
        rounds = [{
            "canonical_company_id": "ukco:1",
            "campaign_name": "Aduna",
            "campaign_url": "https://europe.republic.com/aduna1",
            "legal_company_number": "1",
            "round_id": "reurope:aduna1",
        }]
        index = company_index(rounds)
        business = {
            "business_name": "Aduna Ltd",
            "url": "https://europe.republic.com/businesses/aduna1",
            "eligibility": "ELIGIBLE",
            "content_sha256": "a" * 64,
            "company_numbers_json": "[]",
        }
        rows = candidate_rows(business, index)
        self.assertEqual(len(rows), 1)
        self.assertIn("platform_slug_exact", rows[0]["signals"])
        self.assertIn("deterministic_alias_exact", rows[0]["signals"])
        self.assertEqual(rows[0]["proposed_disposition"], "REVIEW_REQUIRED")
        self.assertEqual(rows[0]["followup_extension_allowed"], "false")

    def test_name_only_candidate_remains_review_only(self):
        rounds = [{
            "canonical_company_id": "ukco:1",
            "campaign_name": "North Star",
            "campaign_url": "https://europe.republic.com/unrelated-slug",
            "legal_company_number": "1",
            "round_id": "reurope:north-star",
        }]
        rows = candidate_rows({
            "business_name": "North Star Limited",
            "url": "https://europe.republic.com/businesses/different-slug",
            "eligibility": "ELIGIBLE",
            "content_sha256": "b" * 64,
            "company_numbers_json": "[]",
        }, company_index(rounds))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["proposed_disposition"], "REVIEW_REQUIRED")
        self.assertEqual(rows[0]["followup_extension_allowed"], "false")

    def test_external_name_collision_can_create_multiple_review_rows(self):
        rounds = [
            {"canonical_company_id": "c1", "campaign_name": "Common", "campaign_url": "https://europe.republic.com/common1", "legal_company_number": "1", "round_id": "r1"},
            {"canonical_company_id": "c2", "campaign_name": "Common", "campaign_url": "https://europe.republic.com/common2", "legal_company_number": "2", "round_id": "r2"},
        ]
        rows = candidate_rows({
            "business_name": "Common",
            "url": "https://europe.republic.com/businesses/common",
            "eligibility": "ELIGIBLE",
            "content_sha256": "c" * 64,
            "company_numbers_json": "[]",
        }, company_index(rounds))
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["followup_extension_allowed"] == "false" for r in rows))


if __name__ == "__main__":
    unittest.main()
