#!/usr/bin/env python3
from __future__ import annotations

import csv, hashlib, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/phase1d"
INFILE=DATA/"cp1_discovery_candidates.csv"
OUTFILE=DATA/"cp2_republic_europe_rounds_raw.csv"
REJECTFILE=DATA/"cp2_republic_europe_rejected.csv"
KEYFILE=DATA/"cp2_republic_europe_date_keys.json"
MANIFEST=DATA/"cp2_republic_europe_manifest.json"

UA="Mozilla/5.0 (compatible; VeraStartupResearch/0.6; +https://github.com/arults/Vera---Startup-Analyst-)"

MONTHS="Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December"
DATE_RE=re.compile(rf"\b(\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}})\b",re.I)
ISO_RE=re.compile(r"\b(20\d\d-\d\d-\d\d(?:T[^\"'\s<]+)?)\b")

FIELD_RULES=[
 ("biotech_therapeutics",["biotech","therapeutic","pharma","drug discovery","life sciences"]),
 ("healthcare_medtech",["healthcare","health & wellbeing","medical","medtech","digital health"]),
 ("saas_enterprise_software",["saas","paas","enterprise software","software"]),
 ("fintech_insurtech",["finance & payments","fintech","insurtech","insurance","wealth"]),
 ("marketplaces_platforms",["marketplace","platform"]),
 ("hardware_robotics_deeptech",["hardware","robotics","deep tech","semiconductor","electronics"]),
 ("climate_energy_industrial",["energy","clean tech","climate","industrial","materials","recycling"]),
 ("food_beverage_agtech",["food","beverage","agriculture","agtech"]),
 ("media_gaming_creator",["gaming","media","content & information","music","entertainment"]),
 ("mobility_logistics_aerospace",["automotive & transport","mobility","logistics","aerospace","travel, leisure & sport"]),
 ("realestate_hospitality_proptech",["property","real estate","hospitality"]),
 ("consumer_retail",["home & personal","retail","consumer","fashion","beauty"]),
]

def parse_date(s):
    if not s: return ""
    s=re.sub(r"\s+"," ",s.strip()).replace("Sept ","Sep ")
    for fmt in ("%d %b %Y","%d %B %Y"):
        try:return datetime.strptime(s,fmt).date().isoformat()
        except ValueError:pass
    return ""

def money_value(s):
    if not s:return ""
    s=s.replace(",","").replace(" ","")
    m=re.search(r"([£€$])([0-9]+(?:\.[0-9]+)?)([KkMmBb]?)",s)
    if not m:return ""
    mult={"":1,"k":1e3,"m":1e6,"b":1e9}[m.group(3).lower()]
    return str(round(float(m.group(2))*mult,2))

def currency(s):
    if not s:return ""
    return "GBP" if "£" in s else "EUR" if "€" in s else "USD" if "$" in s else ""

def extract_after(text,label,maxchars=250):
    idx=text.lower().find(label.lower())
    return text[idx:idx+maxchars] if idx>=0 else ""

def field_from_sectors(sectors):
    low=sectors.lower()
    for field,terms in FIELD_RULES:
        if any(t in low for t in terms):return field
    return "other_diversified"

def candidate_urls():
    rows=[]
    with INFILE.open(newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["platform"]=="republic_europe":
                u=r["url"].split("#")[0].split("?")[0].rstrip("/")
                if "/academy/" in u or "/insights/" in u or "/pages/" in u or "/coming-soon" in u:continue
                rows.append(u)
    return sorted(set(rows))

def fetch_one(url):
    try:
        r=requests.get(url,headers={"User-Agent":UA,"Accept-Language":"en-GB,en;q=0.9"},timeout=25,allow_redirects=True)
        html=r.text
    except Exception as e:
        return {"candidate_url":url,"http_status":"","valid_campaign":False,"reject_reason":"fetch_error:"+repr(e)}
    if r.status_code!=200:
        return {"candidate_url":url,"final_url":r.url,"http_status":r.status_code,"valid_campaign":False,"reject_reason":"http_status"}
    soup=BeautifulSoup(html,"html.parser")
    text="\n".join(x.strip() for x in soup.stripped_strings)
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    low=text.lower()
    funded_match=re.search(rf"Funded\s+(\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}})",text,re.I)
    # Require strong campaign markers, not merely a generic site page.
    strong=bool(funded_match and ("Investment summary" in text or "Business overview" in text) and ("target" in low or "investors" in low))
    if not strong:
        return {"candidate_url":url,"final_url":r.url,"http_status":r.status_code,"valid_campaign":False,"reject_reason":"missing_campaign_markers","title":title,"content_sha256":hashlib.sha256(html.encode()).hexdigest()}

    h1=soup.find("h1")
    name=h1.get_text(" ",strip=True) if h1 else title.split("|")[0].strip()
    funded_raw=funded_match.group(1); funded_date=parse_date(funded_raw)
    funded_year=funded_date[:4] if funded_date else ""

    pct=""
    m=re.search(r"(\d{1,5})%\s*-\s*Funded",text,re.I)
    if m:pct=m.group(1)

    target_raw=""
    m=re.search(r"([£€$][0-9][0-9,.]*\s*[KkMmBb]?)\s+target",text,re.I)
    if m:target_raw=m.group(1)

    raised_raw=""; investors=""
    m=re.search(r"([£€$][0-9][0-9,.]*\s*[KkMmBb]?)\s+from\s+([0-9,]+)\s+investors",text,re.I)
    if m:raised_raw,investors=m.group(1),m.group(2).replace(",","")

    company_number=""
    m=re.search(r"Company number\s*\|?\s*([^\n|]{2,40})",text,re.I)
    if m:company_number=m.group(1).strip()

    sectors=""
    m=re.search(r"Sectors\s*\|?\s*([^\n]{2,160})",text,re.I)
    if m:sectors=m.group(1).strip()

    pre_money_raw=""
    m=re.search(r"Valuation \(pre-money\)\s*\|?\s*([^\n]{2,60})",text,re.I)
    if m:pre_money_raw=m.group(1).strip()

    invest_type=""
    m=re.search(r"Investment summary\s+Type\s*\|?\s*([^\n]{2,50})",text,re.I)
    if m:invest_type=m.group(1).strip()

    approval_raw=""
    m=re.search(rf"approved[^\n]{{0,200}}?as of\s+(\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}})",text,re.I)
    if m:approval_raw=m.group(1)
    approval_date=parse_date(approval_raw)

    # Search embedded HTML/JSON for date-bearing keys that may expose launch/open metadata.
    date_keys=[]
    key_re=re.compile(r'["\']([A-Za-z0-9_\-]*(?:open|launch|publish|start|live|approved|funded|close)[A-Za-z0-9_\-]*)["\']\s*[:=]\s*["\']([^"\']{4,60})["\']',re.I)
    for km in key_re.finditer(html):
        key,val=km.group(1),km.group(2)
        if re.search(r"20\d\d",val):
            date_keys.append([key,val])
    # Also capture likely date meta tags.
    for tag in soup.find_all("meta"):
        key=tag.get("property") or tag.get("name") or tag.get("itemprop")
        val=tag.get("content")
        if key and val and re.search(r"(publish|date|start|open|launch)",key,re.I) and re.search(r"20\d\d",val):
            date_keys.append([key,val])
    date_keys=date_keys[:40]

    # Do not use approval date as first-live date automatically.
    first_live_date=""
    first_live_basis="UNRESOLVED"
    for key,val in date_keys:
        if re.search(r"(campaign_?open|opened_at|open_date|launched_at|launch_date|live_at|published_at)",key,re.I):
            im=ISO_RE.search(val)
            if im:
                first_live_date=im.group(1)[:10]; first_live_basis="embedded_platform_metadata:"+key; break

    return {
      "candidate_url":url,"final_url":r.url,"http_status":r.status_code,"valid_campaign":True,
      "reject_reason":"","campaign_name":name,"company_number":company_number,
      "funded_date":funded_date,"funded_year":funded_year,"funded_percent":pct,
      "target_currency":currency(target_raw),"target_amount":money_value(target_raw),
      "raised_currency":currency(raised_raw),"raised_amount":money_value(raised_raw),"investors":investors,
      "pre_money_currency":currency(pre_money_raw),"pre_money_valuation":money_value(pre_money_raw),
      "investment_type":invest_type,"sectors_raw":sectors,"primary_field":field_from_sectors(sectors),
      "approval_date":approval_date,"first_live_date":first_live_date,"first_live_basis":first_live_basis,
      "date_keys_json":json.dumps(date_keys,separators=(",",":")),
      "title":title,"content_sha256":hashlib.sha256(html.encode()).hexdigest()
    }

def main():
    urls=candidate_urls(); print("CANDIDATES",len(urls),flush=True)
    results=[]
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs={ex.submit(fetch_one,u):u for u in urls}
        for i,fut in enumerate(as_completed(futs),1):
            results.append(fut.result())
            if i%100==0:print("FETCHED",i,flush=True)
    valid=[r for r in results if r.get("valid_campaign")]
    rejected=[r for r in results if not r.get("valid_campaign")]
    valid.sort(key=lambda r:(r.get("funded_date",""),r.get("company_number",""),r.get("candidate_url","")))
    rejected.sort(key=lambda r:r.get("candidate_url",""))
    fields=[
      "candidate_url","final_url","http_status","valid_campaign","reject_reason","campaign_name","company_number",
      "funded_date","funded_year","funded_percent","target_currency","target_amount","raised_currency","raised_amount",
      "investors","pre_money_currency","pre_money_valuation","investment_type","sectors_raw","primary_field",
      "approval_date","first_live_date","first_live_basis","date_keys_json","title","content_sha256"
    ]
    with OUTFILE.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(valid)
    rejfields=sorted(set().union(*(r.keys() for r in rejected))) if rejected else ["candidate_url"]
    with REJECTFILE.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=rejfields,extrasaction="ignore");w.writeheader();w.writerows(rejected)

    freq={}
    for r in valid:
        try: pairs=json.loads(r.get("date_keys_json") or "[]")
        except Exception:pairs=[]
        for k,v in pairs:
            freq[k]=freq.get(k,0)+1
    funded_scope=[r for r in valid if r.get("funded_year") in {"2020","2021","2022","2023","2024","2025"}]
    first_live_known=[r for r in funded_scope if r.get("first_live_date")]
    summary={
      "candidate_urls":len(urls),"valid_campaign_pages":len(valid),"rejected_pages":len(rejected),
      "funded_2020_2025":len(funded_scope),
      "first_live_known_2020_2025":len(first_live_known),
      "first_live_known_share":len(first_live_known)/len(funded_scope) if funded_scope else 0,
      "funded_by_year":{str(y):sum(1 for r in funded_scope if r["funded_year"]==str(y)) for y in range(2020,2026)},
      "first_live_by_year":{str(y):sum(1 for r in funded_scope if (r.get("first_live_date") or "").startswith(str(y))) for y in range(2020,2026)},
      "date_key_frequency":dict(sorted(freq.items(),key=lambda kv:-kv[1])[:100])
    }
    KEYFILE.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    manifest={
      "generated_at":datetime.utcnow().isoformat()+"Z","platform":"republic_europe",
      "files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUTFILE,REJECTFILE,KEYFILE]},
      "summary":summary
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,sort_keys=True))

if __name__=="__main__":main()
