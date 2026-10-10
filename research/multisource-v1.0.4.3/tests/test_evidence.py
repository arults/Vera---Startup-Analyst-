import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evidence import *
ROOT=Path(__file__).resolve().parents[1]

class EvidenceTests(unittest.TestCase):
    def setUp(self): self.d=json.loads((ROOT/'demo.json').read_text())
    def accepted(self):
        c=self.d['claims'][2]
        c['identity']['mapping_review_status']='verified'
        c['predicate_review']={'supported_claim_type':c['claim_type'],'rationale':'Synthetic semantic assessment of completed-act wording'}
        c['reviews']=[{'reviewer':'independent_test_reviewer','decision':'accept','rationale':'Synthetic test review only, not real adjudication','identity_checked':True,'reviewed_at':'2026-10-10T13:00:00Z','claim_sha256':digest_claim(c),'source_snapshot_sha256':source_snapshot(self.d)}]
        return c
    def adjudicate(self,c): return adjudicate(c,{s['id']:s for s in self.d['sources']},date('2026-10-10'))
    def test_demo_valid(self): self.assertEqual(validate(self.d,ROOT),[])
    def test_demo_three_held(self): self.assertEqual(report(self.d,ROOT,date('2026-10-10'))['held_observations'],3)
    def test_narrow_buyer_claim_can_be_accepted(self): self.assertEqual(self.adjudicate(self.accepted())['status'],'ACCEPTED_ATTRIBUTED_OBSERVATION')
    def test_narrow_unknown_terms_do_not_block(self): self.assertIn('shareholder_consideration',self.adjudicate(self.accepted())['unknowns'])
    def test_acquisition_does_not_create_payout(self):
        r=self.adjudicate(self.accepted()); self.assertIsNone(r['state_transition']);self.assertFalse(r['numeric_prior_eligible'])
    def test_no_estimation_even_accepted(self): self.assertFalse(self.adjudicate(self.accepted())['estimation_eligible'])
    def test_period_not_point(self): self.assertIsNone(self.adjudicate(self.d['claims'][0])['point_censor_date'])
    def test_unknown_retrieval_is_visible(self): self.assertIsNone(self.adjudicate(self.accepted())['freshness'][0]['retrieval_age_days'])
    def test_prior_promotion_fails(self):
        self.d['prior_promotion_enabled']=True; self.assertTrue(validate(self.d,ROOT))
    def test_dataset_override_fails(self):
        self.d['dataset']='native'; self.assertTrue(validate(self.d,ROOT))
    def test_registry_not_operating(self):
        c=self.accepted(); c['claim_type']='operating_activity'; self.d['sources'][2]['source_type']='official_registry';self.assertIn('NO_CLAIM_APPROPRIATE_AUTHORITY',self.adjudicate(c)['reasons'])
    def test_ctr_not_closure(self):
        c=self.accepted(); c['claim_type']='reporting_termination';self.assertIsNone(self.adjudicate(c)['state_transition'])
    def test_safe_cap_not_priced_round(self):
        c=self.accepted();c['claim_type']='safe_cap';self.assertIsNone(self.adjudicate(c)['state_transition'])
    def test_petition_not_liquidation(self):
        c=self.accepted();c['claim_type']='final_liquidation';self.d['sources'][2]['source_type']='court_petition';self.assertIn('NO_CLAIM_APPROPRIATE_AUTHORITY',self.adjudicate(c)['reasons'])
    def test_enterprise_value_not_investor_return(self):
        c=self.accepted();c['claim_type']='realized_investor_return';self.assertIn('SECURITY_ISSUER_CHAIN_UNVERIFIED',self.adjudicate(c)['reasons'])
    def test_missing_full_body_holds(self):
        c=self.accepted();self.d['sources'][2]['original_body_inspected']=False;self.assertIn('FULL_BODY_NOT_INSPECTED',self.adjudicate(c)['reasons'])
    def test_identity_pending_holds(self):
        c=self.accepted();c['identity']['mapping_review_status']='pending';self.assertIn('IDENTITY_REVIEW_PENDING',self.adjudicate(c)['reasons'])
    def test_name_only_holds(self):
        c=self.accepted();c['identity']['medium_identifiers']=[{'kind':'name','value':'Inlightened','provenance':'headline'}];self.assertIn('IDENTITY_UNRESOLVED',self.adjudicate(c)['reasons'])
    def test_open_conflict_holds(self):
        c=self.accepted();c['contradictions']=[{'claim_id':self.d['claims'][0]['id'],'status':'open'}];self.assertIn('OPEN_CONTRADICTION',self.adjudicate(c)['reasons'])
    def test_conflicting_review_holds(self):
        c=self.accepted();c['reviews'].append({**c['reviews'][0],'reviewer':'another','decision':'hold'});self.assertIn('REVIEW_DISAGREEMENT',self.adjudicate(c)['reasons'])
    def test_self_review_invalid(self):
        c=self.accepted();c['reviews'][0]['reviewer']=c['collector'];self.assertTrue(validate(self.d,ROOT))
    def test_claim_change_invalidates_review(self):
        c=self.accepted();c['assertion']='Modified';self.assertTrue(validate(self.d,ROOT))
    def test_source_change_invalidates_review(self):
        self.accepted();self.d['sources'][2]['source_type']='official_registry';self.assertTrue(validate(self.d,ROOT))
    def test_origin_change_invalidates_review(self):
        self.accepted();self.d['sources'][2]['origin_family']='independent';self.assertTrue(validate(self.d,ROOT))
    def test_future_publication_holds(self):
        c=self.accepted();self.d['sources'][2]['publication_date']='2027-01-01';self.assertIn('SOURCE_POSTDATES_AS_OF',self.adjudicate(c)['reasons'])
    def test_future_event_holds(self):
        c=self.accepted();c['time']['end']='2027-01-01';self.assertIn('EVENT_POSTDATES_AS_OF',self.adjudicate(c)['reasons'])
    def test_excerpt_tamper_fails(self):
        self.d['claims'][2]['evidence'][0]['excerpt']='Invented';self.assertTrue(validate(self.d,ROOT))
    def test_capture_tamper_fails(self):
        self.d['sources'][2]['capture_sha256']='0'*64;self.assertTrue(validate(self.d,ROOT))
    def test_traversal_fails(self):
        self.d['sources'][2]['capture']='../outcome-wave1/usage.json';self.assertTrue(validate(self.d,ROOT))
    def test_secret_url_fails(self):
        self.d['sources'][2]['url']='https://user:pass@example.org/';self.assertTrue(validate(self.d,ROOT))
    def test_query_token_url_fails(self):
        self.d['sources'][2]['url']+='?token=secret';self.assertTrue(validate(self.d,ROOT))
    def test_duplicate_claim_invalid(self):
        self.d['claims'].append(copy.deepcopy(self.d['claims'][0]));self.assertTrue(validate(self.d,ROOT))
    def test_invalid_interval_fails(self):
        self.d['claims'][0]['time']['start']='2030-01-01';self.assertTrue(validate(self.d,ROOT))
    def test_event_activity_period_fails(self):
        self.d['claims'][2]['time']={'kind':'activity_period','start':'2023-08-01','end':'2023-08-14'};self.assertTrue(validate(self.d,ROOT))
    def test_report_deterministic(self): self.assertEqual(report(self.d,ROOT,date('2026-10-10')),report(self.d,ROOT,date('2026-10-10')))
    def test_native_pins_unchanged(self):
        for path,digest in json.loads((ROOT/'native-pins.json').read_text()).items():
            if not (ROOT.parent/path).is_file(): self.skipTest('Original archive unavailable; portable manifest does not certify native-byte comparison')
            self.assertEqual(sha((ROOT.parent/path).read_bytes()),digest)
if __name__=='__main__': unittest.main()

class PredicateTests(unittest.TestCase):
    setUp=EvidenceTests.setUp
    accepted=EvidenceTests.accepted
    adjudicate=EvidenceTests.adjudicate
    def test_ctr_retyped_cessation_is_not_entailed(self):
        c=self.accepted(); c['claim_type']='business_cessation'
        c['predicate_review']={'supported_claim_type':'reporting_termination','rationale':'Actual filing only terminates reporting'}
        self.d['sources'][2]['source_type']='regulatory_filing'
        self.assertIn('PREDICATE_NOT_REVIEWED',self.adjudicate(c)['reasons'])
    def test_intent_retyped_completed_is_not_entailed(self):
        c=self.accepted();c['predicate_review']['supported_claim_type']='acquisition_intent'
        self.assertIn('PREDICATE_NOT_REVIEWED',self.adjudicate(c)['reasons'])
    def test_asset_retyped_control_is_not_entailed(self):
        c=self.accepted();c['claim_type']='control_transfer';c['predicate_review']['supported_claim_type']='asset_acquisition'
        self.assertIn('PREDICATE_NOT_REVIEWED',self.adjudicate(c)['reasons'])
    def test_same_family_copies_count_once(self):
        c=self.accepted(); original=self.d['sources'][2]
        for i in range(20):
            s={**original,'id':'copy'+str(i),'publisher':'Publisher'+str(i)};self.d['sources'].append(s)
            c['evidence'].append({**c['evidence'][0],'source_id':s['id']})
        r=self.adjudicate(c);self.assertEqual(r['declared_origin_family_count'],1);self.assertEqual(r['publisher_count'],21)
    def test_official_registry_positive_legal_status(self):
        c=self.accepted(); c['claim_type']='legal_active'; c['predicate_review']['supported_claim_type']='legal_active';self.d['sources'][2]['source_type']='official_registry'
        self.assertEqual(self.adjudicate(c)['status'],'ACCEPTED_ATTRIBUTED_OBSERVATION')
    def test_ctr_positive_reporting_termination(self):
        c=self.accepted();c['claim_type']='reporting_termination';c['predicate_review']['supported_claim_type']='reporting_termination';self.d['sources'][2]['source_type']='regulatory_filing'
        self.assertEqual(self.adjudicate(c)['status'],'ACCEPTED_ATTRIBUTED_OBSERVATION')
    def test_news_positive_secondary_only(self):
        c=self.accepted();s=self.d['sources'][2];s['source_type']='independent_reporting';s['editorial_authority_rationale']='Named reporting, original sources inspected; synthetic fixture'
        r=self.adjudicate(c);self.assertEqual(r['status'],'ACCEPTED_ATTRIBUTED_OBSERVATION');self.assertEqual(r['evidence_tier'],'SECONDARY_ATTRIBUTED')
    def test_untrusted_reviewer_never_released(self):
        c=self.accepted();r=report(self.d,ROOT,date('2026-10-10'))['augmented_observations'][2]
        self.assertEqual(r['release_status'],'UNRELEASED_RESEARCH_OBSERVATION')
    def test_public_entrypoint_rejects_changed_source(self):
        self.accepted();self.d['sources'][2]['origin_family']='changed'
        with self.assertRaises(ValueError): report(self.d,ROOT,date('2026-10-10'))

class AdditionalBoundaryTests(unittest.TestCase):
    setUp=EvidenceTests.setUp
    accepted=EvidenceTests.accepted
    adjudicate=EvidenceTests.adjudicate
    def test_public_filing_query_and_page_fragment_allowed(self):
        for url in ['https://www.sec.gov/filing?id=123#page=4','https://find-and-update.company-information.service.gov.uk/search?companyNumber=123']:
            self.assertTrue(public_url(url))
    def test_signed_or_access_token_urls_rejected(self):
        for url in ['https://example.org/?access_token=abc','https://example.org/?signature=abc','https://example.org/#access_token=secret']:
            self.assertFalse(public_url(url))
    def test_empty_strong_id_cannot_bypass_identity(self):
        c=self.accepted();c['identity']['strong_ids']=['',{}];c['identity']['medium_identifiers']=[]
        self.assertIn('IDENTITY_UNRESOLVED',self.adjudicate(c)['reasons'])
