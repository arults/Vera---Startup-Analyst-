"""Regression from real pilot: absent exact tool timestamps must hold, not crash."""
import unittest
import test_source_verifier as fixtures
import source_verifier as sv
import evidence

class MissingSearchTimes(unittest.TestCase):
 def test_null_exact_search_time_reports_missing(self):
  h=fixtures.SourceVerifierTests();d=h.fixture();r=d['research_plan']['routes'][0]
  r['searched_at']=None;r['observed_execution_window_utc']=['2026-10-02T00:00:00Z','2026-10-02T00:00:03Z'];h.sign(d)
  result=sv.audit(d)
  self.assertIn('0:INVALID_SEARCH_TIME',result['blockers'])
  self.assertEqual(result['status'],'INCOMPLETE_MATERIAL_ROUTE')
  self.assertIsNone(r['searched_at'])
 def test_invalid_timestamp_types_rejected_with_valueerror(self):
  for value in [None,False,123,{},[], '']:
   with self.assertRaises(ValueError):evidence.timestamp(value)
 def test_null_search_time_public_report_no_invention(self):
  h=fixtures.SourceVerifierTests();d=h.fixture();r=d['research_plan']['routes'][0];r['searched_at']=None;h.sign(d)
  result=evidence.report(d,fixtures.ROOT,evidence.date('2026-10-10'))
  self.assertEqual(result['implementation_version'],'1.0.3.1')
  self.assertEqual(result['source_coverage_audit']['status'],'INCOMPLETE_MATERIAL_ROUTE')
  self.assertIsNone(r['searched_at']);self.assertEqual(result['prior_promotions'],0)
 def test_malformed_search_timestamp_reports_blocker(self):
  h=fixtures.SourceVerifierTests();d=h.fixture();d['research_plan']['routes'][0]['searched_at']='not-a-time';h.sign(d)
  result=evidence.report(d,fixtures.ROOT,evidence.date('2026-10-10'))
  self.assertIn('0:INVALID_SEARCH_TIME',result['source_coverage_audit']['blockers'])
 def test_timezone_missing_search_timestamp_reports_blocker(self):
  h=fixtures.SourceVerifierTests();d=h.fixture();d['research_plan']['routes'][0]['searched_at']='2026-10-02T00:00:00';h.sign(d)
  result=evidence.report(d,fixtures.ROOT,evidence.date('2026-10-10'))
  self.assertIn('0:INVALID_SEARCH_TIME',result['source_coverage_audit']['blockers'])
 def test_wrong_type_search_times_public_report_blocked(self):
  for value in [False,123,{},[]]:
   h=fixtures.SourceVerifierTests();d=h.fixture();d['research_plan']['routes'][0]['searched_at']=value;h.sign(d)
   result=evidence.report(d,fixtures.ROOT,evidence.date('2026-10-10'))
   self.assertIn('0:INVALID_SEARCH_TIME',result['source_coverage_audit']['blockers'])
   self.assertEqual(result['source_coverage_audit']['status'],'INCOMPLETE_MATERIAL_ROUTE')
