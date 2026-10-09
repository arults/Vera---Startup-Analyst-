#!/usr/bin/env python3
"""Deterministic Phase 1D plateau verifier.

Jev scores remain advisory; plateau is decided from exact research-state dimensions,
material labels and content hashes so evaluator noise cannot manufacture improvement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.phase1d.verifier_v4 import DATA, read_json, verify_v4

ROOT = Path(__file__).resolve().parents[2]
OUT = DATA / "plateau"
THRESHOLD = 0.05


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_state() -> dict:
    coverage = read_json(DATA / "cp1_coverage.json")
    cp2 = read_json(DATA / "cp2_republic_europe_normalized_manifest.json")["summary"]
    identity = read_json(DATA / "cp3_republic_europe_identity_review_applied_summary.json")
    closure = read_json(DATA / "cp3_republic_europe_zero_valuation_closure_adjudication.json")
    candidate = read_json(DATA / "cp4_republic_europe_candidate_v3_summary.json")
    verifier = verify_v4()

    platforms = coverage["platforms"]
    denominator_grade = sum(v["status"] == "PASS_NATIVE_ENUMERABLE" for v in platforms.values())
    dimensions = {
        "denominator_grade_platform_share": denominator_grade / 5,
        "republic_europe_cohort_year_coverage": cp2["cohort_year_usable_rows"] / cp2["normalized_rows"],
        "rate_eligible_strong_identity_share": 1.0,
        "usable_positive_followup_coverage": identity["usable_positive_followup_coverage"],
        "closure_audit_target_coverage": closure["target_company_pages"] / 13,
        "scientific_gate_pass_share": verifier["passed"] / verifier["gate_count"],
        "rq1_reportable_share": (candidate["rq1_cells"] - candidate["rq1_low_information_cells"]) / candidate["rq1_cells"],
        "rq2_reportable_share": candidate["rq2_reportable_cells"] / candidate["rq2_cells"],
        "promoted_rate_share": 0.0 if candidate["rates_promoted"] is False else 1.0,
    }
    labels = {
        "platform_statuses": {k: v["status"] for k, v in sorted(platforms.items())},
        "candidate_version": candidate["version"],
        "promotion_status": candidate["promotion_status"],
        "rates_promoted": candidate["rates_promoted"],
        "closure_events_total": candidate["closure_events_total"],
        "rq1_low_information_cells": candidate["rq1_low_information_cells"],
        "rq2_reportable_cells": candidate["rq2_reportable_cells"],
        "verifier_promotion_gate": verifier["promotion_gate"],
        "closure_audit_effect": verifier["closure_audit_effect"],
    }
    source_paths = [
        DATA / "cp1_coverage.json",
        DATA / "cp2_republic_europe_normalized_manifest.json",
        DATA / "cp3_republic_europe_identity_review_applied_manifest.json",
        DATA / "cp3_republic_europe_outcome_ledger_v4_manifest.json",
        DATA / "cp3_republic_europe_zero_valuation_closure_adjudication_manifest.json",
        DATA / "cp4_republic_europe_candidate_v3_manifest.json",
    ]
    hashes = {p.name: sha(p) for p in source_paths}
    return {
        "dimensions": dimensions,
        "labels": labels,
        "source_hashes": hashes,
        "verifier": {"passed": verifier["passed"], "total": verifier["gate_count"], "promotion_gate": verifier["promotion_gate"]},
    }


def compare_snapshots(previous: dict, current: dict, threshold: float = THRESHOLD) -> dict:
    keys = sorted(set(previous["dimensions"]) | set(current["dimensions"]))
    changes = {}
    missing = []
    for key in keys:
        if key not in previous["dimensions"] or key not in current["dimensions"]:
            missing.append(key)
            continue
        before = float(previous["dimensions"][key])
        after = float(current["dimensions"][key])
        changes[key] = {
            "before": before,
            "after": after,
            "change": after - before,
            "positive_improvement_exceeds_threshold": (after - before) > threshold + 1e-12,
        }
    label_flips = {
        key: {"before": previous["labels"].get(key), "after": current["labels"].get(key)}
        for key in sorted(set(previous["labels"]) | set(current["labels"]))
        if previous["labels"].get(key) != current["labels"].get(key)
    }
    hash_changes = {
        key: {"before": previous["source_hashes"].get(key), "after": current["source_hashes"].get(key)}
        for key in sorted(set(previous["source_hashes"]) | set(current["source_hashes"]))
        if previous["source_hashes"].get(key) != current["source_hashes"].get(key)
    }
    excessive = [key for key, value in changes.items() if value["positive_improvement_exceeds_threshold"]]
    plateau = not missing and not excessive and not label_flips and not hash_changes
    return {
        "threshold": threshold,
        "dimension_changes": changes,
        "missing_dimensions": missing,
        "improvements_over_threshold": excessive,
        "material_label_flips": label_flips,
        "source_hash_changes": hash_changes,
        "plateau": plateau,
    }


def safe_round_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value or ""):
        raise ValueError("invalid round id")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--previous")
    args = parser.parse_args()
    rid = safe_round_id(args.round_id)
    OUT.mkdir(parents=True, exist_ok=True)
    state = exact_state()
    result = {
        "round_id": rid,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "state": state,
        "comparison": None,
    }
    if args.previous:
        prev_id = safe_round_id(args.previous)
        previous = json.loads((OUT / f"{prev_id}.json").read_text(encoding="utf-8"))
        result["previous_round_id"] = prev_id
        result["comparison"] = compare_snapshots(previous["state"], state)
    target = OUT / f"{rid}.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    if result["comparison"] is not None and not result["comparison"]["plateau"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
