import json,unittest
import evidence as e
import scoped_review as sc
import test_scoped_review as fixtures

class ReportVersionTests(unittest.TestCase):
 def test_unscoped_version_matches_engine(self):
  d=json.loads((fixtures.fixtures.ROOT/'demo.json').read_text())
  self.assertEqual(e.report(d,fixtures.fixtures.ROOT,e.date('2026-10-10'))['implementation_version'],e.IMPLEMENTATION_VERSION)
 def test_scoped_version_matches_engine(self):
  helper=fixtures.ScopedTests();d=helper.fixture()
  self.assertEqual(helper.runreport(d)['implementation_version'],e.IMPLEMENTATION_VERSION)
 def test_scoped_import_uses_engine_version(self):
  self.assertEqual(sc.IMPLEMENTATION_VERSION,e.IMPLEMENTATION_VERSION)
 def test_version_lineage_matches_engine(self):
  for name in ('lineage.json','manifest.json','publication-check.json'):
   declared=json.loads((fixtures.fixtures.ROOT/name).read_text())
   self.assertEqual(declared['implementation_version'],e.IMPLEMENTATION_VERSION)
