#!/usr/bin/env python3
"""Bounded public StartEngine census recovery. Never promotes rates from partial coverage."""
from __future__ import annotations

import argparse, base64, gzip, hashlib, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

SEEDS = (
    "https://www.startengine.com/explore",
    "https://www.startengine.com/explore/offerings",
)
PAGE_HOSTS = {"startengine.com", "www.startengine.com"}
OFFICIAL_SUFFIX = ".startengine.com"
SENSITIVE_QUERY_KEYS = {"token", "access_token", "authorization", "signature", "session", "api_key", "apikey", "key"}
SCHEMA = "phase1d-startengine-recovery-v1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def official_host(host: str) -> bool:
    h = (host or "").lower().split(":")[0]
    return h in PAGE_HOSTS or h.endswith(OFFICIAL_SUFFIX)


def canonical_candidate(url: str, base: str = "https://www.startengine.com/") -> str | None:
    p = urlsplit(urljoin(base, url))
    if p.scheme != "https" or p.netloc.lower() not in PAGE_HOSTS or p.username or p.password or p.port:
        return None
    parts = [x for x in p.path.split("/") if x]
    if len(parts) != 2 or parts[0].lower() != "offering":
        return None
    slug = parts[1].lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,160}", slug):
        return None
    if slug in {"new", "search", "explore"}:
        return None
    return f"https://www.startengine.com/offering/{slug}"


def safe_public_resource(url: str) -> bool:
    p = urlsplit(url)
    if p.scheme != "https" or not official_host(p.netloc) or p.username or p.password:
        return False
    keys = {k.lower() for k, _ in parse_qsl(p.query, keep_blank_values=True)}
    return not bool(keys & SENSITIVE_QUERY_KEYS)


def redacted_resource_url(url: str) -> str:
    p = urlsplit(url)
    clean = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in SENSITIVE_QUERY_KEYS]
    return urlunsplit((p.scheme, p.netloc.lower(), p.path, urlencode(clean), ""))


def extract_candidates(value: object) -> list[str]:
    found: set[str] = set()

    def walk(x: object, parent_key: str = "") -> None:
        if isinstance(x, dict):
            # Slug fields alone are accepted only in clearly offering-like records.
            keys = {str(k).lower() for k in x}
            offering_context = bool(keys & {"offering", "offering_id", "offering_slug", "issuer", "investment_type", "amount_raised", "valuation"})
            for k, v in x.items():
                lk = str(k).lower()
                if isinstance(v, str):
                    c = canonical_candidate(v)
                    if c:
                        found.add(c)
                    if lk in {"offering_slug", "slug"} and offering_context:
                        c = canonical_candidate(f"/offering/{v}")
                        if c:
                            found.add(c)
                walk(v, lk)
        elif isinstance(x, list):
            for v in x:
                walk(v, parent_key)
        elif isinstance(x, str):
            for m in re.finditer(r"https?://(?:www\.)?startengine\.com/offering/[A-Za-z0-9._-]+|/offering/[A-Za-z0-9._-]+", x):
                c = canonical_candidate(m.group(0))
                if c:
                    found.add(c)

    walk(value)
    return sorted(found)


def extract_total_hints(value: object) -> list[dict]:
    hints: list[dict] = []
    total_keys = {"total", "total_count", "totalcount", "nbhits", "count", "offerings_count", "offering_count"}

    def walk(x: object, path: str = "$") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                p = f"{path}.{k}"
                if str(k).lower() in total_keys and isinstance(v, (int, float)) and 0 <= v <= 1_000_000:
                    hints.append({"path": p, "value": int(v)})
                walk(v, p)
        elif isinstance(x, list):
            for i, v in enumerate(x[:200]):
                walk(v, f"{path}[{i}]")

    walk(value)
    unique = {(h["path"], h["value"]): h for h in hints}
    return sorted(unique.values(), key=lambda h: (h["value"], h["path"]))


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def store_snapshot(root: Path, raw: bytes) -> str:
    if len(raw) > 15_000_000:
        raise ValueError("oversize response; not silently truncated")
    h = sha256(raw)
    target = root / "snapshots" / f"{h}.json"
    if not target.exists():
        atomic_json(target, {
            "sha256": h,
            "bytes": len(raw),
            "encoding": "gzip+base64",
            "data": base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii"),
        })
    return h


def load_snapshot(root: Path, digest: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid digest")
    record = json.loads((root / "snapshots" / f"{digest}.json").read_text())
    raw = gzip.decompress(base64.b64decode(record["data"], validate=True))
    if record.get("sha256") != digest or sha256(raw) != digest or len(raw) != record.get("bytes"):
        raise ValueError("snapshot integrity failure")
    return raw


def new_manifest(run_id: str) -> dict:
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "created_at": now(),
        "captures": [],
        "errors": [],
        "seeds_completed": [],
        "directory_stops": [],
        "candidate_urls": [],
        "total_hints": [],
        "census_status": "CENSUS_INCOMPLETE",
        "rates_promoted": False,
        "scope": "Public StartEngine directory/network recovery only; historical platform-year denominator unresolved until independently verified.",
    }


def record_capture(manifest: dict, capture: dict) -> bool:
    key = (capture["url"], capture["kind"], capture["sha256"])
    if any((x["url"], x["kind"], x["sha256"]) == key for x in manifest["captures"]):
        return False
    capture["candidate_urls"] = sorted({u for x in capture.get("candidate_urls", []) if (u := canonical_candidate(x))})
    capture["candidate_count"] = len(capture["candidate_urls"])
    manifest["captures"].append(capture)
    manifest["candidate_urls"] = sorted({u for x in manifest["captures"] for u in x.get("candidate_urls", [])})
    manifest["total_hints"] = sorted(
        {(h["source"], h["path"], h["value"]): h for x in manifest["captures"] for h in x.get("total_hints", [])}.values(),
        key=lambda h: (h["value"], h["source"], h["path"]),
    )
    return True


def checkpoint(root: Path, manifest: dict) -> None:
    manifest["updated_at"] = now()
    n = len(list((root / "checkpoints").glob("*.json"))) + 1
    atomic_json(root / "checkpoints" / f"{n:06d}.json", manifest)
    atomic_json(root / "manifest.json", manifest)


def verify(root: Path, manifest: dict) -> dict:
    for h in {c["sha256"] for c in manifest["captures"]}:
        load_snapshot(root, h)
    checks = {
        "schema": manifest["schema"] == SCHEMA,
        "no_rate_promotion": manifest["rates_promoted"] is False,
        "census_not_silently_complete": manifest["census_status"] in {"CENSUS_INCOMPLETE", "POTENTIAL_COMPLETE_REVIEW"},
        "candidate_urls_canonical": all(canonical_candidate(u) == u for u in manifest["candidate_urls"]),
        "capture_counts_reconcile": all(c["candidate_count"] == len(set(c["candidate_urls"])) for c in manifest["captures"]),
        "candidate_union_reconciles": manifest["candidate_urls"] == sorted({u for c in manifest["captures"] for u in c["candidate_urls"]}),
        "captures_distinct": len(manifest["captures"]) == len({(c["url"], c["kind"], c["sha256"]) for c in manifest["captures"]}),
        "public_resources_only": all(safe_public_resource(c["url"]) for c in manifest["captures"] if c["kind"] == "network_json"),
        "timestamps_present": all(bool(c.get("captured_at")) for c in manifest["captures"]),
        "snapshot_hashes_verified": True,
    }
    return {"passed": sum(checks.values()), "total": len(checks), "checks": checks}


def main() -> None:
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--steps-per-seed", type=int, default=12)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.run_id) or not 1 <= args.steps_per_seed <= 30:
        raise ValueError("invalid bounded-run parameters")

    root = Path(__file__).resolve().parents[2] / "data/phase1d/startengine_recovery" / args.run_id
    root.mkdir(parents=True, exist_ok=True)
    current = root / "manifest.json"
    manifest = json.loads(current.read_text()) if current.exists() else new_manifest(args.run_id)
    if manifest["run_id"] != args.run_id or not all(verify(root, manifest)["checks"].values()):
        raise ValueError("refuse invalid resume checkpoint")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            locale="en-US",
            viewport={"width": 1440, "height": 1200},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36",
        )
        page = ctx.new_page()

        def on_response(resp) -> None:
            url = resp.url
            ctype = (resp.headers.get("content-type") or "").lower()
            if not safe_public_resource(url) or ("json" not in ctype and "graphql" not in url.lower() and "/api/" not in url.lower()):
                return
            try:
                if resp.status != 200:
                    return
                raw = resp.body()
                body = json.loads(raw)
                clean_url = redacted_resource_url(url)
                hints = [{"source": clean_url, **h} for h in extract_total_hints(body)]
                record_capture(manifest, {
                    "url": clean_url,
                    "kind": "network_json",
                    "status": resp.status,
                    "captured_at": now(),
                    "sha256": store_snapshot(root, raw),
                    "candidate_urls": extract_candidates(body),
                    "total_hints": hints,
                })
                checkpoint(root, manifest)
                print(json.dumps({"network": clean_url, "candidates": len(manifest["candidate_urls"]), "hints": len(hints)}), flush=True)
            except Exception as exc:
                manifest["errors"].append({"url": redacted_resource_url(url), "error": repr(exc), "at": now()})
                checkpoint(root, manifest)

        page.on("response", on_response)

        for seed in SEEDS:
            if seed in manifest["seeds_completed"]:
                continue
            stop = "STEP_LIMIT"
            try:
                resp = page.goto(seed, wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(2500)
                if resp is None or resp.status != 200:
                    raise ValueError(f"HTTP {resp.status if resp else None}")
                stable = 0
                previous_union = -1
                for step in range(args.steps_per_seed):
                    hrefs = page.locator("a[href]").evaluate_all("xs => xs.map(x => x.href)")
                    candidates = sorted({u for x in hrefs if (u := canonical_candidate(x, page.url))})
                    body_text = page.locator("body").inner_text()
                    total_hints = []
                    for m in re.finditer(r"\b([0-9][0-9,]{2,})\s+(?:offerings|companies|startups|investments)\b", body_text, re.I):
                        total_hints.append({"source": page.url, "path": "body_text", "value": int(m.group(1).replace(",", ""))})
                    html = page.content().encode()
                    record_capture(manifest, {
                        "url": page.url,
                        "seed": seed,
                        "kind": "directory_dom",
                        "status": 200,
                        "step": step,
                        "captured_at": now(),
                        "sha256": store_snapshot(root, html),
                        "candidate_urls": candidates,
                        "total_hints": total_hints,
                        "title": page.title(),
                    })
                    checkpoint(root, manifest)
                    current_union = len(manifest["candidate_urls"])
                    stable = stable + 1 if current_union == previous_union else 0
                    previous_union = current_union
                    print(json.dumps({"seed": seed, "step": step, "page_candidates": len(candidates), "union": current_union}), flush=True)

                    clicked = False
                    for label in ("Load more", "Show more", "View more", "See more"):
                        button = page.get_by_role("button", name=re.compile(rf"^{re.escape(label)}", re.I))
                        if button.count() and button.first.is_visible() and button.first.is_enabled():
                            button.first.click(timeout=3500)
                            page.wait_for_timeout(1500)
                            clicked = True
                            break
                    if clicked:
                        continue
                    next_link = page.locator('a[rel="next"]')
                    if next_link.count():
                        href = next_link.first.get_attribute("href")
                        target = urljoin(page.url, href or "")
                        p = urlsplit(target)
                        if p.scheme == "https" and p.netloc.lower() in PAGE_HOSTS:
                            nav = page.goto(target, wait_until="domcontentloaded", timeout=45_000)
                            if nav is None or nav.status != 200:
                                raise ValueError("pagination HTTP failure")
                            page.wait_for_timeout(1200)
                            continue
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1200)
                    if stable >= 3:
                        stop = "VISIBLE_LIST_STABLE_NOT_HISTORICAL_COMPLETENESS"
                        break
                manifest["seeds_completed"].append(seed)
            except Exception as exc:
                stop = "ACCESS_OR_CAPTURE_ERROR"
                manifest["errors"].append({"url": seed, "error": str(exc), "at": now()})
            manifest["directory_stops"].append({"seed": seed, "reason": stop, "at": now()})
            checkpoint(root, manifest)
        browser.close()

    values = [h["value"] for h in manifest["total_hints"] if h["value"] > 0]
    explicit_total = max(values) if values else None
    if explicit_total and len(manifest["candidate_urls"]) >= explicit_total and all(x["reason"] != "ACCESS_OR_CAPTURE_ERROR" for x in manifest["directory_stops"]):
        manifest["census_status"] = "POTENTIAL_COMPLETE_REVIEW"
    checkpoint(root, manifest)
    gates = verify(root, manifest)
    summary = {
        "run_id": args.run_id,
        "census_status": manifest["census_status"],
        "rates_promoted": False,
        "candidate_count": len(manifest["candidate_urls"]),
        "capture_count": len(manifest["captures"]),
        "explicit_total_hints": sorted(set(values)),
        "completed_seed_count": len(manifest["seeds_completed"]),
        "directory_stops": manifest["directory_stops"],
        "errors": manifest["errors"],
        "integrity_gates": gates,
        "manifest_sha256": sha256((root / "manifest.json").read_bytes()),
    }
    atomic_json(root / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    if gates["passed"] != gates["total"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
