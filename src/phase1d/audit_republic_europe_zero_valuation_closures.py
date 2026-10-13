#!/usr/bin/env python3
"""Audit Republic Europe zero-valuation signals for explicit dated closure evidence.

Zero valuation and Secondary Market ineligibility are review triggers only. This worker
never writes a closure label; it preserves platform evidence and emits review candidates.
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/phase1d"
ROUNDS = DATA / "cp2_republic_europe_rounds_normalized.csv"
BUSINESS_RAW = DATA / "cp3_republic_europe_business_pages_raw.csv"
OBS_V2 = DATA / "cp3_republic_europe_business_observations_v2.csv"
HOST = "europe.republic.com"
UA = "Mozilla/5.0 (compatible; VeraStartupResearch/0.6; +https://github.com/arults/Vera---Startup-Analyst-)"

EXPLICIT_PATTERNS = {
    "administration": re.compile(r"\b(?:entered|placed into|went into|in)\s+administration\b|\badministrator(?:s)?\s+(?:was|were|has been|have been)?\s*appointed\b", re.I),
    "liquidation": re.compile(r"\b(?:entered|placed into|went into|in)\s+(?:creditors'? voluntary )?liquidation\b|\bliquidat(?:ed|ion)\b", re.I),
    "dissolution": re.compile(r"\b(?:was|has been|is)\s+dissolved\b|\bdissolution\b", re.I),
    "ceased_trading": re.compile(r"\b(?:has |had |have |was |were )?ceased\s+(?:to\s+)?trad(?:e|ing)\b|\bno longer trading\b", re.I),
    "ceased_operations": re.compile(r"\b(?:has |had |have |was |were )?ceased\s+operations\b|\bno longer operating\b", re.I),
    "wound_up": re.compile(r"\b(?:was|has been|is|being)\s+wound\s+up\b|\bwinding[- ]up\b|\bwind\s+up\s+the\s+company\b", re.I),
    "bankruptcy": re.compile(r"\bfiled\s+for\s+bankruptcy\b|\bdeclared\s+bankrupt\b|\bbankruptcy\s+proceedings\b", re.I),
    "shutdown": re.compile(r"\bshut\s+down\s+(?:the\s+)?(?:business|company|operations)\b|\bcompany\s+(?:has\s+)?closed\s+down\b", re.I),
}

DATE_PATTERNS = (
    re.compile(r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})\b", re.I),
    re.compile(r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2})\b", re.I),
    re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def official_url(url: str) -> bool:
    p = urlsplit(url or "")
    return p.scheme == "https" and p.netloc.lower() == HOST and not p.username and not p.password


def canonical_url(url: str) -> str:
    p = urlsplit(url)
    return f"https://{HOST}{p.path.rstrip('/') or '/'}"


def zero_valuation(value: str) -> bool:
    text = re.sub(r"\s+", "", value or "")
    m = re.fullmatch(r"[£€$]?([0-9]+(?:[.,][0-9]+)?)([KkMmBb]?)", text)
    if not m:
        return False
    amount = float(m.group(1).replace(",", "."))
    return amount == 0.0


def relevant_update_link(href: str, base: str, campaign_slug: str) -> str | None:
    url = urljoin(base, href)
    if not official_url(url):
        return None
    p = urlsplit(url)
    path = p.path.lower().rstrip("/")
    if any(token in path for token in ("/updates/", "/update/", "/posts/", "/news/")):
        return canonical_url(url)
    if campaign_slug and campaign_slug in path and re.search(r"(?:update|news|post)", path):
        return canonical_url(url)
    return None


def extract_date(text: str) -> str:
    for pattern in DATE_PATTERNS:
        m = pattern.search(text or "")
        if not m:
            continue
        raw = m.group(1).replace(",", "")
        for fmt in ("%d %B %Y", "%B %d %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                pass
    return ""


def extract_candidates(text: str, source_url: str, company_name: str) -> list[dict]:
    flat = re.sub(r"\s+", " ", text or "").strip()
    output = []
    seen = set()
    for event_type, pattern in EXPLICIT_PATTERNS.items():
        for match in pattern.finditer(flat):
            lo = max(0, match.start() - 280)
            hi = min(len(flat), match.end() + 380)
            excerpt = flat[lo:hi].strip()
            key = (event_type, excerpt)
            if key in seen:
                continue
            seen.add(key)
            near_date = extract_date(excerpt)
            output.append({
                "company_name": company_name,
                "source_url": source_url,
                "event_type_candidate": event_type,
                "trigger": match.group(0),
                "date_candidate": near_date,
                "date_status": "EXPLICIT_NEARBY" if near_date else "DATE_UNRESOLVED",
                "excerpt": excerpt,
                "review_status": "PENDING",
                "closure_label_applied": "false",
            })
    return output


def store_snapshot(root: Path, raw: bytes, url: str, status: int, content_type: str) -> dict:
    digest = sha(raw)
    target = root / "snapshots" / f"{digest}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(json.dumps({
            "sha256": digest,
            "bytes": len(raw),
            "url": url,
            "http_status": status,
            "content_type": content_type,
            "encoding": "gzip+base64",
            "data": base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii"),
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"sha256": digest, "bytes": len(raw), "url": url, "http_status": status, "content_type": content_type}


def fetch(url: str) -> dict:
    if not official_url(url):
        raise ValueError("non-platform URL")
    try:
        response = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"}, timeout=30, allow_redirects=True)
        final = canonical_url(response.url)
        if not official_url(final):
            raise ValueError("redirected outside Republic Europe")
        return {"url": final, "status": response.status_code, "content_type": response.headers.get("content-type", ""), "raw": response.content, "error": ""}
    except Exception as exc:
        return {"url": url, "status": None, "content_type": "", "raw": b"", "error": repr(exc)}


def target_companies() -> list[dict]:
    raw_by_url = {canonical_url(r["url"]): r for r in read_csv(BUSINESS_RAW) if r.get("url") and official_url(r["url"])}
    observations = read_csv(OBS_V2)
    targets = []
    for observation in observations:
        url = canonical_url(observation.get("business_url", "")) if observation.get("business_url") else ""
        raw = raw_by_url.get(url)
        if not raw:
            continue
        if observation.get("eligibility") == "NOT_ELIGIBLE" and zero_valuation(raw.get("indicative_valuation", "")):
            targets.append({
                "canonical_company_id": observation["canonical_company_id"],
                "business_name": observation.get("business_name", ""),
                "business_url": url,
                "indicative_valuation": raw.get("indicative_valuation", ""),
                "business_content_sha256": raw.get("content_sha256", ""),
            })
    unique = {(x["canonical_company_id"], x["business_url"]): x for x in targets}
    return sorted(unique.values(), key=lambda x: (x["canonical_company_id"], x["business_url"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-update-links-per-campaign", type=int, default=20)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.run_id) or not 0 <= args.max_update_links_per_campaign <= 30:
        raise ValueError("invalid bounded parameters")

    root = DATA / "republic_europe_closure_audit" / args.run_id
    root.mkdir(parents=True, exist_ok=True)
    targets = target_companies()
    rounds = read_csv(ROUNDS)
    rounds_by_company: dict[str, list[dict]] = {}
    for row in rounds:
        rounds_by_company.setdefault(row["canonical_company_id"], []).append(row)

    jobs = []
    for target in targets:
        jobs.append({**target, "source_type": "business_page", "source_url": target["business_url"], "round_id": ""})
        for round_row in rounds_by_company.get(target["canonical_company_id"], []):
            url = canonical_url(round_row["campaign_url"])
            jobs.append({**target, "source_type": "campaign_page", "source_url": url, "round_id": round_row["round_id"]})
    jobs = list({(j["canonical_company_id"], j["source_url"]): j for j in jobs}.values())

    captures = []
    candidates = []
    update_jobs = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, job["source_url"]): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            result = future.result()
            snapshot = store_snapshot(root, result["raw"], result["url"], result["status"] or 0, result["content_type"])
            capture = {**job, **snapshot, "fetch_error": result["error"], "captured_at": now()}
            captures.append(capture)
            if result["status"] != 200 or not result["raw"]:
                continue
            text = result["raw"].decode("utf-8", "ignore")
            soup = BeautifulSoup(text, "html.parser")
            visible = "\n".join(x.strip() for x in soup.stripped_strings)
            for candidate in extract_candidates(visible, result["url"], job["business_name"]):
                candidates.append({**job, **candidate, "source_content_sha256": snapshot["sha256"]})
            if job["source_type"] == "campaign_page":
                campaign_slug = urlsplit(job["source_url"]).path.strip("/").split("/")[-1].lower()
                links = []
                for anchor in soup.find_all("a", href=True):
                    link = relevant_update_link(anchor["href"], result["url"], campaign_slug)
                    if link:
                        links.append(link)
                for link in sorted(set(links))[:args.max_update_links_per_campaign]:
                    update_jobs.append({**job, "source_type": "platform_update", "source_url": link})

    update_jobs = list({(j["canonical_company_id"], j["source_url"]): j for j in update_jobs}.values())
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, job["source_url"]): job for job in update_jobs}
        for future in as_completed(futures):
            job = futures[future]
            result = future.result()
            snapshot = store_snapshot(root, result["raw"], result["url"], result["status"] or 0, result["content_type"])
            captures.append({**job, **snapshot, "fetch_error": result["error"], "captured_at": now()})
            if result["status"] == 200 and result["raw"]:
                soup = BeautifulSoup(result["raw"].decode("utf-8", "ignore"), "html.parser")
                visible = "\n".join(x.strip() for x in soup.stripped_strings)
                for candidate in extract_candidates(visible, result["url"], job["business_name"]):
                    candidates.append({**job, **candidate, "source_content_sha256": snapshot["sha256"]})

    captures.sort(key=lambda x: (x["canonical_company_id"], x["source_type"], x["source_url"]))
    candidates.sort(key=lambda x: (x["canonical_company_id"], x["source_url"], x["event_type_candidate"], x["excerpt"]))
    capture_fields = [
        "canonical_company_id", "business_name", "business_url", "indicative_valuation", "business_content_sha256",
        "source_type", "source_url", "round_id", "sha256", "bytes", "http_status", "content_type", "fetch_error", "captured_at",
    ]
    candidate_fields = [
        "canonical_company_id", "business_name", "business_url", "indicative_valuation", "business_content_sha256",
        "source_type", "source_url", "round_id", "event_type_candidate", "trigger", "date_candidate", "date_status",
        "excerpt", "review_status", "closure_label_applied", "source_content_sha256",
    ]
    write_csv(root / "captures.csv", captures, capture_fields)
    write_csv(root / "closure_review_candidates.csv", candidates, candidate_fields)
    summary = {
        "run_id": args.run_id,
        "target_company_pages": len(targets),
        "target_unique_companies": len({x["canonical_company_id"] for x in targets}),
        "initial_source_jobs": len(jobs),
        "platform_update_jobs": len(update_jobs),
        "captures": len(captures),
        "successful_captures": sum(x["http_status"] == 200 for x in captures),
        "closure_review_candidates": len(candidates),
        "dated_review_candidates": sum(bool(x["date_candidate"]) for x in candidates),
        "closures_applied": 0,
        "rates_promoted": False,
        "scope": "Republic Europe business pages, original campaign pages, and same-platform update links for Not eligible + zero indicative valuation review triggers only.",
        "policy": "No zero valuation or phrase match is an automatic closure. Every candidate requires Verifier and Jev adjudication; missing dates remain unresolved.",
        "files": {
            "captures.csv": sha((root / "captures.csv").read_bytes()),
            "closure_review_candidates.csv": sha((root / "closure_review_candidates.csv").read_bytes()),
        },
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({
        "generated_at": now(),
        "source_files": {ROUNDS.name: sha(ROUNDS.read_bytes()), BUSINESS_RAW.name: sha(BUSINESS_RAW.read_bytes()), OBS_V2.name: sha(OBS_V2.read_bytes())},
        "summary": summary,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
