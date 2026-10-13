#!/usr/bin/env python3
from __future__ import annotations

import json, hashlib, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/phase1d"
OUT.mkdir(parents=True,exist_ok=True)
RAW=OUT/"cp1_republic_us_probe.json"
SUMMARY=OUT/"cp1_republic_us_probe_summary.json"

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

SEEDS=[
  "https://republic.com/companies/portfolio",
  "https://republic.com/funded-ventures",
  "https://republic.com/reg-cf-offerings",
  "https://republic.com/investment-opportunities"
]
REJECT_TOP={
 "login","register","signup","about","learn","blog","jobs","raise","invest","terms","privacy","contact",
 "companies","investment-opportunities","ventures","trading","sharedrops","launchpad","tokenization","infrastructure",
 "advisory","note","wallet","help","risks","accessibility","insights","events","security","reg-cf-offerings","funded-ventures"
}

def now(): return datetime.now(timezone.utc).isoformat()

def is_candidate(url):
    try:
        p=urlparse(url)
        if p.netloc not in {"republic.com","www.republic.com"}: return False
        parts=[x for x in p.path.split("/") if x]
        if not parts:return False
        if parts[0] in REJECT_TOP:return False
        if len(parts)==1:return True
        if len(parts)>=2 and parts[0]=="companies" and parts[1] not in {"portfolio"}:return True
        return False
    except:return False

def summarize_json(body):
    out={"type":type(body).__name__}
    if isinstance(body,dict):
        out["keys"]=sorted(body.keys())[:200]
        for k in ["total","count","page","pages","current_page","total_pages","next_page","hasNextPage"]:
            if k in body:out[k]=body[k]
        # shallow arrays and their first item keys
        arrays={}
        for k,v in body.items():
            if isinstance(v,list):
                arrays[k]={"length":len(v),"first_keys":sorted(v[0].keys())[:100] if v and isinstance(v[0],dict) else []}
            elif isinstance(v,dict):
                for kk,vv in v.items():
                    if isinstance(vv,list):
                        arrays[f"{k}.{kk}"]={"length":len(vv),"first_keys":sorted(vv[0].keys())[:100] if vv and isinstance(vv[0],dict) else []}
        out["arrays"]=arrays
    elif isinstance(body,list):
        out["length"]=len(body)
        out["first_keys"]=sorted(body[0].keys())[:100] if body and isinstance(body[0],dict) else []
    return out

def main():
    captured=now()
    responses=[]
    pages=[]
    candidate_links=set()
    resources=set()

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        ctx=browser.new_context(user_agent=UA,locale="en-US",viewport={"width":1440,"height":1200})
        page=ctx.new_page()

        def on_response(resp):
            u=resp.url
            if urlparse(u).netloc not in {"republic.com","www.republic.com"}:return
            ct=(resp.headers.get("content-type") or "").lower()
            if "json" not in ct and "graphql" not in u.lower() and "/api/" not in u.lower():
                return
            resources.add(u)
            try:
                txt=resp.text()
                if len(txt)>2_000_000:
                    responses.append({"url":u,"status":resp.status,"content_type":ct,"truncated":True,"length":len(txt)})
                    return
                try: body=json.loads(txt)
                except Exception:
                    body={"_raw_text":txt[:200000]}
                responses.append({"url":u,"status":resp.status,"content_type":ct,"body":body})
                print("JSON",resp.status,u,flush=True)
            except Exception as e:
                responses.append({"url":u,"status":resp.status,"content_type":ct,"error":repr(e)})

        page.on("response",on_response)

        for seed in SEEDS:
            try:
                resp=page.goto(seed,wait_until="domcontentloaded",timeout=60000)
                page.wait_for_timeout(2500)
                # scroll repeatedly to trigger lazy pagination
                previous=0
                stable=0
                for _ in range(30):
                    hrefs=page.locator("a").evaluate_all("(els)=>els.map(e=>e.href).filter(Boolean)")
                    for u in hrefs:
                        if is_candidate(u):candidate_links.add(u.split("#")[0].split("?")[0].rstrip("/"))
                    current=len(hrefs)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(800)
                    if current==previous:stable+=1
                    else:stable=0
                    previous=current
                    if stable>=4:break
                html=page.content()
                scripts=page.locator("script").evaluate_all("(els)=>els.map(e=>({type:e.type||'',id:e.id||'',text:(e.textContent||'').slice(0,500000)}))")
                next_data=[]
                for s in scripts:
                    t=s.get("text") or ""
                    if s.get("id")=="__NEXT_DATA__" or '"pageProps"' in t or '"apolloState"' in t or '"__APOLLO_STATE__"' in t:
                        try: parsed=json.loads(t); next_data.append(parsed)
                        except Exception: next_data.append({"raw_prefix":t[:100000]})
                pages.append({
                    "seed":seed,
                    "status":resp.status if resp else None,
                    "final_url":page.url,
                    "title":page.title(),
                    "html_sha256":hashlib.sha256(html.encode()).hexdigest(),
                    "candidate_links_count":len(candidate_links),
                    "candidate_links_sample":sorted(candidate_links)[:50],
                    "structured_scripts":[summarize_json(x) for x in next_data[:20]],
                    "html_prefix":re.sub(r"\s+"," ",page.locator("body").inner_text()[:20000])
                })
                print("PAGE",seed,resp.status if resp else None,"candidates",len(candidate_links),flush=True)
            except Exception as e:
                pages.append({"seed":seed,"error":repr(e)})
                print("PAGE_ERROR",seed,repr(e),flush=True)
        browser.close()

    # Deduplicate response URLs keeping largest serialized body.
    dedup={}
    for x in responses:
        k=x.get("url","")
        size=len(json.dumps(x.get("body",{}),ensure_ascii=False))
        if k not in dedup or size>dedup[k][0]:dedup[k]=(size,x)
    responses=[v[1] for v in dedup.values()]

    raw={
      "captured_at":captured,
      "pages":pages,
      "candidate_links":sorted(candidate_links),
      "resources":sorted(resources),
      "responses":responses
    }
    RAW.write_text(json.dumps(raw,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    summary={
      "captured_at":captured,
      "candidate_link_count":len(candidate_links),
      "candidate_link_sample":sorted(candidate_links)[:100],
      "resource_count":len(resources),
      "resources":sorted(resources)[:200],
      "page_summaries":[{k:v for k,v in x.items() if k not in {"html_prefix","structured_scripts"}} for x in pages],
      "json_summaries":[{"url":x.get("url"),"status":x.get("status"),"summary":summarize_json(x.get("body"))} for x in responses],
      "raw_sha256":hashlib.sha256(RAW.read_bytes()).hexdigest()
    }
    SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"candidate_link_count":len(candidate_links),"resource_count":len(resources),"json_summaries":summary["json_summaries"]},sort_keys=True))

if __name__=="__main__":
    main()
