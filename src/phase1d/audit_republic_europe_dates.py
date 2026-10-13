#!/usr/bin/env python3
from __future__ import annotations

import csv, hashlib, json
from datetime import date, datetime
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/phase1d"
SRC=DATA/"cp2_republic_europe_rounds_raw.csv"
OUT=DATA/"cp2_republic_europe_date_audit.json"
SAMPLE=DATA/"cp2_republic_europe_date_audit_rows.csv"

def d(s):
    return date.fromisoformat(s) if s else None

def main():
    with SRC.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    scoped=[r for r in rows if r.get("funded_year") in {"2020","2021","2022","2023","2024","2025"}]
    aud=[]
    lags=[]
    cross=0
    negative=0
    approval_known=0
    same_year=0
    for r in scoped:
        funded=d(r.get("funded_date",""))
        approved=d(r.get("approval_date",""))
        if approved:
            approval_known+=1
            if funded:
                lag=(funded-approved).days
                lags.append(lag)
                if lag<0: negative+=1
                if approved.year==funded.year: same_year+=1
                else: cross+=1
        aud.append({
            "campaign_name":r.get("campaign_name",""),
            "candidate_url":r.get("candidate_url",""),
            "company_number":r.get("company_number",""),
            "funded_date":r.get("funded_date",""),
            "funded_year":r.get("funded_year",""),
            "approval_date":r.get("approval_date",""),
            "approval_year":(r.get("approval_date","")[:4] if r.get("approval_date") else ""),
            "lag_days":((funded-approved).days if funded and approved else ""),
            "same_calendar_year":(funded.year==approved.year if funded and approved else ""),
        })
    lags_sorted=sorted(lags)
    def quantile(q):
        if not lags_sorted:return None
        idx=round((len(lags_sorted)-1)*q)
        return lags_sorted[idx]
    summary={
        "platform":"republic_europe",
        "scope_funded_years":"2020-2025",
        "n_scoped":len(scoped),
        "approval_date_known":approval_known,
        "approval_date_coverage":approval_known/len(scoped) if scoped else 0,
        "funded_and_approval_lag_n":len(lags),
        "negative_lag_count":negative,
        "same_calendar_year_count":same_year,
        "same_calendar_year_share":same_year/len(lags) if lags else 0,
        "cross_calendar_year_count":cross,
        "cross_calendar_year_share":cross/len(lags) if lags else 0,
        "lag_days_min":min(lags) if lags else None,
        "lag_days_p10":quantile(.10),
        "lag_days_p25":quantile(.25),
        "lag_days_median":median(lags) if lags else None,
        "lag_days_p75":quantile(.75),
        "lag_days_p90":quantile(.90),
        "lag_days_max":max(lags) if lags else None,
        "interpretation":"Approval date is platform-hosted pre-funding timing evidence; audit is for cohort-year proxy suitability only and does not automatically change the frozen first-live rule."
    }
    OUT.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    with SAMPLE.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(aud[0].keys()) if aud else ["campaign_name"])
        w.writeheader();w.writerows(aud)
    manifest={
        "generated_at":datetime.utcnow().isoformat()+"Z",
        "files":{
            OUT.name:hashlib.sha256(OUT.read_bytes()).hexdigest(),
            SAMPLE.name:hashlib.sha256(SAMPLE.read_bytes()).hexdigest(),
        },
        "summary":summary
    }
    (DATA/"cp2_republic_europe_date_audit_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,sort_keys=True))

if __name__=="__main__":main()
