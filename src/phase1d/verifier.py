#!/usr/bin/env python3
from __future__ import annotations

import csv, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/phase1d"

def read_csv(name):
    with (DATA/name).open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def read_json(name):
    return json.loads((DATA/name).read_text(encoding="utf-8"))

def g(gid,passed,detail):
    return {"id":gid,"passed":bool(passed),"detail":detail}

def fnum(x):
    try:return float(x)
    except:return None

def verify():
    gates=[]

    cov=read_json("cp1_coverage.json")
    p=cov["platforms"]
    gates.append(g("D1_01_CP1_REU_ENUMERABLE",p["republic_europe"]["status"]=="PASS_NATIVE_ENUMERABLE",p["republic_europe"]["status"]))
    incomplete=[k for k,v in p.items() if k!="republic_europe" and v["status"]=="CENSUS_INCOMPLETE"]
    gates.append(g("D1_02_OTHER_PLATFORM_SUPPRESSION",len(incomplete)==4,f"incomplete={sorted(incomplete)}"))

    norm=read_csv("cp2_republic_europe_rounds_normalized.csv")
    usable=[r for r in norm if r["offering_year_status"]=="BOUNDED_YEAR"]
    unresolved=[r for r in norm if r["offering_year_status"]=="YEAR_UNRESOLVED"]
    gates.append(g("D1_03_CP2_COUNTS",len(norm)==952 and len(usable)==796 and len(unresolved)==156,f"all={len(norm)} usable={len(usable)} unresolved={len(unresolved)}"))
    gates.append(g("D1_04_UNIQUE_ROUND_IDS",len({r["round_id"] for r in norm})==len(norm),f"unique={len({r['round_id'] for r in norm})}"))
    gates.append(g("D1_05_USABLE_STRONG_IDS",all(r["canonical_company_id"].startswith("ukco:") for r in usable),"all rate-eligible rows strong"))
    expected_year={"2020":184,"2021":191,"2022":181,"2023":142,"2024":47,"2025":51}
    actual_year={y:sum(1 for r in usable if r["offering_year"]==y) for y in expected_year}
    gates.append(g("D1_06_BOUNDED_YEAR_COUNTS",actual_year==expected_year,f"actual={actual_year}"))

    graph=read_json("cp2_republic_europe_repeat_round_audit.json")
    gates.append(g("D1_07_GRAPH_FREEZE",graph["sequence_edge_candidates"]==160 and graph["same_round_review_candidates"]==0,f"edges={graph['sequence_edge_candidates']} duplicates={graph['same_round_review_candidates']}"))

    ledger=read_csv("cp3_republic_europe_outcome_ledger_v3.csv")
    rate=[r for r in ledger if r["offering_year_status"]=="BOUNDED_YEAR"]
    gates.append(g("D1_08_LEDGER_V3_COUNTS",len(ledger)==952 and len(rate)==796,f"ledger={len(ledger)} rate={len(rate)}"))
    succ=sum(1 for r in rate if r["success_date"])
    closure=sum(1 for r in rate if r["closure_date"])
    terminal=[r for r in rate if r["terminal_event_type"]=="ACQUISITION_VALUE_UNKNOWN"]
    gates.append(g("D1_09_OUTCOME_COUNTS",succ==55 and closure==0 and len(terminal)==2,f"success={succ} closure={closure} terminal_unknown={len(terminal)}"))
    gates.append(g("D1_10_NO_ZERO_VAL_AUTO_CLOSURE",closure==0,"zero indicative valuation was review trigger only"))
    zeigo=[r for r in ledger if r["round_id"] in {"reurope:zeigo-energy","reurope:zeigo-energy1"}]
    gates.append(g("D1_11_ZEIGO_TERMINAL_FOLLOWUP",len(zeigo)==2 and all(r["censor_date"]=="2022-07-02" and r["terminal_event_date_status"]=="INTERVAL_KNOWN_YEAR_ONLY" for r in zeigo),str([(r["round_id"],r["censor_date"]) for r in zeigo])))

    business=read_json("cp3_republic_europe_business_manifest.json")["summary"]
    gates.append(g("D1_12_SECONDARY_CENSUS",business["candidate_business_pages"]==784 and business["successful_fetches"]==784,f"pages={business['candidate_business_pages']} fetched={business['successful_fetches']}"))
    gates.append(g("D1_13_ELIGIBILITY_RULE",business["rule"]["not_eligible"].startswith("neutral") and business["rule"]["valuation_only"].startswith("does not"),str(business["rule"])))

    follow=read_json("cp3_republic_europe_followon_all_later_audit.json")
    gates.append(g("D1_14_ALL_LATER_SUCCESS_SCAN",follow["qualified_index_to_later_successes"]==63 and follow["nonadjacent_first_successes"]==6,f"all={follow['qualified_index_to_later_successes']} nonadj={follow['nonadjacent_first_successes']}"))

    v3=read_json("cp3_republic_europe_outcome_ledger_v3_summary.json")
    gates.append(g("D1_15_V2_SUPERSEDED",v3["supersedes"].startswith("cp3_republic_europe_outcome_ledger_v2"),v3["supersedes"]))

    rq1=read_csv("cp4_republic_europe_rq1_candidate_v2.csv")
    gates.append(g("D1_16_RQ1_SHAPE",len(rq1)==24,f"rows={len(rq1)}"))
    gates.append(g("D1_17_PLATFORM_OBSERVED",all(r["estimand_label"]=="platform_observed" for r in rq1),"all candidate estimates platform-observed"))

    bad_bounds=[]
    for r in rq1:
        for k in ["success_cif","closure_cif","operating_survival","success_ci_lower","success_ci_upper","survival_ci_lower","survival_ci_upper","closure_support_upper_95","success_support_upper_95","survival_support_lower_95"]:
            if r.get(k) not in ("",None):
                v=fnum(r[k])
                if v is None or v<0 or v>1: bad_bounds.append((r["offering_year"],r["horizon_months"],k,r[k]))
    gates.append(g("D1_18_PROBABILITY_BOUNDS",not bad_bounds,f"bad={bad_bounds[:10]}"))

    # No unsupported horizon may carry point estimates.
    bad_unsupported=[r for r in rq1 if r["estimable"]=="false" and any(r[k] not in ("",None) for k in ["success_cif","closure_cif","operating_survival"])]
    gates.append(g("D1_19_NO_HORIZON_EXTRAPOLATION",not bad_unsupported,f"bad={[(r['offering_year'],r['horizon_months']) for r in bad_unsupported]}"))

    # Within each cohort, success CIF must be nondecreasing and survival nonincreasing over estimable horizons.
    monotone=True; details=[]
    for y in sorted({r["offering_year"] for r in rq1}):
        rr=sorted([r for r in rq1 if r["offering_year"]==y and r["estimable"]=="true"],key=lambda x:int(x["horizon_months"]))
        sf=[fnum(r["success_cif"]) for r in rr]; sv=[fnum(r["operating_survival"]) for r in rr]
        if any(sf[i]+1e-12<sf[i-1] for i in range(1,len(sf))) or any(sv[i]>sv[i-1]+1e-12 for i in range(1,len(sv))):
            monotone=False;details.append((y,sf,sv))
    gates.append(g("D1_20_MONOTONE_ESTIMANDS",monotone,f"bad={details}"))

    # Zero target cells must never use a fake 0-0 / 1-1 bootstrap interval.
    bad_zero=[]
    for r in rq1:
        if r["estimable"]!="true": continue
        if int(r["closure_events_observed"])==0 and not r["closure_support_upper_95"]:
            bad_zero.append(("closure",r["offering_year"],r["horizon_months"]))
        if int(r["success_events_observed"])==0 and not r["success_support_upper_95"]:
            bad_zero.append(("success",r["offering_year"],r["horizon_months"]))
        if int(r["terminal_nonclosure_events_observed"])==0 and fnum(r["operating_survival"])==1 and not r["survival_support_lower_95"]:
            bad_zero.append(("survival",r["offering_year"],r["horizon_months"]))
    gates.append(g("D1_21_ZERO_EVENT_SUPPORT_BOUNDS",not bad_zero,f"bad={bad_zero}"))

    y2020={int(r["horizon_months"]):r for r in rq1 if r["offering_year"]=="2020"}
    s24=fnum(y2020[24]["operating_survival"]); s36=fnum(y2020[36]["operating_survival"])
    st24=fnum(y2020[24]["operating_survival_zeigo_start"]); en24=fnum(y2020[24]["operating_survival_zeigo_end"])
    gates.append(g("D1_22_ZEIGO_SURVIVAL_EFFECT",s24 is not None and s24<1 and s36 is not None and s36<=s24,f"s24={s24} s36={s36}"))
    gates.append(g("D1_23_ZEIGO_SENSITIVITY_BRACKETS",st24 is not None and en24 is not None and min(st24,en24)<=s24<=max(st24,en24),f"start={st24} primary={s24} end={en24}"))

    # Every estimable RQ1 cell is intentionally low-information under current support.
    est=[r for r in rq1 if r["estimable"]=="true"]
    gates.append(g("D1_24_RQ1_LOW_INFORMATION_EXPOSED",len(est)==17 and all(r["low_information"]=="true" for r in est),f"estimable={len(est)}"))

    rq2=read_csv("cp4_republic_europe_rq2_field_gate_audit_v2.csv")
    passed=[r for r in rq2 if r["gate_pass"]=="true"]
    gates.append(g("D1_25_RQ2_FAIL_CLOSED",len(passed)==0,f"passing_field_cells={len(passed)}"))

    # No final rates for the four incomplete platforms may exist in Phase 1D data.
    forbidden=[]
    for pth in DATA.glob("cp4_*"):
        n=pth.name.lower()
        if any(x in n for x in ["wefunder","startengine","republic_us","crowdcube"]):
            forbidden.append(n)
    gates.append(g("D1_26_NO_INCOMPLETE_PLATFORM_RATES",not forbidden,f"forbidden={forbidden}"))

    # Candidate v1 must not be treated as final.
    summary=read_json("cp4_republic_europe_candidate_v2_summary.json")
    gates.append(g("D1_27_INVALIDATED_V1_DECLARED","invalidated_prior_candidate" in summary and "must not be used" in summary["invalidated_prior_candidate"],summary.get("invalidated_prior_candidate")))

    return {
      "checkpoint":"PHASE_1D_CP4_CANDIDATE_V2",
      "gate_count":len(gates),
      "passed":sum(1 for x in gates if x["passed"]),
      "promotion_gate":"PASS" if all(x["passed"] for x in gates) else "BLOCKED",
      "gates":gates
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["promotion_gate"]=="PASS" else 1)
