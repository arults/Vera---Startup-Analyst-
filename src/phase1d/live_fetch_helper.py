"""Live SEC fetch helper for Phase 1D pilot.

Fetches EDGAR index pages, computes real content SHA-256, and updates capture records.
Requires network access. Respects SEC rate limits (user-agent required).
"""
from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None

ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / "data" / "phase1d_wefunder_pilot_captures.json"
USER_AGENT = "Vera-Startup-Analyst research@example.com"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fetch_url(url: str, timeout: int = 30) -> tuple[int, bytes | None, str]:
    if requests is None:
        return 0, None, "requests_not_installed"
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        return resp.status_code, resp.content, ""
    except Exception as e:
        return 0, None, str(e)

def update_captures_with_live_hashes(limit: int = 5):
    """Fetch a limited number of captures and replace stub hashes with real content hashes."""
    if not CAPTURES.exists():
        print("Run pilot_extractor first")
        return
    captures = json.loads(CAPTURES.read_text(encoding="utf-8"))
    updated = 0
    for cap in captures:
        if updated >= limit:
            break
        if "live_page_content" not in cap.get("missing_fields", []):
            continue
        url = cap["url"]
        status, content, err = fetch_url(url)
        time.sleep(0.2)  # polite delay
        if status == 200 and content:
            cap["content_sha256"] = sha256_bytes(content)
            cap["captured_at"] = datetime.now(timezone.utc).isoformat()
            cap["missing_fields"] = [f for f in cap.get("missing_fields", []) if f != "live_page_content"]
            cap["fetch_status"] = status
            cap["note"] = "Live fetch completed"
            updated += 1
        else:
            cap["fetch_status"] = status
            cap["fetch_error"] = err
            cap["availability"] = "UNAVAILABLE" if status == 0 else cap["availability"]
    CAPTURES.write_text(json.dumps(captures, indent=2), encoding="utf-8")
    print(f"Updated {updated} captures with live hashes")
    return updated

if __name__ == "__main__":
    update_captures_with_live_hashes(limit=5)
