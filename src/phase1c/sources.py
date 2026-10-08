from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import urlparse

PLATFORM_HOSTS={
    "wefunder":{"wefunder.com","www.wefunder.com"},
    "startengine":{"startengine.com","www.startengine.com"},
    "crowdcube":{"crowdcube.com","www.crowdcube.com"},
    "republic_us":{"republic.com","www.republic.com"},
    "republic_europe":{"europe.republic.com"},
}
PAGE_TYPES={"campaign","hosted_document","issuer_update","platform_portfolio","funded_listing","secondary_page"}
AVAILABILITY={"PUBLIC_VISIBLE","AUTH_REQUIRED","UNAVAILABLE"}

@dataclass(frozen=True)
class SourceCapture:
    capture_id: str
    platform: str
    url: str
    page_type: str
    captured_at: str
    availability: str
    content_sha256: str
    round_id: str | None = None
    missing_fields: tuple[str,...] = ()

def canonical_json_sha256(payload) -> str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def validate_capture(c: SourceCapture) -> list[str]:
    errors=[]
    if c.platform not in PLATFORM_HOSTS:
        errors.append("platform_invalid")
    host=urlparse(c.url).netloc.lower()
    if c.platform in PLATFORM_HOSTS and host not in PLATFORM_HOSTS[c.platform]:
        errors.append("url_host_not_allowed_for_platform")
    if c.page_type not in PAGE_TYPES:
        errors.append("page_type_invalid")
    if c.availability not in AVAILABILITY:
        errors.append("availability_invalid")
    try:
        datetime.fromisoformat(c.captured_at.replace("Z","+00:00"))
    except Exception:
        errors.append("captured_at_invalid")
    if len(c.content_sha256)!=64 or any(ch not in "0123456789abcdef" for ch in c.content_sha256.lower()):
        errors.append("content_sha256_invalid")
    return errors

def build_manifest(captures: list[SourceCapture]) -> dict:
    rows=[asdict(c) for c in sorted(captures,key=lambda x:x.capture_id)]
    return {
        "schema_version":"phase1c-source-manifest-v1",
        "capture_count":len(rows),
        "captures":rows,
        "manifest_sha256":canonical_json_sha256(rows),
    }
