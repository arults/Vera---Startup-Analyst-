import unittest
from datetime import date

from src.phase1c.reporting import CellStats,pool_adjacent_years
from src.phase1c.reports import Interval,Estimate,ResultCell,validate_result_cell,result_cell_dict
from src.phase1c.model import RoundRecord
from src.phase1c.graph import next_round_edges,native_vs_graph_by_platform

def rr(round_id, company, platform, year, valuation):
    return RoundRecord(
        round_id,company,platform,year,date(year,1,1),"funded_completed",
        "saas_enterprise_software","priced_equity",company,"https://example.invalid",
        completion_date=date(year,2,1),comparable_valuation=valuation
    )

class TestPoolingExecutor(unittest.TestCase):
    def test_adjacent_pool_stops_when_gate_passes(self):
        cells=[CellStats(2022,18,3,16),CellStats(2021,20,3,18),CellStats(2023,5,0,4)]
        p=pool_adjacent_years(2022,cells)
        self.assertTrue(p.report)
        self.assertEqual(p.years,(2021,2022))
        self.assertGreaterEqual(p.n,30)
        self.assertGreaterEqual(p.informative_events,5)
        self.assertGreaterEqual(p.ascertainment_coverage,.8)

    def test_young_pool_never_crosses_to_2023(self):
        cells=[CellStats(2025,10,1,10),CellStats(2024,10,1,10),CellStats(2023,100,50,100)]
        p=pool_adjacent_years(2025,cells)
        self.assertTrue(p.suppressed)
        self.assertEqual(p.years,(2024,2025))
        self.assertFalse(p.crossed_maturity_boundary)

class TestReportContract(unittest.TestCase):
    def test_horizon_cannot_exceed_support(self):
        e=Estimate(.8,Interval(.7,.9),Interval(.68,.91))
        c=ResultCell("wefunder",(2024,),None,40,38,10,6,30,4,.9,12,24,e,e,e,False,False)
        self.assertIn("horizon_exceeds_supported_followup",validate_result_cell(c))

    def test_estimand_label_is_forced(self):
        e=Estimate(.8,Interval(.7,.9),Interval(.68,.91))
        c=ResultCell("wefunder",(2024,),None,40,38,10,6,30,4,.9,24,12,e,e,e,False,False)
        self.assertEqual(validate_result_cell(c),[])
        self.assertEqual(result_cell_dict(c)["estimand_label"],"platform_observed")

class TestGraphBiasReport(unittest.TestCase):
    def test_cross_platform_success_increases_origin_graph_rate(self):
        a=rr("a","c","wefunder",2020,10)
        b=rr("b","c","startengine",2022,16)
        edges=next_round_edges([a,b])
        rows=native_vs_graph_by_platform([a,b],edges,set())
        wf=next(x for x in rows if x.platform=="wefunder")
        self.assertEqual(wf.native_successes,0)
        self.assertEqual(wf.graph_successes,1)
        self.assertGreater(wf.absolute_delta,0)

    def test_native_success_is_not_double_counted(self):
        a=rr("a","c","wefunder",2020,10)
        b=rr("b","c","startengine",2022,16)
        edges=next_round_edges([a,b])
        wf=next(x for x in native_vs_graph_by_platform([a,b],edges,{"a"}) if x.platform=="wefunder")
        self.assertEqual(wf.native_successes,1)
        self.assertEqual(wf.graph_successes,1)
        self.assertEqual(wf.cross_platform_reclassified,0)

if __name__=="__main__":
    unittest.main()
