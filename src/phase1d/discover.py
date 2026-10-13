#!/usr/bin/env python3
from __future__ import annotations

import csv, gzip, hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

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
S=requests.Session()
S.headers.update({"User-Agent":UA,"Accept-Language":"en-US,en;q=0.9"})

PLATFORMS={
  "wefunder":{
    "hosts":["wefunder.com","www.wefunder.com"],
    "base":"https://wefunder.com",
    "seeds":["/","/explore","/companies","/funded"],
    "patterns":[r"^/[^/?#]+/?$",r"^/companies/[^/?#]+/?$"],
    "reject":[r"^/(login|signup|about|faq|learn|blog|jobs|raise|invest|terms|privacy|contact|updates|reviews|sitemap|llms)(/|$)"]
  },
  "startengine":{
    "hosts":["startengine.com","www.startengine.com"],
    "base":"https://www.startengine.com",
    "seeds":["/","/explore","/explore/offerings","/offering"],
    "patterns":[r"^/offering/[^/?#]+/?$",r"^/[^/?#]+/?$"],
    "reject":[r"^/(login|signup|about|learn|blog|jobs|raise|invest|terms|privacy|contact|explore|offering$)(/|$)"]
  },
  "republic_us":{
    "hosts":["republic.com","www.republic.com"],
    "base":"https://republic.com",
    "seeds":["/","/investment-opportunities","/companies/portfolio","/funded-ventures","/reg-cf-offerings"],
    "patterns":[r"^/[^/?#]+/?$",r"^/companies/[^/?#]+/?$"],
    "reject":[r"^/(login|register|signup|about|learn|blog|jobs|raise|invest|terms|privacy|contact|companies/portfolio|investment-opportunities|ventures|trading|sharedrops|launchpad|tokenization|infrastructure|advisory|note|wallet|help|risks|accessibility|insights|events|security|reg-cf-offerings|funded-ventures)(/|$)"]
  },
  "crowdcube":{
    "hosts":["crowdcube.com","www.crowdcube.com"],
    "base":"https://www.crowdcube.com",
    "seeds":["/","/explore","/companies","/investments"],
    "patterns":[r"^/companies/[^/?#]+/?$",r"^/investment/[^/?#]+/?$",r"^/[^/?#]+/?$"],
    "reject":[r"^/(login|signup|about|help|blog|jobs|raise|invest|terms|privacy|contact|explore)(/|$)"]
  },
  "republic_europe":{
    "hosts":["europe.republic.com"],
    "base":"https://europe.republic.com",
    "seeds":["/","/invest/raising-now","/invest/secondary-market","/funded"],
    "patterns":[r"^/companies/[^/?#]+/?$",r"^/opportunities/[^/?#]+/?$",r"^/[^/?#]+/?$"],
    "reject":[r"^/(login|signup|about|help|blog|jobs|raise|invest|terms|privacy|contact|insights|institutions)(/|$)"]
  },
}

def now(): return datetime.now(timezone.utc).isoformat()
def sha_bytes(b:bytes): return hashlib.sha256(b).hexdigest()

def decode_body(content:bytes,url:str,headers:dict)->str:
    ct=(headers.get("content-type") or "").lower()
    if url.lower().endswith(".gz") or "gzip" in ct:
        try: content=gzip.decompress(content)
        except Exception: pass
    try: return content.decode("utf-8","ignore")
    except Exception: return ""

def fetch(url,timeout=30,impersonate=False):
    if impersonate and cffi_requests:
        try:
            r=cffi_requests.get(url,timeout=timeout,allow_redirects=True,impersonate="chrome")
            content=bytes(r.content); headers={k.lower():v for k,v in r.headers.items()}
            return {"ok":True,"status":r.status_code,"url":str(r.url),"text":decode_body(content,str(r.url),headers),"content":content,"headers":headers,"error":None,"transport":"curl_cffi"}
        except Exception as e:
            return {"ok":False,"status":None,"url":url,"text":"","content":b"","headers":{},"error":repr(e),"transport":"curl_cffi"}
    try:
        r=S.get(url,timeout=timeout,allow_redirects=True)
        content=r.content; headers={k.lower():v for k,v in r.headers.items()}
        return {"ok":True,"status":r.status_code,"url":r.url,"text":decode_body(content,r.url,headers),"content":content,"headers":headers,"error":None,"transport":"requests"}
    except Exception as e:
        return {"ok":False,"status":None,"url":url,"text":"","content":b"","headers":{},"error":repr(e),"transport":"requests"}

def best_fetch(url):
    r=fetch(url,impersonate=False)
    if r["status"] in {403,429,202} or not r["text"]:
        alt=fetch(url,impersonate=True)
        if alt["ok"] and (alt["status"]==200 or len(alt["text"])>len(r["text"])):
            return alt
    return r

def robots_sitemaps(base):
    u=urljoin(base,"/robots.txt"); r=best_fetch(u); out=[]
    if r["ok"] and r["status"]==200:
        for line in r["text"].splitlines():
            if line.lower().startswith("sitemap:"):
                out.append(line.split(":",1)[1].strip())
    for p in ["/sitemap.xml","/sitemap_index.xml","/sitemap-index.xml"]:
        out.append(urljoin(base,p))
    return list(dict.fromkeys(out)),r

def parse_sitemap(start_url,hosts,max_nested=100,max_urls=200000):
    seen=set(); urls=[]; status=[]; queue=[start_url]
    while queue and len(seen)<max_nested and len(urls)<max_urls:
        u=queue.pop(0)
        if u in seen: continue
        seen.add(u); r=best_fetch(u)
        status.append({"url":u,"status":r["status"],"ok":r["ok"],"transport":r["transport"],"error":r["error"],"prefix":r["text"][:120].replace("\n"," ")})
        if not r["ok"] or r["status"]!=200 or not r["text"]: continue
        txt=r["text"].lstrip("\ufeff\n\r\t ")
        try:
            root=ET.fromstring(txt)
        except Exception:
            for line in txt.splitlines():
                line=line.strip()
                if line.startswith("http") and urlparse(line).netloc in hosts:
                    urls.append(line)
            continue
        locs=[(x.text or "").strip() for x in root.iter() if x.tag.lower().endswith("loc")]
        if root.tag.lower().endswith("sitemapindex"):
            for loc in locs:
                full=urljoin(u,loc)
                if urlparse(full).netloc in hosts and full not in seen:
                    queue.append(full)
        else:
            for loc in locs:
                full=urljoin(u,loc)
                if urlparse(full).netloc in hosts:
                    urls.append(full)
    return list(dict.fromkeys(urls)),status

def html_links(url,hosts):
    r=best_fetch(url); links=[]
    soup=None
    if r["ok"] and r["status"]==200 and r["text"]:
        soup=BeautifulSoup(r["text"],"html.parser")
        for a in soup.find_all("a",href=True):
            full=urljoin(r["url"],a["href"]); p=urlparse(full)
            if p.scheme in {"http","https"} and p.netloc in hosts: links.append(full.split("#")[0])
    title=soup.title.string.strip() if soup and soup.title and soup.title.string else None
    return list(dict.fromkeys(links)),{"seed":url,"status":r["status"],"final_url":r["url"],"ok":r["ok"],"transport":r["transport"],"error":r["error"],"content_sha256":sha_bytes(r["content"]) if r["content"] else None,"title":title}

def browser_links(cfg):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return [],[],[{"error":"playwright_import:"+repr(e)}]
    hosts=set(cfg["hosts"]); links=set(); resources=set(); statuses=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        context=browser.new_context(user_agent=UA,locale="en-US",viewport={"width":1440,"height":1000})
        page=context.new_page()
        def on_response(resp):
            try:
                ct=(resp.headers.get("content-type") or "").lower()
                if ("json" in ct or "graphql" in resp.url.lower() or "/api/" in resp.url.lower()) and urlparse(resp.url).netloc in hosts:
                    resources.add(resp.url.split("#")[0])
            except Exception: pass
        page.on("response",on_response)
        for seed in cfg["seeds"]:
            u=urljoin(cfg["base"],seed)
            try:
                resp=page.goto(u,wait_until="domcontentloaded",timeout=45000)
                page.wait_for_timeout(3500)
                for href in page.locator("a").evaluate_all("(els)=>els.map(e=>e.href).filter(Boolean)"):
                    if urlparse(href).netloc in hosts: links.add(href.split("#")[0])
                statuses.append({"seed":u,"status":resp.status if resp else None,"title":page.title(),"final_url":page.url,"link_count":len(links)})
            except Exception as e:
                statuses.append({"seed":u,"status":None,"title":None,"final_url":page.url,"error":repr(e)})
        browser.close()
    return sorted(links),sorted(resources),statuses

def path_matches(platform,url):
    cfg=PLATFORMS[platform]; p=urlparse(url).path
    if any(re.search(x,p,re.I) for x in cfg["reject"]): return False
    return any(re.search(x,p,re.I) for x in cfg["patterns"])

def classify(platform,url):
    p=urlparse(url).path.lower()
    if platform=="startengine" and p.startswith("/offering/"): return "campaign"
    if platform=="republic_us" and p.startswith("/companies/"): return "campaign"
    if platform=="crowdcube" and (p.startswith("/companies/") or p.startswith("/investment/")): return "campaign"
    if platform=="republic_europe" and (p.startswith("/companies/") or p.startswith("/opportunities/")): return "campaign"
    if platform=="wefunder" and len([x for x in p.split("/") if x])==1: return "campaign_candidate"
    return "candidate"

def main():
    captured=now(); report={"captured_at":captured,"platforms":{},"method_version":"cp1-discovery-v3"}; rows=[]; republic_europe_businesses=[]
    for platform,cfg in PLATFORMS.items():
        hosts=set(cfg["hosts"]); smaps,robots=robots_sitemaps(cfg["base"])
        sitemap_urls=[]; sitemap_status=[]
        for sm in smaps:
            u,s=parse_sitemap(sm,hosts); sitemap_urls.extend(u); sitemap_status.extend(s)
        seed_links=[]; seed_status=[]
        for seed in cfg["seeds"]:
            links,st=html_links(urljoin(cfg["base"],seed),hosts); seed_links.extend(links); seed_status.append(st)
        first_all=list(dict.fromkeys(sitemap_urls+seed_links)); first_candidates=[u for u in first_all if path_matches(platform,u)]
        browser_seed_links=[]; browser_resources=[]; browser_status=[]
        if len(first_candidates)<10:
            browser_seed_links,browser_resources,browser_status=browser_links(cfg)
        all_urls=list(dict.fromkeys(sitemap_urls+seed_links+browser_seed_links)); candidates=[u for u in all_urls if path_matches(platform,u)]
        if platform=="republic_europe":
            republic_europe_businesses=sorted({u.split("#")[0].split("?")[0].rstrip("/") for u in all_urls if urlparse(u).path.startswith("/businesses/")})
        for u in candidates:
            rows.append({"platform":platform,"url":u,"classification":classify(platform,u),"discovery_source":"sitemap_or_public_seed_or_browser","captured_at":captured})
        report["platforms"][platform]={
            "robots":{"status":robots["status"],"final_url":robots["url"],"ok":robots["ok"],"transport":robots["transport"],"error":robots["error"]},
            "sitemap_candidates":smaps,"sitemap_status":sitemap_status,"sitemap_url_count":len(set(sitemap_urls)),
            "seed_status":seed_status,"seed_link_count":len(set(seed_links)),
            "browser_status":browser_status,"browser_link_count":len(set(browser_seed_links)),
            "browser_resources":browser_resources[:200],"candidate_count":len(candidates),"sample_candidates":candidates[:30],
        }
        print(platform,"sitemap",len(set(sitemap_urls)),"seed",len(set(seed_links)),"browser",len(set(browser_seed_links)),"candidates",len(candidates),flush=True)
        for st in seed_status: print("  seed",st["seed"],st["status"],st.get("transport"),st.get("title"),flush=True)
        for st in browser_status: print("  browser",st.get("seed"),st.get("status"),st.get("title"),flush=True)

    rows=sorted({(r["platform"],r["url"]):r for r in rows}.values(),key=lambda x:(x["platform"],x["url"]))
    with (OUT/"cp1_discovery_candidates.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["platform","url","classification","discovery_source","captured_at"]); w.writeheader(); w.writerows(rows)
    (OUT/"cp1_discovery_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    with (OUT/"cp3_republic_europe_business_candidates.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["platform","url","captured_at"]); w.writeheader();
        for u in republic_europe_businesses: w.writerow({"platform":"republic_europe","url":u,"captured_at":captured})
    manifest={"captured_at":captured,"candidate_rows":len(rows),"method_version":"cp1-discovery-v3","republic_europe_business_pages":len(republic_europe_businesses),"files":{
        "cp1_discovery_candidates.csv":hashlib.sha256((OUT/"cp1_discovery_candidates.csv").read_bytes()).hexdigest(),
        "cp1_discovery_report.json":hashlib.sha256((OUT/"cp1_discovery_report.json").read_bytes()).hexdigest(),
        "cp3_republic_europe_business_candidates.csv":hashlib.sha256((OUT/"cp3_republic_europe_business_candidates.csv").read_bytes()).hexdigest()}}
    (OUT/"cp1_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("TOTAL_CANDIDATES",len(rows))
    # CP3 follow-up is derived only from the platform-native Republic Europe business-page census just written above.
    followup=ROOT/"src/phase1d/followup_republic_europe_businesses.py"
    if followup.exists() and (OUT/"cp3_republic_europe_business_candidates.csv").exists():
        subprocess.run([sys.executable,str(followup)],check=True)

if __name__=="__main__": main()
