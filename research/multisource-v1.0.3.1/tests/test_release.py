"""End-to-end release gates, with synthetic approvals explicitly separated from demo."""
import unittest
import test_source_verifier as source_tests
ROOT=source_tests.ROOT
from evidence import *
from source_verifier import coverage_digest

class ReleaseTests(unittest.TestCase):
 def fixture(self):
  helper=source_tests.SourceVerifierTests();d=helper.fixture();c=d['claims'][0]
  c['identity']['mapping_review_status']='verified'
  c['predicate_review']={'supported_claim_type':c['claim_type'],'rationale':'Synthetic full-text completed-act assessment'}
  c['reviews']=[{'reviewer':'synthetic-claim-reviewer','decision':'accept','rationale':'Synthetic fixture only','identity_checked':True,'reviewed_at':'2026-10-03T00:00:00Z','claim_sha256':digest_claim(c),'source_snapshot_sha256':source_snapshot(d)}]
  helper.sign(d)
  d['rollout']['acknowledgements'].append({'actor':'synthetic-claim-reviewer','policy':POLICY,'policy_sha256':sha((ROOT/'POLICY.md').read_bytes()),'acknowledged_at':'2026-10-03T00:00:00Z'})
  return d
 def test_positive_released_narrow_finding(self):
  d=self.fixture();r=report(d,ROOT,date('2026-10-10'),{'synthetic-claim-reviewer':['claim_verifier'],'synthetic-reviewer':['source_verifier']})
  self.assertEqual(r['source_coverage_audit']['blockers'],[])
  self.assertEqual(r['augmented_observations'][0]['release_status'],'RELEASED_RESEARCH_FINDING')
  self.assertEqual(r['prior_promotions'],0);self.assertIsNone(r['rates'])
 def test_pending_source_route_blocks_release_not_narrow_claim(self):
  d=self.fixture();d['research_plan']['routes'][0]['status']='unperformed'
  r=report(d,ROOT,date('2026-10-10'),{'synthetic-claim-reviewer':['claim_verifier'],'synthetic-reviewer':['source_verifier']})
  self.assertEqual(r['augmented_observations'][0]['status'],'ACCEPTED_ATTRIBUTED_OBSERVATION')
  self.assertEqual(r['augmented_observations'][0]['release_status'],'UNRELEASED_RESEARCH_OBSERVATION')
 def test_asof_before_review_blocks(self):
  r=report(self.fixture(),ROOT,date('2026-10-02'))
  self.assertIn('SOURCE_REVIEW_POSTDATES_AS_OF',r['source_coverage_audit']['blockers'])
  self.assertIn('CLAIM_REVIEW_POSTDATES_AS_OF',r['augmented_observations'][0]['reasons'])
 def test_missing_operator_roles_blocks(self):
  r=report(self.fixture(),ROOT,date('2026-10-10'))
  self.assertEqual(r['augmented_observations'][0]['release_status'],'UNRELEASED_RESEARCH_OBSERVATION')
