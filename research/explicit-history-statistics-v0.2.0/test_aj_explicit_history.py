import dataclasses
import math
import random
import unittest
from fractions import Fraction
from aj_explicit_history import (State as S, History as H, Transition as T, STATES,
    trajectory, at_horizon, resample_company_clusters, validate)


def exact_reference(histories, horizon):
    """Separate rational full-matrix product, deriving risk from each prefix."""
    states = list(STATES)
    n = len(states)
    p = [Fraction(sum(h.initial_state == s for h in histories), len(histories)) for s in states]
    product = [[Fraction(i == j) for j in range(n)] for i in range(n)]
    for t in sorted({tr.time for h in histories for tr in h.transitions if tr.time <= horizon}):
        risks = {s: 0 for s in states}
        counts = {}
        for h in histories:
            prefix = [tr for tr in h.transitions if tr.time < t]
            state = prefix[-1].destination if prefix else h.initial_state
            if h.observation_end >= t:
                risks[state] += 1
            for tr in h.transitions:
                if tr.time == t:
                    key = (states.index(tr.source), states.index(tr.destination))
                    counts[key] = counts.get(key, 0) + 1
        step = [[Fraction(i == j) for j in range(n)] for i in range(n)]
        for (i, j), count in counts.items():
            hazard = Fraction(count, risks[states[i]])
            step[i][i] -= hazard
            step[i][j] += hazard
        product = [[sum(product[i][k] * step[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
    return {states[j].value: sum(p[i] * product[i][j] for i in range(n)) for j in range(n)}


class ExactHistoryTests(unittest.TestCase):
    def test_initial_state_mixture_is_not_reset(self):
        hs = [H('a','A',S.PRE,5), H('b','B',S.POST,5), H('c','C',S.POST,5)]
        r = at_horizon(hs,2)
        self.assertAlmostEqual(r.mathematical_probabilities[S.POST.value],2/3)
        self.assertEqual(r.independent_operating_probability,1)

    def test_zero_time_transition(self):
        r = at_horizon([H('a','A',S.PRE,0,(T(0,S.PRE,S.CLOSURE),))],0)
        self.assertEqual(r.independent_operating_probability,0)

    def test_tied_transitions_are_simultaneous(self):
        hs = [H('a','A',S.PRE,2,(T(1,S.PRE,S.POST),)), H('b','B',S.POST,2,(T(1,S.POST,S.CLOSURE),))]
        r = at_horizon(hs,1)
        self.assertEqual(r.mathematical_probabilities[S.POST.value],.5)
        self.assertEqual(r.mathematical_probabilities[S.CLOSURE.value],.5)

    def test_events_before_tied_censors(self):
        hs = [H('a','A',S.PRE,1,(T(1,S.PRE,S.CLOSURE),)),H('b','B',S.PRE,1)]
        r = at_horizon(hs,1)
        self.assertEqual(r.independent_operating_probability,.5)
        self.assertEqual(r.unresolved_states_at_landmark,())
        self.assertEqual(at_horizon(hs,2).unresolved_states_at_landmark,(S.PRE.value,))

    def test_empty_state_residual_mass_is_visible(self):
        hs = [H('a','A',S.PRE,3,(T(1,S.PRE,S.POST),T(3,S.POST,S.CLOSURE))),H('b','B',S.PRE,2)]
        r = at_horizon(hs,3)
        self.assertEqual(r.independent_operating_probability,.5)
        self.assertEqual(r.unresolved_states_at_landmark,(S.PRE.value,))
        self.assertEqual(r.prior_unsupported_intervals,((2,3,(S.PRE.value,)),))

    def test_replenished_state_does_not_erase_prior_gap(self):
        hs = [H('a','A',S.POST,2), H('b','B',S.PRE,4,(T(3,S.PRE,S.POST),))]
        r = at_horizon(hs,4)
        self.assertEqual(r.unresolved_states_at_landmark,())
        self.assertEqual(r.prior_unsupported_intervals,((2,3,(S.POST.value,)),))
        self.assertEqual(r.numerical_support_status,'UNSUPPORTED_OPERATING_MASS_PRESENT_OR_PRIOR_GAP')

    def test_complete_absorption_not_unresolved_tail(self):
        hs = [H('a','A',S.PRE,1,(T(1,S.PRE,S.CLOSURE),))]
        r = at_horizon(hs,60)
        self.assertEqual(r.numerical_support_status,'COMPLETE_MODELED_ABSORPTION')
        self.assertEqual(r.max_observed_endpoint,1)

    def test_pure_censoring_after_support(self):
        hs = [H('a','A',S.PRE,3),H('b','B',S.POST,4)]
        self.assertEqual(at_horizon(hs,3).unresolved_states_at_landmark,())
        self.assertEqual(at_horizon(hs,3.5).unresolved_states_at_landmark,(S.PRE.value,))

    def test_terminal_paths_are_absorbing(self):
        for terminal in (S.CLOSURE,S.SUCCESS_EXIT,S.ACQUISITION_UNKNOWN):
            h = H('a','A',S.PRE,3,(T(1,S.PRE,terminal),T(2,terminal,S.POST)))
            with self.assertRaisesRegex(ValueError,'forbidden_transition'):
                validate([h])

    def test_invalid_histories_rejected(self):
        base = H('a','A',S.PRE,3)
        cases = [[],[base,base], 
                 [dataclasses.replace(base,initial_state='operating_pre_success')],
                 [dataclasses.replace(base,round_id='')], [dataclasses.replace(base,company_id=' ')],
                 [dataclasses.replace(base,observation_end=-1)], [dataclasses.replace(base,observation_end=float('nan'))],
                 [dataclasses.replace(base,observation_end=float('inf'))], [dataclasses.replace(base,observation_end=True)],
                 [dataclasses.replace(base,transitions=(T(4,S.PRE,S.POST),))],
                 [dataclasses.replace(base,transitions=(T(1,S.POST,S.CLOSURE),))],
                 [dataclasses.replace(base,transitions=(T(1,S.PRE,S.PRE),))],
                 [dataclasses.replace(base,transitions=(T(1,S.PRE,S.POST),T(1,S.POST,S.CLOSURE)))],
                 [dataclasses.replace(base,transitions=(T(-1,S.PRE,S.POST),))],
                 [dataclasses.replace(base,transitions=(T(float('nan'),S.PRE,S.POST),))],
                 [dataclasses.replace(base,transitions=(T(1,'operating_pre_success',S.POST),))],
                 [H('a','A',S.POST,3,(T(1,S.POST,S.PRE),))]]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                validate(case)

    def test_bad_landmarks_rejected(self):
        for h in (-1,float('nan'),float('inf'),True,'12'):
            with self.subTest(h=h), self.assertRaises(ValueError):
                at_horizon([H('a','A',S.PRE,3)],h)

    def test_seeded_rational_matrix_oracle(self):
        rng = random.Random(811)
        for trial in range(100):
            histories = []
            for i in range(rng.randint(1,12)):
                initial = rng.choice([S.PRE,S.POST])
                end = rng.randint(0,8)
                state = initial
                trs = []
                for t in range(end+1):
                    if rng.random() < .2:
                        choices = [S.CLOSURE,S.SUCCESS_EXIT,S.ACQUISITION_UNKNOWN]
                        if state == S.PRE:
                            choices += [S.POST]
                        nxt = rng.choice(choices)
                        trs.append(T(t,state,nxt))
                        state = nxt
                        if state not in (S.PRE,S.POST):
                            break
                histories.append(H(str(i),str(i//2),initial,end,tuple(trs)))
            for horizon in (0,1,3,6,10):
                actual = at_horizon(histories,horizon).mathematical_probabilities
                expected = exact_reference(histories,horizon)
                for key in expected:
                    self.assertAlmostEqual(actual[key],float(expected[key]),places=12)
                    self.assertGreaterEqual(actual[key],-1e-14)
                self.assertAlmostEqual(sum(actual.values()),1,places=12)
            self.assertEqual(at_horizon(histories,10),at_horizon(list(reversed(histories)),10))

    def test_cluster_resampling_keeps_rounds_together(self):
        hs = [H('a1','A',S.PRE,3), H('a2','A',S.POST,4), H('b1','B',S.PRE,5)]
        samples = resample_company_clusters(hs,40,3)
        self.assertEqual(samples,resample_company_clusters(hs,40,3))
        self.assertEqual({len(x) for x in samples},{2,3,4})
        for sample in samples:
            validate(sample)
            for occurrence in ('0','1'):
                sub = [h for h in sample if h.company_id.startswith(occurrence+':')]
                company = sub[0].company_id.split(':',1)[1]
                expected = [h for h in hs if h.company_id == company]
                self.assertEqual([h.round_id.split(':',1)[1] for h in sub],[h.round_id for h in expected])
                self.assertEqual([(h.initial_state,h.observation_end,h.transitions) for h in sub],
                                 [(h.initial_state,h.observation_end,h.transitions) for h in expected])

    def test_resampling_does_not_change_round_weighting(self):
        hs = [H('a1','A',S.PRE,3),H('a2','A',S.PRE,3),H('b1','B',S.POST,3)]
        self.assertAlmostEqual(at_horizon(hs,2).mathematical_probabilities[S.POST.value],1/3)

    def test_bad_bootstrap_options_rejected(self):
        hs = [H('a','A',S.PRE,3)]
        for n in (0,-1,True,1.2):
            with self.assertRaises(ValueError): resample_company_clusters(hs,n,0)
        for seed in (True,1.2,'0'):
            with self.assertRaises(ValueError): resample_company_clusters(hs,2,seed)

    def test_input_unchanged(self):
        hs = [H('a','A',S.PRE,3,(T(1,S.PRE,S.POST),))]
        before = dataclasses.asdict(hs[0])
        trajectory(hs); at_horizon(hs,2); resample_company_clusters(hs,5,0)
        self.assertEqual(before,dataclasses.asdict(hs[0]))


if __name__ == '__main__': unittest.main(verbosity=2)
