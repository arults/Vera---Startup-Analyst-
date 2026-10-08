import csv, tempfile, unittest
from src.phase1b_verifier import verify_denominator, verify_outcomes
from src.survival import verify_curve

FIELDS=["offering_key","issuer_name","issuer_cik","sec_file_number","initial_form_c_date","initial_form_c_accession","sec_initial_url","intermediary_name","intermediary_cik","funding_update_date","funding_update_accession","funding_amount_usd","funding_close_date","funding_close_basis","sec_funding_url","funding_evidence_text","withdrawal_count","source_reconstruction","row_status"]

def row(i=1):
    return {"offering_key":f"000000000{i}|020-0000{i}","issuer_name":"X","issuer_cik":f"000000000{i}","sec_file_number":f"020-0000{i}","initial_form_c_date":"2020-01-01","initial_form_c_accession":"0000000000-20-000001","sec_initial_url":"https://www.sec.gov/Archives/edgar/data/1/x-index.htm","intermediary_name":"Wefunder Portal LLC","intermediary_cik":"0001670254","funding_update_date":"2020-06-02","funding_update_accession":"0000000000-20-000002","funding_amount_usd":"100.00","funding_close_date":"2020-06-01","funding_close_basis":"latest_sec_campaign_deadline","sec_funding_url":"https://www.sec.gov/Archives/edgar/data/1/y-index.htm","funding_evidence_text":"final number is $100","withdrawal_count":"0","source_reconstruction":"test","row_status":"PRIMARY_FUNDED"}

class TestDenominator(unittest.TestCase):
    def write(self, rows):
        f=tempfile.NamedTemporaryFile("w",delete=False,newline="",encoding="utf-8")
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows); f.close(); return f.name
    def test_valid(self):
        p=self.write([row(1),row(2)]); self.assertEqual(verify_denominator(p,2)["promotion_gate"],"PASS")
    def test_duplicate(self):
        r=row(1); p=self.write([r,r]); self.assertFalse(next(g for g in verify_denominator(p,2)["gates"] if g["id"]=="D02_UNIQUE_OFFERING_KEYS")["passed"])
    def test_wrong_year(self):
        r=row(); r["initial_form_c_date"]="2019-12-31"; p=self.write([r]); self.assertFalse(next(g for g in verify_denominator(p,1)["gates"] if g["id"]=="D04_INITIAL_FORM_C_IN_2020")["passed"])
    def test_missing_funding(self):
        r=row(); r["funding_amount_usd"]="0"; p=self.write([r]); self.assertFalse(next(g for g in verify_denominator(p,1)["gates"] if g["id"]=="D06_SEC_CONFIRMED_FUNDING")["passed"])
    def test_withdrawal(self):
        r=row(); r["withdrawal_count"]="1"; p=self.write([r]); self.assertFalse(next(g for g in verify_denominator(p,1)["gates"] if g["id"]=="D07_NO_FINAL_WITHDRAWALS")["passed"])
    def test_chronology(self):
        r=row(); r["funding_close_date"]="2019-12-01"; p=self.write([r]); self.assertFalse(next(g for g in verify_denominator(p,1)["gates"] if g["id"]=="D08_CHRONOLOGY")["passed"])

class TestOutcomeEvidence(unittest.TestCase):
    def write_pair(self, out):
        m=tempfile.NamedTemporaryFile("w",delete=False,newline="",encoding="utf-8")
        w=csv.DictWriter(m,fieldnames=FIELDS); w.writeheader(); w.writerow(row()); m.close()
        o=tempfile.NamedTemporaryFile("w",delete=False,newline="",encoding="utf-8")
        fields=["offering_key","issuer_name","event_type","observation_date","evidence_url","secondary_evidence_url","evidence_quality","evidence_basis","evidence_confidence","search_exhausted","evidence_summary"]
        wo=csv.DictWriter(o,fieldnames=fields); wo.writeheader(); wo.writerow(out); o.close()
        return m.name,o.name
    def base(self):
        return {"offering_key":row()["offering_key"],"issuer_name":"X","event_type":"active_censor","observation_date":"2020-06-02","evidence_url":"https://example.com/e","secondary_evidence_url":"","evidence_quality":"independent_secondary","evidence_basis":"dated_independent_operating_evidence","evidence_confidence":"high","search_exhausted":"false","evidence_summary":"x"}
    def test_independent_evidence_passes(self):
        m,o=self.write_pair(self.base()); self.assertEqual(verify_outcomes(m,o)["promotion_gate"],"PASS")
    def test_company_fallback_requires_exhausted_search(self):
        x=self.base(); x.update(evidence_quality="company_controlled_fallback",evidence_basis="current_operating_functionality",evidence_confidence="low",search_exhausted="false")
        m,o=self.write_pair(x); self.assertFalse(next(g for g in verify_outcomes(m,o)["gates"] if g["id"]=="O04_VERIFIED_OUTCOME_EVIDENCE")["passed"])
    def test_company_fallback_passes_when_constrained(self):
        x=self.base(); x.update(evidence_quality="company_controlled_fallback",evidence_basis="current_operating_functionality",evidence_confidence="low",search_exhausted="true")
        m,o=self.write_pair(x); self.assertEqual(verify_outcomes(m,o)["promotion_gate"],"PASS")
    def test_silence_never_equals_cutoff_survival(self):
        x=self.base(); x.update(observation_date="2026-10-08",evidence_basis="silence")
        m,o=self.write_pair(x); self.assertFalse(next(g for g in verify_outcomes(m,o)["gates"] if g["id"]=="O07_NO_SILENCE_EQUALS_SURVIVAL")["passed"])

class TestSurvival(unittest.TestCase):
    def test_valid_curve(self):
        g=verify_curve([{"survival_before":1.0,"survival":.8,"at_risk":10,"events":2,"ci95_lower":.5,"ci95_upper":.95},{"survival_before":.8,"survival":.6,"at_risk":8,"events":2,"ci95_lower":.3,"ci95_upper":.85}])
        # second value is not exact product-limit arithmetic and should fail S03
        self.assertTrue(next(x for x in g if x["id"]=="S01_PROBABILITY_BOUNDS")["passed"])
        self.assertTrue(next(x for x in g if x["id"]=="S02_NON_INCREASING")["passed"])
        self.assertFalse(next(x for x in g if x["id"]=="S03_RISK_SET_ARITHMETIC")["passed"])
    def test_exact_arithmetic_curve(self):
        g=verify_curve([{"survival_before":1.0,"survival":.8,"at_risk":10,"events":2,"ci95_lower":.5,"ci95_upper":.95},{"survival_before":.8,"survival":.7,"at_risk":8,"events":1,"ci95_lower":.4,"ci95_upper":.9}])
        self.assertTrue(all(x["passed"] for x in g))
    def test_increasing_rejected(self):
        g=verify_curve([{"survival_before":1.0,"survival":.6,"at_risk":10,"events":4,"ci95_lower":.3,"ci95_upper":.8},{"survival_before":.6,"survival":.7,"at_risk":8,"events":1,"ci95_lower":.4,"ci95_upper":.9}])
        self.assertFalse(next(x for x in g if x["id"]=="S02_NON_INCREASING")["passed"])

if __name__=="__main__": unittest.main()
