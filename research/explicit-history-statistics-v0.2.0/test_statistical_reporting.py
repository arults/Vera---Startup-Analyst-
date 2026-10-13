import unittest
from unittest.mock import patch
import statistical_reporting as reporting
from statistical_reporting import percentile_linear, operating_cluster_bootstrap as bootstrap, operating_uncertainty_report as report
from aj_explicit_history import History as H, Transition as T, State as S


def complete_mixture():
    return [H(str(i),str(i),S.PRE,5,(T(1,S.PRE,S.CLOSURE),) if i<4 else ()) for i in range(10)]


class ReportingTests(unittest.TestCase):
    def test_quantile_declared_linear_convention(self):
        self.assertEqual(percentile_linear([0,10,20,30],.25),7.5)
        self.assertEqual(percentile_linear([0,10,20,30],.5),15)
        self.assertEqual(percentile_linear([0,10,20,30],0),0)
        self.assertEqual(percentile_linear([0,10,20,30],1),30)
        self.assertEqual(percentile_linear([.3],.97),.3)
        self.assertEqual(percentile_linear([-1e308,1e308],.5),0)
        for values,q in (([],.5),([float('nan')],.5),([10**1000],.5),([True],.5),([1],2),([1],True)):
            with self.assertRaises(ValueError):percentile_linear(values,q)

    def test_seeded_complete_bootstrap_retains_all_draws(self):
        hs=complete_mixture()
        r=bootstrap(hs,3,200,73)
        self.assertEqual(r,bootstrap(hs,3,200,73))
        self.assertEqual(len(r.draws),200)
        self.assertEqual(r.completed_replicates,200)
        self.assertEqual(r.unsupported_draw_count,0)
        self.assertEqual(r.undefined_draw_count,0)
        self.assertAlmostEqual(r.primary_interval[0],.3)
        self.assertAlmostEqual(r.primary_interval[1],.9)
        self.assertEqual(r.primary_interval,(percentile_linear([d.mathematical_value for d in r.draws],.025),percentile_linear([d.mathematical_value for d in r.draws],.975)))
        for d in r.draws:
            expected=sum(int(c)>=4 for c in d.sampled_company_ids)/10
            self.assertAlmostEqual(d.mathematical_value,expected)
            self.assertEqual(d.source_round_ids,d.sampled_company_ids)

    def test_unequal_company_rounds_preserved(self):
        hs=[H('a1','A',S.PRE,5),H('a2','A',S.PRE,5),H('b1','B',S.CLOSURE,5)]
        r=bootstrap(hs,3,40,3)
        self.assertEqual({len(d.source_round_ids) for d in r.draws},{2,3,4})
        for d in r.draws:
            self.assertEqual(d.source_round_ids.count('a1'),d.sampled_company_ids.count('A'))
            self.assertEqual(d.source_round_ids.count('a2'),d.sampled_company_ids.count('A'))
            self.assertEqual(d.source_round_ids.count('b1'),d.sampled_company_ids.count('B'))
        self.assertEqual(r.zero_terminal_transitions,True)
        self.assertEqual(r.degenerate_distribution,False)
        self.assertIsNotNone(r.primary_interval)

    def test_supported_parent_unsupported_draws_withhold_without_filtering(self):
        hs=[H('a','A',S.PRE,1,(T(1,S.PRE,S.CLOSURE),)),H('b','B',S.PRE,2),H('c','C',S.PRE,4)]
        r=bootstrap(hs,3,100,11)
        expected=sum('C' not in d.sampled_company_ids and 'B' in d.sampled_company_ids for d in r.draws)
        self.assertGreater(expected,0)
        self.assertEqual(r.unsupported_draw_count,expected)
        self.assertEqual(len(r.draws),100)
        self.assertIsNone(r.primary_interval)
        self.assertEqual(r.interval_status,'WITHHELD_UNSUPPORTED_BOOTSTRAP_DRAWS')
        self.assertTrue(all(d.mathematical_value is not None for d in r.draws))

    def test_unsupported_parent_cannot_use_supported_subset_draws(self):
        hs=[H('a','A',S.PRE,1),H('b','B',S.POST,4)]
        r=bootstrap(hs,3,40,9)
        self.assertGreater(r.unsupported_draw_count,0)
        self.assertLess(r.unsupported_draw_count,40)
        self.assertIsNone(r.primary_interval)
        self.assertEqual(r.interval_status,'WITHHELD_FULL_SAMPLE_STATE_RISK_GAP')

    def test_undefined_draw_retained_and_no_subset_interval(self):
        real=reporting.at_horizon
        calls=0
        def interrupted(histories,horizon):
            nonlocal calls
            calls+=1
            if calls==3:raise ValueError('synthetic_undefined_statistic')
            return real(histories,horizon)
        with patch.object(reporting,'at_horizon',interrupted):
            r=bootstrap(complete_mixture(),3,20,2)
        self.assertEqual(r.undefined_draw_count,1)
        self.assertEqual(len(r.draws),20)
        self.assertEqual(r.draws[1].failure_reason,'ValueError:synthetic_undefined_statistic')
        self.assertIsNone(r.degenerate_distribution)
        self.assertIsNone(r.primary_interval)
        self.assertEqual(r.interval_status,'WITHHELD_UNDEFINED_BOOTSTRAP_DRAWS')

    def test_zero_events_and_degeneracy_are_explicit(self):
        hs=[H('a','A',S.PRE,4),H('b','B',S.PRE,4)]
        r=bootstrap(hs,2,30,1)
        self.assertTrue(r.zero_terminal_transitions)
        self.assertEqual(r.transition_count,0)
        self.assertTrue(r.degenerate_distribution)
        self.assertEqual(r.completed_replicates,30)
        self.assertEqual(r.interval_status,'WITHHELD_DEGENERATE_BOOTSTRAP_DISTRIBUTION')
        self.assertIsNone(r.primary_interval)

    def test_event_counts_are_landmark_specific(self):
        hs=[H('a','A',S.PRE,5,(T(4,S.PRE,S.CLOSURE),)),H('b','B',S.PRE,5)]
        r=bootstrap(hs,2,20,1)
        self.assertEqual(r.transition_count,0)
        self.assertEqual(r.terminal_transition_count,0)

    def test_not_run_is_not_zero_failed_draws(self):
        for hs,n,status in ((complete_mixture(),0,'NOT_RUN_ZERO_REPLICATES_REQUESTED'),
                            ([H('a','A',S.PRE,4)],20,'NOT_RUN_INSUFFICIENT_COMPANY_CLUSTERS')):
            r=bootstrap(hs,2,n,1)
            self.assertEqual(r.execution_status,status)
            self.assertEqual(r.completed_replicates,0)
            self.assertEqual(r.draws,())
            self.assertIsNone(r.unsupported_draw_count)
            self.assertIsNone(r.undefined_draw_count)
            self.assertIsNone(r.degenerate_distribution)

    def test_one_draw_is_insufficient_not_degenerate_interval(self):
        r=bootstrap(complete_mixture(),3,1,5)
        self.assertEqual(r.completed_replicates,1)
        self.assertEqual(r.interval_status,'WITHHELD_FEWER_THAN_TWO_REPLICATES')

    def test_comparison_requires_explicit_threshold(self):
        with self.assertRaises(TypeError):report(complete_mixture(),3)
        low=report(complete_mixture(),3,n_boot=200,seed=73,disagreement_threshold=0)
        high=report(complete_mixture(),3,n_boot=200,seed=73,disagreement_threshold=1)
        self.assertTrue(low.material_disagreement)
        self.assertFalse(high.material_disagreement)
        self.assertEqual(low.primary,high.primary)
        self.assertEqual(low.analytic,high.analytic)
        equal=report(complete_mixture(),3,n_boot=200,seed=73,disagreement_threshold=low.endpoint_max_absolute_difference)
        self.assertFalse(equal.material_disagreement)

    def test_unavailable_comparison_is_unknown_not_false(self):
        r=report([H('a','A',S.PRE,4),H('b','B',S.PRE,4)],2,n_boot=20,disagreement_threshold=.1)
        self.assertEqual(r.comparison_status,'NOT_COMPARABLE_INTERVAL_UNAVAILABLE')
        self.assertIsNone(r.material_disagreement)
        self.assertIsNone(r.endpoint_max_absolute_difference)

    def test_invalid_configuration_rejected(self):
        hs=complete_mixture()
        for n in (-1,True,2.5):
            with self.assertRaises(ValueError):bootstrap(hs,2,n)
        for seed in (True,1.1,'2'):
            with self.assertRaises(ValueError):bootstrap(hs,2,10,seed)
        for confidence in (0,1,float('nan'),True):
            with self.assertRaises(ValueError):bootstrap(hs,2,10,confidence_level=confidence)
        for threshold in (-1,2,float('nan'),True):
            with self.assertRaises(ValueError):report(hs,2,disagreement_threshold=threshold)


if __name__=='__main__':unittest.main(verbosity=2)
