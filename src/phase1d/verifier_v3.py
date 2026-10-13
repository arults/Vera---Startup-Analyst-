#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/phase1d"
DAYS_PER_MONTH = 30.4375


def read_csv(name: str) -> list[dict]:
    with (DATA / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def latest_run_summary(directory: str) -> dict | None:
    root = DATA / directory
    candidates = []
    for path in root.glob("gh-*/summary.json") if root.exists() else []:
        try:
            run = int(path.parent.name.split("-", 1)[1])
            candidates.append((run, path))
        except Exception:
            pass
    return json.loads(max(candidates)[1].read_text()) if candidates else None


def gate(gid: str, passed: bool, detail: object) -> dict:
    return {"id": gid, "passed": bool(passed), "detail": detail}


def fnum(value):
    try:
        return float(value)
    except Exception:
        return None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def months(start: str, end: str) -> float | None:
    if not start or not end:
        return None
    value = (date.fromisoformat(end) - date.fromisoformat(start)).days / DAYS_PER_MONTH
    if value < -1e-12:
        raise ValueError("negative event time")
    return max(0.0, value)


def terminal_date(row: dict, mode: str = "mid") -> str:
    if row.get("closure_date"):
        return row["closure_date"]
    if mode == "start":
        return row.get("terminal_event_interval_start", "") or row.get("terminal_event_midpoint_for_primary", "")
    if mode == "end":
        return row.get("terminal_event_interval_end", "") or row.get("terminal_event_midpoint_for_primary", "")
    return row.get("terminal_event_midpoint_for_primary", "") or row.get("terminal_event_interval_end", "") or row.get("terminal_event_interval_start", "")


def followup(row: dict) -> float:
    if row.get("followup_months") not in (None, ""):
        return float(row["followup_months"])
    value = months(row.get("completion_date", ""), row.get("censor_date", ""))
    return value or 0.0


def first_observation(row: dict, target: str) -> tuple[float, str | None]:
    events = []
    start = row.get("completion_date", "")
    if target == "success" and row.get("success_date"):
        events.append((months(start, row["success_date"]), 2, "success"))
    if target == "closure" and row.get("closure_date"):
        events.append((months(start, row["closure_date"]), 0, "closure"))
    terminal = terminal_date(row)
    if terminal:
        cause = "closure" if row.get("closure_date") else "terminal_other"
        events.append((months(start, terminal), 0 if cause == "closure" else 1, cause))
    events = [(t, p, c) for t, p, c in events if t is not None and t <= followup(row) + 1e-6]
    if events:
        t, _, cause = min(events, key=lambda x: (x[0], x[1]))
        return t, cause
    return followup(row), None


def cif(rows: list[dict], target: str, horizon: float) -> float:
    observations = [first_observation(r, target) for r in rows]
    times = sorted({t for t, cause in observations if cause is not None and t <= horizon})
    survival = 1.0
    value = 0.0
    for t in times:
        at_risk = sum(1 for time, _ in observations if time >= t)
        all_events = sum(1 for time, cause in observations if cause is not None and abs(time - t) < 1e-9)
        target_events = sum(1 for time, cause in observations if cause == target and abs(time - t) < 1e-9)
        if at_risk <= 0 or all_events > at_risk:
            raise ValueError("invalid CIF risk set")
        value += survival * target_events / at_risk
        survival *= 1.0 - all_events / at_risk
    return value


def km(rows: list[dict], horizon: float, mode: str = "mid") -> float:
    observations = []
    for row in rows:
        terminal = terminal_date(row, mode)
        observations.append((months(row["completion_date"], terminal), True) if terminal else (followup(row), False))
    times = sorted({t for t, event in observations if event and t is not None and t <= horizon})
    survival = 1.0
    for t in times:
        at_risk = sum(1 for time, _ in observations if time is not None and time >= t)
        events = sum(1 for time, event in observations if event and abs(time - t) < 1e-9)
        survival *= 1.0 - events / at_risk
    return survival


def verify() -> dict:
    gates = []

    coverage = read_json("cp1_coverage.json")
    platforms = coverage["platforms"]
    gates.append(gate("D3_01_REU_NATIVE_CENSUS", platforms["republic_europe"]["status"] == "PASS_NATIVE_ENUMERABLE", platforms["republic_europe"]["status"]))
    incomplete = sorted(k for k, v in platforms.items() if k != "republic_europe" and v["status"] == "CENSUS_INCOMPLETE")
    gates.append(gate("D3_02_OTHER_PLATFORM_SUPPRESSION", incomplete == ["crowdcube", "republic_us", "startengine", "wefunder"], incomplete))
    gates.append(gate("D3_03_WEFUNDER_PARTIAL_NOT_CENSUS", platforms["wefunder"].get("archive_status") == "PARTIAL_RECENT_ARCHIVE" and platforms["wefunder"].get("rate_policy") == "SUPPRESS" and platforms["wefunder"].get("phase1b_known_name_matches") == 0, platforms["wefunder"]))

    se_browser = latest_run_summary("startengine_recovery")
    se_endpoint = latest_run_summary("startengine_endpoint_recovery")
    se_ok = bool(
        se_browser and se_endpoint
        and se_browser.get("candidate_count") == 0
        and se_endpoint.get("candidate_count") == 0
        and se_browser.get("rates_promoted") is False
        and se_endpoint.get("rates_promoted") is False
        and se_browser.get("integrity_gates", {}).get("passed") == se_browser.get("integrity_gates", {}).get("total")
        and se_endpoint.get("integrity_gates", {}).get("passed") == se_endpoint.get("integrity_gates", {}).get("total")
    )
    gates.append(gate("D3_04_STARTENGINE_ACCESS_EXHAUSTED_SUPPRESSED", se_ok, {"browser": se_browser, "endpoint": se_endpoint}))
    republic_us = latest_run_summary("republic_us_recovery")
    gates.append(gate("D3_05_REPUBLIC_US_SUPPRESSED", bool(republic_us and republic_us.get("rate_promotion_allowed") is False and republic_us.get("eligible_rate_rows") == 0), republic_us))

    normalized = read_csv("cp2_republic_europe_rounds_normalized.csv")
    usable = [r for r in normalized if r["offering_year_status"] == "BOUNDED_YEAR"]
    unresolved = [r for r in normalized if r["offering_year_status"] == "YEAR_UNRESOLVED"]
    gates.append(gate("D3_06_CP2_COUNTS", len(normalized) == 952 and len(usable) == 796 and len(unresolved) == 156, {"all": len(normalized), "usable": len(usable), "unresolved": len(unresolved)}))
    gates.append(gate("D3_07_UNIQUE_ROUNDS", len({r["round_id"] for r in normalized}) == 952, len({r["round_id"] for r in normalized})))
    gates.append(gate("D3_08_CANONICAL_STRONG_USABLE_IDS", all(r["canonical_company_id"].startswith("reurope-company:") and r["company_id_normalization_status"] == "CANONICAL_NUMBER" for r in usable), "all 796 usable rows have canonical legal IDs"))
    gates.append(gate("D3_09_RAW_LEGAL_IDS_PRESERVED", all("legal_company_number" in r and "legal_company_number_canonical" in r for r in normalized), "raw + canonical fields present"))
    year_expected = {"2020": 184, "2021": 191, "2022": 181, "2023": 142, "2024": 47, "2025": 51}
    year_actual = {y: sum(r["offering_year"] == y for r in usable) for y in year_expected}
    gates.append(gate("D3_10_YEAR_COUNTS", year_actual == year_expected, year_actual))

    collision = read_csv("cp2_republic_europe_company_id_collision_audit.csv")
    merged = [r for r in collision if r["status"] == "FORMATTING_EQUIVALENT_MERGED"]
    blocked = [r for r in collision if r["status"] == "BLOCK_REVIEW"]
    gates.append(gate("D3_11_FORMATTING_COLLISION_AUDIT", len(merged) == 3 and len(blocked) == 0 and all(r["auto_merge"] == "true" for r in merged), {"merged": len(merged), "blocked": len(blocked)}))
    graph = read_json("cp2_republic_europe_repeat_round_audit.json")
    gates.append(gate("D3_12_GRAPH_REBUILT", graph["unique_companies"] == 789 and graph["sequence_edge_candidates"] == 163 and graph["same_round_review_candidates"] == 0, graph))

    identity = read_json("cp3_republic_europe_identity_review_applied_summary.json")
    gates.append(gate("D3_13_IDENTITY_REVIEW_DISPOSITION", identity["accepted_pages"] == 5 and identity["accepted_eligible_pages"] == 2 and identity["held_candidate_rows"] == 22, identity))
    gates.append(gate("D3_14_IDENTITY_COVERAGE_EXPOSED", identity["usable_cohort_unique_companies"] == 676 and identity["usable_companies_with_positive_followup"] == 262 and identity["usable_positive_followup_coverage"] < 0.80, identity["usable_positive_followup_coverage"]))
    decisions = read_csv("cp3_republic_europe_identity_review_decisions.csv")
    unsafe_decisions = [r for r in decisions if r["review_disposition"] == "ACCEPTED_JEV_RULE" and not ({"platform_slug_exact", "deterministic_alias_exact"} <= {x.strip() for x in r["signals"].split("|")})]
    gates.append(gate("D3_15_NO_WEAK_IDENTITY_ACCEPTANCE", not unsafe_decisions, unsafe_decisions[:5]))

    ledger = read_csv("cp3_republic_europe_outcome_ledger_v4.csv")
    rate = [r for r in ledger if r["offering_year_status"] == "BOUNDED_YEAR"]
    norm_by_round = {r["round_id"]: r for r in normalized}
    ledger_ids_match = all(r["canonical_company_id"] == norm_by_round[r["round_id"]]["canonical_company_id"] for r in ledger)
    gates.append(gate("D3_16_LEDGER_V4_COUNTS", len(ledger) == 952 and len(rate) == 796 and len({r["canonical_company_id"] for r in ledger}) == 789, {"ledger": len(ledger), "rate": len(rate), "companies": len({r['canonical_company_id'] for r in ledger})}))
    gates.append(gate("D3_17_LEDGER_IDENTITY_RECONCILIATION", ledger_ids_match, "round IDs map exactly to CP2 canonical identities"))
    success_count = sum(bool(r["success_date"]) for r in ledger)
    closure_count = sum(bool(r["closure_date"]) for r in ledger)
    terminal_count = sum(bool(terminal_date(r)) for r in ledger)
    gates.append(gate("D3_18_OUTCOME_COUNTS", success_count == 63 and closure_count == 0 and terminal_count == 2, {"success": success_count, "closure": closure_count, "terminal": terminal_count}))
    ledger_summary = read_json("cp3_republic_europe_outcome_ledger_v4_summary.json")
    gates.append(gate("D3_19_NO_TERMINAL_REOPEN", ledger_summary["terminal_events_reopened"] == 0 and ledger_summary["followup_rounds_extended"] == 2 and ledger_summary["followup_companies_extended"] == 1, ledger_summary))
    gates.append(gate("D3_20_NO_ZERO_VAL_AUTO_CLOSURE", closure_count == 0, "zero valuation remained a review signal only"))

    rq1 = read_csv("cp4_republic_europe_rq1_candidate_v3.csv")
    rq2 = read_csv("cp4_republic_europe_rq2_gate_v3.csv")
    summary = read_json("cp4_republic_europe_candidate_v3_summary.json")
    gates.append(gate("D3_21_RQ1_SHAPE", len(rq1) == 24, len(rq1)))
    gates.append(gate("D3_22_CANDIDATE_ONLY_LABELS", all(r["estimand_label"] == "platform_observed" and r["promotion_status"] == "CANDIDATE_ONLY" for r in rq1) and summary["rates_promoted"] is False, summary["promotion_status"]))

    recompute_failures = []
    for row in rq1:
        cell = [r for r in rate if r["offering_year"] == row["offering_year"]]
        if row["estimable"] == "true":
            horizon = float(row["horizon_months"])
            expected_success = cif(cell, "success", horizon)
            expected_closure = cif(cell, "closure", horizon)
            expected_survival = km(cell, horizon)
            for metric, expected in (("success_cif", expected_success), ("closure_cif", expected_closure), ("operating_survival", expected_survival)):
                actual = fnum(row[metric])
                if actual is None or abs(actual - expected) > 1e-10:
                    recompute_failures.append((row["offering_year"], row["horizon_months"], metric, actual, expected))
    gates.append(gate("D3_23_INDEPENDENT_POINT_RECOMPUTATION", not recompute_failures, recompute_failures[:10]))

    bad_bounds = []
    probability_fields = ["success_cif", "closure_cif", "operating_survival", "success_ci_lower", "success_ci_upper", "closure_ci_lower", "closure_ci_upper", "survival_ci_lower", "survival_ci_upper", "success_support_upper_95", "closure_support_upper_95", "survival_support_lower_95", "operating_survival_terminal_start", "operating_survival_terminal_end"]
    for row in rq1:
        for field in probability_fields:
            if row.get(field) not in (None, ""):
                value = fnum(row[field])
                if value is None or not 0 <= value <= 1:
                    bad_bounds.append((row["offering_year"], row["horizon_months"], field, row[field]))
    gates.append(gate("D3_24_PROBABILITY_BOUNDS", not bad_bounds, bad_bounds[:10]))

    bad_intervals = []
    for row in rq1:
        for point, lower, upper in (("success_cif", "success_ci_lower", "success_ci_upper"), ("closure_cif", "closure_ci_lower", "closure_ci_upper"), ("operating_survival", "survival_ci_lower", "survival_ci_upper")):
            if row.get(lower) not in (None, "") or row.get(upper) not in (None, ""):
                p, lo, hi = fnum(row.get(point)), fnum(row.get(lower)), fnum(row.get(upper))
                if None in (p, lo, hi) or not lo <= p <= hi:
                    bad_intervals.append((row["offering_year"], row["horizon_months"], point, lo, p, hi))
    gates.append(gate("D3_25_INTERVAL_CONTAINS_POINT", not bad_intervals, bad_intervals[:10]))

    unsupported = [r for r in rq1 if r["estimable"] == "false" and any(r[k] not in (None, "") for k in ("success_cif", "closure_cif", "operating_survival"))]
    gates.append(gate("D3_26_NO_HORIZON_EXTRAPOLATION", not unsupported, [(r["offering_year"], r["horizon_months"]) for r in unsupported]))

    monotone_errors = []
    for year in sorted({r["offering_year"] for r in rq1}):
        rows = sorted([r for r in rq1 if r["offering_year"] == year and r["estimable"] == "true"], key=lambda r: int(r["horizon_months"]))
        success = [fnum(r["success_cif"]) for r in rows]
        closure = [fnum(r["closure_cif"]) for r in rows]
        survival = [fnum(r["operating_survival"]) for r in rows]
        if any(success[i] + 1e-12 < success[i-1] or closure[i] + 1e-12 < closure[i-1] or survival[i] > survival[i-1] + 1e-12 for i in range(1, len(rows))):
            monotone_errors.append((year, success, closure, survival))
    gates.append(gate("D3_27_MONOTONE_ESTIMANDS", not monotone_errors, monotone_errors))

    zero_errors = []
    for row in rq1:
        if row["estimable"] != "true":
            continue
        if int(row["success_events_observed"]) == 0 and not row["success_support_upper_95"]:
            zero_errors.append(("success", row["offering_year"], row["horizon_months"]))
        if int(row["closure_events_observed"]) == 0 and not row["closure_support_upper_95"]:
            zero_errors.append(("closure", row["offering_year"], row["horizon_months"]))
        if int(row["closure_events_observed"]) + int(row["terminal_nonclosure_events_observed"]) == 0 and fnum(row["operating_survival"]) == 1.0 and not row["survival_support_lower_95"]:
            zero_errors.append(("survival", row["offering_year"], row["horizon_months"]))
    gates.append(gate("D3_28_ZERO_EVENT_SUPPORT_BOUNDS", not zero_errors, zero_errors))

    support_errors = [r for r in rq1 if not (0 <= int(r["n_supported_to_horizon"]) <= int(r["n_rounds"]) and 0 <= fnum(r["support_share"]) <= 1 and 0 <= fnum(r["ascertainment_coverage"]) <= 1)]
    gates.append(gate("D3_29_SUPPORT_RECONCILIATION", not support_errors, [(r["offering_year"], r["horizon_months"]) for r in support_errors]))
    estimable = [r for r in rq1 if r["estimable"] == "true"]
    gates.append(gate("D3_30_LOW_INFORMATION_EXPOSED", len(estimable) == 17 and all(r["low_information"] == "true" for r in rq1), {"estimable": len(estimable), "low_all": all(r["low_information"] == "true" for r in rq1)}))
    young_bad = [r for r in rq1 if r["offering_year"] in {"2024", "2025"} and r["estimable"] == "false" and any(r[k] not in (None, "") for k in ("success_cif", "closure_cif", "operating_survival"))]
    gates.append(gate("D3_31_YOUNG_COHORT_CENSORING", not young_bad, young_bad))

    rq2_pass = [r for r in rq2 if r["report"] == "true"]
    maturity_cross = [r for r in rq2 if r["crossed_maturity_boundary"] == "true"]
    gates.append(gate("D3_32_RQ2_FAIL_CLOSED", len(rq2) == 60 and not rq2_pass and not maturity_cross, {"rows": len(rq2), "passed": len(rq2_pass), "crossed": len(maturity_cross)}))

    forbidden = [p.name for p in DATA.glob("cp4_*") if any(name in p.name.lower() for name in ("wefunder", "startengine", "republic_us", "crowdcube"))]
    gates.append(gate("D3_33_NO_INCOMPLETE_PLATFORM_RATES", not forbidden, forbidden))
    delta = summary["comparison_to_candidate_v2"].get("max_absolute_point_estimate_delta")
    gates.append(gate("D3_34_MATERIAL_REEXECUTION_DELTA_EXPOSED", delta is not None and delta > 0.05 and summary["promotion_status"] == "CANDIDATE_ONLY", summary["comparison_to_candidate_v2"]))
    gates.append(gate("D3_35_PRIOR_CANDIDATE_RETAINED", (DATA / "cp4_republic_europe_rq1_candidate_v2.csv").exists() and summary["source_ledger"] == "cp3_republic_europe_outcome_ledger_v4.csv", summary))

    manifest = read_json("cp4_republic_europe_candidate_v3_manifest.json")
    hash_errors = []
    for name, expected in manifest["output_files"].items():
        actual = sha(DATA / name)
        if actual != expected:
            hash_errors.append((name, expected, actual))
    gates.append(gate("D3_36_OUTPUT_HASH_INTEGRITY", not hash_errors, hash_errors))

    return {
        "checkpoint": "PHASE_1D_CP4_CANDIDATE_V3",
        "gate_count": len(gates),
        "passed": sum(x["passed"] for x in gates),
        "promotion_gate": "PASS" if all(x["passed"] for x in gates) else "BLOCKED",
        "material_reexecution_delta": delta,
        "rates_promoted": False,
        "gates": gates,
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["promotion_gate"] == "PASS" else 1)
