import unittest
from datetime import date

from src.phase1c.outcomes import (
    OutcomeEvent,EventType,State,is_qualified_success,is_confirmed_closure,next_state,censor_date
)
from src.phase1c.estimators import (
    TimedTransition,SubjectFollowup,aalen_johansen_occupancy,
    independent_operating_probability,cluster_bootstrap_indices,km_greenwood_interval
)
from src.phase1c.reporting import rq1_cell_decision,rq2_field_cell_decision,adjacent_pool_order,lost_followup_sensitivity

class TestOutcomes(unittest.TestCase):
    def test_followon_requires_comparable_1_5x(self):
        e=OutcomeEvent("r",date(2024,1,1),EventType.QUALIFIED_FOLLOWON,"u",True,10,15)
        self.assertTrue(is_qualified_success(e))
        e2=OutcomeEvent("r",date(2024,1,1),EventType.QUALIFIED_FOLLOWON,"u",True,None,20)
        self.assertFalse(is_qualified_success(e2))

    def test_acquisition_needs_consideration_for_success(self):
        e=OutcomeEvent("r",date(2024,1,1),EventType.ACQUISITION,"u",True)
        self.assertFalse(is_qualified_success(e))
        self.assertEqual(next_state(State.OPERATING_PRE_SUCCESS,e),State.ACQUISITION_VALUE_UNKNOWN)
        e2=OutcomeEvent("r",date(2024,1,1),EventType.ACQUISITION,"u",True,shareholder_consideration_known=True)
        self.assertTrue(is_qualified_success(e2))
        self.assertEqual(next_state(State.OPERATING_PRE_SUCCESS,e2),State.TERMINAL_SUCCESS_EXIT)

    def test_secondary_or_nonplatform_cannot_create_success(self):
        e=OutcomeEvent("r",date(2024,1,1),EventType.IPO_DIRECT_LISTING,"u",False)
        self.assertFalse(is_qualified_success(e))

    def test_closure_requires_explicit_platform_evidence(self):
        e=OutcomeEvent("r",date(2024,1,1),EventType.CLOSURE,"u",True,explicit_closure=False)
        self.assertFalse(is_confirmed_closure(e))
        e2=OutcomeEvent("r",date(2024,1,1),EventType.CLOSURE,"u",True,explicit_closure=True)
        self.assertTrue(is_confirmed_closure(e2))

    def test_censor_never_extends_beyond_extraction(self):
        self.assertEqual(censor_date(date(2026,12,1),date(2026,10,8),date(2025,1,1)),date(2026,10,8))

class TestEstimator(unittest.TestCase):
    def test_aj_occupancy_simple(self):
        f=[SubjectFollowup("a","ca",5),SubjectFollowup("b","cb",5)]
        tr=[
            TimedTransition("a","ca",1,State.OPERATING_PRE_SUCCESS,State.OPERATING_POST_SUCCESS),
            TimedTransition("b","cb",2,State.OPERATING_PRE_SUCCESS,State.CLOSURE),
        ]
        pts=aalen_johansen_occupancy(tr,f)
        self.assertEqual(len(pts),2)
        self.assertAlmostEqual(independent_operating_probability(pts[0]),1.0)
        self.assertAlmostEqual(independent_operating_probability(pts[1]),0.5)

    def test_event_after_censor_rejected(self):
        with self.assertRaises(ValueError):
            aalen_johansen_occupancy(
                [TimedTransition("a","c",3,State.OPERATING_PRE_SUCCESS,State.CLOSURE)],
                [SubjectFollowup("a","c",2)]
            )

    def test_cluster_bootstrap_preserves_company_rounds(self):
        reps=cluster_bootstrap_indices(["c1","c1","c2"],n_boot=5,seed=1)
        self.assertEqual(len(reps),5)
        # c1 is sampled as a unit: its two row indices occur together with equal multiplicity.
        for idx in reps:
            self.assertEqual(idx.count(0),idx.count(1))

    def test_greenwood_diagnostic_bounds(self):
        s,lo,hi=km_greenwood_interval([1,2,3],[True,False,False],2)
        self.assertTrue(0<=lo<=s<=hi<=1)

class TestReporting(unittest.TestCase):
    def test_rq1_low_n_still_reports(self):
        d=rq1_cell_decision(12,2)
        self.assertTrue(d.report); self.assertTrue(d.low_information); self.assertFalse(d.pool)

    def test_rq2_sparse_cell_pools(self):
        d=rq2_field_cell_decision(29,5,.90)
        self.assertFalse(d.report); self.assertTrue(d.pool)

    def test_rq2_low_ascertainment_pools(self):
        d=rq2_field_cell_decision(50,8,.79)
        self.assertTrue(d.pool)
        self.assertIn("ascertainment_lt_80pct",d.reasons)

    def test_pooling_does_not_cross_maturity_block(self):
        self.assertEqual(set(adjacent_pool_order(2025)),{2024,2025})
        self.assertNotIn(2023,adjacent_pool_order(2025))

    def test_lost_followup_bounds(self):
        x=lost_followup_sensitivity(2,3,10)
        self.assertEqual(x["optimistic_rate"],.2)
        self.assertEqual(x["adverse_rate"],.5)

if __name__=="__main__":
    unittest.main()
