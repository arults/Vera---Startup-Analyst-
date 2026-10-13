import unittest,json,tempfile,copy
from pathlib import Path
import test_source_verifier as fixtures
import source_verifier as sv
import evidence as e
from timing import bounds,availability

class WindowTests(unittest.TestCase):
 def fixture(self,low='2026-10-02T00:00:00Z',high='2026-10-02T00:00:03Z'):
  h=fixtures.SourceVerifierTests();d=h.fixture();tmp=tempfile.TemporaryDirectory();root=Path(tmp.name)
  for s in d['sources']:
   p=root/s['capture'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((fixtures.ROOT/s['capture']).read_bytes())
  # Scope policy hash acknowledgements are checked against module-adjacent policy, not data root.
  f=root/'receipt.json';f.write_text(json.dumps({'window':[low,high]}));r=d['research_plan']['routes'][0]
  r['searched_at']=None;r['search_timing']={'kind':'observed_window','lower':low,'upper':high,'evidence_reference':'receipt.json','evidence_sha256':e.sha(f.read_bytes()),'evidence_pointer':'/window'};h.sign(d)
  return d,root,tmp
 def test_window_positive_without_exacttime_imputation(self):
  d,root,tmp=self.fixture();r=sv.audit(d,root);self.assertEqual(r['blockers'],[]);self.assertIsNone(d['research_plan']['routes'][0]['searched_at']);tmp.cleanup()
 def test_plan_overlap_unknown(self):
  d,root,tmp=self.fixture('2026-09-30T23:59:59Z','2026-10-01T00:00:03Z');self.assertTrue(any('ORDER_UNPROVEN' in x for x in sv.audit(d,root)['blockers']));tmp.cleanup()
 def test_review_overlap_unknown(self):
  d,root,tmp=self.fixture('2026-10-02T23:59:59Z','2026-10-03T00:00:03Z');self.assertIn('REVIEW_SEARCH_ORDER_UNPROVEN',sv.audit(d,root)['blockers']);tmp.cleanup()
 def test_fake_receipt_hash_blocks(self):
  d,root,tmp=self.fixture();d['research_plan']['routes'][0]['search_timing']['evidence_sha256']='0'*64;fixtures.SourceVerifierTests().sign(d);self.assertTrue(any('INVALID_SEARCH_TIME' in x for x in sv.audit(d,root)['blockers']));tmp.cleanup()
 def test_wrong_receipt_bounds_block(self):
  d,root,tmp=self.fixture();d['research_plan']['routes'][0]['search_timing']['upper']='2026-10-02T00:00:02Z';fixtures.SourceVerifierTests().sign(d);self.assertTrue(any('INVALID_SEARCH_TIME' in x for x in sv.audit(d,root)['blockers']));tmp.cleanup()
 def test_reversed_window_blocks(self):
  d,root,tmp=self.fixture('2026-10-02T00:00:03Z','2026-10-02T00:00:00Z');self.assertTrue(any('INVALID_SEARCH_TIME' in x for x in sv.audit(d,root)['blockers']));tmp.cleanup()
 def test_completedby_cannot_establish_start(self):
  d,root,tmp=self.fixture();r=d['research_plan']['routes'][0];f=root/'upper.json';f.write_text(json.dumps({'upper':'2026-10-02T00:00:03Z'}));r['search_timing']={'kind':'completed_by','upper':'2026-10-02T00:00:03Z','evidence_reference':'upper.json','evidence_sha256':e.sha(f.read_bytes()),'evidence_pointer':'/upper'};fixtures.SourceVerifierTests().sign(d)
  self.assertIn('0:SEARCH_START_NOT_ESTABLISHED',sv.audit(d,root)['blockers']);tmp.cleanup()
 def test_offset_order_and_availability(self):
  a=e.timestamp('2026-10-02T15:00:00+02:00');b=e.timestamp('2026-10-02T13:30:00Z');self.assertLess(a,b)
  self.assertEqual(availability(a,b,e.timestamp('2026-10-02T12:59:00Z')),'NOT_YET_ESTABLISHED')
  self.assertEqual(availability(a,b,e.timestamp('2026-10-02T13:15:00Z')),'ACQUISITION_TIME_UNCERTAIN')
  self.assertEqual(availability(a,b,b),'KNOWN_BY_UPPER_BOUND')
 def test_source_local_date_unchanged(self):
  d=json.loads((fixtures.ROOT/'demo.json').read_text());d['claims'][0]['time']['source_local_day']='2024-11-22 PST';e.report(d,fixtures.ROOT,e.date('2026-10-10'));self.assertEqual(d['claims'][0]['time']['source_local_day'],'2024-11-22 PST')
 def test_malformed_window_types_hold_without_crash(self):
  for value in [[],False,'bad',42]:
   d,root,tmp=self.fixture();d['research_plan']['routes'][0]['search_timing']=value;fixtures.SourceVerifierTests().sign(d)
   self.assertTrue(any('INVALID_SEARCH_TIME' in x for x in sv.audit(d,root)['blockers']));tmp.cleanup()
 def test_exact_time_cannot_override_conflicting_window(self):
  d,root,tmp=self.fixture();d['research_plan']['routes'][0]['searched_at']='2026-10-02T12:00:00Z';fixtures.SourceVerifierTests().sign(d)
  self.assertTrue(any('INVALID_SEARCH_TIME' in x for x in sv.audit(d,root)['blockers']));tmp.cleanup()
 def test_utc_max_knownby_retrieval(self):
  d=json.loads((fixtures.ROOT/'demo.json').read_text());s=d['sources'][0];s['retrieved_at']='2026-10-02T15:00:00+02:00';s2=copy.deepcopy(s);s2['id']='second-offset';s2['retrieved_at']='2026-10-02T13:30:00Z';d['sources'].append(s2);d['claims'][0]['evidence'].append({**d['claims'][0]['evidence'][0],'source_id':s2['id']})
  r=e.report(d,fixtures.ROOT,e.date('2026-10-10'));self.assertEqual(r['augmented_observations'][0]['known_by_retrieval'],'2026-10-02T13:30:00+00:00')
 def test_split_receipt_window_is_bound(self):
  d,root,tmp=self.fixture();r=d['research_plan']['routes'][0];t=r['search_timing']
  for bound in ('lower','upper'):
   p=root/(bound+'.json');p.write_text(json.dumps({'observed':t[bound]}));t[bound+'_evidence']={'evidence_reference':p.name,'evidence_sha256':e.sha(p.read_bytes()),'evidence_pointer':'/observed'}
  fixtures.SourceVerifierTests().sign(d);self.assertEqual(sv.audit(d,root)['blockers'],[])
  (root/'lower.json').write_text(json.dumps({'observed':'2026-10-02T00:00:01Z'}));self.assertTrue(any('INVALID_SEARCH_TIME' in x for x in sv.audit(d,root)['blockers']));tmp.cleanup()
