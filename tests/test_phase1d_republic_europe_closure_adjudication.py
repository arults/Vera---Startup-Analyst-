import unittest

from src.phase1d.adjudicate_republic_europe_closure_audit import classify


def row(excerpt, date="", applied="false"):
    return {
        "excerpt": excerpt,
        "date_candidate": date,
        "closure_label_applied": applied,
    }


class RepublicEuropeClosureAdjudicationTests(unittest.TestCase):
    def test_share_class_liquidation_preference_is_false_positive(self):
        disposition, reason = classify(row("A Ordinary shares have a preference on liquidation, exit and dividend."))
        self.assertEqual(disposition, "FALSE_POSITIVE_CONTRACT_LANGUAGE")
        self.assertIn("share_class_liquidation_preference", reason)

    def test_hypothetical_default_clause_is_false_positive(self):
        disposition, reason = classify(row("Events of Default include liquidation or winding up and creditors rank first."))
        self.assertEqual(disposition, "FALSE_POSITIVE_CONTRACT_LANGUAGE")
        self.assertIn("hypothetical_default_or_winding_up_clause", reason)

    def test_dated_candidate_is_held_not_accepted(self):
        disposition, _ = classify(row("The company ceased trading.", date="2025-01-01"))
        self.assertEqual(disposition, "HELD_EXPLICIT_DATE_REVIEW")

    def test_unclassified_undated_phrase_is_held(self):
        disposition, _ = classify(row("The company is no longer operating."))
        self.assertEqual(disposition, "HELD_MANUAL_UNRESOLVED")

    def test_upstream_applied_label_blocks_input(self):
        disposition, _ = classify(row("preference on liquidation", applied="true"))
        self.assertEqual(disposition, "BLOCK_INVALID_INPUT")

    def test_contract_language_never_accepts_closure(self):
        for excerpt in (
            "On liquidation or exit the share class is redeemable for £1.",
            "In the event of a winding up or liquidation event the loan ranks behind creditors.",
            "The rights attached to share classes include a liquidation preference.",
        ):
            disposition, _ = classify(row(excerpt))
            self.assertNotEqual(disposition, "ACCEPTED_CLOSURE")


if __name__ == "__main__":
    unittest.main()
