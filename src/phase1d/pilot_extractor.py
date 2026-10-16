"""Phase 1D pilot extractor skeleton.

Uses existing Phase 1C models and adapters.
Full implementation requires live platform/SEC capture.
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path

# Placeholder — expand with real adapters from src.phase1c.adapters
def build_sample_manifest():
    sample = [
        {
            "round_id": "wf_2020_sample_001",
            "platform": "wefunder",
            "offering_year": 2020,
            "status": "funded_completed",
            "source_availability": "PUBLIC_VISIBLE",
            "note": "Seed from Phase 1B lineage. Replace with hashed captures."
        }
    ]
    out = Path("data/phase1d_wefunder_pilot_sample_rounds.json")
    out.write_text(json.dumps(sample, indent=2))
    print(f"Wrote sample to {out}")
    return sample

if __name__ == "__main__":
    build_sample_manifest()
