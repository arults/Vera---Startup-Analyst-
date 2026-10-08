#!/usr/bin/env python3
from __future__ import annotations

import csv, hashlib, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as cffi_requests
except Exception:
    cffi_requests=None

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/phase1d"
OUT.mkdir(parents=True,exist_ok=True)

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
SECTORS=["software","saas","biotech","healthcare","fintech","consumer","marketplace","hardware","climate","energy","food","gaming","mobility","real estate","hospitality","robotics"]
YEARS=[2020,2021,2022,2023,2024,2025]

PLATFORMS={
 "wefunder":{
   "host_suffix":"wefunder.com",
   "base_query":'site:wefunder.com "This offering is hosted by Wefunder Portal LLC"',
   "reject":r"^/(explore|articles|blog|help|faq|about|legal|terms|privacy|news|top-investors|updates|case-studies|community-round|investor-warmup|funds|agents|developers|settings|login|signup)(/|$)",
   "accept":r"^/[^/]+/?$"
 },
 "startengine":{
   "host_suffix":"startengine.com",
   "base_query":'site:startengine.com/offering "Offering Closed"',
   "reject":r"^/(blog|help|about|explore|offering-directory|terms|privacy|contact)(/|$)",
   "accept":r"^/offering/[^/]+/?$"
 },
 "crowdcube":{
   "host_suffix":"crowdcube.com",
   "base_query":'site:crowdcube.com "Crowdcube" "funded"',
   "reject":r"^/(hc|help|blog|careers|about|terms|privacy|contact|cdn|files)(/|$)",
   "accept":r"^/.+"
 },
 "republic_us":{
   "host_suffix":"republic.com",
   "base_query":'site:republic.com "Successfully funded and closed on"',
   "reject":r"^/(companies/portfolio|investment-opportunities|insights|academy|events|help|about|terms|privacy|login|register|app|wallet|capital|ventures|trading|funded-ventures|reg-cf-offerings|2024|2025)(/|$)",
   "accept":r"^/[^/]+/?$"
 },
}

def now(): return datetime.now(timezone.utc).isoformat()

def fetch(url):
    headers={"User-Agent":UA,"Accept-Language":"en-US,en;q=0.9"}
    if cffi_requests:
        try:
            r=cffi_requests.get(url,headers=headers,timeout=25,impersonate="chrome")
            return r.status_code,str(r.url),r.text
        except Exception:
            pass
    try:
        r=requests.get(url,headers=headers,timeout=25)
        return r.status_code,r.url,r.text
    except Exception as e:
        return None,url,""

def unwrap(href):
    if not href: return ""
    if href.startswith("/ck/a"):
        # Bing redirect can't be resolved reliably without clicking; ignore.
        return ""
    if "duckduckgo.com/l/?" in href:
        q=parse_qs(urlparse(href).query)
        if "uddg" in q: return unquote(q["uddg"][0])
    return href

def is_platform_url(platform,u):
    if not u.startswith("http"): return False
    p=urlparse(u); cfg=PLATFORMS[platform]
    if not p.netloc.endswith(cfg["host_suffix"]): return False
    path=p.path or "/"
    if re.search(cfg["reject"],path,re.I): return False
    return bool(re.search(cfg["accept"],path,re.I))

def bing(query,first=1):
    url="https://www.bing.com/search?q="+quote_plus(query)+f"&count=50&first={first}&setlang=en-US"
    status,final,html=fetch(url); out=[]
    if status==200 and html:
        soup=BeautifulSoup(html,"html.parser")
        for a in soup.select("li.b_algo h2 a[href], a[href]"):
            href=unwrap(a.get("href",""))
            if href.startswith("http"): out.append(href.split("#")[0])
    return status,list(dict.fromkeys(out))

def ddg(query):
    url="https://html.duckduckgo.com/html/?q="+quote_plus(query)
    status,final,html=fetch(url); out=[]
    if status==200 and html:
        soup=BeautifulSoup(html,"html.parser")
        for a in soup.select("a.result__a[href]"):
            href=unwrap(a.get("href",""))
            if href.startswith("http"): out.append(href.split("#")[0])
    return status,list(dict.fromkeys(out))

def queries_for(platform):
    base=PLATFORMS[platform]["base_query"]
    qs=[base]
    for y in YEARS:
        qs.append(f"{base} {y}")
        for s in SECTORS:
            qs.append(f'{base} {y} "{s}"')
    return qs

def main():
    captured=now(); rows={}; diagnostics={"captured_at":captured,"method":"search-discovery-v1","platforms":{}}
    for platform in PLATFORMS:
        qstats=[]; purls=set()
        for qi,q in enumerate(queries_for(platform)):
            pages=[1,11,21] if any(str(y) in q for y in YEARS) and q.count('"')<=2 else [1]
            found=set(); statuses=[]
            for first in pages:
                st,urls=bing(q,first); statuses.append({"provider":"bing","first":first,"status":st,"n":len(urls)})
                found.update(urls)
            if len(found)<3:
                st,urls=ddg(q); statuses.append({"provider":"ddg","status":st,"n":len(urls)})
                found.update(urls)
            accepted=[u for u in found if is_platform_url(platform,u)]
            for u in accepted:
                purls.add(u)
                rows[(platform,u)]={
                    "platform":platform,"url":u,"discovery_source":"search_engine_only",
                    "evidence_status":"UNVERIFIED_DISCOVERY","captured_at":captured
                }
            qstats.append({"query":q,"accepted":len(accepted),"raw":len(found),"statuses":statuses})
            if qi and qi%25==0:
                print(platform,"queries",qi,"unique",len(purls),flush=True)
            time.sleep(0.08)
        diagnostics["platforms"][platform]={"query_count":len(qstats),"unique_urls":len(purls),"query_stats":qstats}
        print("SEARCH",platform,len(purls),flush=True)

    outrows=sorted(rows.values(),key=lambda x:(x["platform"],x["url"]))
    with (OUT/"cp1_search_candidates.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["platform","url","discovery_source","evidence_status","captured_at"])
        w.writeheader(); w.writerows(outrows)
    (OUT/"cp1_search_diagnostics.json").write_text(json.dumps(diagnostics,indent=2,sort_keys=True)+"\n")
    manifest={
      "captured_at":captured,"rows":len(outrows),"method":"search-discovery-v1",
      "files":{
        "cp1_search_candidates.csv":hashlib.sha256((OUT/"cp1_search_candidates.csv").read_bytes()).hexdigest(),
        "cp1_search_diagnostics.json":hashlib.sha256((OUT/"cp1_search_diagnostics.json").read_bytes()).hexdigest()
      }
    }
    (OUT/"cp1_search_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("TOTAL_SEARCH_URLS",len(outrows))

if __name__=="__main__": main()
