"""Primary evidence hash capture skeleton.

Lists the capture-ready URLs. Real fetch + SHA-256 must be run with network access.
Updates the primary evidence links file with hash placeholders until live run.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINKS = ROOT / "data" / "phase1d_primary_evidence_links.json"

def add_hash_placeholders():
    if not LINKS.exists():
        print("Run prior primary evidence step first")
        return
    data = json.loads(LINKS.read_text(encoding="utf-8"))
    for rec in data.get("records", []):
        rec["content_sha256"] = None
        rec["hash_status"] = "pending_live_fetch"
        rec["note"] = "Replace None with real SHA-256 of page/PDF content"
    LINKS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Hash placeholders added. Run live fetch to populate real hashes.")

if __name__ == "__main__":
    add_hash_placeholders()
