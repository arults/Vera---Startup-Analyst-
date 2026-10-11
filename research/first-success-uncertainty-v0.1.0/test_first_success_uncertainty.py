import math
import unittest
from unittest.mock import patch
from collections import Counter
from dataclasses import asdict
import json

from aj_explicit_history import History as H, State as S, Transition as T, at_horizon
from first_success import InitialPostPolicy as P, success_at_horizon
from first_success_uncertainty import (SuccessEndpoint as E, COMPONENTS,
    first_success_ij_diagnostic as ij, first_success_cluster_bootstrap as boot,
    first_success_uncertainty_report as report)


def fixture():
    return [H('a:1','A:company',S.PRE,5,(T(1,S.PRE,S.POST),T(2,S.POST,S.CLOSURE))),
            H('a:2','A:company',S.POST,5), H('b','B',S.PRE,5,(T(2,S.PRE,S.CLOSURE),)),
            H('c','C',S.PRE,5), H('d','D',S.PRE,5)]


class FirstSuccessUncertaintyTests(unittest.TestCase):
    def test_endpoint_mandatory_and_enum_only(self):
        for fun in (ij, boot):
            with self.assertRaises(TypeError): fun(fixture(),3,P.BASELINE_QUALIFIED)
            with self.assertRaisesRegex(ValueError,'explicit_success_endpoint'):
                fun(fixture(),3,P.BASELINE_QUALIFIED,endpoint='incident_success_cif')

    def test_policy_mandatory_and_enum_only(self):
        for fun in (ij, boot):
            with self.assertRaisesRegex(ValueError,'explicit_initial_post'):
                fun(fixture(),3,'already_index_qualified_at_entry',endpoint=E.INCIDENT)
            with self.assertRaisesRegex(ValueError,'initial_post_not_incident'):
                fun(fixture(),3,P.REJECT,endpoint=E.INCIDENT)

    def test_initial_terminal_prior_success_remains_rejected(self):
        for state in (S.CLOSURE,S.ACQUISITION_UNKNOWN,S.SUCCESS_EXIT):
            hs=[H('x','X',state,3),H('y','Y',S.PRE,3)]
            for fun in (ij,boot):
                with self.assertRaisesRegex(ValueError,'endpoint_specific_prior_success'):
                    fun(hs,2,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED)

    def test_distinct_targets_and_all_round_denominator(self):
        hs=fixture()
        a=ij(hs,3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT)
        b=ij(hs,3,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED)
        self.assertAlmostEqual(a.point,.2)
        self.assertAlmostEqual(b.point,.4)
        self.assertNotEqual(a.variance,b.variance)
        self.assertAlmostEqual(a.variance,.0192)
        self.assertAlmostEqual(b.variance,.0768)

    def test_not_operating_occupancy(self):
        hs=fixture()
        r=ij(hs,3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT)
        self.assertAlmostEqual(at_horizon(hs,3).independent_operating_probability,.6)
        self.assertAlmostEqual(r.point,.2)
        self.assertNotIn('occupancy',r.method)

    def test_per_round_binomial_derivatives_without_censoring(self):
        hs=fixture()
        for endpoint in E:
            r=ij(hs,3,P.BASELINE_QUALIFIED,endpoint=endpoint)
            for h in hs:
                yes=(h.round_id=='a:1' or (h.round_id=='a:2' and endpoint==E.EVER_QUALIFIED))
                self.assertAlmostEqual(r.round_gradients[h.round_id][endpoint.value],(yes-r.point)/len(hs))

    def test_company_score_aggregation_keeps_multiple_rounds(self):
        r=ij(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED)
        for k in COMPONENTS:
            self.assertAlmostEqual(r.company_gradients['A:company'][k],
                r.round_gradients['a:1'][k]+r.round_gradients['a:2'][k])
        expected=sum(g[E.EVER_QUALIFIED.value]**2 for g in r.company_gradients.values())
        self.assertAlmostEqual(r.variance,expected)
        unclustered=sum(g[E.EVER_QUALIFIED.value]**2 for g in r.round_gradients.values())
        self.assertGreater(r.variance,unclustered)

    def test_mass_derivatives_and_covariance_symmetry(self):
        r=ij(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT)
        for k in COMPONENTS:
            self.assertAlmostEqual(sum(g[k] for g in r.round_gradients.values()),0)
            for j in COMPONENTS: self.assertEqual(r.covariance[k][j],r.covariance[j][k])
        for g in r.round_gradients.values():
            self.assertAlmostEqual(g['ever_qualified_probability'],g['baseline_qualified_fraction']+g['incident_success_cif'])
            self.assertAlmostEqual(sum(g[k] for k in COMPONENTS if k!='ever_qualified_probability'),0)

    def test_tied_events_competitor_and_censor(self):
        hs=[H('a','A',S.PRE,1,(T(1,S.PRE,S.POST),)),
            H('b','B',S.PRE,1,(T(1,S.PRE,S.CLOSURE),)),H('c','C',S.PRE,1)]
        r=ij(hs,1,P.REJECT,endpoint=E.INCIDENT)
        self.assertAlmostEqual(r.point,1/3)
        self.assertAlmostEqual(r.variance,2/27)
        self.assertIsNotNone(r.normal_diagnostic_interval)
        later=ij(hs,2,P.REJECT,endpoint=E.INCIDENT)
        self.assertIsNone(later.normal_diagnostic_interval)
        self.assertIn('RISK_GAP',later.interval_status)

    def test_censoring_point_matches_hand_calculation(self):
        hs=[H('a','A',S.PRE,4,(T(1,S.PRE,S.CLOSURE),)),H('b','B',S.PRE,4,(T(2,S.PRE,S.POST),)),
            H('c','C',S.PRE,1),H('d','D',S.PRE,4)]
        r=ij(hs,3,P.REJECT,endpoint=E.INCIDENT)
        self.assertEqual(r.point,.375)
        self.assertEqual(r.mathematical_probabilities['incident_success_cif'],.375)

    def test_zero_time_success_is_incident_not_baseline(self):
        hs=[H('a','A',S.PRE,3,(T(0,S.PRE,S.POST),)),H('b','B',S.POST,3),H('c','C',S.PRE,3)]
        r=ij(hs,0,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT)
        self.assertAlmostEqual(r.point,1/3)
        self.assertAlmostEqual(r.mathematical_probabilities['baseline_qualified_fraction'],1/3)

    def test_direct_success_exit_and_unknown_acquisition(self):
        hs=[H('a','A',S.PRE,3,(T(1,S.PRE,S.SUCCESS_EXIT),)),
            H('b','B',S.PRE,3,(T(1,S.PRE,S.ACQUISITION_UNKNOWN),))]
        r=boot(hs,3,P.REJECT,endpoint=E.INCIDENT,n_boot=10)
        self.assertEqual(r.first_success_event_count,1)
        self.assertEqual(r.competing_event_count,1)
        self.assertEqual(r.point,.5)

    def test_order_invariance_and_deterministic_draws(self):
        a=report(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED,n_boot=100,seed=7,disagreement_threshold=.1)
        b=report(list(reversed(fixture())),3,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED,n_boot=100,seed=7,disagreement_threshold=.1)
        self.assertEqual(a.analytic,b.analytic)
        self.assertEqual([d.mathematical_value for d in a.primary.draws],[d.mathematical_value for d in b.primary.draws])
        self.assertEqual(a,report(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED,n_boot=100,seed=7,disagreement_threshold=.1))

    def test_preserve_all_draws_company_occurrences_and_rounds(self):
        r=boot(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,n_boot=80,seed=12)
        self.assertEqual(len(r.draws),80)
        self.assertEqual([d.index for d in r.draws],list(range(80)))
        mapping={'A:company':('a:1','a:2'),'B':('b',),'C':('c',),'D':('d',)}
        for d in r.draws:
            self.assertEqual(len(d.sampled_company_ids),4)
            expected=Counter(x for c in d.sampled_company_ids for x in mapping[c])
            self.assertEqual(Counter(d.source_round_ids),expected)
        self.assertTrue(any(len(d.source_round_ids)!=5 for d in r.draws))

    def test_metadata_counts_use_first_events_before_horizon(self):
        r=boot(fixture(),1,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,n_boot=3)
        self.assertEqual((r.baseline_qualified_count,r.incident_risk_count_at_entry,r.first_success_event_count,r.competing_event_count),(1,4,1,0))

    def test_not_run_distinct_from_degenerate(self):
        r=boot(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,n_boot=0)
        self.assertIsNone(r.degenerate_distribution)
        self.assertIsNone(r.undefined_draw_count)
        self.assertIsNone(r.unsupported_draw_count)
        self.assertEqual(r.completed_replicates,0)
        self.assertEqual(r.draws,())
        self.assertIn('NOT_RUN',r.execution_status)

    def test_single_company_not_run_and_analytic_withheld(self):
        hs=fixture()[:2]
        r=report(hs,3,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED,n_boot=50,disagreement_threshold=.1)
        self.assertEqual(r.primary.completed_replicates,0)
        self.assertIn('INSUFFICIENT_COMPANY',r.primary.execution_status)
        self.assertIn('FEWER_THAN_TWO_COMPANY',r.analytic.interval_status)
        self.assertEqual(r.comparison_status,'NOT_COMPARABLE_INTERVAL_UNAVAILABLE')

    def test_one_replicate_withheld(self):
        r=boot(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,n_boot=1)
        self.assertEqual(r.completed_replicates,1)
        self.assertIsNone(r.primary_interval)
        self.assertIn('FEWER_THAN_TWO_REPLICATES',r.interval_status)

    def test_baseline_only_boundaries(self):
        hs=[H('a','A',S.POST,2),H('b','B',S.POST,2)]
        for endpoint,point in ((E.INCIDENT,0),(E.EVER_QUALIFIED,1)):
            r=report(hs,5,P.BASELINE_QUALIFIED,endpoint=endpoint,n_boot=10,disagreement_threshold=.1)
            self.assertEqual(r.primary.point,point)
            self.assertTrue(r.primary.degenerate_distribution)
            self.assertEqual(r.primary.unsupported_draw_count,0)
            self.assertIsNone(r.primary.primary_interval)
            self.assertIsNone(r.analytic.normal_diagnostic_interval)

    def test_no_event_supported_is_degenerate_not_not_run(self):
        hs=[H('a','A',S.PRE,5),H('b','B',S.PRE,5)]
        r=boot(hs,3,P.REJECT,endpoint=E.INCIDENT,n_boot=10)
        self.assertEqual(r.completed_replicates,10)
        self.assertEqual(r.undefined_draw_count,0)
        self.assertTrue(r.degenerate_distribution)
        self.assertIn('DEGENERATE',r.interval_status)

    def test_complete_absorption_supported_past_observation(self):
        hs=[H('a','A',S.PRE,1,(T(1,S.PRE,S.POST),)),H('b','B',S.PRE,1,(T(1,S.PRE,S.CLOSURE),))]
        r=report(hs,100,P.REJECT,endpoint=E.INCIDENT,n_boot=30,disagreement_threshold=.1)
        self.assertEqual(r.primary.unsupported_draw_count,0)
        self.assertIsNotNone(r.primary.primary_interval)
        self.assertIsNotNone(r.analytic.normal_diagnostic_interval)

    def test_full_sample_unsupported_withholds_both_intervals(self):
        hs=[H('a','A',S.PRE,1,(T(1,S.PRE,S.POST),)),H('b','B',S.PRE,2)]
        r=report(hs,5,P.REJECT,endpoint=E.INCIDENT,n_boot=40,disagreement_threshold=.1)
        self.assertEqual(r.primary.completed_replicates,40)
        self.assertIsNone(r.primary.primary_interval)
        self.assertIn('FULL_SAMPLE',r.primary.interval_status)
        self.assertIsNone(r.analytic.normal_diagnostic_interval)
        self.assertIsNone(r.material_disagreement)

    def test_supported_sample_unsupported_draws_not_filtered(self):
        hs=[H('a','A',S.PRE,1),H('b','B',S.PRE,5,(T(2,S.PRE,S.POST),)),H('c','C',S.PRE,5)]
        r=boot(hs,3,P.REJECT,endpoint=E.INCIDENT,n_boot=200,seed=0)
        self.assertNotIn('UNSUPPORTED',r.full_sample_support_status)
        self.assertGreater(r.unsupported_draw_count,0)
        self.assertEqual(len(r.draws),200)
        self.assertIsNone(r.primary_interval)
        self.assertIn('UNSUPPORTED_BOOTSTRAP_DRAWS',r.interval_status)

    def test_undefined_draw_retained_and_no_subset_interval(self):
        original=success_at_horizon
        calls=[0]
        def sometimes(*args,**kwargs):
            calls[0]+=1
            if calls[0]==3: raise ValueError('injected_test_failure')
            return original(*args,**kwargs)
        with patch('first_success_uncertainty.success_at_horizon',side_effect=sometimes):
            r=boot(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,n_boot=10)
        self.assertEqual(r.undefined_draw_count,1)
        self.assertEqual(r.completed_replicates,10)
        self.assertIsNone(r.degenerate_distribution)
        self.assertIsNone(r.primary_interval)
        self.assertEqual(r.draws[1].failure_reason,'ValueError:injected_test_failure')

    def test_matched_comparison_uses_selected_endpoint(self):
        for endpoint in E:
            r=report(fixture(),3,P.BASELINE_QUALIFIED,endpoint=endpoint,n_boot=100,disagreement_threshold=.1)
            self.assertEqual(r.primary.endpoint,r.analytic.endpoint)
            self.assertEqual(r.primary.initial_post_policy,r.analytic.initial_post_policy)
            self.assertEqual(r.primary.horizon,r.analytic.horizon)
            self.assertEqual(r.primary.confidence_level,r.analytic.confidence_level)
            self.assertEqual(r.primary.point,r.analytic.point)
            self.assertEqual(r.comparison_status,'COMPARABLE_MATCHED_FIRST_SUCCESS_ENDPOINT')
            self.assertAlmostEqual(r.endpoint_max_absolute_difference,max(abs(x-y) for x,y in zip(r.primary.primary_interval,r.analytic.normal_diagnostic_interval)))

    def test_disagreement_strict_threshold(self):
        r=report(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED,n_boot=50,disagreement_threshold=0)
        same=report(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.EVER_QUALIFIED,n_boot=50,disagreement_threshold=r.endpoint_max_absolute_difference)
        self.assertFalse(same.material_disagreement)

    def test_sequential_complete_success_roundoff_never_emits_false_interval(self):
        hs=[H(str(i),str(i),S.PRE,200,(T(i,S.PRE,S.POST),)) for i in range(5)]
        for endpoint in E:
            r=report(hs,200,P.REJECT,endpoint=endpoint,n_boot=100,seed=0,disagreement_threshold=.1)
            self.assertIsNone(r.analytic.normal_diagnostic_interval)
            self.assertIsNone(r.primary.primary_interval)
            self.assertTrue(r.primary.numerically_degenerate_distribution)
            self.assertEqual(len(r.primary.draws),100)
            self.assertEqual(r.comparison_status,"NOT_COMPARABLE_INTERVAL_UNAVAILABLE")

    def test_invalid_arguments(self):
        for bad in (True,-1,.5):
            with self.assertRaises(ValueError): boot(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,n_boot=bad)
        for bad in (True,.5):
            with self.assertRaises(ValueError): boot(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,seed=bad)
        for bad in (True,0,1,float('nan'),float('inf')):
            for fun in (ij,boot):
                with self.assertRaises(ValueError): fun(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,confidence_level=bad)
        for bad in (-1,True,float('inf'),10**1000):
            with self.assertRaises(ValueError): ij(fixture(),bad,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT)
        with self.assertRaises(ValueError): report(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,disagreement_threshold=float('nan'))

    def test_extreme_valid_confidence_level(self):
        r=ij(fixture(),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,confidence_level=math.nextafter(1.,0.))
        self.assertEqual(r.normal_diagnostic_interval,(0.,1.))

    def test_json_serializable_report_and_generator(self):
        r=report(iter(fixture()),3,P.BASELINE_QUALIFIED,endpoint=E.INCIDENT,n_boot=5,disagreement_threshold=.1)
        payload=json.loads(json.dumps(asdict(r),allow_nan=False))
        self.assertEqual(payload['primary']['endpoint'],'incident_success_cif')
        self.assertEqual(len(payload['primary']['draws']),5)


if __name__=='__main__': unittest.main(verbosity=2)
