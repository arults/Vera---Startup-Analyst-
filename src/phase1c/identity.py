from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

LEGAL_SUFFIXES = {
    "inc","incorporated","llc","ltd","limited","corp","corporation","plc",
    "company","co","gmbh","sa","sas","bv","ag","pte"
}

@dataclass(frozen=True)
class CompanyIdentity:
    legal_name: str
    brand_name: str = ""
    jurisdiction_entity_id: str = ""
    domain: str = ""
    founders: tuple[str, ...] = ()
    hq: str = ""
    product_key: str = ""

@dataclass(frozen=True)
class MatchResult:
    decision: str   # MATCH | REVIEW | NO_MATCH
    tier: str       # STRONG | MEDIUM_BUNDLE | AMBIGUOUS | NONE
    score: int
    reasons: tuple[str, ...]

def _tokens(s: str) -> list[str]:
    s=re.sub(r"[^a-z0-9 ]+"," ",s.lower())
    return [x for x in s.split() if x and x not in LEGAL_SUFFIXES]

def normalize_name(s: str) -> str:
    return " ".join(_tokens(s))

def normalize_domain(s: str) -> str:
    if not s:
        return ""
    s=s.strip().lower()
    if "://" not in s:
        s="https://"+s
    host=urlparse(s).netloc.split(":")[0]
    if host.startswith("www."):
        host=host[4:]
    return host

def _founders(x: CompanyIdentity) -> set[str]:
    return {normalize_name(v) for v in x.founders if normalize_name(v)}

def match_company(a: CompanyIdentity, b: CompanyIdentity) -> MatchResult:
    reasons=[]
    if a.jurisdiction_entity_id and b.jurisdiction_entity_id:
        if a.jurisdiction_entity_id == b.jurisdiction_entity_id:
            return MatchResult("MATCH","STRONG",100,("exact_entity_id",))
        return MatchResult("NO_MATCH","STRONG",0,("conflicting_entity_id",))

    medium=0
    if normalize_name(a.legal_name) and normalize_name(a.legal_name)==normalize_name(b.legal_name):
        medium+=1; reasons.append("legal_name")
    if normalize_domain(a.domain) and normalize_domain(a.domain)==normalize_domain(b.domain):
        medium+=1; reasons.append("domain")
    if _founders(a) and _founders(b) and _founders(a).intersection(_founders(b)):
        medium+=1; reasons.append("founder")
    if a.hq and b.hq and normalize_name(a.hq)==normalize_name(b.hq):
        medium+=1; reasons.append("hq")
    if a.product_key and b.product_key and normalize_name(a.product_key)==normalize_name(b.product_key):
        medium+=1; reasons.append("product")

    if medium >= 2:
        return MatchResult("MATCH","MEDIUM_BUNDLE",medium,tuple(reasons))
    if medium == 1:
        return MatchResult("REVIEW","AMBIGUOUS",medium,tuple(reasons))
    return MatchResult("NO_MATCH","NONE",0,())

def audit_match_sample(results: list[tuple[MatchResult, bool]], reopen_threshold: float=0.02) -> dict:
    """truth=True means the candidate pair is actually the same company."""
    if not results:
        return {"n":0,"false_match_rate":0.0,"false_split_rate":0.0,"reopen":False}
    auto=[(r,t) for r,t in results if r.decision=="MATCH"]
    nonauto=[(r,t) for r,t in results if r.decision!="MATCH"]
    false_matches=sum(1 for r,t in auto if not t)
    false_splits=sum(1 for r,t in nonauto if t)
    fm=false_matches/max(1,len(auto))
    fs=false_splits/max(1,len(nonauto))
    return {
        "n":len(results),
        "false_match_rate":fm,
        "false_split_rate":fs,
        "reopen": fm>reopen_threshold or fs>reopen_threshold,
    }
