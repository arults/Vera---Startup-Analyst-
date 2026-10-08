#!/usr/bin/env python3
import csv, hashlib, json, math
from datetime import date, datetime
from pathlib import Path

EXPECTED_INTERMEDIARY = "Wefunder Portal LLC"
EXPECTED_INTERMEDIARY_CIK = "0001670254"

def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def d(s): return date.fromisoformat(s)

def verify_denominator(path, expected_count=42):
    rows=read_csv(path)
    gates=[]
    def add(i, ok, detail): gates.append({"id":i,"passed":bool(ok),"detail":detail})
    add("D01_EXACT_COUNT", len(rows)==expected_count, f"rows={len(rows)} expected={expected_count}")
    keys=[r.get("offering_key","") for r in rows]
    add("D02_UNIQUE_OFFERING_KEYS", all(keys) and len(keys)==len(set(keys)), f"unique={len(set(keys))}/{len(keys)}")
    add("D03_WEFUNDER_ONLY", all(r.get("intermediary_name")==EXPECTED_INTERMEDIARY and r.get("intermediary_cik")==EXPECTED_INTERMEDIARY_CIK for r in rows), "required Wefunder identifiers")
    add("D04_INITIAL_FORM_C_IN_2020", all(r.get("initial_form_c_date","").startswith("2020-") for r in rows), "all anchors in 2020")
    add("D05_INITIAL_SEC_EVIDENCE", all(r.get("initial_form_c_accession") and r.get("sec_initial_url","").startswith("https://www.sec.gov/Archives/edgar/data/") for r in rows), "accession + direct SEC URL retained")
    def positive(r):
        try: amt=float(r.get("funding_amount_usd",""))
        except: return False
        return amt>0 and bool(r.get("funding_update_accession")) and bool(r.get("funding_evidence_text")) and r.get("sec_funding_url","").startswith("https://www.sec.gov/Archives/edgar/data/")
    add("D06_SEC_CONFIRMED_FUNDING", all(positive(r) for r in rows), "positive proceeds + C-U evidence + SEC URL")
    add("D07_NO_FINAL_WITHDRAWALS", all(int(r.get("withdrawal_count","0") or 0)==0 for r in rows), "zero withdrawals on admitted rows")
    chrono=True; bad=[]
    for r in rows:
        try:
            ok=d(r["initial_form_c_date"]) <= d(r["funding_close_date"]) <= d(r["funding_update_date"])
        except Exception: ok=False
        if not ok: bad.append(r.get("offering_key")); chrono=False
    add("D08_CHRONOLOGY", chrono, f"bad={bad}")
    return {
        "milestone":"Phase 1B denominator freeze",
        "manifest":str(path),
        "manifest_sha256":sha256(path),
        "verified_manifest_rows":len(rows),
        "promotion_gate":"PASS" if all(g["passed"] for g in gates) else "BLOCKED",
        "gates":gates,
    }

def verify_outcomes(manifest_path, outcomes_path, cutoff="2026-10-08"):
    cohort=read_csv(manifest_path); outs=read_csv(outcomes_path)
    keys={r["offering_key"] for r in cohort}; okeys=[r.get("offering_key","") for r in outs]
    gates=[]
    def add(i,ok,detail): gates.append({"id":i,"passed":bool(ok),"detail":detail})
    add("O01_ONE_OUTCOME_PER_COHORT_ROW", len(outs)==len(cohort) and set(okeys)==keys and len(okeys)==len(set(okeys)), f"outcomes={len(outs)} cohort={len(cohort)}")
    add("O02_NO_EXTRA_OUTCOME_ROWS", set(okeys)<=keys, f"extra={sorted(set(okeys)-keys)}")
    allowed={"failure","active_censor","acquisition_censor","listing_censor"}
    add("O03_ALLOWED_EVENT_TYPES", all(r.get("event_type") in allowed for r in outs), "event types valid")
    add("O04_VERIFIED_OUTCOME_EVIDENCE", all(r.get("evidence_url") and r.get("evidence_quality") in {"primary","independent_secondary","regulatory"} for r in outs), "source + quality required")
    cutoff_d=d(cutoff); dated=True; bad=[]
    close={r["offering_key"]:d(r["funding_close_date"]) for r in cohort}
    for r in outs:
        try: od=d(r["observation_date"]); ok=close[r["offering_key"]] <= od <= cutoff_d
        except Exception: ok=False
        if not ok: dated=False; bad.append(r.get("offering_key"))
    add("O05_DATED_OBSERVATIONS", dated, f"bad={bad}")
    add("O06_OUTCOME_AFTER_FUNDING", dated, "observation date is not before funding close")
    add("O07_NO_SILENCE_EQUALS_SURVIVAL", all(not (r.get("event_type")=="active_censor" and r.get("observation_date")==cutoff and r.get("evidence_basis")=="silence") for r in outs), "no silence-to-cutoff rule")
    return {"gates":gates,"promotion_gate":"PASS" if all(g["passed"] for g in gates) else "BLOCKED"}

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",default="data/cohort_manifest.csv")
    ap.add_argument("--outcomes")
    ap.add_argument("--output")
    a=ap.parse_args()
    out=verify_denominator(a.manifest)
    if a.outcomes:
        oo=verify_outcomes(a.manifest,a.outcomes)
        out["outcome_gates"]=oo["gates"]
        if oo["promotion_gate"]!="PASS": out["promotion_gate"]="BLOCKED"
    text=json.dumps(out,indent=2,sort_keys=True)
    if a.output: Path(a.output).write_text(text+"\n",encoding="utf-8")
    print(text)
