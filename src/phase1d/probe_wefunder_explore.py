#!/usr/bin/env python3
from __future__ import annotations

import csv, json, hashlib, re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/phase1d"
OUT.mkdir(parents=True,exist_ok=True)
RAW=OUT/"cp1_wefunder_explore_probe.json"
SUMMARY=OUT/"cp1_wefunder_explore_probe_summary.json"
ENUMCSV=OUT/"cp1_wefunder_us_listed_visible.csv"
ENUMSUMMARY=OUT/"cp1_wefunder_us_listed_visible_summary.json"

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

def now(): return datetime.now(timezone.utc).isoformat()

def summarize_body(body):
    s={"type":type(body).__name__}
    if isinstance(body,dict):
        s["keys"]=sorted(body.keys())
        for k in ["nbHits","page","nbPages","hitsPerPage","total","count","query","processingTimeMS"]:
            if k in body: s[k]=body[k]
        hits=body.get("hits") if isinstance(body.get("hits"),list) else None
        if hits is not None:
            s["hit_count"]=len(hits)
            if hits:
                s["first_hit_keys"]=sorted(hits[0].keys())
                s["first_hit"]=hits[0]
        # capture facet/filter/tag-like structures without assuming schema
        facetish={}
        for k,v in body.items():
            lk=k.lower()
            if any(x in lk for x in ["facet","filter","tag","status","index"]):
                facetish[k]=v
        s["facetish"]=facetish
    elif isinstance(body,list):
        s["length"]=len(body)
        if body and isinstance(body[0],dict):
            s["first_item_keys"]=sorted(body[0].keys())
    return s

def main():
    captures=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        context=browser.new_context(user_agent=UA,locale="en-US",viewport={"width":1440,"height":1000})
        page=context.new_page()

        def on_response(resp):
            if "/-/companies/explore" not in resp.url:
                return
            try:
                text=resp.text()
                try: body=json.loads(text)
                except Exception: body={"_raw_text":text[:200000]}
                captures.append({
                    "url":resp.url,
                    "status":resp.status,
                    "headers":{k:v for k,v in resp.headers.items() if k.lower() in {"content-type","etag","cache-control"}},
                    "body":body
                })
                print("CAPTURED",resp.status,resp.url,flush=True)
            except Exception as e:
                captures.append({"url":resp.url,"status":resp.status,"error":repr(e)})

        page.on("response",on_response)
        for url in ["https://wefunder.com/companies","https://wefunder.com/explore"]:
            try:
                resp=page.goto(url,wait_until="domcontentloaded",timeout=60000)
                page.wait_for_timeout(7000)
                print("PAGE",url,resp.status if resp else None,page.url,page.title(),flush=True)
            except Exception as e:
                print("PAGE_ERROR",url,repr(e),flush=True)
        # Probe historical-enumeration variants inside the same browser context.
        base="https://wefunder.com/-/companies/explore"
        variants=[
            ("baseline_live","Company_sorted_by_funding_closed_at_asc",["-eu","closing_soon","listed_campaign","status_fundraising","visible_by_non_accredited_investors"],True),
            ("asc_no_tags_cap","Company_sorted_by_funding_closed_at_asc",[],True),
            ("asc_listed_cap","Company_sorted_by_funding_closed_at_asc",["listed_campaign"],True),
            ("asc_us_listed_visible_cap","Company_sorted_by_funding_closed_at_asc",["-eu","listed_campaign","visible_by_non_accredited_investors"],True),
            ("asc_us_listed_visible_nocap","Company_sorted_by_funding_closed_at_asc",["-eu","listed_campaign","visible_by_non_accredited_investors"],False),
            ("promoted_us_listed_visible_cap","Company_sorted_by_profile_promoted_at_desc",["-eu","listed_campaign","visible_by_non_accredited_investors"],True),
            ("promoted_us_listed_visible_nocap","Company_sorted_by_profile_promoted_at_desc",["-eu","listed_campaign","visible_by_non_accredited_investors"],False),
        ]
        status_guesses=[
            "status_funded","status_closed","status_finished","status_completed",
            "status_successfully_funded","status_not_fundraising","past_campaign","funding_closed"
        ]
        for tag in status_guesses:
            variants.append(("asc_guess_"+tag,"Company_sorted_by_funding_closed_at_asc",["-eu","listed_campaign",tag,"visible_by_non_accredited_investors"],True))
        for label,index_name,tags,cap in variants:
            params={
                "index":index_name,
                "tagFilters":json.dumps(tags,separators=(",",":")),
                "page":"0","hitsPerPage":"5","filters":"",
                "vipOverride":"false","capCompanyCount":"true" if cap else "false"
            }
            try:
                rr=context.request.get(base,params=params,timeout=30000)
                txt=rr.text()
                try: body=json.loads(txt)
                except Exception: body={"_raw_text":txt[:200000]}
                captures.append({"url":rr.url,"status":rr.status,"probe_label":label,"body":body})
                print("PROBE",label,rr.status,body.get("nbHits") if isinstance(body,dict) else None,flush=True)
            except Exception as e:
                captures.append({"url":base,"status":None,"probe_label":label,"error":repr(e)})
                print("PROBE_ERROR",label,repr(e),flush=True)
        # Full enumeration probes for the historical listed subset.
        enum_variants=[
            ("enum_us_listed_visible","Company_sorted_by_funding_closed_at_asc",["-eu","listed_campaign","visible_by_non_accredited_investors"],False),
            ("enum_status_funded","Company_sorted_by_funding_closed_at_asc",["-eu","listed_campaign","status_funded","visible_by_non_accredited_investors"],False),
            ("enum_no_tags_nocap","Company_sorted_by_funding_closed_at_asc",[],False),
            ("enum_listed_only_nocap","Company_sorted_by_funding_closed_at_asc",["listed_campaign"],False),
        ]
        for label,index_name,tags,cap in enum_variants:
            params={
                "index":index_name,
                "tagFilters":json.dumps(tags,separators=(",",":")),
                "page":"0","hitsPerPage":"1000","filters":"",
                "vipOverride":"false","capCompanyCount":"true" if cap else "false"
            }
            try:
                rr=context.request.get(base,params=params,timeout=30000)
                txt=rr.text()
                try: body=json.loads(txt)
                except Exception: body={"_raw_text":txt[:500000]}
                captures.append({"url":rr.url,"status":rr.status,"probe_label":label,"body":body})
                print("ENUM",label,rr.status,body.get("nbHits") if isinstance(body,dict) else None,len(body.get("companies",[])) if isinstance(body,dict) else None,flush=True)
            except Exception as e:
                captures.append({"url":base,"status":None,"probe_label":label,"error":repr(e)})
                print("ENUM_ERROR",label,repr(e),flush=True)
        browser.close()

    # Deduplicate by URL + probe label, keeping last response.
    by_url={(c.get("url",""),c.get("probe_label","browser_capture")):c for c in captures if c.get("url")}
    captures=list(by_url.values())
    payload={
        "captured_at":now(),
        "capture_count":len(captures),
        "captures":captures
    }
    RAW.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    summary={
        "captured_at":payload["captured_at"],
        "capture_count":len(captures),
        "responses":[{"url":c.get("url"),"status":c.get("status"),"probe_label":c.get("probe_label","browser_capture"),"summary":summarize_body(c.get("body"))} for c in captures],
        "raw_sha256":hashlib.sha256(RAW.read_bytes()).hexdigest()
    }
    SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")

    # Compact historical listed-visible enumeration and completeness audit.
    enum_capture=next((x for x in captures if x.get("probe_label")=="enum_us_listed_visible"),None)
    companies=(enum_capture or {}).get("body",{}).get("companies",[]) if isinstance((enum_capture or {}).get("body"),dict) else []
    def iso(sec):
        try:
            sec=float(sec)
            if sec<=0:return ""
            return datetime.fromtimestamp(sec,timezone.utc).date().isoformat()
        except Exception:return ""
    fields=["id","objectID","name","legalName","slug","fundraiseHostName","fundingStartedDate","fundingPublicDate","fundingClosedDate","fundingClosedAtInPast","fundingAmount","totalRaisedThisCampaign","pastFunding","securityType","valuation","latestFundraiseCurrency","Tags"]
    with ENUMCSV.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
        for x in companies:
            w.writerow({
                "id":x.get("id",""),"objectID":x.get("objectID",""),"name":x.get("name",""),"legalName":x.get("legalName",""),"slug":x.get("slug",""),
                "fundraiseHostName":x.get("fundraiseHostName",""),"fundingStartedDate":iso(x.get("fundingStartedAtSeconds")),
                "fundingPublicDate":iso(x.get("fundingPublicAtSeconds")),"fundingClosedDate":iso(x.get("fundingClosedAtSeconds")),
                "fundingClosedAtInPast":x.get("fundingClosedAtInPast",""),"fundingAmount":x.get("fundingAmount",""),
                "totalRaisedThisCampaign":x.get("totalRaisedThisCampaign",""),"pastFunding":x.get("pastFunding",""),
                "securityType":x.get("securityType",""),"valuation":x.get("valuation",""),"latestFundraiseCurrency":x.get("latestFundraiseCurrency",""),
                "Tags":json.dumps(x.get("Tags",[]),separators=(",",":"))
            })

    def norm_name(s):
        s=re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()
        suffix={"inc","incorporated","llc","ltd","limited","corp","corporation","company","co","plc","pbc"}
        return " ".join(x for x in s.split() if x not in suffix)
    known=[]
    known_path=ROOT/"data/cohort_manifest.csv"
    if known_path.exists():
        with known_path.open(newline="",encoding="utf-8") as fh:
            known=list(csv.DictReader(fh))
    enum_names={}
    for x in companies:
        for raw in [x.get("name"),x.get("legalName")]:
            n=norm_name(raw)
            if n: enum_names.setdefault(n,[]).append(x.get("slug") or x.get("name"))
    matched=[];unmatched=[]
    for r in known:
        n=norm_name(r.get("issuer_name"))
        if n in enum_names: matched.append({"issuer_name":r.get("issuer_name"),"matches":enum_names[n]})
        else: unmatched.append(r.get("issuer_name"))

    def year_counts(field):
        d={}
        for x in companies:
            y=(field(x) or "")[:4]
            if y:d[y]=d.get(y,0)+1
        return dict(sorted(d.items()))
    enum_summary={
        "nbHits":(enum_capture or {}).get("body",{}).get("nbHits"),
        "company_count":len(companies),
        "fundraise_host_counts":{},
        "closed_year_counts":year_counts(lambda x:iso(x.get("fundingClosedAtSeconds"))),
        "started_year_counts":year_counts(lambda x:iso(x.get("fundingStartedAtSeconds"))),
        "public_year_counts":year_counts(lambda x:iso(x.get("fundingPublicAtSeconds"))),
        "status_funded_count":sum(1 for x in companies if "status_funded" in (x.get("Tags") or [])),
        "funded_tag_count":sum(1 for x in companies if "funded" in (x.get("Tags") or [])),
        "has_non_draft_form_c_count":sum(1 for x in companies if "has_non_draft_form_c" in (x.get("Tags") or [])),
        "closed_in_past_count":sum(1 for x in companies if x.get("fundingClosedAtInPast")),
        "positive_total_raised_count":sum(1 for x in companies if (x.get("totalRaisedThisCampaign") or 0)>0),
        "phase1b_2020_known_denominator":len(known),
        "phase1b_name_matches":len(matched),
        "phase1b_name_match_share":len(matched)/len(known) if known else None,
        "phase1b_matches":matched,
        "phase1b_unmatched":unmatched,
        "csv_sha256":hashlib.sha256(ENUMCSV.read_bytes()).hexdigest()
    }
    for x in companies:
        h=x.get("fundraiseHostName") or "MISSING"
        enum_summary["fundraise_host_counts"][h]=enum_summary["fundraise_host_counts"].get(h,0)+1
    ENUMSUMMARY.write_text(json.dumps(enum_summary,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"capture_count":len(captures),"enum_summary":enum_summary},sort_keys=True))

if __name__=="__main__":
    main()
