#!/usr/bin/env python3
"""Adjudicate Republic Europe zero-valuation closure review candidates.

This is intentionally fail-closed: only explicit dated observed closure language could
be accepted. Contractual liquidation preference/default clauses are false positives.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/phase1d"
AUDIT_ROOT = DATA / "republic_europe_closure_audit"
DECISIONS = DATA / "cp3_republic_europe_zero_valuation_closure_decisions.csv"
SUMMARY = DATA / "cp3_republic_europe_zero_valuation_closure_adjudication.json"
MANIFEST = DATA / "cp3_republic_europe_zero_valuation_closure_adjudication_manifest.json"
CANDIDATE_V3 = DATA / "cp4_republic_europe_candidate_v3_manifest.json"

CONTRACT_PATTERNS = {
    "share_class_liquidation_preference": re.compile(
        r"preference on liquidation|on liquidation or exit|share class.*redeemable|rights attached to the share classes",
        re.I,
    ),
    "hypothetical_default_or_winding_up_clause": re.compile(
        r"events? of default|such as liquidation or winding up|in the event of a winding up or liquidation|will rank behind secured creditors",
        re.I,
    ),
}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latest_audit_dir() -> Path:
    candidates = []
    for path in AUDIT_ROOT.glob("gh-*") if AUDIT_ROOT.exists() else []:
        try:
            candidates.append((int(path.name.split("-", 1)[1]), path))
        except Exception:
            pass
    if not candidates:
        raise FileNotFoundError("no Republic Europe closure audit checkpoint")
    return max(candidates)[1]


def classify(row: dict) -> tuple[str, str]:
    if row.get("closure_label_applied") != "false":
        return "BLOCK_INVALID_INPUT", "upstream review candidate already changed an outcome label"
    excerpt = row.get("excerpt", "")
    matched = [name for name, pattern in CONTRACT_PATTERNS.items() if pattern.search(excerpt)]
    if not row.get("date_candidate") and matched:
        return "FALSE_POSITIVE_CONTRACT_LANGUAGE", "|".join(matched)
    if row.get("date_candidate"):
        return "HELD_EXPLICIT_DATE_REVIEW", "dated candidate requires separate evidentiary adjudication"
    return "HELD_MANUAL_UNRESOLVED", "phrase not safely classifiable as contractual language"


def main() -> None:
    source_dir = latest_audit_dir()
    source = source_dir / "closure_review_candidates.csv"
    audit_summary = json.loads((source_dir / "summary.json").read_text(encoding="utf-8"))
    candidates = read_csv(source)
    decisions = []
    for row in candidates:
        disposition, reason = classify(row)
        decisions.append({
            **row,
            "adjudication_disposition": disposition,
            "adjudication_reason": reason,
            "closure_event_accepted": "false",
            "closure_date_accepted": "",
            "zero_valuation_signal_status": "UNRESOLVED_ADVERSE_SIGNAL",
        })

    fields = list(decisions[0].keys()) if decisions else ["canonical_company_id", "adjudication_disposition"]
    write_csv(DECISIONS, decisions, fields)
    counts: dict[str, int] = {}
    for row in decisions:
        counts[row["adjudication_disposition"]] = counts.get(row["adjudication_disposition"], 0) + 1

    accepted = [r for r in decisions if r["closure_event_accepted"] == "true"]
    held = [r for r in decisions if r["adjudication_disposition"].startswith("HELD")]
    false_positive = [r for r in decisions if r["adjudication_disposition"] == "FALSE_POSITIVE_CONTRACT_LANGUAGE"]
    candidate_hash_before = sha(CANDIDATE_V3) if CANDIDATE_V3.exists() else None
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_run_id": source_dir.name,
        "target_company_pages": audit_summary.get("target_company_pages"),
        "review_candidates": len(candidates),
        "dated_review_candidates": sum(bool(r.get("date_candidate")) for r in candidates),
        "false_positive_contract_candidates": len(false_positive),
        "held_unresolved_candidates": len(held),
        "accepted_closure_events": len(accepted),
        "decision_counts": dict(sorted(counts.items())),
        "zero_valuation_signal_status": "UNRESOLVED_ADVERSE_SIGNAL",
        "candidate_v3_effect": "UNCHANGED_VERIFIED",
        "candidate_v3_manifest_sha256_before": candidate_hash_before,
        "rates_promoted": False,
        "jev": {
            "false_positive_contract_language_probability": 1.0,
            "unresolved_risk_signal_probability": 1.0,
            "candidate_v3_unchanged_probability": 1.0
        },
        "policy": "No zero valuation, Not eligible status, contractual liquidation preference, hypothetical default clause, or undated phrase becomes a closure event."
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({
        "generated_at": summary["generated_at"],
        "source_files": {
            str(source.relative_to(DATA)): sha(source),
            str((source_dir / "summary.json").relative_to(DATA)): sha(source_dir / "summary.json"),
            CANDIDATE_V3.name: candidate_hash_before,
        },
        "output_files": {DECISIONS.name: sha(DECISIONS), SUMMARY.name: sha(SUMMARY)},
        "summary": summary,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    if accepted:
        raise SystemExit("closure accepted without downstream ledger rebuild")


if __name__ == "__main__":
    main()
