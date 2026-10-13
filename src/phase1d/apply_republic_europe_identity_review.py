#!/usr/bin/env python3
"""Apply the conservative Jev identity-review rule and build follow-up observations v2."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src.phase1d.build_republic_europe_cohort import canonical_company_number

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/phase1d"
QUEUE = DATA / "cp3_republic_europe_identity_review_queue.csv"
RAW_BUSINESS = DATA / "cp3_republic_europe_business_pages_raw.csv"
OBS_V1 = DATA / "cp3_republic_europe_business_observations.csv"
ROUNDS = DATA / "cp2_republic_europe_rounds_normalized.csv"
DECISIONS = DATA / "cp3_republic_europe_identity_review_decisions.csv"
ACCEPTED = DATA / "cp3_republic_europe_identity_matches_accepted.csv"
OBS_V2 = DATA / "cp3_republic_europe_business_observations_v2.csv"
SUMMARY = DATA / "cp3_republic_europe_identity_review_applied_summary.json"
MANIFEST = DATA / "cp3_republic_europe_identity_review_applied_manifest.json"

REQUIRED_SIGNALS = {"platform_slug_exact", "deterministic_alias_exact"}


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


def signal_set(row: dict) -> set[str]:
    return {x.strip() for x in (row.get("signals") or "").split("|") if x.strip()}


def review_group(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Jev rule: only one candidate on the page, unique top, and slug + explicit alias."""
    accepted: list[dict] = []
    decisions: list[dict] = []
    group_size = len(rows)
    for row in rows:
        signals = signal_set(row)
        unique_top = row.get("unique_top_candidate") == "true" and row.get("top_score_tie_count") == "1"
        required = REQUIRED_SIGNALS <= signals
        if group_size == 1 and unique_top and required:
            disposition = "ACCEPTED_JEV_RULE"
            reason = "unique_candidate_with_platform_slug_and_deterministic_alias"
            accepted.append(row)
        elif group_size > 1:
            disposition = "HELD_COLLISION"
            reason = "multiple_legal_entity_candidates_for_business_page"
        elif not unique_top:
            disposition = "HELD_AMBIGUOUS_TOP"
            reason = "top_candidate_not_unique"
        else:
            disposition = "HELD_INSUFFICIENT_SIGNALS"
            reason = "requires_platform_slug_and_deterministic_alias"
        decisions.append({**row, "review_disposition": disposition, "review_reason": reason})
    return accepted, decisions


def normalize_existing_company_id(value: str) -> str:
    if value.startswith("ukco:"):
        key = canonical_company_number(value.split(":", 1)[1])
        return "reurope-company:" + key if key else value
    return value


def make_observation(row: dict, raw: dict) -> dict:
    eligible = row.get("business_eligibility") == "ELIGIBLE"
    return {
        "canonical_company_id": row["candidate_company_id"],
        "business_name": row.get("business_name", ""),
        "business_url": row.get("business_url", ""),
        "captured_at": raw.get("captured_at", ""),
        "eligibility": row.get("business_eligibility", ""),
        "positive_operating_evidence": str(eligible).lower(),
        "evidence_confidence": "medium" if eligible else "",
        "evidence_basis": "secondary_market_current_eligible" if eligible else "secondary_market_status_neutral",
        "content_sha256": row.get("business_content_sha256", ""),
        "match_basis": "JEV_REVIEW_PLATFORM_SLUG_PLUS_ALIAS",
    }


def main() -> None:
    queue = read_csv(QUEUE)
    raw_business = {r.get("url", ""): r for r in read_csv(RAW_BUSINESS)}
    observations_v1 = read_csv(OBS_V1)
    rounds = read_csv(ROUNDS)
    valid_company_ids = {r["canonical_company_id"] for r in rounds}

    by_url: dict[str, list[dict]] = defaultdict(list)
    for row in queue:
        by_url[row["business_url"]].append(row)

    accepted: list[dict] = []
    decisions: list[dict] = []
    for url, rows in sorted(by_url.items()):
        group_accepted, group_decisions = review_group(rows)
        accepted.extend(group_accepted)
        decisions.extend(group_decisions)

    bad_targets = sorted({r["candidate_company_id"] for r in accepted if r["candidate_company_id"] not in valid_company_ids})
    if bad_targets:
        raise ValueError(f"accepted target not in normalized cohort: {bad_targets}")

    migrated = []
    for row in observations_v1:
        migrated.append({**row, "canonical_company_id": normalize_existing_company_id(row.get("canonical_company_id", ""))})
    new_observations = [make_observation(r, raw_business.get(r["business_url"], {})) for r in accepted]

    dedup: dict[tuple[str, str], dict] = {}
    for row in migrated + new_observations:
        key = (row.get("canonical_company_id", ""), row.get("business_url", ""))
        existing = dedup.get(key)
        if existing is None or (row.get("positive_operating_evidence") == "true" and existing.get("positive_operating_evidence") != "true"):
            dedup[key] = row
    observations_v2 = sorted(dedup.values(), key=lambda r: (r.get("canonical_company_id", ""), r.get("business_url", "")))

    decision_fields = list(decisions[0].keys()) if decisions else ["business_url", "review_disposition", "review_reason"]
    accepted_fields = list(accepted[0].keys()) if accepted else ["business_url", "candidate_company_id"]
    observation_fields = [
        "canonical_company_id", "business_name", "business_url", "captured_at", "eligibility",
        "positive_operating_evidence", "evidence_confidence", "evidence_basis",
        "content_sha256", "match_basis",
    ]
    write_csv(DECISIONS, decisions, decision_fields)
    write_csv(ACCEPTED, accepted, accepted_fields)
    write_csv(OBS_V2, observations_v2, observation_fields)

    usable_company_ids = {r["canonical_company_id"] for r in rounds if r.get("offering_year_status") == "BOUNDED_YEAR"}
    positive_ids = {r["canonical_company_id"] for r in observations_v2 if r.get("positive_operating_evidence") == "true"}
    accepted_eligible = [r for r in accepted if r.get("business_eligibility") == "ELIGIBLE"]
    dispositions: dict[str, int] = defaultdict(int)
    for r in decisions:
        dispositions[r["review_disposition"]] += 1
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queue_pages": len(by_url),
        "candidate_rows": len(queue),
        "accepted_pages": len(accepted),
        "accepted_eligible_pages": len(accepted_eligible),
        "accepted_not_eligible_pages": len(accepted) - len(accepted_eligible),
        "held_candidate_rows": len(decisions) - len(accepted),
        "decision_counts": dict(sorted(dispositions.items())),
        "observations_v1_rows": len(observations_v1),
        "observations_v2_rows": len(observations_v2),
        "usable_cohort_unique_companies": len(usable_company_ids),
        "usable_companies_with_positive_followup": len(usable_company_ids & positive_ids),
        "usable_positive_followup_coverage": len(usable_company_ids & positive_ids) / len(usable_company_ids) if usable_company_ids else 0,
        "followup_rows_extended": len(accepted_eligible),
        "policy": "Accepted only single-candidate pages with a unique top and both platform_slug_exact and deterministic_alias_exact; every collision, tie and one-signal rebrand remains held.",
        "jev": {
            "acceptance_rule_probability": 0.87,
            "hold_lower_ranked_collision_probability": 0.83,
            "normalize_then_rebuild_probability": 0.94,
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({
        "generated_at": summary["generated_at"],
        "source_files": {QUEUE.name: sha(QUEUE), RAW_BUSINESS.name: sha(RAW_BUSINESS), OBS_V1.name: sha(OBS_V1), ROUNDS.name: sha(ROUNDS)},
        "output_files": {DECISIONS.name: sha(DECISIONS), ACCEPTED.name: sha(ACCEPTED), OBS_V2.name: sha(OBS_V2), SUMMARY.name: sha(SUMMARY)},
        "summary": summary,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
