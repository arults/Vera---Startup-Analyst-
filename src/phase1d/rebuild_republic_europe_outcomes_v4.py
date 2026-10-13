#!/usr/bin/env python3
"""Migrate the verified v3 ledger to canonical company IDs and reviewed follow-up v4."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/phase1d"
ROUNDS = DATA / "cp2_republic_europe_rounds_normalized.csv"
LEDGER_V3 = DATA / "cp3_republic_europe_outcome_ledger_v3.csv"
OBS_V2 = DATA / "cp3_republic_europe_business_observations_v2.csv"
LEDGER_V4 = DATA / "cp3_republic_europe_outcome_ledger_v4.csv"
SUMMARY = DATA / "cp3_republic_europe_outcome_ledger_v4_summary.json"
MANIFEST = DATA / "cp3_republic_europe_outcome_ledger_v4_manifest.json"


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


def iso_day(value: str) -> str:
    return (value or "")[:10]


def months_between(start: str, end: str) -> str:
    if not start or not end:
        return ""
    return f"{(date.fromisoformat(end) - date.fromisoformat(start)).days / 30.4375:.3f}"


def latest_positive_observations(rows: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in rows:
        if row.get("positive_operating_evidence") != "true":
            continue
        cid = row.get("canonical_company_id", "")
        observed = iso_day(row.get("captured_at", ""))
        if not cid or not observed:
            continue
        prior = latest.get(cid)
        if prior is None or observed > prior["date"]:
            latest[cid] = {"date": observed, "url": row.get("business_url", ""), "basis": row.get("match_basis", "")}
    return latest


def terminal_date(row: dict) -> str:
    return (
        row.get("closure_date", "")
        or row.get("terminal_event_midpoint_for_primary", "")
        or row.get("terminal_event_interval_end", "")
        or row.get("terminal_event_interval_start", "")
    )


def migrate_row(row: dict, authoritative: dict, positive: dict[str, dict]) -> tuple[dict, bool, bool]:
    result = dict(row)
    old_cid = row.get("canonical_company_id", "")
    new_cid = authoritative["canonical_company_id"]
    result.update({
        "canonical_company_id": new_cid,
        "campaign_name": authoritative.get("campaign_name", row.get("campaign_name", "")),
        "platform": authoritative.get("platform", "republic_europe"),
        "offering_year": authoritative.get("offering_year", ""),
        "offering_year_status": authoritative.get("offering_year_status", ""),
        "primary_field": authoritative.get("primary_field", row.get("primary_field", "")),
        "completion_date": authoritative.get("completion_date", row.get("completion_date", "")),
    })
    identity_changed = old_cid != new_cid
    extended = False
    obs = positive.get(new_cid)
    terminal = terminal_date(result)
    # Terminal events define the primary endpoint; later secondary-page status cannot reopen it.
    if obs and not terminal and obs["date"] > (result.get("last_positive_date") or result.get("completion_date") or ""):
        result["last_positive_date"] = obs["date"]
        result["censor_date"] = obs["date"]
        result["current_eligible_evidence"] = "true"
        token = f"secondary_market_current_eligible:{obs['date']}:{obs['url']}"
        trace = [x for x in (result.get("evidence_trace") or "").split("|") if x]
        if token not in trace:
            trace.append(token)
        result["evidence_trace"] = "|".join(trace)
        extended = True
    elif obs and not terminal:
        result["current_eligible_evidence"] = "true"
    elif terminal:
        result["current_eligible_evidence"] = "false"

    result["followup_months"] = months_between(result.get("completion_date", ""), result.get("censor_date", ""))
    return result, identity_changed, extended


def main() -> None:
    rounds = read_csv(ROUNDS)
    ledger = read_csv(LEDGER_V3)
    observations = read_csv(OBS_V2)
    round_map = {r["round_id"]: r for r in rounds}
    if len(round_map) != len(rounds):
        raise ValueError("normalized round IDs are not unique")
    missing = sorted({r["round_id"] for r in ledger} - set(round_map))
    extra = sorted(set(round_map) - {r["round_id"] for r in ledger})
    if missing or extra or len(ledger) != len(rounds):
        raise ValueError(f"ledger/round mismatch missing={missing[:5]} extra={extra[:5]}")

    positive = latest_positive_observations(observations)
    output = []
    identity_changes = 0
    extended_rounds = 0
    extended_companies = set()
    for row in ledger:
        migrated, changed, extended = migrate_row(row, round_map[row["round_id"]], positive)
        output.append(migrated)
        identity_changes += int(changed)
        if extended:
            extended_rounds += 1
            extended_companies.add(migrated["canonical_company_id"])

    fields = list(ledger[0].keys()) if ledger else []
    write_csv(LEDGER_V4, output, fields)
    usable = [r for r in output if r.get("offering_year_status") == "BOUNDED_YEAR"]
    terminal_count = sum(1 for r in output if terminal_date(r))
    success_count = sum(1 for r in output if r.get("success_date"))
    closure_count = sum(1 for r in output if r.get("closure_date"))
    summary = {
        "version": "v4",
        "supersedes_for_estimation": "cp3_republic_europe_outcome_ledger_v3.csv",
        "rows": len(output),
        "usable_rows": len(usable),
        "unique_companies": len({r["canonical_company_id"] for r in output}),
        "usable_unique_companies": len({r["canonical_company_id"] for r in usable}),
        "identity_rows_migrated": identity_changes,
        "positive_observation_companies": len(positive),
        "followup_rounds_extended": extended_rounds,
        "followup_companies_extended": len(extended_companies),
        "success_rows": success_count,
        "closure_rows": closure_count,
        "terminal_rows": terminal_count,
        "terminal_events_reopened": 0,
        "rules": {
            "company_identity": "round_id -> canonical normalized company identity from CP2 rebuild",
            "positive_followup": "latest reviewed Eligible business-page observation extends only nonterminal rows",
            "not_eligible": "neutral; does not extend follow-up and is not closure",
            "terminal": "later secondary status cannot reopen a terminal endpoint",
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": {ROUNDS.name: sha(ROUNDS), LEDGER_V3.name: sha(LEDGER_V3), OBS_V2.name: sha(OBS_V2)},
        "output_files": {LEDGER_V4.name: sha(LEDGER_V4), SUMMARY.name: sha(SUMMARY)},
        "summary": summary,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
