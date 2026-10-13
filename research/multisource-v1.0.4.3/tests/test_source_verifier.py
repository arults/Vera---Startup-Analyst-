"""Independent mutation suite; metadata marked synthetic, not verified real evidence."""
import copy,datetime,json,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).parents[1];sys.path.insert(0,str(ROOT))
import evidence as e
import source_verifier as sv
class SourceVerifierTests(unittest.TestCase):
 def fixture(self):
  d=json.loads((ROOT/'demo.json').read_text());d['claims']=[d['claims'][-1]];c=d['claims'][0]
  d['sources']=[s for s in d['sources'] if s['id']==c['evidence'][0]['source_id']]
  s=d['sources'][0];s.update(original_body_inspected=True,origin_rationale='Synthetic original buyer statement.',upstream_urls=[s['url']])
  d['research_plan']={'policy':e.POLICY,'declared_at':'2026-10-01T00:00:00Z','retrospective_import':False,'search_cutoff':'2026-10-03',
   'entities':[{'company_id':c['company_id'],'aliases':['Inlightened','getinlightened.com'],'identity_basis':'Synthetic domain and issuer mapping.'}],
   'routes':[],'stopping_rationale':'Synthetic bounded case, all families assessed.','stop_kind':'claim_sufficient'}
  for n,(family,purpose) in enumerate([('native_platform','primary'),('direct_party','primary'),('legal_regulatory','alternative'),('independent_reporting','contradiction')]):
   d['research_plan']['routes'].append({'id':str(n),'claim_ids':[c['id']],'claim_types':[c['claim_type']],'company_ids':[c['company_id']],
    'purpose':purpose,'source_family':family,'status':'searched','query':'Synthetic Inlightened acquisition '+family,
    'searched_at':'2026-10-02T00:00:00Z','result':'Original buyer report or no counterevidence in synthetic fixture.',
    'result_class':'relevant_positive' if n==1 else 'no_relevant_result','receipt':'synthetic://receipt/'+str(n),
    'aliases_searched':['Inlightened','getinlightened.com'],'time_scope':'unrestricted','source_ids':[s['id']] if n==1 else []})
  self.sign(d);return d
 def sign(self,d):
  d['source_review']={'reviewer':'synthetic-reviewer','researcher':'demo_importer','plan_sha256':e.sha(e.stable(d['research_plan'])),
   'coverage_sha256':sv.coverage_digest(d),'reviewed_at':'2026-10-03T00:00:00Z','verdict':'SUFFICIENT_FOR_NARROW_CLAIM',
   'rationale':'Synthetic test assertion, not an authenticated approval.','origin_families_checked':True,'depth_checked':True,
   'claim_ids':[c['id'] for c in d['claims']],'approved_exception_route_ids':[]}
  d['rollout']['acknowledgements']=[{'actor':x,'policy':e.POLICY,'policy_sha256':e.sha((ROOT/'POLICY.md').read_bytes()),'acknowledged_at':'2026-10-01T00:00:00Z'} for x in ('synthetic-reviewer','demo_importer')]
 def assertBlocked(self,d,fragment):
  r=sv.audit(d);self.assertNotEqual(r['status'],'SUFFICIENT_FOR_NARROW_CLAIM');self.assertTrue(any(fragment in x for x in r['blockers']),r)
 def test_positive_structural_fixture(self):
  r=sv.audit(self.fixture());self.assertEqual(r['blockers'],[]);self.assertEqual(r['status'],'SUFFICIENT_FOR_NARROW_CLAIM')
  self.assertFalse(r['research_conclusion_authorized']);self.assertFalse(r['reviewer_identity_authenticated'])
 def test_native_only_not_outside_sufficient(self):
  d=self.fixture()
  for r in d['research_plan']['routes']:r['source_family']='native_platform'
  self.sign(d);self.assertBlocked(d,'OUTSIDE_SOURCES_NOT_SEARCHED')
 def test_all_blocked_not_sufficient(self):
  d=self.fixture()
  for r in d['research_plan']['routes']:r.update(status='blocked',reason='Authentication required')
  self.sign(d);self.assertBlocked(d,'MATERIAL_ACCESS_BLOCK')
 def test_all_na_not_sufficient(self):
  d=self.fixture()
  for r in d['research_plan']['routes']:r.update(status='not_applicable',reason='Budget priority')
  self.sign(d);self.assertBlocked(d,'NO_COMPLETED_PRIMARY_ROUTE')
 def test_company_substitution_invalidates_source_review(self):
  d=self.fixture();d['claims'][0]['company_id']='different-company';self.assertBlocked(d,'STALE_SOURCE_REVIEW')
 def test_source_origin_substitution_invalidates_source_review(self):
  d=self.fixture();d['sources'][0]['origin_family']='fake';self.assertBlocked(d,'STALE_SOURCE_REVIEW')
 def test_future_search(self):
  d=self.fixture();d['research_plan']['routes'][0]['searched_at']='2036-10-02T00:00:00Z';self.sign(d);self.assertBlocked(d,'SEARCH_POSTDATES_CUTOFF')
 def test_unperformed_material_route(self):
  d=self.fixture();d['research_plan']['routes'][0]['status']='unperformed';self.sign(d);self.assertBlocked(d,'UNPERFORMED_MATERIAL_ROUTE')
 def test_missing_original_body(self):
  d=self.fixture();d['sources'][0]['original_body_inspected']=False;self.sign(d);self.assertBlocked(d,'FULL_BODY_NOT_INSPECTED')
 def test_alias_gap(self):
  d=self.fixture();d['research_plan']['entities'][0]['aliases'].append('unsearched legal alias');self.sign(d);self.assertBlocked(d,'ALIASES_NOT_SEARCHED')
 def test_grouped_query(self):
  d=self.fixture();d['research_plan']['routes'][0]['grouped_query']=True;self.sign(d);self.assertBlocked(d,'GROUPED_QUERY_UNREVIEWED')
 def test_date_restriction(self):
  d=self.fixture();d['research_plan']['routes'][0]['time_scope']='2026 only';self.sign(d);self.assertBlocked(d,'UNJUSTIFIED_DATE_RESTRICTION')
 def test_budget_stop_not_sufficient(self):
  d=self.fixture();d['research_plan']['stop_kind']='budget_exhausted';self.sign(d);self.assertBlocked(d,'OPERATIONAL_STOP_NOT_SUFFICIENT')
 def test_optional_block_with_reviewed_alternative(self):
  d=self.fixture();r=copy.deepcopy(d['research_plan']['routes'][1]);r.update(id='optional',status='blocked',material=False,reason='Optional mirror unavailable',adequate_alternative_route_ids=['1']);d['research_plan']['routes'].append(r);self.sign(d);d['source_review']['approved_exception_route_ids']=['optional'];self.assertEqual(sv.audit(d)['blockers'],[])
 def test_fabricated_reviewer_never_authorizes_conclusion(self):
  d=self.fixture();d['source_review']['reviewer']='fabricated';d['rollout']['acknowledgements'].append({'actor':'fabricated','policy':e.POLICY,'policy_sha256':e.sha((ROOT/'POLICY.md').read_bytes()),'acknowledged_at':'2026-10-01T00:00:00Z'});r=sv.audit(d);self.assertFalse(r['research_conclusion_authorized'])
 def test_budget_not_exhausted_unknowns(self):
  d=self.fixture();d['research_plan']['stop_kind']='budget_exhausted';self.sign(d);d['source_review']['verdict']='EXHAUSTED_WITH_UNKNOWNS';self.assertBlocked(d,'VERDICT_STOP_MISMATCH')
 def test_counterevidence_cannot_be_ignored(self):
  d=self.fixture();d['research_plan']['routes'][3]['result_class']='relevant_counterevidence';self.sign(d);self.assertBlocked(d,'COUNTEREVIDENCE_DISPOSITION_MISSING')
 def test_counterevidence_resolved_narrowly(self):
  d=self.fixture();r=d['research_plan']['routes'][3];r['result_class']='relevant_counterevidence';r['counterevidence_disposition']={'claim_ids':r['claim_ids'],'status':'narrow_scope_exclusion','rationale':'Synthetic different earlier cancelled transaction; current narrow event independently identified.'};self.sign(d);self.assertEqual(sv.audit(d)['blockers'],[])
 def test_partial_counterevidence_disposition(self):
  d=self.fixture();r=d['research_plan']['routes'][3];r['claim_ids'].append('additional-claim');r['result_class']='relevant_counterevidence';r['counterevidence_disposition']={'claim_ids':[r['claim_ids'][0]],'status':'resolved','rationale':'Only first claim resolved'};self.sign(d);self.assertBlocked(d,'COUNTEREVIDENCE_DISPOSITION_MISSING')
 def test_stale_policy_acknowledgement(self):
  d=self.fixture();d['rollout']['acknowledgements'][0]['policy_sha256']='0'*64;self.assertBlocked(d,'POLICY_ACKNOWLEDGEMENTS_MISSING')
 def test_demo_preserves_abstention(self):
  d=json.loads((ROOT/'demo.json').read_text());r=e.report(d,ROOT,datetime.date(2026,10,10));self.assertEqual(r['native_changes'],0);self.assertIsNone(r['rates']);self.assertNotEqual(sv.audit(d)['status'],'SUFFICIENT_FOR_NARROW_CLAIM')
if __name__=='__main__':unittest.main(verbosity=2)
