"""Fail-closed tests for a deliberately exact-two-row adapter, not synthetic source proof."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import copy,importlib.util,json,tempfile,unittest
P=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('admission_adapter',P/'scripts/admission_adapter.py');A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)

class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.original=A.load_bundle()
    def test_approved_two_rows_admitted_only_to_research(self):
        ledger=A.build_ledger(self.original)
        self.assertEqual(ledger['counts'],{'canonical_research_companies':2,'canonical_research_rounds':2,'research_layer_b_rows':2,'production_admissions':0,'estimation_eligible_rows':0})
        self.assertFalse(any(ledger['promotion_gates'].values()))
    def test_all_downstream_unknowns_preserve_accepted_stages(self):
        ledger=A.build_ledger(self.original)
        for row in ledger['stage_ledger']:
            self.assertEqual(row['stages']['aggregate_funded_status'],'ACCEPTED_PLATFORM_OBSERVED')
            self.assertEqual(row['stages']['outcomes'],'UNKNOWN_NOT_ADJUDICATED')
            self.assertEqual(row['stages']['estimator'],'SUPPRESSED')
        self.assertTrue(all(x['does_not_erase_earlier_accepted_stages'] for x in ledger['unresolved_ledger']))
    def test_caps_remain_nonoperative_nonpriced_metadata(self):
        for row in A.build_ledger(self.original)['canonical_rounds']:
            self.assertIsNone(row['valuation_cap']);self.assertIsNone(row['comparable_valuation'])
            self.assertGreater(row['offered_valuation_cap']['amount_usd'],0)
            self.assertFalse(row['offered_valuation_cap']['operative_individual_terms_verified'])
    def test_blank_private_contracts_do_not_block_approved_public_funding(self):
        for row in A.build_ledger(self.original)['canonical_rounds']:
            self.assertFalse(row['funding_observation']['individual_executed_contracts_verified'])
            self.assertTrue(row['research_layer_b_eligible'])
    def test_no_invented_cohost_or_amendment_bridge(self):
        ledger=A.build_ledger(self.original)
        self.assertEqual(ledger['cohost_bridges'],[]);self.assertEqual(ledger['amendment_bridges'],[])
        self.assertTrue(all(not r['cohost_review']['complete_cross_platform_deduplication'] for r in ledger['canonical_rounds']))
    def test_source_amount_precision_preserved(self):
        row=next(x for x in A.build_ledger(self.original)['canonical_rounds'] if x['source_url'].endswith('/phantom-phood'))
        d=row['funding_observation']['all_source_displays'];self.assertEqual((d['campaign_hero_usd'],d['phantom_footer_usd'],d['timeline_successfully_raised_usd']),('39645','39646','39645.69'))
    def test_byte_identical_replay(self):
        self.assertEqual(A.encode(A.build_ledger(self.original)),A.encode(A.build_ledger(A.load_bundle())))
    def test_frozen_inputs_unchanged(self):
        before={k:A.sha(v) for k,v in self.original['raw'].items()};A.build_ledger(self.original)
        self.assertEqual(before,{k:A.sha(v) for k,v in A.load_bundle()['raw'].items()})
    def test_atomic_nonoverwrite_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json';payload=b'complete\n'
            self.assertEqual(A.atomic_create(p,payload),'CREATED_IMMUTABLE_RELEASE')
            self.assertEqual(A.atomic_create(p,payload),'UNCHANGED_IDENTICAL_REPLAY')
            with self.assertRaises(A.AdmissionError):A.atomic_create(p,b'changed\n')
            self.assertEqual(p.read_bytes(),payload);self.assertEqual(list(Path(tmp).iterdir()),[p])
    def test_concurrent_identical_atomic_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json'
            with ThreadPoolExecutor(2) as ex:results=list(ex.map(lambda _:A.atomic_create(p,b'whole'),range(2)))
            self.assertEqual(p.read_bytes(),b'whole');self.assertEqual(results.count('CREATED_IMMUTABLE_RELEASE'),1)
    def test_existing_release_matches_recomputed_payload(self):
        self.assertEqual((P/'releases/v0.3.0/canonical-research-ledger.json').read_bytes(),A.encode(A.build_ledger(self.original)))

def rejection_test(name,mutate):
    def test(self):
        b=copy.deepcopy(self.original);mutate(b)
        with self.assertRaises((A.AdmissionError,KeyError)):A.build_ledger(b)
    test.__name__='test_reject_'+name;return test

mutations={
 'changed_manifest':lambda b:b['manifest'].update(version='forged'),
 'wrong_matrix_hash':lambda b:b['review'].update(matrix_sha256='0'*64),
 'wrong_decision_hash':lambda b:b['decisions'].update(review_sha256='0'*64),
 'changed_original_source_bytes':lambda b:b['raw'].__setitem__('phantom-phood__form_c',b['raw']['phantom-phood__form_c']+b'!'),
 'missing_original_source_bytes':lambda b:b['raw'].pop('stockcard__native_timeline'),
 'extra_unreviewed_round':lambda b:b['matrix']['proposals'].append(copy.deepcopy(b['matrix']['proposals'][0])),
 'missing_independent_review':lambda b:b['review']['checks'][0].update(bounded_identity_and_round_independently_accepted=False),
 'jev_without_review':lambda b:b['review'].update(checks=[]),
 'name_only_identity':lambda b:b['matrix']['proposals'][0]['criteria'][1].update(evidence='Name similarity alone'),
 'intermediary_as_issuer':lambda b:b['matrix']['proposals'][0]['proposal'].update(canonical_company_id='intermediary-0001751525'),
 'conflicting_strong_identity':lambda b:b['matrix']['proposals'][0]['proposal'].update(legal_name='Different Issuer Inc.'),
 'ambiguous_coissuer':lambda b:b['matrix']['proposals'][0]['criteria'][1].update(status='HOLD_COISSUER'),
 'missing_launch':lambda b:b['matrix']['proposals'][0]['proposal'].update(first_live_date=None),
 'deadline_as_completion':lambda b:b['matrix']['proposals'][1]['proposal'].update(completion_date='2023-02-24'),
 'prior_year_launch':lambda b:b['matrix']['proposals'][0]['proposal'].update(first_live_date='2019-02-14',offering_year=2019),
 'close_year_as_cohort':lambda b:b['matrix']['proposals'][1]['proposal'].update(offering_year=2023),
 'pending_positive_amount':lambda b:b['matrix']['proposals'][0]['proposal'].update(status='pending'),
 'failed_positive_amount':lambda b:b['matrix']['proposals'][0]['proposal'].update(status='failed'),
 'template_only_not_funded':lambda b:b['matrix']['proposals'][0]['criteria'][5].update(status='NOT_ESTABLISHED'),
 'wrong_native_id':lambda b:b['matrix']['proposals'][0].update(native_offering_id=1759),
 'wrong_canonical_id':lambda b:b['matrix']['proposals'][0]['proposal'].update(round_id='wrong'),
 'duplicate_url':lambda b:b['matrix']['proposals'][1].update(campaign_url='https://republic.com/phantom-phood'),
 'duplicate_canonical_round':lambda b:b['matrix']['proposals'][1]['proposal'].update(round_id=b['matrix']['proposals'][0]['proposal']['round_id']),
 'cap_as_priced_value':lambda b:b['matrix']['proposals'][0]['proposal'].update(comparable_valuation=12000000),
 'lost_offered_cap_scope':lambda b:b['matrix']['proposals'][0]['proposal'].pop('valuation_cap_scope'),
 'invented_final_cap':lambda b:b['matrix']['proposals'][0]['proposal'].update(valuation_cap=5000000),
 'cohost_absence_claim':lambda b:b['matrix']['proposals'][0]['proposal'].update(cohost_platforms_scope='All cohosts ruled out globally'),
 'amount_precision_loss':lambda b:b['matrix']['proposals'][0]['source_amounts'].update(timeline_successfully_raised_usd='39646'),
 'same_offering_tranche_as_new_round':lambda b:b['matrix']['proposals'].append({**copy.deepcopy(b['matrix']['proposals'][0]),'native_offering_id':9999}),
 'sequential_round_without_new_review':lambda b:b['matrix']['proposals'].append({**copy.deepcopy(b['matrix']['proposals'][1]),'campaign_url':'https://republic.com/stockcard-2'}),
 'estimator_promotion':lambda b:b['matrix']['proposals'][0]['proposal'].update(estimation_eligible=True),
 'production_promotion':lambda b:b['decisions']['recommendations'][0].update(production_admitted=True),
 'global_completion':lambda b:b['decisions'].update(phase_complete=True),
 'census_or_rate_promotion':lambda b:b['decisions'].update(numeric_rates_promoted=2),
}
for name,mutation in mutations.items():setattr(AdapterTests,'test_reject_'+name,rejection_test(name,mutation))
if __name__=='__main__':unittest.main(verbosity=2)
