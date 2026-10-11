import unittest
import random
from aj_explicit_history import State as S, History as H, Transition as T, validate, at_horizon
from first_success import InitialPostPolicy as P, first_events, success_trajectory, success_at_horizon


class FirstSuccessTests(unittest.TestCase):
    def test_success_then_closure_retains_success(self):
        hs = [H('a','A',S.PRE,3,(T(1,S.PRE,S.POST),T(2,S.POST,S.CLOSURE)))]
        r = success_at_horizon(hs,3,P.REJECT)
        self.assertEqual(r.incident_success_cif,1)
        self.assertEqual(at_horizon(hs,3).independent_operating_probability,0)
        self.assertEqual(r.competing_cif,0)

    def test_direct_success_exit_counts_once(self):
        hs = [H('a','A',S.PRE,3,(T(1,S.PRE,S.SUCCESS_EXIT),))]
        self.assertEqual(success_at_horizon(hs,3,P.REJECT).incident_success_cif,1)

    def test_initial_post_requires_explicit_interpretation(self):
        hs = [H('a','A',S.POST,3)]
        with self.assertRaisesRegex(ValueError,'initial_post_not_incident'):
            success_at_horizon(hs,2,P.REJECT)
        with self.assertRaisesRegex(ValueError,'explicit_initial_post'):
            success_at_horizon(hs,2,'already_index_qualified_at_entry')
        with self.assertRaises(TypeError):
            success_at_horizon(hs,2)

    def test_baseline_post_is_not_incident_success(self):
        hs = [H('a','A',S.POST,3,(T(1,S.POST,S.SUCCESS_EXIT),))]
        r = success_at_horizon(hs,3,P.BASELINE_QUALIFIED)
        self.assertEqual(r.baseline_qualified_fraction,1)
        self.assertEqual(r.incident_success_cif,0)
        self.assertEqual(r.ever_qualified_probability,1)
        self.assertEqual(r.numerical_support_status,'NO_INCIDENT_RISK_AT_ENTRY_BASELINE_QUALIFIED_ONLY')

    def test_zero_time_incident_and_baseline_remain_distinct(self):
        hs = [H('a','A',S.PRE,3,(T(0,S.PRE,S.POST),)),H('b','B',S.POST,3)]
        r = success_at_horizon(hs,0,P.BASELINE_QUALIFIED)
        self.assertEqual(r.baseline_qualified_fraction,.5)
        self.assertEqual(r.incident_success_cif,.5)
        self.assertEqual(r.ever_qualified_probability,1)

    def test_all_round_denominator_is_not_conditional_incidence(self):
        hs = [H('a','A',S.POST,5),H('b','B',S.PRE,5,(T(1,S.PRE,S.POST),)),H('c','C',S.PRE,5)]
        r = success_at_horizon(hs,3,P.BASELINE_QUALIFIED)
        self.assertAlmostEqual(r.baseline_qualified_fraction,1/3)
        self.assertAlmostEqual(r.incident_success_cif,1/3)  # not 1/2
        self.assertAlmostEqual(r.ever_qualified_probability,2/3)

    def test_unknown_acquisition_is_competing_not_success(self):
        hs = [H('a','A',S.PRE,2,(T(1,S.PRE,S.ACQUISITION_UNKNOWN),))]
        r = success_at_horizon(hs,2,P.REJECT)
        self.assertEqual(r.incident_success_cif,0)
        self.assertEqual(r.competing_cif,1)

    def test_hand_competing_risk_with_censoring(self):
        hs = [H('a','A',S.PRE,4,(T(1,S.PRE,S.CLOSURE),)),H('b','B',S.PRE,4,(T(2,S.PRE,S.POST),)),
              H('c','C',S.PRE,1),H('d','D',S.PRE,4)]
        r = success_at_horizon(hs,3,P.REJECT)
        self.assertEqual(r.competing_cif,.25)
        self.assertEqual(r.incident_success_cif,.375)
        self.assertEqual(r.event_free_probability,.375)

    def test_tied_success_competitor_censor(self):
        hs = [H('a','A',S.PRE,1,(T(1,S.PRE,S.POST),)),H('b','B',S.PRE,1,(T(1,S.PRE,S.CLOSURE),)),H('c','C',S.PRE,1)]
        r = success_at_horizon(hs,1,P.REJECT)
        self.assertAlmostEqual(r.incident_success_cif,1/3)
        self.assertAlmostEqual(r.competing_cif,1/3)
        self.assertEqual(r.risk_at_landmark,1)
        self.assertEqual(r.prior_unsupported_intervals,())
        self.assertIn('UNSUPPORTED',success_at_horizon(hs,2,P.REJECT).numerical_support_status)

    def test_all_censor_tail_flagged(self):
        hs = [H('a','A',S.PRE,1),H('b','B',S.PRE,2)]
        r = success_at_horizon(hs,5,P.REJECT)
        self.assertEqual(r.prior_unsupported_intervals,((2,5),))
        self.assertEqual(r.event_free_probability,1)

    def test_complete_absorption_not_tail(self):
        hs = [H('a','A',S.PRE,1,(T(1,S.PRE,S.POST),)),H('b','B',S.PRE,1,(T(1,S.PRE,S.CLOSURE),))]
        r = success_at_horizon(hs,60,P.REJECT)
        self.assertEqual(r.numerical_support_status,'COMPLETE_MODELED_FIRST_EVENT_ABSORPTION')

    def test_fully_observed_matches_empirical_ever_success(self):
        rng = random.Random(978)
        for _ in range(200):
            hs = []
            for i in range(rng.randint(1,20)):
                initial = rng.choice([S.PRE,S.POST])
                trs=[]
                if rng.random()<.6:
                    destination=rng.choice([S.CLOSURE,S.ACQUISITION_UNKNOWN,S.SUCCESS_EXIT]+([S.POST] if initial==S.PRE else []))
                    trs.append(T(rng.randint(0,3),initial,destination))
                    if destination==S.POST and rng.random()<.6:
                        trs.append(T(4,S.POST,S.CLOSURE))
                hs.append(H(str(i),str(i//2),initial,5,tuple(trs)))
            for horizon in (0,1,3,5):
                r=success_at_horizon(hs,horizon,P.BASELINE_QUALIFIED)
                expected=sum(h.initial_state==S.POST or any(t.time<=horizon and t.destination in (S.POST,S.SUCCESS_EXIT) for t in h.transitions) for h in hs)/len(hs)
                self.assertAlmostEqual(r.ever_qualified_probability,expected,places=12)
                self.assertAlmostEqual(r.baseline_qualified_fraction+r.incident_success_cif+r.competing_cif+r.event_free_probability,1,places=12)

    def test_terminal_initial_mass_preserved_by_occupancy(self):
        hs=[H('a','A',S.PRE,3),H('b','B',S.CLOSURE,3)]
        self.assertEqual(at_horizon(hs,2).independent_operating_probability,.5)
        self.assertEqual(at_horizon(hs,2).mathematical_probabilities[S.CLOSURE.value],.5)
        with self.assertRaisesRegex(ValueError,'endpoint_specific_prior_success'):
            success_at_horizon(hs,2,P.BASELINE_QUALIFIED)

    def test_enormous_times_fail_cleanly(self):
        huge=10**1000
        with self.assertRaises(ValueError): validate([H('a','A',S.PRE,huge)])
        with self.assertRaises(ValueError): at_horizon([H('a','A',S.PRE,1)],huge)
        with self.assertRaises(ValueError): success_at_horizon([H('a','A',S.PRE,1)],huge,P.REJECT)


if __name__=='__main__': unittest.main(verbosity=2)
