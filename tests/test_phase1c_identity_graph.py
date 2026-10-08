import unittest
from datetime import date

from src.phase1c.model import RoundRecord, validate_round
from src.phase1c.identity import (
    CompanyIdentity,IdentityRecord,match_company,audit_match_sample,
    generate_cross_platform_candidates,build_review_queue
)
from src.phase1c.graph import same_economic_round, qualifying_followon, next_round_edges, native_vs_graph_reclassification

def rr(round_id, company, platform, open_date, close_date, valuation, instrument="priced_equity", status="funded_completed"):
    return RoundRecord(
        round_id=round_id, canonical_company_id=company, platform=platform,
        offering_year=open_date.year, first_live_date=open_date, completion_date=close_date,
        status=status, primary_field="saas_enterprise_software",
        instrument_type=instrument, legal_name=company, source_url="https://example.invalid/"+round_id,
        comparable_valuation=valuation
    )

class TestRoundModel(unittest.TestCase):
    def test_layer_b_requires_completion(self):
        r=rr("r1","c1","wefunder",date(2024,1,1),None,5_000_000)
        self.assertIn("funded_round_requires_completion_date",validate_round(r))

    def test_pending_not_layer_b(self):
        r=rr("r1","c1","wefunder",date(2025,1,1),None,None,status="pending")
        self.assertFalse(r.layer_b_eligible)
        self.assertEqual(validate_round(r),[])

    def test_offering_year_is_first_live_year(self):
        r=RoundRecord("r1","c1","wefunder",2023,date(2024,1,1),"pending","saas_enterprise_software","safe","C","x")
        self.assertIn("offering_year_must_equal_first_live_year",validate_round(r))

class TestIdentity(unittest.TestCase):
    def test_exact_entity_id_is_strong_match(self):
        a=CompanyIdentity("Acme Inc",jurisdiction_entity_id="US-DE-123")
        b=CompanyIdentity("Acme Holdings",jurisdiction_entity_id="US-DE-123")
        self.assertEqual(match_company(a,b).decision,"MATCH")
        self.assertEqual(match_company(a,b).tier,"STRONG")

    def test_conflicting_strong_ids_are_no_match(self):
        a=CompanyIdentity("Acme",jurisdiction_entity_id="A")
        b=CompanyIdentity("Acme",jurisdiction_entity_id="B")
        self.assertEqual(match_company(a,b).decision,"NO_MATCH")

    def test_name_only_never_auto_matches(self):
        a=CompanyIdentity("North Star, Inc.")
        b=CompanyIdentity("North Star LLC")
        self.assertEqual(match_company(a,b).decision,"REVIEW")

    def test_two_medium_identifiers_auto_match(self):
        a=CompanyIdentity("Acme Inc",domain="acme.com",founders=("Ada Lovelace",))
        b=CompanyIdentity("Acme LLC",domain="https://www.acme.com",founders=("Ada Lovelace",))
        self.assertEqual(match_company(a,b).decision,"MATCH")
        self.assertEqual(match_company(a,b).tier,"MEDIUM_BUNDLE")

    def test_cross_platform_candidate_generation(self):
        rows=[
            IdentityRecord("wf","wefunder",CompanyIdentity("Acme Inc",domain="acme.com",founders=("Ada",))),
            IdentityRecord("re","republic_us",CompanyIdentity("Acme LLC",domain="www.acme.com",founders=("Ada",))),
            IdentityRecord("wf2","wefunder",CompanyIdentity("Acme alt",domain="acme.com",founders=("Ada",))),
        ]
        c=generate_cross_platform_candidates(rows)
        self.assertEqual(len(c),1)
        self.assertEqual(c[0].result.decision,"MATCH")

    def test_name_only_candidate_goes_to_review(self):
        rows=[
            IdentityRecord("a","wefunder",CompanyIdentity("North Star Inc")),
            IdentityRecord("b","startengine",CompanyIdentity("North Star LLC")),
        ]
        c=generate_cross_platform_candidates(rows)
        self.assertEqual(c[0].result.decision,"REVIEW")
        q=build_review_queue(c)
        self.assertEqual(q["mandatory_review_count"],1)

    def test_medium_bundle_always_reviewed(self):
        rows=[
            IdentityRecord("a","wefunder",CompanyIdentity("Acme",domain="acme.com",founders=("Ada",))),
            IdentityRecord("b","startengine",CompanyIdentity("Acme",domain="acme.com",founders=("Ada",))),
        ]
        c=generate_cross_platform_candidates(rows)
        q=build_review_queue(c)
        self.assertEqual(q["mandatory_review_count"],1)

    def test_strong_match_audit_is_stratified(self):
        rows=[]
        for i in range(20):
            rows.extend([
                IdentityRecord(f"w{i}","wefunder",CompanyIdentity(f"A{i}",jurisdiction_entity_id=f"E{i}")),
                IdentityRecord(f"r{i}","republic_us",CompanyIdentity(f"A{i}",jurisdiction_entity_id=f"E{i}")),
            ])
        c=generate_cross_platform_candidates(rows)
        q=build_review_queue(c,.10)
        self.assertEqual(q["strong_auto_match_count"],20)
        self.assertGreaterEqual(q["strong_audit_count"],2)

    def test_audit_reopens_over_2pct(self):
        m=match_company(CompanyIdentity("A",domain="a.com",founders=("X",)),CompanyIdentity("A",domain="a.com",founders=("X",)))
        result=audit_match_sample([(m,False)])
        self.assertTrue(result["reopen"])

class TestRoundGraph(unittest.TestCase):
    def test_same_round_cohost(self):
        a=rr("a","c1","wefunder",date(2022,1,1),date(2022,3,1),10_000_000)
        b=rr("b","c1","republic_us",date(2022,2,1),date(2022,3,15),10_000_000)
        self.assertTrue(same_economic_round(a,b))
        edges=next_round_edges([a,b])
        self.assertEqual(edges[0].edge_type,"COHOST_SAME_ROUND")

    def test_cross_platform_qualified_followon(self):
        a=rr("a","c1","wefunder",date(2020,1,1),date(2020,3,1),10_000_000)
        b=rr("b","c1","startengine",date(2022,1,1),date(2022,3,1),16_000_000)
        self.assertTrue(qualifying_followon(a,b))
        edges=next_round_edges([a,b])
        self.assertTrue(edges[0].cross_platform)
        self.assertTrue(edges[0].qualified_followon_success)
        d=native_vs_graph_reclassification(edges)
        self.assertEqual(d["cross_platform_reclassified"],1)

    def test_cap_not_used_as_priced_valuation(self):
        a=RoundRecord("a","c1","wefunder",2020,date(2020,1,1),"funded_completed","saas_enterprise_software","safe","C","x",completion_date=date(2020,2,1),valuation_cap=10_000_000)
        b=rr("b","c1","republic_us",date(2022,1,1),date(2022,2,1),20_000_000)
        self.assertFalse(qualifying_followon(a,b))

    def test_nonoverlap_is_not_same_round(self):
        a=rr("a","c1","wefunder",date(2020,1,1),date(2020,2,1),10_000_000)
        b=rr("b","c1","wefunder",date(2021,1,1),date(2021,2,1),10_000_000)
        self.assertFalse(same_economic_round(a,b))

if __name__=="__main__":
    unittest.main()
