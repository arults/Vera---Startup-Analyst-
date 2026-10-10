"""Admissible visible timelines only; JSON envelope correction is not new collection."""
from __future__ import annotations
import csv,gzip,json,re,hashlib,io
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime
from urllib.parse import urljoin,urlparse
from collections import Counter
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/phase1d/cp9/cycle-1-issuer-history-updates'
OUT=ROOT/'data/phase1d/cp9/cycle-1-reconciled'
def sha(b):return hashlib.sha256(b).hexdigest()
def jb(x):return (json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def readrows(p):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def csvput(p,rs):
 s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=list(dict.fromkeys(k for r in rs for k in r)));w.writeheader();w.writerows(rs);put(p,s.getvalue().encode())
def date(d,y):return datetime.strptime(' '.join((d+' '+y).split()),'%b %d %Y').date().isoformat()
class MilestoneOracle(HTMLParser):
 """Separate stdlib parser, independent of BeautifulSoup extraction."""
 def __init__(self):super().__init__(convert_charrefs=True);self.active=False;self.depth=0;self.capture=None;self.card={};self.out=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);cs=a.get('class','').split()
  if tag=='article':self.active='offerings-updates-shared-milestone_card' in cs;self.card={};self.depth=0;self.capture=None
  if self.active and tag=='div':
   self.depth+=1
   for field in ['date-day-month','date-year','title']:
    if 'offerings-updates-shared-milestone_card__'+field in cs:self.capture=(field,self.depth);self.card.setdefault(field,[])
 def handle_data(self,data):
  if self.active and self.capture:self.card[self.capture[0]].append(data)
 def handle_endtag(self,tag):
  if self.active and tag=='div':
   if self.capture and self.capture[1]==self.depth:self.capture=None
   self.depth-=1
  if self.active and tag=='article':
   v={k:' '.join(''.join(s).split()) for k,s in self.card.items()};self.out.append((date(v['date-day-month'],v['date-year']),v['title']));self.active=False

def decode(raw):
 x=json.loads(raw)
 if not isinstance(x,dict) or not isinstance(x.get('update_section'),str):raise ValueError('missing JSON HTML envelope')
 s=BeautifulSoup(x['update_section'],'html.parser')
 if len(s.select('.offerings-show-update_section'))!=1:raise ValueError('wrong native timeline structure')
 return x['update_section'],s

def milestones(html,s):
 primary=[]
 for a in s.select('article.offerings-updates-shared-milestone_card'):
  d=a.select_one('.offerings-updates-shared-milestone_card__date-day-month');y=a.select_one('.offerings-updates-shared-milestone_card__date-year');t=a.select_one('.offerings-updates-shared-milestone_card__title')
  if not(d and y and t):raise ValueError('missing milestone field')
  primary.append((date(d.get_text(' ',strip=True),y.get_text(' ',strip=True)),t.get_text(' ',strip=True)))
 oracle=MilestoneOracle();oracle.feed(html)
 if primary!=oracle.out:raise ValueError('independent milestone parser disagreement')
 launch=[d for d,t in primary if t.startswith('Launched')];close=[d for d,t in primary if t.startswith('Successfully raised')]
 if len(launch)!=1 or len(close)!=1 or len(primary)!=2:raise ValueError('ambiguous campaign milestones')
 if not launch[0]<=close[0]<='2026-10-10':raise ValueError('invalid launch/close chronology')
 return launch[0],close[0],primary

def main():
 if OUT.exists():raise SystemExit('Refusing reconciliation overwrite')
 rs=json.loads((BASE/'native_update_fragment_candidates.json').read_text());campaigns={r['source_url']:r for r in readrows(ROOT/'data/phase1d/cp8/cycle-2-native-outcomes/republic_us_candidate_union.csv')}
 bindings={r['source_url']:r for r in readrows(BASE/'republic_native_identifier_bindings.csv')}
 dates=[];posts=[];milestone_rows=[];holds=[]
 for r in rs:
  raw=gzip.decompress((ROOT/r['source_path']).read_bytes())
  if sha(raw)!=r['source_sha256']:raise ValueError('source hash mismatch')
  parent=campaigns[r['campaign_url']]
  if parent['source_content_sha256']!=r['parent_sha256']:raise ValueError('parent source mismatch')
  parent_raw=gzip.decompress((ROOT/parent['capture_path']).read_bytes())
  if sha(parent_raw)!=r['parent_sha256']:raise ValueError('parent source bytes changed')
  html,s=decode(raw);launch,close,ms=milestones(html,s)
  if parent['successful_close_date'] and close!=parent['successful_close_date']:raise ValueError('timeline and native campaign disagree on close date')
  complete_binding=bool(parent['successful_close_date'] and bindings[r['campaign_url']]['native_offering_id'])
  if not complete_binding:holds.append({'campaign_url':r['campaign_url'],'reason':'NATIVE_PARENT_CLOSE_OR_IDENTIFIER_MISSING_TIMELINE_FIELDS_NOT_FULLY_VERIFIED'})
  row={**parent,'first_live_date':launch,'offering_year':int(launch[:4]),'native_launch_date':launch,'native_completion_date':close,'native_offering_id':bindings[r['campaign_url']]['native_offering_id'],'date_fields_status':'VERIFIED_NATIVE_TIMELINE_TWO_PARSERS' if complete_binding else 'TIMELINE_ONLY_PARENT_BINDING_HOLD','date_fields_verified':complete_binding,'year_in_study':2020<=int(launch[:4])<=2025,'close_year_would_misclassify':bool(parent['successful_close_date']) and launch[:4]!=parent['successful_close_date'][:4],'timeline_url':r['url'],'timeline_source_sha256':r['source_sha256'],'timeline_source_path':r['source_path'],'estimation_eligible':False,'census_complete':False,'status':'VERIFIED_DATES_IDENTITY_SCOPE_CENSUS_HOLDS','limitations':'Verified source dates are not complete population or canonical economic-round identity. Preserve security/scope and issuer holds.'}
  dates.append(row)
  for d,t in ms:milestone_rows.append({'campaign_url':r['campaign_url'],'date':d,'title':t,'source_sha256':r['source_sha256'],'independent_parsers_agree':True})
  for a in s.select('article.offerings-updates-shared-card'):
   w=a.select_one('.js-offerings_update_content_wrapper')
   if w is None:continue
   for el in list(w.select('form,script,style,textarea,input,select,.u-hidden,[hidden]')):el.decompose()
   if re.search(r'investors only|log in to (?:read|view)|sign in to (?:read|view)',w.get_text(' ',strip=True),re.I):holds.append({'campaign_url':r['campaign_url'],'reason':'INVESTOR_ONLY_OR_LOGIN_REQUIRED_PREVIEW_NOT_USED'});continue
   title=w.select_one('.offerings-updates-shared-card_content__title a[href]');desc=w.select_one('.offerings-updates-shared-card_content__description');d=w.select_one('.offerings-updates-shared-card__date-day-month');y=w.select_one('.offerings-updates-shared-card__date-year')
   if not(title and desc and d and y):holds.append({'campaign_url':r['campaign_url'],'reason':'MISSING_PUBLIC_PREVIEW_FIELDS'});continue
   u=urljoin(r['campaign_url'],title['href']);pr=urlparse(u)
   if pr.scheme!='https' or pr.hostname!='republic.com' or not re.fullmatch(r'/[\w.-]+',pr.path):raise ValueError('nonpublic post URL')
   day=date(d.get_text(' ',strip=True),y.get_text(' ',strip=True));heading=title.get_text(' ',strip=True);text=desc.get_text(' ',strip=True)
   if day>'2026-10-10':holds.append({'url':u,'reason':'AFTER_CUTOFF'});continue
   posts.append({'url':u,'campaign_url':r['campaign_url'],'title':heading,'publication_date':day,'visible_excerpt':text,'post_completion':day>close,'terminal_keyword_lead':bool(re.search(r'\bacquir(?:ed|es)|\bacquisition\b|\bceas|\bshutdown\b|\bshut down\b|\bdissolu|\bbankrupt|\bliquidat|\bwind(?:ing)?[ -]down\b|\bpayout\b|\bIPO\b',heading+' '+text,re.I)),'preview_is_not_full_event_proof':True,'source_sha256':r['source_sha256'],'source_path':r['source_path'],'native_first_live_date':launch,'native_completion_date':close})
 csvput(OUT/'republic_us_verified_date_candidates.csv',dates);put(OUT/'milestones.json',jb(milestone_rows));put(OUT/'public_post_candidates.json',jb(posts));put(OUT/'holds.json',jb(holds))
 selected=[r for r in posts if r['post_completion'] or r['terminal_keyword_lead']]
 selected=list({r['url']:r for r in selected}.values());selected.sort(key=lambda r:(not(r['campaign_url'].endswith('/ternio') and 'winding down' in r['title']),not r['terminal_keyword_lead'],r['url']))
 put(OUT/'public_post_followup_queue.json',jb(selected))
 changed=[{k:r[k] for k in ['source_url','first_live_date','offering_year','successful_close_date','year_in_study']} for r in dates if r['close_year_would_misclassify']]
 summary={'source_payloads_verified':len(rs),'native_launch_dates_extracted':len(dates),'date_pairs_verified_with_native_id_and_parent_close':sum(r['date_fields_verified'] for r in dates),'native_completion_dates_extracted':len(dates),'milestones_independently_agree':len(milestone_rows),'year_eligible_selected_campaigns':sum(r['year_in_study'] for r in dates),'year_counts_selected_NOT_population':dict(Counter(r['offering_year'] for r in dates)),'close_year_misclassification_risks':len(changed),'changed_year_examples':changed,'visible_public_post_previews':len(posts),'new_source_linked_followup_posts_queued':len(selected),'holds':len(holds),'new_live_requests_this_reconciliation':0,'scope':'Additive correction of JSON envelope parsing, not another substantive collection iteration; original raw/escaped outputs retained. Hidden forms excluded.','census_complete':False,'rates_promoted':False,'research_plateau':False}
 put(OUT/'summary.json',jb(summary));print(jb(summary).decode())
if __name__=='__main__':main()
