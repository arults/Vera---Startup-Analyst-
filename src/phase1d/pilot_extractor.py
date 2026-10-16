"""Phase 1D pilot extractor — converts Phase 1B cohort_manifest.csv into Phase 1C RoundRecords and source-capture stubs.

Real content hashes and live page captures still required; this produces the structural skeleton from known SEC-backed 2020 funded rows.
"""
from __future__ import annotations
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "cohort_manifest.csv"
OUT_ROUNDS = ROOT / "data" / "phase1d_wefunder_pilot_rounds.json"
OUT_CAPTURES = ROOT / "data" / "phase1d_wefunder_pilot_captures.json"

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def load_cohort():
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def to_round_record(row: dict) -> dict:
    # Map Phase 1B fields to Phase 1C RoundRecord shape
    close = row.get("funding_close_date") or row.get("funding_close_date_late_bound")
    return {
        "round_id": f"wf_2020_{row['offering_key'].replace('|', '_')}",
        "canonical_company_id": f"cik_{row['issuer_cik']}",
        "platform": "wefunder",
        "offering_year": 2020,
        "first_live_date": row["initial_form_c_date"],
        "status": "funded_completed",
        "primary_field": "other_diversified",  # to be classified later
        "instrument_type": "unknown",  # refine from funding_evidence_text
        "legal_name": row["issuer_name"],
        "source_url": row["sec_initial_url"],
        "source_availability": "PUBLIC_VISIBLE",
        "completion_date": close,
        "comparable_valuation": None,
        "valuation_cap": None,
        "amount_raised": float(row["funding_amount_usd"]) if row.get("funding_amount_usd") else None,
        "cohost_platforms": [],
        "phase1b_offering_key": row["offering_key"],
        "funding_evidence_text": row.get("funding_evidence_text", "")[:500],
    }

def to_capture(row: dict, round_id: str) -> dict:
    # Stub capture; real hash requires fetching the page
    content_stub = json.dumps({"accession": row["initial_form_c_accession"], "url": row["sec_initial_url"]})
    return {
        "capture_id": f"cap_{round_id}_sec_initial",
        "platform": "wefunder",
        "url": row["sec_initial_url"],
        "page_type": "hosted_document",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "availability": "PUBLIC_VISIBLE",
        "content_sha256": sha256_text(content_stub),
        "round_id": round_id,
        "missing_fields": ["live_page_content"],
        "note": "Structural stub from Phase 1B manifest. Replace with live fetch + real content hash.",
    }

def main():
    rows = load_cohort()
    rounds = []
    captures = []
    for r in rows:
        rr = to_round_record(r)
        rounds.append(rr)
        captures.append(to_capture(r, rr["round_id"]))
        if r.get("sec_funding_url"):
            fund_cap = to_capture(r, rr["round_id"])
            fund_cap["capture_id"] = f"cap_{rr['round_id']}_sec_funding"
            fund_cap["url"] = r["sec_funding_url"]
            fund_cap["content_sha256"] = sha256_text(r["sec_funding_url"])
            captures.append(fund_cap)
    OUT_ROUNDS.write_text(json.dumps(rounds, indent=2), encoding="utf-8")
    OUT_CAPTURES.write_text(json.dumps(captures, indent=2), encoding="utf-8")
    print(f"Wrote {len(rounds)} rounds and {len(captures)} captures")
    return {"rounds": len(rounds), "captures": len(captures)}

if __name__ == "__main__":
    main()
