#!/usr/bin/env python3
"""Independent scientific verifier after the bounded Republic Europe closure audit."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from src.phase1d.verifier_v3_repaired import DATA, repaired_verify


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate(gid: str, passed: bool, detail: object) -> dict:
    return {"id": gid, "passed": bool(passed), "detail": detail}


def latest_closure_audit() -> Path:
    root = DATA / "republic_europe_closure_audit"
    candidates = []
    for path in root.glob("gh-*") if root.exists() else []:
        try:
            candidates.append((int(path.name.split("-", 1)[1]), path))
        except Exception:
            pass
    if not candidates:
        raise FileNotFoundError("no closure audit checkpoint")
    return max(candidates)[1]


def official_republic_europe(url: str) -> bool:
    p = urlsplit(url or "")
    return p.scheme == "https" and p.netloc.lower() == "europe.republic.com" and not p.username and not p.password


def verify_v4() -> dict:
    result = repaired_verify()
    gates = list(result["gates"])

    audit_dir = latest_closure_audit()
    audit_summary_path = audit_dir / "summary.json"
    captures_path = audit_dir / "captures.csv"
    candidates_path = audit_dir / "closure_review_candidates.csv"
    audit_summary = read_json(audit_summary_path)
    captures = read_csv(captures_path)
    candidates = read_csv(candidates_path)

    gates.append(gate(
        "D4_37_CLOSURE_AUDIT_SCOPE",
        audit_summary.get("target_company_pages") == 13
        and audit_summary.get("target_unique_companies") == 13
        and audit_summary.get("captures") == 41
        and audit_summary.get("successful_captures") == 41
        and audit_summary.get("rates_promoted") is False,
        audit_summary,
    ))
    gates.append(gate(
        "D4_38_CLOSURE_AUDIT_HASH_INTEGRITY",
        audit_summary.get("files", {}).get("captures.csv") == sha(captures_path)
        and audit_summary.get("files", {}).get("closure_review_candidates.csv") == sha(candidates_path),
        {
            "captures_expected": audit_summary.get("files", {}).get("captures.csv"),
            "captures_actual": sha(captures_path),
            "candidates_expected": audit_summary.get("files", {}).get("closure_review_candidates.csv"),
            "candidates_actual": sha(candidates_path),
        },
    ))
    bad_urls = [r.get("source_url") for r in captures if not official_republic_europe(r.get("source_url", ""))]
    gates.append(gate(
        "D4_39_PLATFORM_ONLY_CLOSURE_SOURCES",
        not bad_urls and all(r.get("http_status") == "200" for r in captures),
        {"bad_urls": bad_urls[:10], "captures": len(captures)},
    ))
    gates.append(gate(
        "D4_40_REVIEW_CANDIDATES_NOT_OUTCOMES",
        len(candidates) == 14
        and all(r.get("closure_label_applied") == "false" for r in candidates)
        and all(not r.get("date_candidate") for r in candidates),
        {"rows": len(candidates), "dated": sum(bool(r.get("date_candidate")) for r in candidates)},
    ))

    adjudication_path = DATA / "cp3_republic_europe_zero_valuation_closure_adjudication.json"
    decisions_path = DATA / "cp3_republic_europe_zero_valuation_closure_decisions.csv"
    adjudication = read_json(adjudication_path)
    decisions = read_csv(decisions_path)
    gates.append(gate(
        "D4_41_CLOSURE_ADJUDICATION",
        adjudication.get("review_candidates") == 14
        and adjudication.get("false_positive_contract_candidates") == 14
        and adjudication.get("accepted_closure_events") == 0
        and adjudication.get("held_unresolved_candidates") == 0
        and adjudication.get("decision_counts") == {"FALSE_POSITIVE_CONTRACT_LANGUAGE": 14},
        adjudication,
    ))
    gates.append(gate(
        "D4_42_NO_ZERO_VALUATION_AUTO_CLOSURE",
        len(decisions) == 14
        and all(r.get("adjudication_disposition") == "FALSE_POSITIVE_CONTRACT_LANGUAGE" for r in decisions)
        and all(r.get("closure_event_accepted") == "false" and not r.get("closure_date_accepted") for r in decisions)
        and all(r.get("zero_valuation_signal_status") == "UNRESOLVED_ADVERSE_SIGNAL" for r in decisions),
        {"rows": len(decisions)},
    ))

    candidate_manifest_path = DATA / "cp4_republic_europe_candidate_v3_manifest.json"
    candidate_summary = read_json(DATA / "cp4_republic_europe_candidate_v3_summary.json")
    ledger_summary = read_json(DATA / "cp3_republic_europe_outcome_ledger_v4_summary.json")
    gates.append(gate(
        "D4_43_CANDIDATE_UNCHANGED_AFTER_AUDIT",
        adjudication.get("candidate_v3_effect") == "UNCHANGED_VERIFIED"
        and adjudication.get("candidate_v3_manifest_sha256_before") == sha(candidate_manifest_path)
        and candidate_summary.get("closure_events_total") == 0
        and ledger_summary.get("closure_rows") == 0
        and candidate_summary.get("rates_promoted") is False,
        {
            "adjudication_manifest_hash": adjudication.get("candidate_v3_manifest_sha256_before"),
            "actual_manifest_hash": sha(candidate_manifest_path),
            "candidate_closures": candidate_summary.get("closure_events_total"),
            "ledger_closures": ledger_summary.get("closure_rows"),
        },
    ))

    result["checkpoint"] = "PHASE_1D_CP4_POST_CLOSURE_AUDIT"
    result["verifier_revision"] = "v4_post_zero_valuation_closure_audit"
    result["gates"] = gates
    result["gate_count"] = len(gates)
    result["passed"] = sum(bool(g["passed"]) for g in gates)
    result["promotion_gate"] = "PASS" if result["passed"] == result["gate_count"] else "BLOCKED"
    result["rates_promoted"] = False
    result["closure_audit_effect"] = "NO_OUTCOME_LABEL_CHANGE"
    return result


if __name__ == "__main__":
    output = verify_v4()
    print(json.dumps(output, indent=2, sort_keys=True))
    raise SystemExit(0 if output["promotion_gate"] == "PASS" else 1)
