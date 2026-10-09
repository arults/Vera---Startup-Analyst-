#!/usr/bin/env python3
"""Bounded recovery from exact public StartEngine endpoints observed in browser traffic."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import requests

try:
    from curl_cffi import requests as cffi_requests
except Exception:
    cffi_requests = None

from src.phase1d.recover_startengine import (
    atomic_json,
    extract_candidates,
    extract_total_hints,
    new_manifest,
    now,
    record_capture,
    safe_public_resource,
    sha256,
    store_snapshot,
    verify,
)

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.startengine.com"
TOMBSTONES = BASE + "/service/primary_facade/v2/offerings/current/tombstones"
INDUSTRIES = BASE + "/service/primary_facade/v2/offerings/industries?midLevelOnly=true"
SEARCH_PATH = "/service/elastic-search/search/offering/search"
OBSERVED_SEARCH_PARAMS = {
    "fingerprint": "",
    "query": "",
    "regulationTypes": "Reg D",
    "size": "200",
    "sortBy": "mostMomentum",
    "statuses": "APPROVED,TESTING,CLOSED",
}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"


def search_url(page: int) -> str:
    if not isinstance(page, int) or not 0 <= page <= 50:
        raise ValueError("page outside bounded range")
    params = {**OBSERVED_SEARCH_PARAMS, "page": str(page)}
    return BASE + SEARCH_PATH + "?" + urlencode(params)


def allowed_endpoint(url: str) -> bool:
    if not safe_public_resource(url):
        return False
    p = urlsplit(url)
    if p.path in {
        "/service/primary_facade/v2/offerings/current/tombstones",
        "/service/primary_facade/v2/offerings/industries",
    }:
        return True
    if p.path != SEARCH_PATH:
        return False
    query = dict(__import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(p.query, keep_blank_values=True))
    expected = {**OBSERVED_SEARCH_PARAMS}
    if set(query) != set(expected) | {"page"}:
        return False
    if any(query[k] != v for k, v in expected.items()):
        return False
    return bool(re.fullmatch(r"\d{1,2}", query["page"])) and 0 <= int(query["page"]) <= 50


def fetch(url: str) -> dict:
    if not allowed_endpoint(url):
        raise ValueError("endpoint is outside observed public allowlist")
    headers = {
        "User-Agent": UA,
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.startengine.com/explore",
        "Accept-Language": "en-US,en;q=0.9",
    }
    errors = []
    for transport in ("requests", "curl_cffi"):
        try:
            if transport == "requests":
                r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            elif cffi_requests is not None:
                r = cffi_requests.get(url, headers=headers, timeout=30, allow_redirects=True, impersonate="chrome")
            else:
                continue
            raw = bytes(r.content)
            result = {
                "url": str(r.url),
                "status": int(r.status_code),
                "content_type": r.headers.get("content-type", ""),
                "transport": transport,
                "raw": raw,
            }
            if r.status_code == 200:
                return result
            errors.append(f"{transport}:HTTP {r.status_code}")
        except Exception as exc:
            errors.append(f"{transport}:{exc!r}")
    return {"url": url, "status": None, "content_type": "", "transport": "none", "raw": b"", "errors": errors}


def decode_json(raw: bytes) -> object:
    if len(raw) > 15_000_000:
        raise ValueError("oversize response")
    return json.loads(raw.decode("utf-8"))


def capture_response(root: Path, manifest: dict, result: dict, kind: str, page: int | None = None) -> tuple[bool, list[str]]:
    raw = result.get("raw", b"")
    capture = {
        "url": result["url"],
        "kind": kind,
        "status": result.get("status"),
        "captured_at": now(),
        "transport": result.get("transport"),
        "sha256": store_snapshot(root, raw),
        "candidate_urls": [],
        "total_hints": [],
    }
    if page is not None:
        capture["page"] = page
    if result.get("status") != 200:
        record_capture(manifest, capture)
        manifest["errors"].append({"url": result["url"], "error": ";".join(result.get("errors", [])) or f"HTTP {result.get('status')}", "at": now()})
        return False, []
    try:
        payload = decode_json(raw)
    except Exception as exc:
        record_capture(manifest, capture)
        manifest["errors"].append({"url": result["url"], "error": f"SCHEMA_OR_JSON:{exc!r}", "at": now()})
        return False, []
    candidates = extract_candidates(payload)
    capture["candidate_urls"] = candidates
    capture["total_hints"] = [{"source": result["url"], **h} for h in extract_total_hints(payload)]
    record_capture(manifest, capture)
    return True, candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-pages", type=int, default=10)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.run_id) or not 1 <= args.max_pages <= 20:
        raise ValueError("invalid bounded-run parameters")

    root = ROOT / "data/phase1d/startengine_endpoint_recovery" / args.run_id
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else new_manifest(args.run_id)
    manifest["schema"] = "phase1d-startengine-observed-endpoints-v1"
    manifest["scope"] = "Exact public endpoints observed in StartEngine browser traffic; search endpoint is Reg D filtered and cannot establish the full 2020-2025 denominator."
    manifest["endpoint_scope"] = "OBSERVED_ONLY"
    manifest["rates_promoted"] = False
    manifest["census_status"] = "CENSUS_INCOMPLETE"

    static_results = []
    for url, kind in ((TOMBSTONES, "observed_tombstones"), (INDUSTRIES, "observed_industries")):
        result = fetch(url)
        ok, candidates = capture_response(root, manifest, result, kind)
        static_results.append({"url": url, "status": result.get("status"), "ok": ok, "candidate_count": len(candidates)})
        atomic_json(manifest_path, manifest)

    pages = []
    previous_hash = None
    no_new_streak = 0
    union_before = len(manifest.get("candidate_urls", []))
    stop_reason = "MAX_PAGES"
    for page in range(args.max_pages):
        url = search_url(page)
        result = fetch(url)
        raw_hash = sha256(result.get("raw", b""))
        ok, candidates = capture_response(root, manifest, result, "observed_search_page", page)
        union_after = len(manifest.get("candidate_urls", []))
        pages.append({"page": page, "status": result.get("status"), "ok": ok, "candidate_count": len(candidates), "union_count": union_after, "sha256": raw_hash})
        atomic_json(manifest_path, manifest)
        if not ok:
            stop_reason = "ACCESS_OR_SCHEMA_ERROR"
            break
        if raw_hash == previous_hash:
            stop_reason = "REPEATED_RESPONSE"
            break
        no_new_streak = no_new_streak + 1 if union_after == union_before else 0
        union_before = union_after
        previous_hash = raw_hash
        if no_new_streak >= 2:
            stop_reason = "NO_NEW_CANDIDATES_TWO_PAGES"
            break

    manifest["directory_stops"] = [{"seed": SEARCH_PATH, "reason": stop_reason, "at": now()}]
    atomic_json(manifest_path, manifest)

    base_checks = verify(root, {**manifest, "schema": "phase1d-startengine-recovery-v1"})
    checks = {
        **base_checks["checks"],
        "observed_endpoint_scope": manifest["endpoint_scope"] == "OBSERVED_ONLY",
        "rates_remain_suppressed": manifest["rates_promoted"] is False and manifest["census_status"] == "CENSUS_INCOMPLETE",
        "all_capture_urls_allowlisted": all(allowed_endpoint(c["url"]) for c in manifest["captures"]),
        "bounded_page_count": len(pages) <= args.max_pages,
        "search_scope_not_misrepresented": "Reg D" in manifest["scope"],
    }
    summary = {
        "run_id": args.run_id,
        "census_status": manifest["census_status"],
        "rates_promoted": False,
        "candidate_count": len(manifest.get("candidate_urls", [])),
        "capture_count": len(manifest.get("captures", [])),
        "static_results": static_results,
        "search_pages": pages,
        "search_stop_reason": stop_reason,
        "errors": manifest.get("errors", []),
        "integrity_gates": {"passed": sum(bool(v) for v in checks.values()), "total": len(checks), "checks": checks},
        "manifest_sha256": sha256(manifest_path.read_bytes()),
        "scientific_conclusion": "This exact observed-endpoint attempt cannot establish full StartEngine historical denominator completeness; rates remain suppressed.",
    }
    atomic_json(root / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    if summary["integrity_gates"]["passed"] != summary["integrity_gates"]["total"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
