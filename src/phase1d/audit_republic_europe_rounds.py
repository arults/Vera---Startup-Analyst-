#!/usr/bin/env python3
from __future__ import annotations
import csv, json, hashlib
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/phase1d"
SRC=DATA/"cp2_republic_europe_rounds_normalized.csv"
OUT=DATA/"cp2_republic_europe_repeat_round_audit.json"
PAIRS=DATA/"cp2_republic_europe_same_round_candidates.csv"
EDGES=DATA/"cp2_republic_europe_sequence_edges.csv"
MAN=DATA/"cp2_republic_europe_graph_audit_manifest.json"

def d(s):
    return date.fromisoformat(s) if s else None

def f(s):
    try:return float(s) if s not in (None,"") else None
    except:return None

def overlap(a0,a1,b0,b1):
    if not all([a0,a1,b0,b1]): return False
    return max(a0,b0) <= min(a1,b1)

def same_terms(a,b):
    if (a.get("instrument_type") or "").strip().lower() != (b.get("instrument_type") or "").strip().lower():
        return False
    av,bv=f(a.get("pre_money_valuation")),f(b.get("pre_money_valuation"))
    ac,bc=(a.get("pre_money_currency") or ""),(b.get("pre_money_currency") or "")
    if av is None or bv is None or ac != bc:
        return False
    denom=max(abs(av),abs(bv),1.0)
    return abs(av-bv)/denom <= 0.01

def main():
    with SRC.open(newline="",encoding="utf-8") as fh:
        rows=list(csv.DictReader(fh))
    by=defaultdict(list)
    for r in rows:
        by[r["canonical_company_id"]].append(r)

    dist=Counter(len(v) for v in by.values())
    repeated={k:v for k,v in by.items() if len(v)>1}
    candidates=[]
    edges=[]

    for cid,rs in repeated.items():
        rs=sorted(rs,key=lambda r:(r.get("completion_date",""),r.get("round_id","")))
        for i in range(len(rs)):
            for j in range(i+1,len(rs)):
                a,b=rs[i],rs[j]
                a0=d(a.get("first_live_lower_bound","")); a1=d(a.get("first_live_upper_bound",""))
                b0=d(b.get("first_live_lower_bound","")); b1=d(b.get("first_live_upper_bound",""))
                iv=overlap(a0,a1,b0,b1)
                terms=same_terms(a,b)
                same_completion=bool(a.get("completion_date") and a.get("completion_date")==b.get("completion_date"))
                same_raised=bool(a.get("raised_amount") and a.get("raised_amount")==b.get("raised_amount") and a.get("raised_currency")==b.get("raised_currency"))
                score=sum([iv,terms,same_completion,same_raised])
                if score>=2:
                    candidates.append({
                        "canonical_company_id":cid,
                        "round_a":a["round_id"],"round_b":b["round_id"],
                        "campaign_a":a["campaign_name"],"campaign_b":b["campaign_name"],
                        "completion_a":a.get("completion_date",""),"completion_b":b.get("completion_date",""),
                        "approval_a":a.get("approval_date",""),"approval_b":b.get("approval_date",""),
                        "interval_overlap":iv,"same_terms":terms,
                        "same_completion":same_completion,"same_raised":same_raised,
                        "evidence_score":score,"review_required":True
                    })
        for a,b in zip(rs,rs[1:]):
            ad=d(a.get("completion_date","")); bd=d(b.get("completion_date",""))
            edges.append({
                "canonical_company_id":cid,
                "source_round_id":a["round_id"],
                "destination_round_id":b["round_id"],
                "source_completion":a.get("completion_date",""),
                "destination_completion":b.get("completion_date",""),
                "days_between":((bd-ad).days if ad and bd else ""),
                "source_year":a.get("offering_year",""),
                "destination_year":b.get("offering_year",""),
                "edge_type":"NEXT_ROUND_CANDIDATE"
            })

    pf=list(candidates[0].keys()) if candidates else ["canonical_company_id"]
    with PAIRS.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=pf);w.writeheader();w.writerows(candidates)
    ef=list(edges[0].keys()) if edges else ["canonical_company_id"]
    with EDGES.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=ef);w.writeheader();w.writerows(edges)

    summary={
        "platform":"republic_europe",
        "normalized_rounds":len(rows),
        "unique_companies":len(by),
        "companies_with_multiple_rounds":len(repeated),
        "repeat_round_rows":sum(len(v) for v in repeated.values()),
        "rounds_per_company_distribution":{str(k):v for k,v in sorted(dist.items())},
        "sequence_edge_candidates":len(edges),
        "same_round_review_candidates":len(candidates),
        "same_round_score_distribution":dict(Counter(str(x["evidence_score"]) for x in candidates)),
        "policy":"Audit only; no candidate auto-collapsed before Jev/Verifier decision."
    }
    OUT.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    MAN.write_text(json.dumps({
        "generated_at":datetime.utcnow().isoformat()+"Z",
        "files":{
            OUT.name:hashlib.sha256(OUT.read_bytes()).hexdigest(),
            PAIRS.name:hashlib.sha256(PAIRS.read_bytes()).hexdigest(),
            EDGES.name:hashlib.sha256(EDGES.read_bytes()).hexdigest()
        },
        "summary":summary
    },indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,sort_keys=True))

if __name__=="__main__":
    main()
