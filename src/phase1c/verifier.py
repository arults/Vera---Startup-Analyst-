from __future__ import annotations
import json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

REQUIRED_CP2=[
    "schema/phase1c_round.schema.json",
    "src/phase1c/model.py",
    "src/phase1c/identity.py",
    "src/phase1c/graph.py",
    "tests/test_phase1c_identity_graph.py",
    "decisions/PHASE_1C_DECISIONS.json",
]
REQUIRED_CP3=[
    "src/phase1c/outcomes.py",
    "src/phase1c/estimators.py",
    "src/phase1c/reporting.py",
    "tests/test_phase1c_outcomes_estimators.py",
    "fixtures/phase1c/synthetic_cases.json",
]

def gate(gid,passed,detail):
    return {"id":gid,"passed":bool(passed),"detail":detail}

def verify_all():
    gates=[]
    missing=[p for p in REQUIRED_CP2+REQUIRED_CP3 if not (ROOT/p).exists()]
    gates.append(gate("C_01_REQUIRED_FILES",not missing,f"missing={missing}"))

    d=json.loads((ROOT/"decisions/PHASE_1C_DECISIONS.json").read_text())
    ids={x["id"] for x in d["nodes"]}
    expected={f"D{i:02d}" for i in range(1,13)} | {"D13R","D14","D15R"} | {f"D{i}" for i in range(16,27)} | {"D27R","D28","D29R"} | {f"D{i}" for i in range(30,40)}
    gates.append(gate("C_02_TYPED_DECISIONS",expected<=ids,f"typed={len(ids)} expected_subset={len(expected)}"))
    required_fields=["id","question","type","options","prior","evidence","likelihood","posterior","expected_value","selected_option","confidence","reversible"]
    gates.append(gate("C_03_DECISION_FIELDS",all(all(k in n for k in required_fields) for n in d["nodes"]),"required fields on every node"))

    from src.phase1c.model import PLATFORMS, PRIMARY_FIELDS
    gates.append(gate("C_04_PLATFORM_ENUM",len(PLATFORMS)==5,f"platforms={sorted(PLATFORMS)}"))
    gates.append(gate("C_05_FIELD_ENUM",len(PRIMARY_FIELDS)==13,f"fields={len(PRIMARY_FIELDS)} incl fallback"))

    from src.phase1c.identity import CompanyIdentity, match_company
    name_only=match_company(CompanyIdentity("Same Name Inc"),CompanyIdentity("Same Name LLC"))
    gates.append(gate("C_06_NO_NAME_ONLY_AUTOMATCH",name_only.decision!="MATCH",f"decision={name_only.decision}"))

    from src.phase1c.outcomes import OutcomeEvent,EventType,State,is_qualified_success,is_confirmed_closure,next_state,censor_date
    cap_only=OutcomeEvent("r",date(2024,1,1),EventType.QUALIFIED_FOLLOWON,"u",True,None,20)
    gates.append(gate("C_07_NO_INCOMPARABLE_FOLLOWON_SUCCESS",not is_qualified_success(cap_only),"missing pre comparable valuation cannot qualify"))
    acq=OutcomeEvent("r",date(2024,1,1),EventType.ACQUISITION,"u",True)
    gates.append(gate("C_08_ACQ_VALUE_UNKNOWN",next_state(State.OPERATING_PRE_SUCCESS,acq)==State.ACQUISITION_VALUE_UNKNOWN,"unknown-consideration acquisition is not automatic success"))
    weak_close=OutcomeEvent("r",date(2024,1,1),EventType.CLOSURE,"u",True,explicit_closure=False)
    gates.append(gate("C_09_EXPLICIT_CLOSURE_REQUIRED",not is_confirmed_closure(weak_close),"staleness/no-news cannot establish closure"))
    cd=censor_date(date(2027,1,1),date(2026,10,8),date(2025,1,1))
    gates.append(gate("C_10_CENSOR_CAPPED_AT_EXTRACTION",cd==date(2026,10,8),f"censor={cd.isoformat()}"))

    from src.phase1c.estimators import TimedTransition,SubjectFollowup,aalen_johansen_occupancy,independent_operating_probability,cluster_bootstrap_indices
    pts=aalen_johansen_occupancy(
        [
            TimedTransition("a","ca",1,State.OPERATING_PRE_SUCCESS,State.OPERATING_POST_SUCCESS),
            TimedTransition("b","cb",2,State.OPERATING_PRE_SUCCESS,State.CLOSURE),
        ],
        [SubjectFollowup("a","ca",5),SubjectFollowup("b","cb",5)]
    )
    sums=[sum(p.probabilities.values()) for p in pts]
    gates.append(gate("C_11_AJ_PROBABILITY_CONSERVATION",all(abs(x-1)<1e-12 for x in sums),f"sums={sums}"))
    gates.append(gate("C_12_AJ_SURVIVAL_STATE",abs(independent_operating_probability(pts[-1])-.5)<1e-12,f"operating={independent_operating_probability(pts[-1])}"))

    reps=cluster_bootstrap_indices(["c1","c1","c2"],n_boot=10,seed=7)
    clustered=all(r.count(0)==r.count(1) for r in reps)
    gates.append(gate("C_13_CLUSTERED_BOOTSTRAP",clustered,"repeat rounds move together"))

    from src.phase1c.reporting import rq1_cell_decision,rq2_field_cell_decision,adjacent_pool_order
    gates.append(gate("C_14_RQ1_SMALL_N_VISIBLE",rq1_cell_decision(12,2).report and rq1_cell_decision(12,2).low_information,"small RQ1 cell remains visible with flag"))
    gates.append(gate("C_15_RQ2_CELL_GATE",rq2_field_cell_decision(29,8,.95).pool and rq2_field_cell_decision(50,8,.79).pool,"n/event/ascertainment gates enforced"))
    gates.append(gate("C_16_MATURITY_POOLING",set(adjacent_pool_order(2025))=={2024,2025},"2025 pooling cannot silently cross into 2023"))

    return {
        "checkpoint":"PHASE_1C_FRAMEWORK",
        "gates":gates,
        "promotion_gate":"PASS" if all(x["passed"] for x in gates) else "BLOCKED",
    }

if __name__=="__main__":
    out=verify_all()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["promotion_gate"]=="PASS" else 1)
