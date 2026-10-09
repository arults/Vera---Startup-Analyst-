#!/usr/bin/env python3
from __future__ import annotations

import csv, hashlib, json, re, unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/phase1d"
SRC=DATA/"cp2_republic_europe_rounds_raw.csv"
OUT=DATA/"cp2_republic_europe_rounds_normalized.csv"
UNRES=DATA/"cp2_republic_europe_year_unresolved.csv"
COLLISIONS=DATA/"cp2_republic_europe_company_id_collision_audit.csv"
MAN=DATA/"cp2_republic_europe_normalized_manifest.json"

YEARS={str(y) for y in range(2020,2026)}


def norm(s):
    return re.sub(r"[^a-z0-9]+","-", (s or "").lower()).strip("-")


def hid(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:16]


def round_id(url):
    slug=urlparse(url).path.strip("/").split("/")[-1] or hid(url)
    return "reurope:"+slug


def canonical_company_number(value):
    """Canonical comparison key; raw platform value is always preserved separately."""
    text=unicodedata.normalize("NFKC", value or "")
    text="".join(ch for ch in text if unicodedata.category(ch) not in {"Cf","Cc"})
    key="".join(ch for ch in text.upper() if ch.isalnum())
    if key.isdigit():
        key=key.lstrip("0") or "0"
    return key


def company_name_key(value):
    return " ".join(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", value or "").encode("ascii","ignore").decode().lower()))


def collision_plan(rows):
    by_key=defaultdict(lambda: defaultdict(set))
    for r in rows:
        raw=(r.get("company_number") or "").strip()
        key=canonical_company_number(raw)
        if key:
            by_key[key][raw].add(company_name_key(r.get("campaign_name","")))

    audit=[]
    blocked=set()
    for key,raw_map in sorted(by_key.items()):
        if len(raw_map)<=1:
            continue
        name_sets=[{x for x in names if x} for names in raw_map.values()]
        common=set.intersection(*name_sets) if name_sets and all(name_sets) else set()
        status="FORMATTING_EQUIVALENT_MERGED" if common else "BLOCK_REVIEW"
        if status=="BLOCK_REVIEW":
            blocked.add(key)
        audit.append({
            "canonical_number_key":key,
            "raw_company_numbers":" | ".join(sorted(raw_map)),
            "raw_variant_count":len(raw_map),
            "campaign_name_keys":" | ".join(sorted({x for names in raw_map.values() for x in names if x})),
            "shared_name_key":" | ".join(sorted(common)),
            "status":status,
            "auto_merge":str(status=="FORMATTING_EQUIVALENT_MERGED").lower(),
        })
    return audit,blocked


def company_id(company_number,name,blocked_keys):
    raw=(company_number or "").strip()
    key=canonical_company_number(raw)
    if key:
        if key in blocked_keys:
            return "reurope-company:"+key+":raw-"+hid(raw),key,"COLLISION_REVIEW_SEPARATE"
        return "reurope-company:"+key,key,"CANONICAL_NUMBER"
    return "reurope-name:"+hid(norm(name)),"","NAME_FALLBACK"


def float_or_blank(s):
    try:return str(float(s)) if s not in (None,"") else ""
    except:return ""


def write_csv(path,rows,fields):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def main():
    with SRC.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    scoped=[r for r in rows if r.get("funded_year") in YEARS]
    collision_rows,blocked_keys=collision_plan(scoped)

    normalized=[]
    unresolved=[]
    for r in scoped:
        approved=r.get("approval_date","")
        funded=r.get("funded_date","")
        approval_year=approved[:4] if approved else ""
        funded_year=funded[:4] if funded else ""
        same=bool(approved and funded and approval_year==funded_year and approval_year in YEARS)
        offering_year=approval_year if same else ""
        year_status="BOUNDED_YEAR" if same else "YEAR_UNRESOLVED"
        cid,number_key,id_status=company_id(r.get("company_number",""),r.get("campaign_name",""),blocked_keys)
        rec={
            "round_id":round_id(r.get("candidate_url","")),
            "canonical_company_id":cid,
            "platform":"republic_europe",
            "campaign_name":r.get("campaign_name",""),
            "legal_company_number":r.get("company_number",""),
            "legal_company_number_canonical":number_key,
            "company_id_normalization_status":id_status,
            "campaign_url":r.get("candidate_url",""),
            "source_content_sha256":r.get("content_sha256",""),
            "status":"funded_completed",
            "offering_year":offering_year,
            "offering_year_status":year_status,
            "first_live_date":"",
            "first_live_date_status":"UNRESOLVED_EXACT",
            "first_live_lower_bound":approved if approved else "",
            "first_live_upper_bound":funded if funded else "",
            "completion_date":funded,
            "completion_date_basis":"platform_funded_date",
            "approval_date":approved,
            "funded_date":funded,
            "primary_field":r.get("primary_field","other_diversified"),
            "platform_sectors_raw":r.get("sectors_raw",""),
            "instrument_type":r.get("investment_type",""),
            "raised_currency":r.get("raised_currency",""),
            "raised_amount":float_or_blank(r.get("raised_amount","")),
            "target_currency":r.get("target_currency",""),
            "target_amount":float_or_blank(r.get("target_amount","")),
            "pre_money_currency":r.get("pre_money_currency",""),
            "pre_money_valuation":float_or_blank(r.get("pre_money_valuation","")),
            "investors":r.get("investors",""),
            "cohort_evidence_rule":"approval_to_funded_same_calendar_year" if same else "",
            "cohort_exclusion_reason":"" if same else ("missing_approval_date" if not approved else "approval_funding_cross_calendar_year"),
        }
        normalized.append(rec)
        if not same:
            unresolved.append(rec)

    fields=list(normalized[0].keys()) if normalized else []
    write_csv(OUT,normalized,fields)
    write_csv(UNRES,unresolved,fields)
    collision_fields=["canonical_number_key","raw_company_numbers","raw_variant_count","campaign_name_keys","shared_name_key","status","auto_merge"]
    write_csv(COLLISIONS,collision_rows,collision_fields)

    usable=[r for r in normalized if r["offering_year_status"]=="BOUNDED_YEAR"]
    ids=[r["round_id"] for r in normalized]
    companies=[r["canonical_company_id"] for r in normalized]
    counts={str(y):sum(1 for r in usable if r["offering_year"]==str(y)) for y in range(2020,2026)}
    field_counts={}
    for r in usable:
        field_counts[r["primary_field"]]=field_counts.get(r["primary_field"],0)+1
    merged=[r for r in collision_rows if r["status"]=="FORMATTING_EQUIVALENT_MERGED"]
    blocked=[r for r in collision_rows if r["status"]=="BLOCK_REVIEW"]
    summary={
        "platform":"republic_europe",
        "scope":"funded rounds with platform funded year 2020-2025",
        "normalized_rows":len(normalized),
        "unique_round_ids":len(set(ids)),
        "unique_companies":len(set(companies)),
        "repeat_company_round_rows":len(normalized)-len(set(companies)),
        "cohort_year_usable_rows":len(usable),
        "cohort_year_usable_share":len(usable)/len(normalized) if normalized else 0,
        "cohort_year_unresolved_rows":len(unresolved),
        "bounded_year_by_year":counts,
        "bounded_year_field_counts":dict(sorted(field_counts.items())),
        "company_id_rule":"Unicode NFKC; remove control/format and non-alphanumeric separators; uppercase; strip leading zeroes for all-digit comparison key; preserve raw value",
        "formatting_collision_groups_merged":len(merged),
        "collision_groups_blocked_for_review":len(blocked),
        "blocked_collision_keys":sorted(blocked_keys),
        "year_rule":"offering year assigned only when approval_date and funded_date are both platform-hosted and in the same calendar year; exact first_live_date remains null",
        "jev":{
            "bounded_same_year_probability":0.61,
            "exact_date_interval_bounds_probability":1.0,
            "design_reopen_yes_probability":0.16,
            "company_number_normalization_probability":0.95,
            "merge_with_audit_probability":0.98,
            "block_nonformat_collision_probability":1.0
        }
    }
    man={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT,UNRES,COLLISIONS]},
        "summary":summary
    }
    MAN.write_text(json.dumps(man,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(summary,sort_keys=True))

if __name__=="__main__":main()
