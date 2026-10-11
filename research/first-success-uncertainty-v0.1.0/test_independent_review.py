import math
import random
import unittest
from fractions import Fraction
from unittest.mock import patch
from collections import Counter
from aj_explicit_history import State as S, History as H, Transition as T
from first_success import InitialPostPolicy as P
import first_success_uncertainty as u
from independent_reference import weighted_reference, finite_difference
from review_fixtures import random_histories, mixed_fixture

class IndependentReview(unittest.TestCase):
    def test_random_rational_estimator_round_and_company_derivatives(self):
        max_error=0.
        cases=0
        for histories in random_histories(901225,120):
            for horizon in (0,2,5,9):
                for endpoint in u.SuccessEndpoint:
                    result=u.first_success_ij_diagnostic(histories,horizon,P.BASELINE_QUALIFIED,endpoint=endpoint)
                    expected=weighted_reference(histories,horizon)
                    for target in expected:
                        self.assertAlmostEqual(result.mathematical_probabilities[target],float(expected[target]),places=12)
                        for i,h in enumerate(histories):
                            reference=finite_difference(histories,horizon,target,{i})
                            observed=result.round_gradients[h.round_id][target]
                            error=abs(reference-observed)
                            max_error=max(error,max_error)
                            self.assertLess(error,2e-9,(histories,horizon,target,i,reference,observed))
                        for company in {h.company_id for h in histories}:
                            indices={i for i,h in enumerate(histories) if h.company_id==company}
                            reference=finite_difference(histories,horizon,target,indices)
                            observed=result.company_gradients[company][target]
                            self.assertLess(abs(reference-observed),2e-9)
                        self.assertAlmostEqual(sum(g[target] for g in result.round_gradients.values()),0,places=12)
                    self.assertAlmostEqual(result.variance,sum(finite_difference(histories,horizon,endpoint.value,{i for i,h in enumerate(histories) if h.company_id==company})**2 for company in {h.company_id for h in histories}),places=9)
                    cases+=1
        print(f'Independent exact-rational checks: {cases} endpoint/horizon cases; largest central-difference round error {max_error:.3g}')

    def test_complete_binary_known_solution(self):
        rows=[H(str(i),str(i),S.PRE,10,(T(1,S.PRE,S.POST),) if i<3 else ()) for i in range(8)]
        report=u.first_success_ij_diagnostic(rows,4,P.REJECT,endpoint=u.SuccessEndpoint.INCIDENT)
        self.assertEqual(report.point,3/8)
        self.assertAlmostEqual(report.variance,(3/8)*(5/8)/8,places=14)
        for i in range(8):
            self.assertEqual(report.round_gradients[str(i)]['incident_success_cif'],((i<3)-3/8)/8)

    def test_unequal_company_closed_form_variance(self):
        values=[('A',True),('A',True),('A',False),('B',False),('C',True),('C',False)]
        rows=[H(str(i),company,S.PRE,10,(T(1,S.PRE,S.POST),) if hit else ()) for i,(company,hit) in enumerate(values)]
        result=u.first_success_ij_diagnostic(rows,3,P.REJECT,endpoint=u.SuccessEndpoint.INCIDENT)
        self.assertEqual(result.point,.5)
        self.assertAlmostEqual(result.company_gradients['A']['incident_success_cif'],1/12)
        self.assertAlmostEqual(result.company_gradients['B']['incident_success_cif'],-1/12)
        self.assertAlmostEqual(result.company_gradients['C']['incident_success_cif'],0)
        self.assertAlmostEqual(result.variance,1/72)
        self.assertNotAlmostEqual(result.variance,.5*.5/6)

    def test_censor_competing_known_solution(self):
        rows=[H('0','a',S.PRE,4,(T(1,S.PRE,S.CLOSURE),)),H('1','b',S.PRE,4,(T(2,S.PRE,S.POST),)),H('2','c',S.PRE,1),H('3','d',S.PRE,4)]
        result=u.first_success_ij_diagnostic(rows,3,P.REJECT,endpoint=u.SuccessEndpoint.INCIDENT)
        self.assertEqual(result.point,3/8)
        # F = (1 - w0/W) * w1/(w1+w3); censor at 1 remains at risk at event 1.
        expected=[-3/32,7/32,1/32,-5/32]
        for i,v in enumerate(expected): self.assertAlmostEqual(result.round_gradients[str(i)]['incident_success_cif'],v)
        self.assertAlmostEqual(result.variance,sum(v*v for v in expected))

    def test_unequal_round_cluster_exact_draw_reconstruction(self):
        rows=mixed_fixture()
        for endpoint in u.SuccessEndpoint:
            report=u.first_success_cluster_bootstrap(rows,3,P.BASELINE_QUALIFIED,endpoint=endpoint,n_boot=257,seed=991)
            rng=random.Random(991)
            companies=sorted({h.company_id for h in rows})
            self.assertEqual(len(report.draws),257)
            for index,draw in enumerate(report.draws):
                picks=tuple(rng.choice(companies) for _ in companies)
                self.assertEqual(draw.sampled_company_ids,picks)
                reconstructed=[h for company in picks for h in rows if h.company_id==company]
                self.assertEqual(draw.index,index)
                self.assertEqual(draw.source_round_ids,tuple(h.round_id for h in reconstructed))
                reference=weighted_reference(reconstructed,3)[endpoint.value]
                self.assertAlmostEqual(draw.mathematical_value,float(reference),places=12)
            self.assertTrue(any(len(d.source_round_ids)!=len(rows) for d in report.draws))

    def test_baseline_target_and_later_closure(self):
        rows=[H('0','a',S.POST,9,(T(1,S.POST,S.CLOSURE),)),H('1','b',S.PRE,9,(T(1,S.PRE,S.POST),T(2,S.POST,S.CLOSURE))),H('2','c',S.PRE,9)]
        a=u.first_success_ij_diagnostic(rows,3,P.BASELINE_QUALIFIED,endpoint=u.SuccessEndpoint.INCIDENT)
        b=u.first_success_ij_diagnostic(rows,3,P.BASELINE_QUALIFIED,endpoint=u.SuccessEndpoint.EVER_QUALIFIED)
        self.assertAlmostEqual(a.point,1/3); self.assertAlmostEqual(b.point,2/3)
        self.assertNotEqual(a.round_gradients['0']['incident_success_cif'],b.round_gradients['0']['ever_qualified_probability'])

    def test_zero_one_cluster_empty_duplicate_terminal_initial(self):
        for endpoint in u.SuccessEndpoint:
            rows=[H('a','same',S.PRE,4,(T(1,S.PRE,S.POST),)),H('b','same',S.PRE,4)]
            b=u.first_success_cluster_bootstrap(rows,3,P.REJECT,endpoint=endpoint,n_boot=3)
            self.assertEqual(b.completed_replicates,0); self.assertIsNone(b.primary_interval)
            a=u.first_success_ij_diagnostic(rows,3,P.REJECT,endpoint=endpoint)
            self.assertIn('FEWER_THAN_TWO',a.interval_status)
            with self.assertRaisesRegex(ValueError,'empty_histories'):u.first_success_ij_diagnostic([],3,P.REJECT,endpoint=endpoint)
            with self.assertRaisesRegex(ValueError,'duplicate_economic_round'):u.first_success_cluster_bootstrap([rows[0],rows[0]],3,P.REJECT,endpoint=endpoint)
            for state in (S.CLOSURE,S.ACQUISITION_UNKNOWN,S.SUCCESS_EXIT):
                with self.assertRaisesRegex(ValueError,'endpoint_specific_prior_success'):u.first_success_cluster_bootstrap(rows+[H('terminal','other',state,4)],3,P.BASELINE_QUALIFIED,endpoint=endpoint)
            b=u.first_success_cluster_bootstrap(mixed_fixture(),3,P.BASELINE_QUALIFIED,endpoint=endpoint,n_boot=0)
            self.assertEqual(b.completed_replicates,0);self.assertIsNone(b.undefined_draw_count)

    def test_ties_censor_tail_and_absorption(self):
        rows=[H('s','a',S.PRE,1,(T(1,S.PRE,S.POST),)),H('c','b',S.PRE,1,(T(1,S.PRE,S.CLOSURE),)),H('z','c',S.PRE,1)]
        a=u.first_success_ij_diagnostic(rows,1,P.REJECT,endpoint=u.SuccessEndpoint.INCIDENT)
        self.assertAlmostEqual(a.point,1/3);self.assertNotIn('UNSUPPORTED',a.numerical_support_status)
        a=u.first_success_ij_diagnostic(rows,2,P.REJECT,endpoint=u.SuccessEndpoint.INCIDENT)
        self.assertIsNone(a.normal_diagnostic_interval);self.assertIn('UNSUPPORTED',a.numerical_support_status)
        a=u.first_success_ij_diagnostic(rows[:2],200,P.REJECT,endpoint=u.SuccessEndpoint.INCIDENT)
        self.assertEqual(a.point,.5);self.assertNotIn('UNSUPPORTED',a.numerical_support_status)

    def test_undefined_draws_retained_no_selection(self):
        original=u.success_at_horizon
        calls=[0]
        def failure(*args,**kwargs):
            calls[0]+=1
            if calls[0] in (2,4): raise ValueError('review_injected_undefined')
            return original(*args,**kwargs)
        with patch.object(u,'success_at_horizon',failure):
            report=u.first_success_cluster_bootstrap(mixed_fixture(),3,P.BASELINE_QUALIFIED,endpoint=u.SuccessEndpoint.INCIDENT,n_boot=20)
        self.assertEqual(len(report.draws),20);self.assertEqual(report.undefined_draw_count,2)
        self.assertIsNone(report.primary_interval);self.assertIsNone(report.degenerate_distribution)
        self.assertEqual([d.index for d in report.draws if d.mathematical_value is None],[0,2])
        self.assertIn('UNDEFINED',report.interval_status)
        for d in report.draws:
            if d.mathematical_value is None:self.assertIn('review_injected_undefined',d.failure_reason)

    def test_unsupported_draws_retained_no_selection(self):
        rows=[H('event','a',S.PRE,4,(T(1,S.PRE,S.POST),)),H('short','b',S.PRE,1),H('long','c',S.PRE,4)]
        report=u.first_success_cluster_bootstrap(rows,3,P.REJECT,endpoint=u.SuccessEndpoint.INCIDENT,n_boot=1000,seed=41)
        self.assertEqual(len(report.draws),1000)
        self.assertGreater(report.unsupported_draw_count,0)
        self.assertEqual(report.unsupported_draw_count,sum('UNSUPPORTED' in d.numerical_support_status for d in report.draws))
        self.assertIsNone(report.primary_interval)

    def test_roundoff_boundary_and_bootstrap_degeneracy(self):
        rows=[H(str(i),str(i),S.PRE,200,(T(i,S.PRE,S.POST),)) for i in range(5)]
        for endpoint in u.SuccessEndpoint:
            a=u.first_success_ij_diagnostic(rows,200,P.REJECT,endpoint=endpoint)
            self.assertIsNone(a.normal_diagnostic_interval)
            b=u.first_success_cluster_bootstrap(rows,200,P.REJECT,endpoint=endpoint,n_boot=100,seed=0)
            self.assertTrue(b.numerically_degenerate_distribution)
            self.assertIsNone(b.primary_interval)
            self.assertEqual(b.completed_replicates,100)

    def test_comparison_positive_branch(self):
        rows=[H(str(i),str(i),S.PRE,10,(T(1,S.PRE,S.POST),) if i<3 else ()) for i in range(8)]
        for endpoint in u.SuccessEndpoint:
            for threshold in (0,1):
                result=u.first_success_uncertainty_report(rows,4,P.REJECT,endpoint=endpoint,disagreement_threshold=threshold,n_boot=101,seed=17,confidence_level=.8)
                self.assertEqual(result.comparison_status,'COMPARABLE_MATCHED_FIRST_SUCCESS_ENDPOINT')
                expected=max(abs(a-b) for a,b in zip(result.primary.primary_interval,result.analytic.normal_diagnostic_interval))
                self.assertEqual(result.endpoint_max_absolute_difference,expected)
                self.assertEqual(result.material_disagreement,expected>threshold)
                self.assertEqual(result.primary.confidence_level,.8)
                self.assertEqual(result.analytic.confidence_level,.8)

    def test_matched_report_and_extreme_confidence(self):
        for endpoint in u.SuccessEndpoint:
            result=u.first_success_uncertainty_report(mixed_fixture(),3,P.BASELINE_QUALIFIED,endpoint=endpoint,disagreement_threshold=.1,n_boot=101,seed=900,confidence_level=.8)
            for attr in ('endpoint','horizon','initial_post_policy','confidence_level','point'):
                self.assertEqual(getattr(result.primary,attr),getattr(result.analytic,attr))
            if result.primary.primary_interval is not None and result.analytic.normal_diagnostic_interval is not None:
                expected=max(abs(a-b) for a,b in zip(result.primary.primary_interval,result.analytic.normal_diagnostic_interval))
                self.assertEqual(result.endpoint_max_absolute_difference,expected)
                self.assertEqual(result.material_disagreement,expected>.1)
            high=u.first_success_ij_diagnostic(mixed_fixture(),3,P.BASELINE_QUALIFIED,endpoint=endpoint,confidence_level=math.nextafter(1.,0.))
            self.assertTrue(all(math.isfinite(x) for x in high.normal_diagnostic_interval))

if __name__=='__main__':unittest.main(verbosity=2)
