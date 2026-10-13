import json
import tempfile
import unittest
from pathlib import Path

from src.phase1d.recover_startengine import (
    canonical_candidate,
    safe_public_resource,
    redacted_resource_url,
    extract_candidates,
    extract_total_hints,
    store_snapshot,
    load_snapshot,
    new_manifest,
    record_capture,
    checkpoint,
    verify,
    sha256,
)


class StartEngineRecoveryTests(unittest.TestCase):
    def test_campaign_canonicalization(self):
        self.assertEqual(
            canonical_candidate("https://startengine.com/offering/Acme/?utm_source=x#top"),
            "https://www.startengine.com/offering/acme",
        )

    def test_non_offering_and_external_rejected(self):
        for url in [
            "https://www.startengine.com/explore",
            "https://www.startengine.com/offering",
            "https://evil.example/offering/acme",
            "javascript:alert(1)",
            "http://www.startengine.com/offering/acme",
            "https://x:y@www.startengine.com/offering/acme",
        ]:
            self.assertIsNone(canonical_candidate(url), url)

    def test_sensitive_public_resource_rejected(self):
        self.assertTrue(safe_public_resource("https://api.startengine.com/public/offerings?page=2"))
        self.assertFalse(safe_public_resource("https://api.startengine.com/public/offerings?token=secret"))
        self.assertFalse(safe_public_resource("https://evil.example/public/offerings"))

    def test_redaction_removes_sensitive_query(self):
        url = redacted_resource_url(
            "https://api.startengine.com/public/offerings?page=2&token=secret&sort=recent"
        )
        self.assertIn("page=2", url)
        self.assertIn("sort=recent", url)
        self.assertNotIn("token", url)
        self.assertNotIn("secret", url)

    def test_nested_candidate_extraction(self):
        payload = {
            "results": [
                {"offering_slug": "alpha", "valuation": 100},
                {"url": "https://www.startengine.com/offering/beta?x=1"},
                {"nested": {"path": "/offering/gamma"}},
            ]
        }
        self.assertEqual(
            extract_candidates(payload),
            [
                "https://www.startengine.com/offering/alpha",
                "https://www.startengine.com/offering/beta",
                "https://www.startengine.com/offering/gamma",
            ],
        )

    def test_generic_slug_without_offering_context_is_not_candidate(self):
        self.assertEqual(extract_candidates({"article": {"slug": "not-an-offering"}}), [])

    def test_total_hint_extraction(self):
        hints = extract_total_hints({"meta": {"total_count": 1539}, "results": [{"count": 4}]})
        values = sorted(h["value"] for h in hints)
        self.assertEqual(values, [4, 1539])

    def test_snapshot_roundtrip_and_corruption_detection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            digest = store_snapshot(root, b"source")
            self.assertEqual(load_snapshot(root, digest), b"source")
            record = root / "snapshots" / f"{digest}.json"
            obj = json.loads(record.read_text())
            obj["bytes"] = 999
            record.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                load_snapshot(root, digest)

    def test_capture_union_and_resume_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = new_manifest("run1")
            raw = b"one"
            digest = store_snapshot(root, raw)
            capture = {
                "url": "https://www.startengine.com/explore",
                "kind": "directory_dom",
                "sha256": digest,
                "captured_at": "2026-10-09T00:00:00+00:00",
                "candidate_urls": ["/offering/alpha", "/offering/alpha", "/about"],
                "total_hints": [],
            }
            self.assertTrue(record_capture(manifest, capture))
            self.assertFalse(record_capture(manifest, capture))
            self.assertEqual(manifest["candidate_urls"], ["https://www.startengine.com/offering/alpha"])
            checkpoint(root, manifest)
            first = (root / "checkpoints" / "000001.json").read_bytes()
            checkpoint(root, manifest)
            self.assertEqual((root / "checkpoints" / "000001.json").read_bytes(), first)
            self.assertTrue((root / "checkpoints" / "000002.json").exists())
            checks = verify(root, manifest)
            self.assertEqual(checks["passed"], checks["total"])

    def test_partial_recovery_never_promotes_rates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = new_manifest("run1")
            checks = verify(root, manifest)
            self.assertEqual(checks["passed"], checks["total"])
            self.assertEqual(manifest["census_status"], "CENSUS_INCOMPLETE")
            self.assertFalse(manifest["rates_promoted"])

    def test_tampered_candidate_count_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = new_manifest("run1")
            digest = store_snapshot(root, b"x")
            record_capture(
                manifest,
                {
                    "url": "https://www.startengine.com/explore",
                    "kind": "directory_dom",
                    "sha256": digest,
                    "captured_at": "2026-10-09T00:00:00+00:00",
                    "candidate_urls": ["/offering/alpha"],
                    "total_hints": [],
                },
            )
            manifest["captures"][0]["candidate_count"] = 99
            self.assertFalse(verify(root, manifest)["checks"]["capture_counts_reconcile"])

    def test_unsafe_promotion_fails(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = new_manifest("run1")
            manifest["rates_promoted"] = True
            self.assertFalse(verify(Path(d), manifest)["checks"]["no_rate_promotion"])


if __name__ == "__main__":
    unittest.main()
