from __future__ import annotations
import json
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

def gate(gid,passed,detail):
    return {"id":gid,"passed":bool(passed),"detail":detail}

def verify_cp2():
    gates=[]
    missing=[p for p in REQUIRED_CP2 if not (ROOT/p).exists()]
    gates.append(gate("C2_01_REQUIRED_FILES",not missing,f"missing={missing}"))

    d=json.loads((ROOT/"decisions/PHASE_1C_DECISIONS.json").read_text())
    ids={x["id"] for x in d["nodes"]}
    expected={f"D{i:02d}" for i in range(1,13)} | {f"D{i}" for i in range(14,27)} | {f"D{i}" for i in range(28,40)} | {"D13R","D15R","D27R","D29R"}
    gates.append(gate("C2_02_TYPED_DECISIONS",expected<=ids,f"typed={len(ids)} expected_subset={len(expected)}"))
    gates.append(gate("C2_03_DECISION_FIELDS",all(all(k in n for k in ["id","question","type","options","prior","evidence","likelihood","posterior","expected_value","selected_option","confidence","reversible"]) for n in d["nodes"]),"required fields on every node"))

    from src.phase1c.model import PLATFORMS, PRIMARY_FIELDS
    gates.append(gate("C2_04_PLATFORM_ENUM",len(PLATFORMS)==5,f"platforms={sorted(PLATFORMS)}"))
    gates.append(gate("C2_05_FIELD_ENUM",len(PRIMARY_FIELDS)==13,f"fields={len(PRIMARY_FIELDS)} incl fallback"))

    from src.phase1c.identity import CompanyIdentity, match_company
    name_only=match_company(CompanyIdentity("Same Name Inc"),CompanyIdentity("Same Name LLC"))
    gates.append(gate("C2_06_NO_NAME_ONLY_AUTOMATCH",name_only.decision!="MATCH",f"decision={name_only.decision}"))

    return {"checkpoint":"PHASE_1C_CP2","gates":gates,"promotion_gate":"PASS" if all(x["passed"] for x in gates) else "BLOCKED"}

if __name__=="__main__":
    out=verify_cp2()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["promotion_gate"]=="PASS" else 1)
