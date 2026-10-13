import copy, json, unittest
from pathlib import Path
from neutral_preparer import prepare,validate_output,InvalidInput

def close(i,d,final='FALSE',position='TRUE',completed='TRUE'):
    return dict(id=i,date=d,completed=completed,position_produced=position,aggregate_complete=final,provenance={'hypothetical_assertion_id':i})
def event(i,d,terminal='FALSE',success='FALSE',closure='FALSE',operating='FALSE'):
    return dict(id=i,date=d,terminal=terminal,success=success,closure=closure,affirmative_operation=operating,provenance={'hypothetical_assertion_id':i})
def base():
    return dict(closes=[close('first','2021-01-01'),close('final','2021-03-01',final='TRUE',position='FALSE')],events=[],round_position_status='TRUE',close_ledger_complete='TRUE',offering_year=2020,admin_limit='2021-12-31',operating_last_positive='2021-06-01',entry_assertions=[{'id':'entry1','date':'2021-01-01','independent':'TRUE','provenance':{'hypothetical_assertion_id':'entry1'}}])

class Regression(unittest.TestCase):
    def test_final_no_new_position(self):
        o=prepare(base()); self.assertEqual(o['scenarios']['B']['candidate_origin'],'2021-03-01')
    def test_missing_round_position_semantics(self):
        f=base();f['round_position_status']='UNKNOWN';o=prepare(f)
        self.assertIsNone(o['scenarios']['B']['candidate_origin']);self.assertIsNotNone(o['scenarios']['A']['candidate_origin'])
    def test_unknown_close_status(self):
        f=base();f['closes'][0]['completed']='UNKNOWN';o=prepare(f)
        self.assertIsNone(o['scenarios']['A']['candidate_origin'])
    def test_unknown_terminal_status(self):
        f=base();f['events']=[event('t','2020-12-01',terminal='UNKNOWN')]
        self.assertEqual(prepare(f)['scenarios']['A']['entry_disposition'],'ENTRY_ORDER_OR_TERMINAL_STATUS_UNRESOLVED')
    def test_invalid_truthy_types(self):
        for value in (True,1,'yes','unknown',{},[]):
            f=base();f['closes'][0]['completed']=value
            with self.assertRaises(InvalidInput):prepare(f)
    def test_duplicate_event_identifiers(self):
        f=base();f['events']=[event('x','2021-02-01'),event('x','2021-04-01')]
        with self.assertRaises(InvalidInput):prepare(f)
    def test_distinct_same_day_conflict(self):
        f=base();f['events']=[event('terminal','2021-03-01',terminal='TRUE'),event('financing','2021-03-01',success='TRUE')]
        o=prepare(f);self.assertEqual(len(o['event_ledger']),2)
        self.assertEqual(o['scenarios']['B']['entry_disposition'],'ENTRY_ORDER_OR_TERMINAL_STATUS_UNRESOLVED')
        self.assertEqual(set(o['scenarios']['B']['relations'].values()),{'ORDER_UNRESOLVED'})
    def test_terminal_inside_span(self):
        f=base();f['events']=[event('t','2021-02-01',terminal='TRUE')];o=prepare(f)
        self.assertEqual(o['scenarios']['A']['relations']['t'],'AFTER');self.assertEqual(o['scenarios']['B']['relations']['t'],'BEFORE')
        self.assertEqual(o['scenarios']['B']['entry_disposition'],'KNOWN_NONINDEPENDENT')
    def test_entry_contradiction(self):
        f=base();f['events']=[event('t','2020-12-01',terminal='TRUE')]
        self.assertEqual(prepare(f)['scenarios']['A']['entry_disposition'],'ENTRY_CONFLICT')
    def test_unknown_entry(self):
        f=base();f['entry_assertions']=[]
        self.assertEqual(prepare(f)['scenarios']['A']['entry_disposition'],'ENTRY_UNKNOWN')
    def test_month_only_rejected(self):
        f=base();f['events']=[event('x','2021-01')]
        with self.assertRaises(InvalidInput):prepare(f)
    def test_interval_preserved(self):
        f=base();f['events']=[event('x',{'earliest':'2021-02-01','latest':'2021-04-01'},terminal='TRUE')]
        o=prepare(f);self.assertEqual(o['scenarios']['B']['relations']['x'],'ORDER_UNRESOLVED')
        self.assertEqual(o['event_ledger'],f['events'])
    def test_multiple_final_completions_held(self):
        f=base();f['closes'].append(close('extra','2021-04-01',final='TRUE'))
        self.assertIsNone(prepare(f)['scenarios']['B']['candidate_origin'])
    def test_multiple_first_close_order_held(self):
        f=base();f['closes'].append(close('other','2021-01-01'))
        self.assertIsNone(prepare(f)['scenarios']['A']['candidate_origin'])
    def test_financing_no_operation_extension(self):
        f=base();f['events']=[event('s','2021-09-01',success='TRUE')];o=prepare(f)
        self.assertEqual(o['operating_last_positive'],'2021-06-01');self.assertEqual(o['post_success_operating_state'],'NOT_INFERRED')
        self.assertEqual(o['analytical_endpoint_eligibility'],'NOT_EVALUATED')
    def test_event_report_and_admin(self):
        f=base();e=event('x','2021-09-01');e['reported']='2022-01-01';f['events']=[e,event('y','2022-01-01'),event('z',{'earliest':'2021-12-01','latest':'2022-01-01'})]
        self.assertEqual(prepare(f)['within_admin_window'],{'x':'WITHIN','y':'AFTER','z':'BOUNDARY_UNRESOLVED'})
    def test_dual_predicate_preserved(self):
        f=base();f['events']=[event('x','2021-09-01',terminal='TRUE',success='TRUE')]
        o=prepare(f);self.assertEqual(o['event_ledger'],f['events'])
    def test_round_position_contradiction_rejected(self):
        f=base();f['round_position_status']='FALSE'
        with self.assertRaises(InvalidInput):prepare(f)
    def test_permutation_semantics_and_provenance(self):
        f=base();f['events']=[event('z','2021-04-01'),event('a','2021-09-01')];g=copy.deepcopy(f)
        g['closes'].reverse();g['events'].reverse();a=prepare(f);b=prepare(g)
        self.assertEqual(a.pop('input_record'),f);self.assertEqual(b.pop('input_record'),g);self.assertEqual(a,b)
    def test_provenance_and_inputs_immutable(self):
        f=base();before=copy.deepcopy(f);o=prepare(f)
        self.assertEqual(f,before);self.assertEqual(o['input_record'],before);self.assertTrue(validate_output(f,o))
    def test_negative_entry_assertion(self):
        f=base();f['entry_assertions'][0]['independent']='FALSE'
        self.assertEqual(prepare(f)['scenarios']['A']['entry_disposition'],'KNOWN_NONINDEPENDENT_ASSERTION')
    def test_conflicting_entry_assertions(self):
        f=base();a=copy.deepcopy(f['entry_assertions'][0]);a['id']='entry2';a['independent']='FALSE';f['entry_assertions'].append(a)
        self.assertEqual(prepare(f)['scenarios']['A']['entry_disposition'],'ENTRY_CONFLICT')
    def test_entry_ids_and_provenance_required(self):
        for key in ('id','provenance'):
            f=base();del f['entry_assertions'][0][key]
            with self.assertRaises(InvalidInput):prepare(f)
        f=base();f['entry_assertions'].append(copy.deepcopy(f['entry_assertions'][0]))
        with self.assertRaises(InvalidInput):prepare(f)
    def test_origin_close_provenance(self):
        o=prepare(base());self.assertEqual(o['scenarios']['A']['origin_close_ids'],['first']);self.assertEqual(o['scenarios']['B']['origin_close_ids'],['final'])
    def test_position_after_aggregate_requires_review(self):
        f=base();f['closes'][0]['date']='2021-04-01'
        self.assertIsNone(prepare(f)['scenarios']['B']['candidate_origin'])
    def test_index_success_explicitly_not_evaluated(self):
        self.assertEqual(prepare(base())['index_relative_success_qualification'],'NOT_EVALUATED')
    def test_incomplete_ledger_holds_first_origin(self):
        f=base();f['close_ledger_complete']='UNKNOWN';o=prepare(f)
        self.assertIsNone(o['scenarios']['A']['candidate_origin']);self.assertEqual(o['scenarios']['B']['candidate_origin'],'2021-03-01')
    def test_mutations_rejected(self):
        f=base();f['events']=[event('t','2021-02-01',terminal='TRUE')];o=prepare(f)
        mutations=[lambda x:x['scenarios']['A'].update(candidate_origin='2021-02-01'),lambda x:x.update(event_ledger=[]),lambda x:x.update(operating_last_positive='2021-09-01'),lambda x:x.update(post_success_operating_state='TRUE'),lambda x:x['within_admin_window'].update(t='AFTER'),lambda x:x.update(offering_year=2021),lambda x:x['scenarios']['B'].update(entry_disposition='INDEPENDENT_ASSERTION_SUPPLIED'),lambda x:x['scenarios']['A']['relations'].update(t='BEFORE')]
        for mutate in mutations:
            broken=copy.deepcopy(o);mutate(broken)
            with self.assertRaises(InvalidInput):validate_output(f,broken)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Regression))
    Path(__file__).with_name('TEST_RESULT.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'status':'UNADOPTED_HYPOTHETICAL_CANDIDATE','real_rows':0,'estimator_calls':0},indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
