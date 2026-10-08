#!/usr/bin/env python3
from __future__ import annotations

import csv, gzip, hashlib, json, re, sys, time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/phase1d"
OUT.mkdir(parents=True,exist_ok=True)

UA="Mozilla/5.0 (compatible; VeraStartupResearch/0.6; +https://github.com/arults/Vera---Startup-Analyst-)"
S=requests.Session()
S.headers.update({"User-Agent":UA,"Accept-Language":"en-US,en;q=0.9"})

PLATFORMS={
  "wefunder":{
    "hosts":["wefunder.com","www.wefunder.com"],
    "base":"https://wefunder.com",
    "seeds":["/","/explore","/companies","/funded"],
    "patterns":[r"^/[^/?#]+/?$",r"^/companies/[^/?#]+/?$"],
    "reject":[r"^/(login|signup|about|faq|learn|blog|jobs|raise|invest|terms|privacy|contact|updates|reviews)(/|$)"]
  },
  "startengine":{
    "hosts":["startengine.com","www.startengine.com"],
    "base":"https://www.startengine.com",
    "seeds":["/","/explore","/explore/offerings","/offering"],
    "patterns":[r"^/offering/[^/?#]+/?$",r"^/[^/?#]+/?$"],
    "reject":[r"^/(login|signup|about|learn|blog|jobs|raise|invest|terms|privacy|contact|explore)(/|$)"]
  },
  "republic_us":{
    "hosts":["republic.com","www.republic.com"],
    "base":"https://republic.com",
    "seeds":["/","/companies","/companies/portfolio"],
    "patterns":[r"^/[^/?#]+/?$",r"^/companies/[^/?#]+/?$"],
    "reject":[r"^/(login|signup|about|learn|blog|jobs|raise|invest|terms|privacy|contact|companies/portfolio)(/|$)"]
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
    "seeds":["/","/invest","/companies","/opportunities"],
    "patterns":[r"^/companies/[^/?#]+/?$",r"^/opportunities/[^/?#]+/?$",r"^/[^/?#]+/?$"],
    "reject":[r"^/(login|signup|about|help|blog|jobs|raise|invest|terms|privacy|contact)(/|$)"]
  },
}

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(text:str):
    return hashlib.sha256(text.encode("utf-8","ignore")).hexdigest()

def get(url,timeout=25):
    try:
        r=S.get(url,timeout=timeout,allow_redirects=True)
        return {"ok":True,"status":r.status_code,"url":r.url,"text":r.text,"content_type":r.headers.get("content-type",""),"error":None}
    except Exception as e:
        return {"ok":False,"status":None,"url":url,"text":"","content_type":"","error":repr(e)}

def robots_sitemaps(base):
    u=urljoin(base,"/robots.txt")
    r=get(u)
    out=[]
    if r["ok"] and r["status"]==200:
        for line in r["text"].splitlines():
            if line.lower().startswith("sitemap:"):
                out.append(line.split(":",1)[1].strip())
    for p in ["/sitemap.xml","/sitemap_index.xml","/sitemap-index.xml"]:
        out.append(urljoin(base,p))
    return list(dict.fromkeys(out)),r

def parse_sitemap(url,hosts,max_nested=30):
    seen=set(); urls=[]; status=[]
    queue=[url]
    while queue and len(seen)<max_nested:
        u=queue.pop(0)
        if u in seen: continue
        seen.add(u)
        r=get(u)
        status.append({"url":u,"status":r["status"],"ok":r["ok"],"error":r["error"]})
        if not r["ok"] or r["status"]!=200: continue
        txt=r["text"]
        try:
            root=ET.fromstring(txt)
        except Exception:
            continue
        locs=[(x.text or "").strip() for x in root.iter() if x.tag.lower().endswith("loc")]
        if root.tag.lower().endswith("sitemapindex"):
            for loc in locs:
                if urlparse(loc).netloc in hosts and loc not in seen:
                    queue.append(loc)
        else:
            for loc in locs:
                if urlparse(loc).netloc in hosts:
                    urls.append(loc)
    return list(dict.fromkeys(urls)),status

def html_links(url,hosts):
    r=get(url)
    links=[]
    if r["ok"] and r["status"]==200:
        soup=BeautifulSoup(r["text"],"html.parser")
        for a in soup.find_all("a",href=True):
            full=urljoin(r["url"],a["href"])
            p=urlparse(full)
            if p.scheme in {"http","https"} and p.netloc in hosts:
                links.append(full.split("#")[0])
    return list(dict.fromkeys(links)),{"seed":url,"status":r["status"],"final_url":r["url"],"ok":r["ok"],"error":r["error"],"content_sha256":sha(r["text"]) if r["text"] else None}

def path_matches(platform,url):
    cfg=PLATFORMS[platform]
    p=urlparse(url).path
    if any(re.search(x,p,re.I) for x in cfg["reject"]): return False
    return any(re.search(x,p,re.I) for x in cfg["patterns"])

def classify(platform,url):
    p=urlparse(url).path.lower()
    if platform=="startengine" and p.startswith("/offering/"): return "campaign"
    if platform=="republic_us" and p.startswith("/companies/") and p!="/companies/portfolio": return "campaign"
    if platform=="crowdcube" and (p.startswith("/companies/") or p.startswith("/investment/")): return "campaign"
    if platform=="republic_europe" and (p.startswith("/companies/") or p.startswith("/opportunities/")): return "campaign"
    if platform=="wefunder":
        # Most Wefunder company pages are one-slug paths; validation happens in the next phase.
        if len([x for x in p.split("/") if x])==1: return "campaign_candidate"
    return "candidate"

def main():
    captured=now()
    report={"captured_at":captured,"platforms":{}}
    rows=[]
    for platform,cfg in PLATFORMS.items():
        hosts=set(cfg["hosts"])
        smaps,robots=robots_sitemaps(cfg["base"])
        sitemap_urls=[]; sitemap_status=[]
        for sm in smaps:
            u,s=parse_sitemap(sm,hosts)
            sitemap_urls.extend(u); sitemap_status.extend(s)
        seed_links=[]; seed_status=[]
        for seed in cfg["seeds"]:
            links,st=html_links(urljoin(cfg["base"],seed),hosts)
            seed_links.extend(links); seed_status.append(st)
        all_urls=list(dict.fromkeys(sitemap_urls+seed_links))
        candidates=[u for u in all_urls if path_matches(platform,u)]
        for u in candidates:
            rows.append({
                "platform":platform,
                "url":u,
                "classification":classify(platform,u),
                "discovery_source":"sitemap_or_public_seed",
                "captured_at":captured,
            })
        report["platforms"][platform]={
            "robots":{"status":robots["status"],"final_url":robots["url"],"ok":robots["ok"],"error":robots["error"]},
            "sitemap_candidates":smaps,
            "sitemap_status":sitemap_status,
            "sitemap_url_count":len(set(sitemap_urls)),
            "seed_status":seed_status,
            "seed_link_count":len(set(seed_links)),
            "candidate_count":len(candidates),
            "sample_candidates":candidates[:20],
        }
        print(platform, "sitemap",len(set(sitemap_urls)),"seed",len(set(seed_links)),"candidates",len(candidates), flush=True)

    rows=sorted({(r["platform"],r["url"]):r for r in rows}.values(),key=lambda x:(x["platform"],x["url"]))
    with (OUT/"cp1_discovery_candidates.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["platform","url","classification","discovery_source","captured_at"])
        w.writeheader(); w.writerows(rows)
    raw=json.dumps(report,indent=2,sort_keys=True)
    (OUT/"cp1_discovery_report.json").write_text(raw+"\n",encoding="utf-8")
    manifest={
        "captured_at":captured,
        "candidate_rows":len(rows),
        "files":{
            "cp1_discovery_candidates.csv":hashlib.sha256((OUT/"cp1_discovery_candidates.csv").read_bytes()).hexdigest(),
            "cp1_discovery_report.json":hashlib.sha256((OUT/"cp1_discovery_report.json").read_bytes()).hexdigest(),
        }
    }
    (OUT/"cp1_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("TOTAL_CANDIDATES",len(rows))

if __name__=="__main__":
    main()
