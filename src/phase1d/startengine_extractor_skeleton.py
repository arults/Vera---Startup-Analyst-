"""StartEngine discovery extractor skeleton.

Target: StartEngine Capital LLC CIK 0001665160 Form C / C-U filings 2020-2022.
Produces discovery RoundRecords only. Real EDGAR fetch and content hashes required later.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "phase1d_startengine_discovery_rounds.json"

def seed_records():
    # Placeholder seeds based on known volume; replace with real EDGAR parse
    return [
        {
            "round_id": "se_2020_placeholder_001",
            "platform": "startengine",
            "offering_year": 2020,
            "legal_name": "Placeholder StartEngine Issuer",
            "status": "discovery_only",
            "discovery_flag": "edgar_cik_0001665160_pending",
            "source_note": "Replace with real Form C accession from CIK 0001665160 search",
            "multi_source_status": "not_started",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

def main():
    records = seed_records()
    OUT.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} StartEngine discovery placeholders to {OUT}")
    return len(records)

if __name__ == "__main__":
    main()
