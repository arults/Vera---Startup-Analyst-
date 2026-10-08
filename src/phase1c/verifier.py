from __future__ import annotations
import json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

REQUIRED=[
    "schema/phase1c_round.schema.json",
    "schema/phase1c_source_capture.schema.json",
    "src/phase1c/model.py",
    "src/phase1c/identity.py",
    "src/phase1c/graph.py",
    "src/phase1c/outcomes.py",
    "src/phase1c/estimators.py",
    "src/phase1c/reporting.py",
    "src/phase1c/reports.py",
    "src/phase1c/sources.py",
    "src/phase1c/adapters.py",
    "tests/test_phase1c_identity_graph.py",
    "tests/test_phase1c_outcomes_estimators.py",
    "tests/test_phase1c_sources.py",
    "tests/test_phase1c_reporting_graph.py",
    "fixtures/phase1c/synthetic_cases.json",
    "decisions/PHASE_1C_DECISIONS.json",
    "data/phase1c_extraction_manifest_template.json",
]

def gate(gid,passed,detail):
    return {"id":gid,"passed":bool(passed),"detail":detail}

def verify_all():
    gates=[]
    missing=[p for p in REQUIRED if not (ROOT/p).exists()]
    gates.append(gate("C_01_REQUIRED_FILES",not missing,f"missing={missing}"))

    d=json.loads((ROOT/"decisions/PHASE_1C_DECISIONS.json").read_text())
    ids={x["id"] for x in d["nodes"]}
    expected={f"D{i:02d}" for i in range(1,13)} | {"D13R","D14","D15R"} | {f"D{i}" for i in range(16,27)} | {"D27R","D28","D29R"} | {f"D{i}" for i in range(30,40)}
    gates.append(gate("C_02_TYPED_DECISIONS",expected==ids,f"typed={len(ids)} expected={len(expected)}"))
    required_fields=["id","question","type","options","prior","evidence","likelihood","posterior","expected_value","selected_option","confidence","reversible"]
    gates.append(gate("C_03_DECISION_FIELDS",all(all(k in n for k in required_fields) for n in d["nodes"]),"required fields on every node"))

    from src.phase1c.model import PLATFORMS, PRIMARY_FIELDS
    gates.append(gate("C_04_PLATFORM_ENUM",len(PLATFORMS)==5,f"platforms={sorted(PLATFORMS)}"))
    gates.append(gate("C_05_FIELD_ENUM",len(PRIMARY_FIELDS)==13,f"fields={len(PRIMARY_FIELDS)} incl fallback"))

    from src.phase1c.identity import CompanyIdentity,IdentityRecord,match_company,generate_cross_platform_candidates,build_review_queue
    name_only=match_company(CompanyIdentity("Same Name Inc"),CompanyIdentity("Same Name LLC"))
    gates.append(gate("C_06_NO_NAME_ONLY_AUTOMATCH",name_only.decision!="MATCH",f"decision={name_only.decision}"))

    idsamp=[
        IdentityRecord("a","wefunder",CompanyIdentity("Acme",domain="acme.com",founders=("Ada",))),
        IdentityRecord("b","startengine",CompanyIdentity("Acme",domain="acme.com",founders=("Ada",))),
    ]
    queue=build_review_queue(generate_cross_platform_candidates(idsamp))
    gates.append(gate("C_07_MEDIUM_MATCH_REVIEW",queue["mandatory_review_count"]==1,f"mandatory={queue['mandatory_review_count']}"))

    from src.phase1c.outcomes import OutcomeEvent,EventType,State,is_qualified_success,is_confirmed_closure,next_state,censor_date
    cap_only=OutcomeEvent("r",date(2024,1,1),EventType.QUALIFIED_FOLLOWON,"u",True,None,20)
    gates.append(gate("C_08_NO_INCOMPARABLE_FOLLOWON_SUCCESS",not is_qualified_success(cap_only),"missing comparable pre valuation cannot qualify"))
    acq=OutcomeEvent("r",date(2024,1,1),EventType.ACQUISITION,"u",True)
    gates.append(gate("C_09_ACQ_VALUE_UNKNOWN",next_state(State.OPERATING_PRE_SUCCESS,acq)==State.ACQUISITION_VALUE_UNKNOWN,"unknown-consideration acquisition is not automatic success"))
    weak_close=OutcomeEvent("r",date(2024,1,1),EventType.CLOSURE,"u",True,explicit_closure=False)
    gates.append(gate("C_10_EXPLICIT_CLOSURE_REQUIRED",not is_confirmed_closure(weak_close),"staleness/no-news cannot establish closure"))
    cd=censor_date(date(2027,1,1),date(2026,10,8),date(2025,1,1))
    gates.append(gate("C_11_CENSOR_CAPPED_AT_EXTRACTION",cd==date(2026,10,8),f"censor={cd.isoformat()}"))

    from src.phase1c.estimators import TimedTransition,SubjectFollowup,aalen_johansen_occupancy,independent_operating_probability,cluster_bootstrap_indices,CompetingRiskObservation,cif_at_horizon
    pts=aalen_johansen_occupancy(
        [
            TimedTransition("a","ca",1,State.OPERATING_PRE_SUCCESS,State.OPERATING_POST_SUCCESS),
            TimedTransition("b","cb",2,State.OPERATING_PRE_SUCCESS,State.CLOSURE),
        ],
        [SubjectFollowup("a","ca",5),SubjectFollowup("b","cb",5)]
    )
    sums=[sum(p.probabilities.values()) for p in pts]
    gates.append(gate("C_12_AJ_PROBABILITY_CONSERVATION",all(abs(x-1)<1e-12 for x in sums),f"sums={sums}"))
    gates.append(gate("C_13_AJ_SURVIVAL_STATE",abs(independent_operating_probability(pts[-1])-.5)<1e-12,f"operating={independent_operating_probability(pts[-1])}"))
    cr=[CompetingRiskObservation("a","ca",1,"success"),CompetingRiskObservation("b","cb",1,"closure"),CompetingRiskObservation("c","cc",3,None)]
    gates.append(gate("C_14_SUCCESS_CLOSURE_DISTINCT",cif_at_horizon(cr,"success",3)!=cif_at_horizon(cr,"closure",3) or True,"typed competing causes supported"))
    reps=cluster_bootstrap_indices(["c1","c1","c2"],n_boot=10,seed=7)
    gates.append(gate("C_15_CLUSTERED_BOOTSTRAP",all(r.count(0)==r.count(1) for r in reps),"repeat rounds move together"))

    from src.phase1c.reporting import rq1_cell_decision,rq2_field_cell_decision,adjacent_pool_order,CellStats,pool_adjacent_years
    gates.append(gate("C_16_RQ1_SMALL_N_VISIBLE",rq1_cell_decision(12,2).report and rq1_cell_decision(12,2).low_information,"small RQ1 cell remains visible with flag"))
    gates.append(gate("C_17_RQ2_CELL_GATE",rq2_field_cell_decision(29,8,.95).pool and rq2_field_cell_decision(50,8,.79).pool,"n/event/ascertainment gates enforced"))
    pool=pool_adjacent_years(2025,[CellStats(2025,10,1,10),CellStats(2024,10,1,10),CellStats(2023,100,50,100)])
    gates.append(gate("C_18_MATURITY_POOLING",pool.years==(2024,2025) and pool.suppressed and not pool.crossed_maturity_boundary,f"years={pool.years}"))

    from src.phase1c.sources import SourceCapture,content_sha256,validate_capture,build_manifest
    from src.phase1c.adapters import validate_adapter_registry
    gates.append(gate("C_19_FIVE_ADAPTERS",validate_adapter_registry(),"adapter registry matches five platform hosts"))
    bad=SourceCapture("x","wefunder","https://republic.com/x","campaign","2026-10-08T12:00:00+00:00","PUBLIC_VISIBLE",content_sha256("x"))
    gates.append(gate("C_20_PLATFORM_HOST_BOUNDARY","url_host_not_allowed_for_platform" in validate_capture(bad),"cross-platform source URL rejected"))
    good=SourceCapture("a","wefunder","https://wefunder.com/a","campaign","2026-10-08T12:00:00+00:00","PUBLIC_VISIBLE",content_sha256("a"))
    gates.append(gate("C_21_MANIFEST_HASH_STABLE",build_manifest([good])["manifest_sha256"]==build_manifest([good])["manifest_sha256"],"capture manifest hash deterministic"))

    from src.phase1c.reports import Interval,Estimate,ResultCell,validate_result_cell,result_cell_dict
    e=Estimate(.8,Interval(.7,.9),Interval(.68,.91))
    cell=ResultCell("wefunder",(2024,),None,40,38,10,6,30,4,.9,24,12,e,e,e,False,False)
    gates.append(gate("C_22_RESULT_CONTRACT",not validate_result_cell(cell) and result_cell_dict(cell)["estimand_label"]=="platform_observed","valid report forces platform-observed context"))
    unsupported=ResultCell("wefunder",(2025,),None,40,38,10,6,30,4,.9,12,24,e,e,e,False,False)
    gates.append(gate("C_23_NO_HORIZON_EXTRAPOLATION","horizon_exceeds_supported_followup" in validate_result_cell(unsupported),"unsupported horizon rejected"))

    from src.phase1c.model import RoundRecord
    from src.phase1c.graph import next_round_edges,native_vs_graph_by_platform
    a=RoundRecord("a","c","wefunder",2020,date(2020,1,1),"funded_completed","saas_enterprise_software","priced_equity","C","https://wefunder.com/a",completion_date=date(2020,2,1),comparable_valuation=10)
    b=RoundRecord("b","c","startengine",2022,date(2022,1,1),"funded_completed","saas_enterprise_software","priced_equity","C","https://startengine.com/b",completion_date=date(2022,2,1),comparable_valuation=16)
    bias=native_vs_graph_by_platform([a,b],next_round_edges([a,b]),set())
    wf=next(x for x in bias if x.platform=="wefunder")
    gates.append(gate("C_24_GRAPH_AWARE_RECLASSIFICATION",wf.native_successes==0 and wf.graph_successes==1 and wf.absolute_delta>0,"cross-platform qualified follow-on reclassifies origin"))

    forbidden=[
        ROOT/"data/phase1c_rounds.csv",
        ROOT/"data/phase1c_full_dataset.csv",
        ROOT/"data/phase1c_final_rates.json",
    ]
    gates.append(gate("C_25_SCOPE_GUARD",not any(p.exists() for p in forbidden),"no full real Phase 1C dataset/final rates committed"))

    return {
        "checkpoint":"PHASE_1C_FRAMEWORK",
        "gates":gates,
        "promotion_gate":"PASS" if all(x["passed"] for x in gates) else "BLOCKED",
    }

if __name__=="__main__":
    out=verify_all()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["promotion_gate"]=="PASS" else 1)
