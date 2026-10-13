import base64
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from src.phase1d.audit_republic_europe_zero_valuation_closures import (
    canonical_url,
    extract_candidates,
    extract_date,
    official_url,
    relevant_update_link,
    store_snapshot,
    zero_valuation,
)


class RepublicEuropeClosureAuditTests(unittest.TestCase):
    def test_zero_valuation_signal_is_exact(self):
        for value in ("£0.00", "€0.00", "$0", "0", "0.0"):
            self.assertTrue(zero_valuation(value), value)
        for value in ("£0.01", "€1", "", "Unavailable", "-£1"):
            self.assertFalse(zero_valuation(value), value)

    def test_only_official_https_pages_are_allowed(self):
        self.assertTrue(official_url("https://europe.republic.com/businesses/acme"))
        self.assertFalse(official_url("http://europe.republic.com/businesses/acme"))
        self.assertFalse(official_url("https://evil.example/businesses/acme"))
        self.assertFalse(official_url("https://user:pass@europe.republic.com/businesses/acme"))

    def test_canonical_url_strips_query_and_fragment(self):
        self.assertEqual(
            canonical_url("https://europe.republic.com/acme?ref=x#updates"),
            "https://europe.republic.com/acme",
        )

    def test_update_link_is_same_platform_and_relevant(self):
        base = "https://europe.republic.com/acme"
        self.assertEqual(
            relevant_update_link("/acme/updates/closed", base, "acme"),
            "https://europe.republic.com/acme/updates/closed",
        )
        self.assertEqual(
            relevant_update_link("https://europe.republic.com/news/acme-update", base, "acme"),
            "https://europe.republic.com/news/acme-update",
        )
        self.assertIsNone(relevant_update_link("https://evil.example/acme/updates/closed", base, "acme"))
        self.assertIsNone(relevant_update_link("/academy/closure-guide", base, "acme"))

    def test_date_extraction_supported_formats(self):
        self.assertEqual(extract_date("Company ceased trading on 8 September 2025."), "2025-09-08")
        self.assertEqual(extract_date("On September 8, 2025 the company ceased trading."), "2025-09-08")
        self.assertEqual(extract_date("The event occurred 2025-09-08."), "2025-09-08")
        self.assertEqual(extract_date("No date here."), "")

    def test_explicit_closure_phrase_creates_review_candidate_only(self):
        rows = extract_candidates(
            "On 8 September 2025 the company ceased trading after appointing administrators.",
            "https://europe.republic.com/acme/updates/final",
            "Acme",
        )
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(any(r["event_type_candidate"] in {"ceased_trading", "administration"} for r in rows))
        self.assertTrue(all(r["closure_label_applied"] == "false" for r in rows))
        self.assertTrue(any(r["date_candidate"] == "2025-09-08" for r in rows))

    def test_campaign_closed_or_acquired_does_not_trigger_closure(self):
        text = "The campaign is now closed and the shares were acquired from a prior investor."
        self.assertEqual(extract_candidates(text, "https://europe.republic.com/acme", "Acme"), [])

    def test_generic_liquid_word_does_not_trigger(self):
        text = "The company provides liquid cooling and operates a liquidity marketplace."
        self.assertEqual(extract_candidates(text, "https://europe.republic.com/acme", "Acme"), [])

    def test_snapshot_is_content_addressed_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = b"platform evidence"
            record = store_snapshot(root, raw, "https://europe.republic.com/acme", 200, "text/html")
            path = root / "snapshots" / f"{record['sha256']}.json"
            saved = json.loads(path.read_text())
            recovered = gzip.decompress(base64.b64decode(saved["data"], validate=True))
            self.assertEqual(recovered, raw)
            self.assertEqual(saved["bytes"], len(raw))
            self.assertEqual(saved["url"], "https://europe.republic.com/acme")


if __name__ == "__main__":
    unittest.main()
