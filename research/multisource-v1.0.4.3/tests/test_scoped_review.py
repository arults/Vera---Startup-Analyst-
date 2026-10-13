import copy,json,tempfile,unittest
from pathlib import Path
import test_source_verifier as fixtures
import evidence as e
import scoped_review as sc
import timing

class ScopedTests(unittest.TestCase):
 def fixture(self):
  h=fixtures.SourceVerifierTests();d=h.fixture();c=d['claims'][0];s=d['sources'][0];s['original_sha256']=s['capture_sha256']
  c['identity']['mapping_review_status']='verified';c['predicate_review']={'supported_claim_type':c['claim_type'],'rationale':'Synthetic reviewed complete-act context'}
  i={'mode':'relevant_sections','document_sha256':s['original_sha256'],'document_reference':s['capture'],'sections':[{'locator':'Article substantive paragraphs1-5','context':'Completed-act clause plus retained autonomy and relevant qualifiers'}],'excluded_sections':['Unrelated navigation'],'limitations':['Synthetic test review, not a real approval'],'qualifications_checked':True,'cross_references_checked':True,'unresolved_material':[],'claim_ids':[c['id']]}
  i['review']={'reviewer':'synthetic-reviewer','adequate_claim_ids':[c['id']],'rationale':'Narrow assertion context sufficient; fixture only','inspection_sha256':sc.inspection_digest(i)};s['inspection']=i
  d['research_scope']={'selected_claim_ids':[c['id']],'context_links':[],'route_dispositions':{}}
  self.sign(d);return d
 def sign(self,d):
  c=d['claims'][0];c['reviews']=[]
  c['reviews']=[{'reviewer':'synthetic-claim-reviewer','decision':'accept','rationale':'Synthetic scope test only','identity_checked':True,'reviewed_at':'2026-10-03T00:00:00Z','claim_sha256':e.digest_claim(c),'source_snapshot_sha256':e.source_snapshot(d)}]
  fixtures.SourceVerifierTests().sign(d)
  r=d['source_review'];r.update(scope_sha256=sc.scope_digest(d),context_claim_ids=[x for x in sc.context_closure(d)[0] if x not in d['research_scope']['selected_claim_ids']],timing_checked=True,inspection_scope_checked=True,origin_assessments={s['id']:{'kind':'issuer_assertion','factual_origin_id':'issuer-business','rationale':'Same underlying issuer assertion; synthetic reviewed origin'} for s in d['sources']})
  r['claim_ids']=d['research_scope']['selected_claim_ids']
  d['rollout']['acknowledgements'].append({'actor':'synthetic-claim-reviewer','policy':e.POLICY,'policy_sha256':e.sha((fixtures.ROOT/'POLICY.md').read_bytes()),'acknowledged_at':'2026-10-03T00:00:00Z'})
 def runreport(self,d,root=None):return e.report(d,root or fixtures.ROOT,e.date('2026-10-10'),{'synthetic-reviewer':['source_verifier'],'synthetic-claim-reviewer':['claim_verifier']})
 def test_positive_scoped_source_finding(self):
  r=self.runreport(self.fixture());self.assertEqual(r['scope']['blockers'],[]);self.assertEqual(r['released_selected_claims'],1)
 def test_section_mode_does_not_fake_fullread(self):
  d=self.fixture();d['sources'][0]['original_body_inspected']=False;self.sign(d);r=self.runreport(d)
  self.assertEqual(r['released_selected_claims'],1);self.assertFalse(d['sources'][0]['original_body_inspected'])
 def test_unread_material_appendix_blocks(self):
  d=self.fixture();i=d['sources'][0]['inspection'];i['unresolved_material']=['Referenced closing-condition exhibit not inspected'];i['review']['inspection_sha256']=sc.inspection_digest(i);self.sign(d)
  r=self.runreport(d);self.assertEqual(r['released_selected_claims'],0);self.assertTrue(any('UNINSPECTED_MATERIAL_SECTION' in x for x in r['scope']['blockers']))
 def add_context(self,d,relation='temporal_context'):
  c=copy.deepcopy(d['claims'][0]);c['id']='later-intent';c['claim_type']='acquisition_intent';c['reviews']=[];c['predicate_review']={'supported_claim_type':None,'rationale':None};d['claims'].append(c)
  d['research_scope']['context_links'].append({'from':d['claims'][0]['id'],'to':c['id'],'relation':relation,'rationale':'Later intent does not contradict earlier narrow historical assertion; synthetic fixture','reviewed_by':'synthetic-reviewer'})
  d['research_plan']['routes'].append({'id':'later-unperformed','claim_ids':[c['id']],'company_ids':[c['company_id']],'claim_types':[c['claim_type']],'source_family':'direct_party','purpose':'primary','status':'unperformed','reason':'New lead, not searched'})
  return c
 def test_unrelated_context_unperformed_does_not_block_selected(self):
  d=self.fixture();self.add_context(d);self.sign(d);r=self.runreport(d)
  self.assertEqual(r['released_selected_claims'],1);self.assertEqual(len(r['augmented_observations']),2);self.assertEqual(r['augmented_observations'][1]['release_status'],'UNRELEASED_RESEARCH_OBSERVATION');self.assertEqual(r['whole_batch_source_coverage_audit']['status'],'INCOMPLETE_MATERIAL_ROUTE')
 def test_omitted_relevance_review_blocks(self):
  d=self.fixture();self.add_context(d);d['research_scope']['context_links']=[];self.sign(d);r=self.runreport(d)
  self.assertEqual(r['released_selected_claims'],0);self.assertTrue(any('CONTEXT_RELEVANCE_UNREVIEWED' in x for x in r['scope']['blockers']))
 def test_later_correction_cannot_be_projected_away(self):
  d=self.fixture();c=self.add_context(d,'contradiction');d['claims'][0]['contradictions']=[{'claim_id':c['id'],'status':'open'}];self.sign(d);r=self.runreport(d)
  self.assertEqual(r['released_selected_claims'],0);self.assertIn(c['id'],r['scope']['effective_context_claim_ids'])
 def test_dependency_cycle_terminates_and_missing_holds(self):
  d=self.fixture();c=self.add_context(d);c['dependencies']=[d['claims'][0]['id']];d['claims'][0]['dependencies']=[c['id'],'absent'];self.sign(d);r=self.runreport(d)
  self.assertEqual(r['released_selected_claims'],0);self.assertIn('MISSING_CONTEXT_DEPENDENCY:absent',r['scope']['blockers'])
 def test_stale_scope_review_cannot_migrate(self):
  d=self.fixture();d['research_scope']['reason']='Changed';r=self.runreport(d);self.assertIn('SCOPE_REVIEW_STALE_OR_MISSING',r['scope']['blockers'])
 def test_regulatory_and_issuer_origin_not_doublecounted(self):
  d=self.fixture();s=copy.deepcopy(d['sources'][0]);s['id']='issuer-filing';s['source_type']='regulatory_filing';s['publisher']='SEC';d['sources'].append(s);d['claims'][0]['evidence'].append({**d['claims'][0]['evidence'][0],'source_id':s['id']});self.sign(d)
  r=self.runreport(d);self.assertEqual(r['scope']['reviewed_origin_group_count'],1)
 def test_unproven_fullread_bool_not_enough_for_scoped_release(self):
  d=self.fixture();d['sources'][0].pop('inspection');self.sign(d);self.assertEqual(self.runreport(d)['released_selected_claims'],0)
 def test_link_only_contradiction_blocks_without_self_conflict(self):
  d=self.fixture();self.add_context(d,'contradiction');self.sign(d);r=self.runreport(d)
  self.assertEqual(r['released_selected_claims'],0);self.assertTrue(any('UNRESOLVED_CONTEXT_LINK' in x for x in r['scope']['blockers']))
 def test_reverse_contradiction_cannot_evade_closure(self):
  d=self.fixture();c=self.add_context(d,'contradiction');link=d['research_scope']['context_links'][0];link['from'],link['to']=link['to'],link['from'];self.sign(d)
  r=self.runreport(d);self.assertEqual(r['released_selected_claims'],0);self.assertIn(c['id'],r['scope']['effective_context_claim_ids'])
 def test_malformed_inspection_reported_hold(self):
  for value in ['bad',[],True]:
   d=self.fixture();d['sources'][0]['inspection']=value;self.sign(d);self.assertEqual(self.runreport(d)['released_selected_claims'],0)
