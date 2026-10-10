import unittest,copy,json,tempfile
from pathlib import Path
import test_scoped_review as fixtures
import evidence as e
import scoped_review as sc

class HistoricalPlanTests(unittest.TestCase):
 def fixture(self):
  helper=fixtures.ScopedTests();d=helper.fixture();tmp=tempfile.TemporaryDirectory();root=Path(tmp.name)
  for s in d['sources']:
   p=root/s['capture'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((fixtures.fixtures.ROOT/s['capture']).read_bytes())
  d['research_plan']['policy']='vera.multisource.claim-policy.v1.0.0';parent=copy.deepcopy(d);parent['policy']='vera.multisource.claim-policy.v1.0.0'
  (root/'parent.json').write_text(json.dumps(parent));(root/'plan.md').write_text('Synthetic historical plan, not actual evidence')
  d['research_scope']['historical_plan_reassessment']={'original_policy':d['research_plan']['policy'],'reviewed_under':e.POLICY,'reviewed_by':'synthetic-reviewer','same_selected_claim_scope':True,'selected_claim_ids':d['research_scope']['selected_claim_ids'],'rationale':'Synthetic equivalent narrow scope, retrospective only','retrospective_reassessment':True,'new_policy_prospectively_registered':False,'original_plan_document_reference':'plan.md','original_plan_document_sha256':e.sha((root/'plan.md').read_bytes()),'parent_dataset_reference':'parent.json','parent_dataset_sha256':e.sha((root/'parent.json').read_bytes()),'original_policy_hash':'21982e1c32472136cae3cbd208347734f985b2143c5758f177f7b328846c6df0','reviewed_policy_hash':e.sha((Path(sc.__file__).parent/'POLICY.md').read_bytes()),'original_plan_sha256':e.sha(e.stable(parent['research_plan'])),'coverage_equivalence':{k:{'status':'satisfied_for_selected_scope','basis':'Synthetic requirement checked'} for k in ['claim_scope','source_authority','identity_mapping','contradiction_search','timing_provenance','inspection_scope']},'new_required_searches':[]}
  helper.sign(d);return d,root,tmp,helper
 def test_retrospective_positive_preserves_old_policy(self):
  d,root,tmp,h=self.fixture();r=h.runreport(d,root)
  self.assertEqual(r['released_selected_claims'],1);self.assertEqual(d['research_plan']['policy'],'vera.multisource.claim-policy.v1.0.0');self.assertIn('Retrospective',r['amended_policy_design']);tmp.cleanup()
 def test_forged_plan_hash_blocks(self):
  d,root,tmp,h=self.fixture();d['research_scope']['historical_plan_reassessment']['original_plan_sha256']='0'*64;h.sign(d);self.assertEqual(h.runreport(d,root)['released_selected_claims'],0);tmp.cleanup()
 def test_missing_new_requirement_holds(self):
  d,root,tmp,h=self.fixture();d['research_scope']['historical_plan_reassessment']['new_required_searches']=['new material search'];h.sign(d);self.assertEqual(h.runreport(d,root)['released_selected_claims'],0);tmp.cleanup()
 def test_changed_semantic_scope_is_not_equivalent(self):
  d,root,tmp,h=self.fixture();d['claims'][0]['claim_type']='control_transfer';h.sign(d);self.assertIn('HISTORICAL_PLAN_REASSESSMENT_PENDING',h.runreport(d,root)['scope']['blockers']);tmp.cleanup()
 def test_stale_reassessment_review_blocks(self):
  d,root,tmp,h=self.fixture();d['research_scope']['historical_plan_reassessment']['rationale']='Edited';self.assertIn('SCOPE_REVIEW_STALE_OR_MISSING',h.runreport(d,root)['scope']['blockers']);tmp.cleanup()
 def test_cannot_claim_new_policy_preregistered(self):
  d,root,tmp,h=self.fixture();d['research_scope']['historical_plan_reassessment']['new_policy_prospectively_registered']=True;h.sign(d);self.assertEqual(h.runreport(d,root)['released_selected_claims'],0);tmp.cleanup()
 def test_required_route_cannot_be_demoted(self):
  d,root,tmp,h=self.fixture();d['research_plan']['verifier_required_route_ids']=['0'];d['research_scope']['route_dispositions']['0']={'role':'context_only','rationale':'Attempted downgrade','reviewed_by':'synthetic-reviewer'};h.sign(d)
  self.assertIn('VERIFIER_REQUIRED_ROUTE_DOWNGRADED:0',h.runreport(d,root)['scope']['blockers']);tmp.cleanup()

 def test_parent_bytes_changed_without_plan_change_holds(self):
  d,root,tmp,h=self.fixture();parent=json.loads((root/'parent.json').read_text());parent['claims'][0]['missingness']['mutation']='Mutated parent';(root/'parent.json').write_text(json.dumps(parent))
  self.assertIn('HISTORICAL_PLAN_REASSESSMENT_PENDING',h.runreport(d,root)['scope']['blockers']);tmp.cleanup()
 def test_policy_hashes_required(self):
  for key in ('original_policy_hash','reviewed_policy_hash','parent_dataset_sha256'):
   d,root,tmp,h=self.fixture();d['research_scope']['historical_plan_reassessment'][key]='0'*64;h.sign(d)
   self.assertEqual(h.runreport(d,root)['released_selected_claims'],0);tmp.cleanup()
