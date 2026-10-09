import unittest

from src.phase1d.apply_republic_europe_identity_review import (
    make_observation,
    normalize_existing_company_id,
    review_group,
)


def row(signals, *, unique="true", tie="1", eligibility="ELIGIBLE", cid="reurope-company:1"):
    return {
        "business_url": "https://europe.republic.com/businesses/acme",
        "business_name": "Acme",
        "business_eligibility": eligibility,
        "business_content_sha256": "a" * 64,
        "candidate_company_id": cid,
        "signals": " | ".join(signals),
        "unique_top_candidate": unique,
        "top_score_tie_count": tie,
    }


class RepublicEuropeIdentityApplyTests(unittest.TestCase):
    def test_single_slug_alias_unique_candidate_is_accepted(self):
        accepted, decisions = review_group([row(["platform_slug_exact", "deterministic_alias_exact"])])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(decisions[0]["review_disposition"], "ACCEPTED_JEV_RULE")

    def test_single_one_signal_candidate_is_held(self):
        accepted, decisions = review_group([row(["platform_slug_exact"])])
        self.assertEqual(accepted, [])
        self.assertEqual(decisions[0]["review_disposition"], "HELD_INSUFFICIENT_SIGNALS")

    def test_every_multi_candidate_page_is_held(self):
        accepted, decisions = review_group([
            row(["platform_slug_exact", "deterministic_alias_exact"], cid="reurope-company:1"),
            row(["deterministic_alias_exact"], cid="reurope-company:2"),
        ])
        self.assertEqual(accepted, [])
        self.assertTrue(all(d["review_disposition"] == "HELD_COLLISION" for d in decisions))

    def test_top_tie_is_held(self):
        accepted, decisions = review_group([row(["platform_slug_exact", "deterministic_alias_exact"], unique="false", tie="2")])
        self.assertEqual(accepted, [])
        self.assertEqual(decisions[0]["review_disposition"], "HELD_AMBIGUOUS_TOP")

    def test_old_ukco_id_uses_canonical_legal_key(self):
        self.assertEqual(normalize_existing_company_id("ukco:09464530"), "reurope-company:9464530")
        self.assertEqual(normalize_existing_company_id("ukco:CHE\u00ad152.681.235"), "reurope-company:CHE152681235")

    def test_eligible_match_creates_positive_medium_evidence(self):
        observation = make_observation(
            row(["platform_slug_exact", "deterministic_alias_exact"]),
            {"captured_at": "2026-10-09T00:00:00+00:00"},
        )
        self.assertEqual(observation["positive_operating_evidence"], "true")
        self.assertEqual(observation["evidence_confidence"], "medium")
        self.assertEqual(observation["match_basis"], "JEV_REVIEW_PLATFORM_SLUG_PLUS_ALIAS")

    def test_not_eligible_match_does_not_extend_followup(self):
        observation = make_observation(
            row(["platform_slug_exact", "deterministic_alias_exact"], eligibility="NOT_ELIGIBLE"),
            {"captured_at": "2026-10-09T00:00:00+00:00"},
        )
        self.assertEqual(observation["positive_operating_evidence"], "false")
        self.assertEqual(observation["evidence_basis"], "secondary_market_status_neutral")


if __name__ == "__main__":
    unittest.main()
