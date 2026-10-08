import unittest
from src.phase1c.sources import SourceCapture,content_sha256,validate_capture,build_manifest
from src.phase1c.adapters import get_adapter,validate_adapter_registry

class TestSourceAdapters(unittest.TestCase):
    def test_all_five_adapters_registered(self):
        self.assertTrue(validate_adapter_registry())
        for p in ["wefunder","startengine","crowdcube","republic_us","republic_europe"]:
            self.assertEqual(get_adapter(p).platform,p)

    def test_cross_platform_url_rejected(self):
        c=SourceCapture("x","wefunder","https://republic.com/x","campaign","2026-10-08T12:00:00+00:00","PUBLIC_VISIBLE",content_sha256("x"))
        self.assertIn("url_host_not_allowed_for_platform",validate_capture(c))

    def test_auth_required_is_explicit_not_missing(self):
        c=SourceCapture("x","republic_europe","https://europe.republic.com/x","campaign","2026-10-08T12:00:00+00:00","AUTH_REQUIRED",content_sha256("auth wall"))
        self.assertEqual(validate_capture(c),[])

    def test_search_snippet_page_type_not_allowed(self):
        c=SourceCapture("x","wefunder","https://wefunder.com/x","search_snippet","2026-10-08T12:00:00+00:00","PUBLIC_VISIBLE",content_sha256("x"))
        self.assertIn("page_type_invalid",validate_capture(c))

    def test_manifest_is_order_stable(self):
        a=SourceCapture("a","wefunder","https://wefunder.com/a","campaign","2026-10-08T12:00:00+00:00","PUBLIC_VISIBLE",content_sha256("a"))
        b=SourceCapture("b","startengine","https://www.startengine.com/b","campaign","2026-10-08T12:00:00+00:00","PUBLIC_VISIBLE",content_sha256("b"))
        self.assertEqual(build_manifest([a,b])["manifest_sha256"],build_manifest([b,a])["manifest_sha256"])

if __name__=="__main__":
    unittest.main()
