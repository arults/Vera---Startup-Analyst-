from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from math import ceil
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
class IdentityRecord:
    record_id: str
    platform: str
    identity: CompanyIdentity

@dataclass(frozen=True)
class MatchResult:
    decision: str   # MATCH | REVIEW | NO_MATCH
    tier: str       # STRONG | MEDIUM_BUNDLE | AMBIGUOUS | NONE
    score: int
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class IdentityCandidate:
    left_record_id: str
    right_record_id: str
    left_platform: str
    right_platform: str
    result: MatchResult

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

def blocking_keys(x: CompanyIdentity) -> set[str]:
    keys=set()
    if x.jurisdiction_entity_id:
        keys.add("entity:"+x.jurisdiction_entity_id.lower())
    n=normalize_name(x.legal_name)
    if n: keys.add("name:"+n)
    d=normalize_domain(x.domain)
    if d: keys.add("domain:"+d)
    for f in _founders(x):
        keys.add("founder:"+f)
    return keys

def generate_cross_platform_candidates(records: list[IdentityRecord]) -> list[IdentityCandidate]:
    """
    Candidate generation is blocking-key based. Pairs on the same platform are never emitted.
    Pairs with no shared blocking key are not compared; name-only shared keys yield REVIEW, not MATCH.
    """
    blocks: dict[str,list[int]]={}
    for i,r in enumerate(records):
        for key in blocking_keys(r.identity):
            blocks.setdefault(key,[]).append(i)
    pairs=set()
    for ids in blocks.values():
        for p in range(len(ids)):
            for q in range(p+1,len(ids)):
                i,j=ids[p],ids[q]
                if records[i].platform==records[j].platform:
                    continue
                pairs.add((min(i,j),max(i,j)))
    out=[]
    for i,j in sorted(pairs):
        a,b=records[i],records[j]
        result=match_company(a.identity,b.identity)
        if result.decision!="NO_MATCH":
            out.append(IdentityCandidate(a.record_id,b.record_id,a.platform,b.platform,result))
    return out

def _candidate_key(c: IdentityCandidate) -> str:
    return "|".join(sorted([c.left_record_id,c.right_record_id]))

def _pair_key(c: IdentityCandidate) -> str:
    return "→".join(sorted([c.left_platform,c.right_platform]))

def build_review_queue(candidates: list[IdentityCandidate], strong_audit_rate: float=0.10) -> dict:
    """
    100% review of ambiguous and medium-bundle matches.
    Strong exact matches receive a deterministic, platform-pair-stratified audit sample.
    """
    if not 0 <= strong_audit_rate <= 1:
        raise ValueError("invalid_audit_rate")
    mandatory=[
        c for c in candidates
        if c.result.decision=="REVIEW" or c.result.tier=="MEDIUM_BUNDLE"
    ]
    strong=[c for c in candidates if c.result.decision=="MATCH" and c.result.tier=="STRONG"]

    by_pair: dict[str,list[IdentityCandidate]]={}
    for c in strong:
        by_pair.setdefault(_pair_key(c),[]).append(c)

    audit=[]
    for pair,group in sorted(by_pair.items()):
        ranked=sorted(
            group,
            key=lambda c: hashlib.sha256(_candidate_key(c).encode()).hexdigest()
        )
        k=ceil(len(ranked)*strong_audit_rate) if ranked else 0
        audit.extend(ranked[:k])

    dedup={_candidate_key(c):c for c in mandatory+audit}
    return {
        "mandatory_review_count":len(mandatory),
        "strong_auto_match_count":len(strong),
        "strong_audit_count":len(audit),
        "review_record_ids":sorted(dedup),
        "review_candidates":[dedup[k] for k in sorted(dedup)],
    }

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
