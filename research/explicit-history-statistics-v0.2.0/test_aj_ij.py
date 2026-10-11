import math
import random
import unittest
from aj_explicit_history import State as S, STATES, History as H, Transition as T, at_horizon
from aj_ij import aj_ij_diagnostic


def weighted_reference(histories,horizon,weights):
    # Separate scalar full-matrix oracle. No differentiation code is reused.
    states=list(STATES); n=len(states)
    initial=[sum(w for h,w in zip(histories,weights) if h.initial_state==s)/sum(weights) for s in states]
    product=[[float(i==j) for j in range(n)] for i in range(n)]
    times=sorted({t.time for h in histories for t in h.transitions if t.time<=horizon})
    for time in times:
        risk={s:0.0 for s in states}; counts={}
        for h,w in zip(histories,weights):
            prefix=[tr for tr in h.transitions if tr.time<time]
            state=prefix[-1].destination if prefix else h.initial_state
            if h.observation_end>=time: risk[state]+=w
            for tr in h.transitions:
                if tr.time==time:
                    key=(states.index(tr.source),states.index(tr.destination))
                    counts[key]=counts.get(key,0.0)+w
        step=[[float(i==j) for j in range(n)] for i in range(n)]
        for (i,j),d in counts.items():
            q=d/risk[states[i]]
            step[i][i]-=q;step[i][j]+=q
        product=[[sum(product[i][k]*step[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
    return {states[j].value:sum(initial[i]*product[i][j] for i in range(n)) for j in range(n)}


class IJTests(unittest.TestCase):
    def test_bernoulli_scale(self):
        hs=[H(str(i),str(i),S.PRE,5,(T(1,S.PRE,S.CLOSURE),) if i<2 else ()) for i in range(5)]
        result=aj_ij_diagnostic(hs,3)
        self.assertAlmostEqual(result.operating_variance,.6*.4/5)
        for h in hs:
            indicator=int(not h.transitions)
            g=result.round_gradients[h.round_id]
            self.assertAlmostEqual(g[S.PRE.value]+g[S.POST.value],(indicator-.6)/5)
        self.assertEqual(result.interval_status,'NORMAL_DELTA_DIAGNOSTIC_ONLY')

    def test_repeated_company_cluster_scale(self):
        hs=[H('a1','A',S.PRE,5),H('a2','A',S.PRE,5),H('b1','B',S.PRE,5,(T(1,S.PRE,S.CLOSURE),))]
        r=aj_ij_diagnostic(hs,3)
        expected=((2-2*(2/3))/3)**2+((0-1*(2/3))/3)**2
        self.assertAlmostEqual(r.operating_variance,expected)
        self.assertAlmostEqual(r.operating_variance,8/81)

    def test_initial_distribution_gradient_includes_terminal_mass(self):
        hs=[H('a','A',S.PRE,3),H('b','B',S.CLOSURE,3)]
        r=aj_ij_diagnostic(hs,2)
        self.assertEqual(r.operating_variance,.125)
        self.assertEqual(r.round_gradients['a'][S.PRE.value],.25)
        self.assertEqual(r.round_gradients['b'][S.PRE.value],-.25)

    def test_unsupported_risk_does_not_gain_an_interval(self):
        hs=[H('a','A',S.PRE,3,(T(1,S.PRE,S.POST),T(3,S.POST,S.CLOSURE))),H('b','B',S.PRE,2)]
        r=aj_ij_diagnostic(hs,3)
        self.assertEqual(r.interval_status,'WITHHELD_NUMERICAL_STATE_RISK_GAP')
        self.assertIsNone(r.normal_diagnostic_interval)

    def test_zero_variance_is_not_no_uncertainty_claim(self):
        hs=[H('a','A',S.PRE,3),H('b','B',S.PRE,3)]
        r=aj_ij_diagnostic(hs,2)
        self.assertEqual(r.operating_variance,0)
        self.assertIsNone(r.normal_diagnostic_interval)
        self.assertIn('NOT_INFORMATIVE_COVERAGE',r.interval_status)

    def test_one_company_cannot_generate_diagnostic_interval(self):
        hs=[H('a','A',S.PRE,3),H('b','A',S.PRE,3,(T(1,S.PRE,S.CLOSURE),))]
        r=aj_ij_diagnostic(hs,2)
        self.assertIn('FEWER_THAN_TWO',r.interval_status)
        self.assertIsNone(r.normal_diagnostic_interval)

    def test_confidence_level_validation_and_extreme(self):
        hs=[H('a','A',S.PRE,3),H('b','B',S.CLOSURE,3)]
        for conf in (0,1,-1,2,True,'95%',float('nan'),float('inf')):
            with self.assertRaises(ValueError):aj_ij_diagnostic(hs,2,conf)
        r=aj_ij_diagnostic(hs,2,math.nextafter(1,0))
        self.assertEqual(r.normal_diagnostic_interval,(0,1))

    def test_seeded_finite_difference_covariance_and_conservation(self):
        rng=random.Random(461)
        for trial in range(60):
            hs=[]
            for i in range(rng.randint(2,8)):
                initial=rng.choice([S.PRE,S.POST,S.CLOSURE]);current=initial
                end=rng.randint(1,5);trs=[]
                if current in (S.PRE,S.POST):
                    for t in range(end+1):
                        if rng.random()<.25:
                            choices=[S.CLOSURE,S.SUCCESS_EXIT,S.ACQUISITION_UNKNOWN]+([S.POST] if current==S.PRE else [])
                            dest=rng.choice(choices);trs.append(T(t,current,dest));current=dest
                            if current not in (S.PRE,S.POST):break
                hs.append(H(str(i),str(i//2),initial,end,tuple(trs)))
            for horizon in (0,2,6):
                r=aj_ij_diagnostic(hs,horizon)
                for state in STATES:
                    self.assertAlmostEqual(r.mathematical_probabilities[state.value],at_horizon(hs,horizon).mathematical_probabilities[state.value],places=12)
                    self.assertAlmostEqual(sum(g[state.value] for g in r.round_gradients.values()),0,places=12)
                for i,h in enumerate(hs):
                    delta=1e-5;plus=[1.0]*len(hs);minus=plus.copy();plus[i]+=delta;minus[i]-=delta
                    a=weighted_reference(hs,horizon,plus);b=weighted_reference(hs,horizon,minus)
                    for state in STATES:
                        self.assertAlmostEqual(r.round_gradients[h.round_id][state.value],(a[state.value]-b[state.value])/(2*delta),places=8)
                    self.assertAlmostEqual(sum(r.round_gradients[h.round_id].values()),0,places=12)
                for a in STATES:
                    for b in STATES:self.assertEqual(r.covariance[a.value][b.value],r.covariance[b.value][a.value])
                for _ in range(5):
                    direction={s:rng.uniform(-3,3) for s in STATES}
                    quadratic=sum(direction[a]*direction[b]*r.covariance[a.value][b.value] for a in STATES for b in STATES)
                    self.assertGreaterEqual(quadratic,-1e-12)
                self.assertEqual(r,aj_ij_diagnostic(list(reversed(hs)),horizon))


if __name__=='__main__':unittest.main(verbosity=2)
