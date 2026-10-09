"""CP8 feedback repair: short public directory != inaccessible or historical census.
Runs against already captured bytes; adds no live observations. The old cycle-2
snapshot remains immutable. Scope-specific parsing does not relax outcome rules.
"""
from __future__ import annotations
import json,re
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup
from src.phase1d.capture_cp7_sources import ROOT,DATA,write_new,jbytes
from src.phase1d.analyze_cp7_empirical import capture_bytes
URL='https://republic.com/reg-cf-offerings'
LABEL='directory of all active reg cf offerings'

def classify(raw: bytes, url: str=URL) -> dict:
    soup=BeautifulSoup(raw,'html.parser')
    title=soup.title.get_text(' ',strip=True).lower() if soup.title else ''
    headings=[' '.join(h.get_text(' ',strip=True).lower().split()) for h in soup.find_all(re.compile('^h[1-6]$'))]
    links=set()
    for a in soup.find_all('a',href=True):
        p=urlparse(urljoin(url,a['href']))
        if p.scheme=='https' and p.hostname=='republic.com' and re.fullmatch(r'/[a-zA-Z0-9._-]+',p.path) and not p.query and p.path not in {'/login','/signup','/register','/reg-cf-offerings'}:
            links.add('https://republic.com'+p.path)
    accepted=(url==URL and LABEL in headings and len(links)>=2 and 'republic' in title and not any(t in title for t in ('access denied','just a moment','login','log in')))
    return {'source_structure_verified':accepted,'scope':'ACTIVE_ONLY_NOT_HISTORICAL_CENSUS' if accepted else 'HELD_STRUCTURE_OR_SOURCE_MISMATCH',
            'public_campaign_links':sorted(links) if accepted else [],'historical_census_complete':False,'rates_promoted':False}

def self_tests():
    good=b'<title>Republic</title><h4>Directory of all active Reg CF offerings</h4><a href="/alpha">A</a><a href="/beta">B</a>'
    checks={
        'valid_short_page_accepted':classify(good)['source_structure_verified'],
        'active_scope_not_historical':not classify(good)['historical_census_complete'],
        'generic_text_without_heading_rejected':not classify(good.replace(b'h4',b'p'))['source_structure_verified'],
        'wrong_page_rejected':not classify(good,'https://republic.com/other')['source_structure_verified'],
        'no_platform_links_rejected':not classify(good.replace(b'href="/',b'href="https://example.org/'))['source_structure_verified'],
        'challenge_title_rejected':not classify(good.replace(b'<title>Republic',b'<title>Access denied Republic'))['source_structure_verified'],
        'different_directory_scope_not_assumed':not classify(good.replace(b'all active',b'all historical'))['source_structure_verified']}
    assert all(checks.values()),checks
    return checks

def main():
    records=json.loads((DATA/'cp8/cycle-2-native-outcomes/manifest.json').read_text())
    record=next(r for r in records if r['url']==URL)
    if record['http_status']!=200:raise ValueError('directory source unavailable')
    result=classify(capture_bytes(ROOT,record),record['final_url'])
    result.update(source_url=URL,source_sha256=record['content_sha256'],source_capture_path=record['capture_path'],
        new_live_observations=0,repair='252-character native directory was rejected by generic300-character cutoff. The exact source and heading structure now determine directory scope only.',
        supersedes_only='cycle-2 summary active_only_directory_confirmed=false and public_pages_verified=3; corrected values true and4. No campaign/outcome/rate change.',
        original_snapshot_preserved=True,self_tests=self_tests(),research_plateau=False)
    assert result['source_structure_verified'],result
    path=DATA/'cp8/cycle-2-feedback/directory-scope-verifier.json'
    write_new(path,jbytes(result));print(jbytes(result).decode())
if __name__=='__main__':main()
