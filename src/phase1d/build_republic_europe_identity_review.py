#!/usr/bin/env python3
"""Build a fail-closed review queue for unmatched Republic Europe business pages."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/phase1d"
BUSINESS = DATA / "cp3_republic_europe_business_pages_raw.csv"
ROUNDS = DATA / "cp2_republic_europe_rounds_normalized.csv"
QUEUE = DATA / "cp3_republic_europe_identity_review_queue.csv"
UNMATCHED = DATA / "cp3_republic_europe_identity_unmatched_after_queue.csv"
SUMMARY = DATA / "cp3_republic_europe_identity_review_summary.json"
MANIFEST = DATA / "cp3_republic_europe_identity_review_manifest.json"

LEGAL = {
    "limited", "ltd", "plc", "inc", "incorporated", "llc", "corp", "corporation",
    "company", "co", "holdings", "holding", "group", "gmbh", "ag", "sas", "sa",
    "bv", "pte", "srl", "spa", "spv", "aps", "as",
}
NOISE = {
    "formerly", "former", "previously", "trading", "as", "dba", "formerlyknown",
    "the", "and", "of", "by", "formerlyknownas",
}


def ascii_text(value: str) -> str:
    return unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")


def tokens(value: str, drop_legal: bool = True) -> list[str]:
    raw = re.findall(r"[a-z0-9]+", ascii_text(value).lower())
    return [x for x in raw if x not in NOISE and (not drop_legal or x not in LEGAL)]


def norm_name(value: str) -> str:
    return " ".join(tokens(value))


def slug_from_url(url: str) -> str:
    parts = [x for x in urlsplit(url or "").path.split("/") if x]
    return parts[-1].lower() if parts else ""


def norm_slug(value: str) -> str:
    parts = [x for x in re.findall(r"[a-z0-9]+", ascii_text(value).lower()) if x not in LEGAL]
    if parts and re.fullmatch(r"\d+", parts[-1]):
        parts = parts[:-1]
    elif parts:
        parts[-1] = re.sub(r"\d+$", "", parts[-1]) or parts[-1]
    return " ".join(x for x in parts if x)


def explicit_aliases(name: str) -> set[str]:
    out = {norm_name(name)} if norm_name(name) else set()
    for content in re.findall(r"\(([^)]{2,100})\)", name or ""):
        cleaned = re.sub(r"^(formerly|former|previously|trading as|dba)\s+", "", content, flags=re.I)
        n = norm_name(cleaned)
        if n:
            out.add(n)
    before = re.split(r"\s*\(", name or "", maxsplit=1)[0]
    n = norm_name(before)
    if n:
        out.add(n)
    for part in re.split(r"\s+(?:formerly|previously|trading as|dba)\s+", name or "", flags=re.I):
        n = norm_name(part)
        if n:
            out.add(n)
    return out


def jaccard(a: str, b: str) -> float:
    aa, bb = set(tokens(a)), set(tokens(b))
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


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


def company_index(rounds: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for r in rounds:
        cid = r["canonical_company_id"]
        item = index.setdefault(cid, {"company_id": cid, "names": set(), "aliases": set(), "slugs": set(), "numbers": set(), "round_ids": set()})
        name = r.get("campaign_name", "")
        if name:
            item["names"].add(name)
            item["aliases"].update(explicit_aliases(name))
        slug = norm_slug(slug_from_url(r.get("campaign_url", "")))
        if slug:
            item["slugs"].add(slug)
        number = re.sub(r"\s+", "", r.get("legal_company_number", "")).upper()
        if number:
            item["numbers"].add(number)
        item["round_ids"].add(r["round_id"])
    return index


def candidate_rows(business: dict, companies: dict[str, dict]) -> list[dict]:
    bname = business.get("business_name", "")
    baliases = explicit_aliases(bname)
    bslug = norm_slug(slug_from_url(business.get("url", "")))
    try:
        bnumbers = {re.sub(r"\s+", "", x).upper() for x in json.loads(business.get("company_numbers_json") or "[]")}
    except Exception:
        bnumbers = set()

    output = []
    for cid, item in companies.items():
        number_exact = bool(bnumbers & item["numbers"])
        slug_exact = bool(bslug and bslug in item["slugs"])
        aliases = baliases & item["aliases"]
        alias_exact = bool(aliases)
        best_name = max((jaccard(bname, n) for n in item["names"]), default=0.0)
        high_overlap = best_name >= 0.80
        if not (number_exact or slug_exact or alias_exact or high_overlap):
            continue
        score = 100 if number_exact else (3 if slug_exact else 0) + (3 if alias_exact else 0) + (1 if high_overlap else 0)
        signals = [k for k, ok in (("company_number_exact", number_exact), ("platform_slug_exact", slug_exact), ("deterministic_alias_exact", alias_exact), ("name_token_overlap_ge_0_80", high_overlap)) if ok]
        output.append({
            "business_url": business.get("url", ""),
            "business_name": bname,
            "business_eligibility": business.get("eligibility", ""),
            "business_content_sha256": business.get("content_sha256", ""),
            "candidate_company_id": cid,
            "candidate_names": " | ".join(sorted(item["names"])),
            "candidate_round_ids": " | ".join(sorted(item["round_ids"])),
            "matched_aliases": " | ".join(sorted(aliases)),
            "business_slug_normalized": bslug,
            "candidate_slugs": " | ".join(sorted(item["slugs"])),
            "signals": " | ".join(signals),
            "signal_count": len(signals),
            "score": score,
            "name_jaccard": f"{best_name:.6f}",
            "proposed_disposition": "REVIEW_REQUIRED",
            "review_status": "PENDING",
            "followup_extension_allowed": "false",
        })
    return sorted(output, key=lambda x: (-int(x["score"]), x["candidate_company_id"]))


def main() -> None:
    businesses = read_csv(BUSINESS)
    rounds = read_csv(ROUNDS)
    companies = company_index(rounds)
    unmatched = [r for r in businesses if not r.get("canonical_company_id")]

    queue: list[dict] = []
    still_unmatched: list[dict] = []
    page_counts: dict[str, int] = {}
    for business in unmatched:
        rows = candidate_rows(business, companies)
        page_counts[business.get("url", "")] = len(rows)
        if rows:
            top = int(rows[0]["score"])
            tied = sum(1 for r in rows if int(r["score"]) == top)
            for r in rows:
                r["top_score"] = top
                r["top_score_tie_count"] = tied
                r["unique_top_candidate"] = str(int(r["score"]) == top and tied == 1).lower()
            queue.extend(rows[:10])
        else:
            still_unmatched.append({
                "business_url": business.get("url", ""),
                "business_name": business.get("business_name", ""),
                "business_eligibility": business.get("eligibility", ""),
                "business_content_sha256": business.get("content_sha256", ""),
                "reason": "NO_DETERMINISTIC_CANDIDATE",
            })

    queue_fields = [
        "business_url", "business_name", "business_eligibility", "business_content_sha256",
        "candidate_company_id", "candidate_names", "candidate_round_ids", "matched_aliases",
        "business_slug_normalized", "candidate_slugs", "signals", "signal_count", "score",
        "name_jaccard", "top_score", "top_score_tie_count", "unique_top_candidate",
        "proposed_disposition", "review_status", "followup_extension_allowed",
    ]
    unmatched_fields = ["business_url", "business_name", "business_eligibility", "business_content_sha256", "reason"]
    write_csv(QUEUE, queue, queue_fields)
    write_csv(UNMATCHED, still_unmatched, unmatched_fields)

    pages_with_candidates = len({r["business_url"] for r in queue})
    unique_top_pages = len({r["business_url"] for r in queue if r["unique_top_candidate"] == "true"})
    two_signal_unique_pages = len({r["business_url"] for r in queue if r["unique_top_candidate"] == "true" and int(r["signal_count"]) >= 2})
    eligible_candidate_pages = len({r["business_url"] for r in queue if r["business_eligibility"] == "ELIGIBLE"})
    strong_number_pages = len({r["business_url"] for r in queue if "company_number_exact" in r["signals"]})
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "unmatched_business_pages_input": len(unmatched),
        "pages_with_candidates": pages_with_candidates,
        "candidate_rows": len(queue),
        "pages_without_candidates": len(still_unmatched),
        "unique_top_candidate_pages": unique_top_pages,
        "unique_top_with_two_or_more_signals": two_signal_unique_pages,
        "eligible_pages_with_candidates": eligible_candidate_pages,
        "strong_company_number_candidate_pages": strong_number_pages,
        "matches_applied": 0,
        "followup_rows_extended": 0,
        "policy": {
            "slug_signal": "review only; no automatic match",
            "alias_signal": "deterministic aliases create review candidates; no automatic match",
            "all_new_candidates": "100% review required before follow-up extension",
            "name_similarity_only": "never auto-match",
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({
        "generated_at": summary["generated_at"],
        "source_files": {BUSINESS.name: sha(BUSINESS), ROUNDS.name: sha(ROUNDS)},
        "output_files": {QUEUE.name: sha(QUEUE), UNMATCHED.name: sha(UNMATCHED), SUMMARY.name: sha(SUMMARY)},
        "summary": summary,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
