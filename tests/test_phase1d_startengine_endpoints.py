import json
import tempfile
import unittest
from pathlib import Path

from src.phase1d.recover_startengine import new_manifest
from src.phase1d.recover_startengine_endpoints import (
    BASE,
    INDUSTRIES,
    TOMBSTONES,
    allowed_endpoint,
    capture_response,
    decode_json,
    search_url,
)


class StartEngineObservedEndpointTests(unittest.TestCase):
    def test_search_url_is_exact_observed_scope(self):
        url = search_url(4)
        self.assertTrue(allowed_endpoint(url))
        self.assertIn("regulationTypes=Reg+D", url)
        self.assertIn("statuses=APPROVED%2CTESTING%2CCLOSED", url)
        self.assertIn("size=200", url)
        self.assertIn("page=4", url)

    def test_page_bounds_fail_closed(self):
        for page in (-1, 51):
            with self.assertRaises(ValueError):
                search_url(page)

    def test_only_observed_endpoints_allowed(self):
        self.assertTrue(allowed_endpoint(TOMBSTONES))
        self.assertTrue(allowed_endpoint(INDUSTRIES))
        self.assertFalse(allowed_endpoint(BASE + "/service/guessed/private"))
        self.assertFalse(allowed_endpoint("https://evil.example/service/elastic-search/search/offering/search"))

    def test_parameter_broadening_rejected(self):
        self.assertFalse(allowed_endpoint(search_url(0).replace("Reg+D", "Reg+CF")))
        self.assertFalse(allowed_endpoint(search_url(0) + "&extra=1"))
        self.assertFalse(allowed_endpoint(search_url(0).replace("size=200", "size=10000")))

    def test_json_decode_is_bounded_and_strict(self):
        self.assertEqual(decode_json(b'{"x":1}'), {"x": 1})
        with self.assertRaises(Exception):
            decode_json(b"not-json")
        with self.assertRaises(ValueError):
            decode_json(b" " * 15_000_001)

    def test_capture_access_failure_never_creates_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = new_manifest("x")
            ok, candidates = capture_response(
                root,
                manifest,
                {"url": search_url(0), "status": 403, "transport": "requests", "raw": b"blocked", "errors": ["HTTP 403"]},
                "observed_search_page",
                0,
            )
            self.assertFalse(ok)
            self.assertEqual(candidates, [])
            self.assertEqual(manifest["candidate_urls"], [])
            self.assertEqual(len(manifest["errors"]), 1)

    def test_valid_payload_preserves_candidates_and_totals(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = new_manifest("x")
            payload = {"meta": {"total_count": 2}, "results": [{"offering_slug": "alpha", "valuation": 1}, {"url": "/offering/beta"}]}
            raw = json.dumps(payload).encode()
            ok, candidates = capture_response(
                root,
                manifest,
                {"url": search_url(0), "status": 200, "transport": "requests", "raw": raw},
                "observed_search_page",
                0,
            )
            self.assertTrue(ok)
            self.assertEqual(candidates, [
                "https://www.startengine.com/offering/alpha",
                "https://www.startengine.com/offering/beta",
            ])
            self.assertEqual(manifest["total_hints"][0]["value"], 2)


if __name__ == "__main__":
    unittest.main()
