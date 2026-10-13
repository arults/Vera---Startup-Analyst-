#!/usr/bin/env python3
from __future__ import annotations

import csv, hashlib, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/phase1d"
CAND=DATA/"cp3_republic_europe_business_candidates.csv"
ROUNDS=DATA/"cp2_republic_europe_rounds_normalized.csv"
RAW=DATA/"cp3_republic_europe_business_pages_raw.csv"
OBS=DATA/"cp3_republic_europe_business_observations.csv"
EVENTS=DATA/"cp3_republic_europe_event_candidates.csv"
MAN=DATA/"cp3_republic_europe_business_manifest.json"

UA="Mozilla/5.0 (compatible; VeraStartupResearch/0.6; +https://github.com/arults/Vera---Startup-Analyst-)"

EVENT_PATTERNS={
    "acquisition":re.compile(r"\b(acquired|acquisition|wholly owned subsidiary|takeover)\b",re.I),
    "closure":re.compile(r"\b(administration|liquidat(?:e|ed|ion|ing)|dissolv(?:e|ed|ution)|ceased trading|ceased operations|wound up|bankrupt(?:cy)?)\b",re.I),
    "listing":re.compile(r"\b(ipo|initial public offering|listed on|direct listing)\b",re.I),
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def norm(s):
    return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()

def sha(s):
    return hashlib.sha256((s or "").encode("utf-8","ignore")).hexdigest()

def company_number_candidates(html,text):
    vals=[]
    pats=[
        r'company[_\- ]?number["\']?\s*[:=]\s*["\']?([A-Z]{0,3}\d{5,10})',
        r'Company number\s*:?\s*([A-Z]{0,3}\d{5,10})',
        r'companyNumber["\']?\s*[:=]\s*["\']([^"\']+)',
    ]
    for pat in pats:
        for m in re.finditer(pat,html,re.I):
            v=re.sub(r"\s+","",m.group(1)).upper()
            if v and v not in vals: vals.append(v)
        for m in re.finditer(pat,text,re.I):
            v=re.sub(r"\s+","",m.group(1)).upper()
            if v and v not in vals: vals.append(v)
    return vals[:10]

def event_excerpts(text):
    out=[]
    flat=re.sub(r"\s+"," ",text)
    for et,pat in EVENT_PATTERNS.items():
        for m in pat.finditer(flat):
            lo=max(0,m.start()-180); hi=min(len(flat),m.end()+260)
            excerpt=flat[lo:hi].strip()
            out.append((et,m.group(0),excerpt))
            if len([x for x in out if x[0]==et])>=5: break
    return out

def fetch_one(url):
    try:
        r=requests.get(url,headers={"User-Agent":UA,"Accept-Language":"en-GB,en;q=0.9"},timeout=25,allow_redirects=True)
        html=r.text
    except Exception as e:
        return {"url":url,"http_status":"","fetch_ok":False,"error":repr(e)}
    if r.status_code!=200:
        return {"url":url,"final_url":r.url,"http_status":r.status_code,"fetch_ok":False,"error":"http_status"}
    soup=BeautifulSoup(html,"html.parser")
    text="\n".join(x.strip() for x in soup.stripped_strings)
    h1=soup.find("h1")
    name=h1.get_text(" ",strip=True) if h1 else ""
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    if not name and title: name=title.split("|")[0].strip()

    eligibility=""
    m=re.search(r"Eligibility status\s+(Not eligible|Eligible)\b",text,re.I)
    if m: eligibility="NOT_ELIGIBLE" if m.group(1).lower().startswith("not") else "ELIGIBLE"

    valuation_change=""; valuation_amount=""
    m=re.search(r"Indicative valuation\s+([+\-]?[0-9.]+%)?\s*([£€$][0-9][0-9,.]*\s*[KkMmBb]?)?",text,re.I)
    if m:
        valuation_change=(m.group(1) or "").strip()
        valuation_amount=(m.group(2) or "").strip()

    incorporation=""
    m=re.search(r"Incorporation date\s+([^\n]{3,40})",text,re.I)
    if m: incorporation=m.group(1).strip()

    numbers=company_number_candidates(html,text)
    evs=event_excerpts(text)
    return {
        "url":url,"final_url":r.url,"http_status":r.status_code,"fetch_ok":True,"error":"",
        "business_name":name,"eligibility":eligibility,"indicative_change":valuation_change,
        "indicative_valuation":valuation_amount,"incorporation_date":incorporation,
        "company_numbers_json":json.dumps(numbers,separators=(",",":")),
        "event_count":len(evs),"events_json":json.dumps(evs,separators=(",",":")),
        "content_sha256":sha(html)
    }

def read_rows():
    with ROUNDS.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    by_company={r["canonical_company_id"]:r for r in rows}
    by_number={}
    by_name={}
    for r in rows:
        num=(r.get("legal_company_number") or "").replace(" ","").upper()
        if num: by_number.setdefault(num,set()).add(r["canonical_company_id"])
        n=norm(r.get("campaign_name",""))
        if n: by_name.setdefault(n,set()).add(r["canonical_company_id"])
    return rows,by_company,by_number,by_name

def match_business(rec,by_number,by_name):
    nums=json.loads(rec.get("company_numbers_json") or "[]")
    strong=set()
    for n in nums: strong |= by_number.get(n,set())
    if len(strong)==1:
        return next(iter(strong)),"COMPANY_NUMBER"
    n=norm(rec.get("business_name",""))
    names=by_name.get(n,set()) if n else set()
    if len(names)==1:
        return next(iter(names)),"EXACT_NORMALIZED_NAME"
    return "","UNMATCHED"

def main():
    if not CAND.exists(): raise SystemExit("business candidate file missing")
    urls=[]
    with CAND.open(newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            u=(r.get("url") or "").split("#")[0].split("?")[0].rstrip("/")
            if u and "/businesses/" in urlparse(u).path: urls.append(u)
    urls=sorted(set(urls))
    capture=now_iso()
    print("BUSINESS_CANDIDATES",len(urls),flush=True)
    results=[]
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs={ex.submit(fetch_one,u):u for u in urls}
        for i,fut in enumerate(as_completed(futs),1):
            results.append(fut.result())
            if i%100==0: print("FETCHED",i,flush=True)
    results.sort(key=lambda r:r.get("url",""))

    rows,by_company,by_number,by_name=read_rows()
    observations=[]; event_rows=[]
    for rec in results:
        cid,basis=match_business(rec,by_number,by_name) if rec.get("fetch_ok") else ("","FETCH_FAILED")
        rec["canonical_company_id"]=cid
        rec["match_basis"]=basis
        rec["captured_at"]=capture
        if cid:
            observations.append({
                "canonical_company_id":cid,
                "business_name":rec.get("business_name",""),
                "business_url":rec.get("url",""),
                "captured_at":capture,
                "eligibility":rec.get("eligibility",""),
                "positive_operating_evidence":str(rec.get("eligibility")=="ELIGIBLE").lower(),
                "evidence_confidence":"medium" if rec.get("eligibility")=="ELIGIBLE" else "",
                "evidence_basis":"secondary_market_current_eligible" if rec.get("eligibility")=="ELIGIBLE" else "secondary_market_status_neutral",
                "content_sha256":rec.get("content_sha256",""),
                "match_basis":basis,
            })
            try: evs=json.loads(rec.get("events_json") or "[]")
            except Exception: evs=[]
            for et,trigger,excerpt in evs:
                event_rows.append({
                    "canonical_company_id":cid,"business_name":rec.get("business_name",""),
                    "business_url":rec.get("url",""),"captured_at":capture,
                    "event_type_candidate":et,"trigger":trigger,"excerpt":excerpt,
                    "review_required":"true","content_sha256":rec.get("content_sha256","")
                })

    raw_fields=sorted(set().union(*(r.keys() for r in results))) if results else ["url"]
    with RAW.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=raw_fields,extrasaction="ignore");w.writeheader();w.writerows(results)
    obs_fields=["canonical_company_id","business_name","business_url","captured_at","eligibility","positive_operating_evidence","evidence_confidence","evidence_basis","content_sha256","match_basis"]
    with OBS.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=obs_fields);w.writeheader();w.writerows(observations)
    ev_fields=["canonical_company_id","business_name","business_url","captured_at","event_type_candidate","trigger","excerpt","review_required","content_sha256"]
    with EVENTS.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=ev_fields);w.writeheader();w.writerows(event_rows)

    matched_ids={o["canonical_company_id"] for o in observations}
    eligible_ids={o["canonical_company_id"] for o in observations if o["positive_operating_evidence"]=="true"}
    usable_ids={r["canonical_company_id"] for r in rows if r.get("offering_year_status")=="BOUNDED_YEAR"}
    summary={
        "candidate_business_pages":len(urls),
        "successful_fetches":sum(1 for r in results if r.get("fetch_ok")),
        "matched_business_pages":sum(1 for r in results if r.get("canonical_company_id")),
        "matched_unique_companies":len(matched_ids),
        "eligible_business_pages":sum(1 for r in results if r.get("eligibility")=="ELIGIBLE"),
        "not_eligible_business_pages":sum(1 for r in results if r.get("eligibility")=="NOT_ELIGIBLE"),
        "eligible_matched_unique_companies":len(eligible_ids),
        "usable_cohort_unique_companies":len(usable_ids),
        "usable_companies_with_current_eligible_evidence":len(usable_ids & eligible_ids),
        "usable_current_eligible_coverage":len(usable_ids & eligible_ids)/len(usable_ids) if usable_ids else 0,
        "event_review_candidates":len(event_rows),
        "rule":{
            "eligible":"medium-confidence positive operating evidence at capture date",
            "not_eligible":"neutral, not closure and does not extend follow-up",
            "valuation_only":"does not extend follow-up"
        }
    }
    MAN.write_text(json.dumps({
        "generated_at":capture,
        "files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [RAW,OBS,EVENTS]},
        "summary":summary
    },indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,sort_keys=True))

if __name__=="__main__":
    main()
