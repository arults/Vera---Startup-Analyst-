"""CP9 source-field verification and conservative semantic evidence ledger.
Native issuer reports are not independently certified real-world survival.
No incomplete census, SAFE cap or announcement is promoted into a numerical prior.
"""
from __future__ import annotations
import csv,gzip,hashlib,io,json,re
from datetime import datetime
from pathlib import Path
from lxml import html
import fitz
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/phase1d/cp9'
OUT=BASE/'adjudication'
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(s):return ' '.join(s.split())
def jb(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def readcsv(p):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def csvput(p,rows):
 s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows);put(p,s.getvalue().encode())
def cls(node,name):return node.xpath(".//*[contains(concat(' ', normalize-space(@class), ' '), ' "+name+" ')]")
def text(node):return norm(''.join(node.itertext()))
def verify_body(r):
 raw=gzip.decompress((ROOT/r['source_path']).read_bytes())
 if sha(raw)!=r['source_sha256']:raise ValueError('Native source hash mismatch')
 tree=html.fromstring(raw);wrappers=cls(tree,'js-offerings_update_content_wrapper')
 if len(wrappers)!=1:raise ValueError('Ambiguous issuer body')
 w=wrappers[0]
 for el in w.xpath('.//script|.//style|.//form|.//textarea|.//input|.//select|.//*[@hidden]')+cls(w,'u-hidden'):
  if el.getparent() is not None:el.drop_tree()
 for el in w.xpath('.//*[@style]'):
  if re.search(r'display\s*:\s*none|visibility\s*:\s*hidden',el.get('style',''),re.I):el.drop_tree()
 def single(c):
  found=cls(w,c)
  if len(found)!=1:raise ValueError('Missing or ambiguous '+c)
  return found[0]
 body=text(single('offerings-updates-shared-card_content__description'))
 title=text(single('offerings-updates-shared-card_content__title'))
 day=text(single('offerings-updates-shared-card__date-day-month'));year=text(single('offerings-updates-shared-card__date-year'))
 date=datetime.strptime(day+' '+year,'%b %d %Y').date().isoformat()
 if norm(title)!=norm(r['title']) or date!=r['publication_date']:raise ValueError('Independent full-page/timeline field disagreement')
 return body,{'url':r['url'],'source_path':r['source_path'],'source_sha256':r['source_sha256'],'publication_date':date,'title':title,'body_sha256':sha(body.encode()),'body_chars':len(body),'full_post_fields_verified':True,'scope':'Visible issuer card only; excludes hidden edit forms, comments, scripts and page chrome.'}

# Reviewed decision inputs. Anchors are verified against the original visible body.
ANCHORS={
'acfn':'All units were installed this month',
'alphaflow':'AlphaFlow has become one of the largest buyers',
'alphaflow-august-2020':'AlphaFlow has become one of the largest buyers',
'ample-foods':'we just sent out a survey',
'axle-ai-2020':"We've been heads-down building the business",
'base8':'The new version of the app is now available',
'beacons-ai':'Today we launched Beacons 2.0',
'bucket-list':'the Bucket List App has now reached more than 70,000 early users',
'cricclubs':'You can download both the Android and iOS App',
'currently-wine':'Q1’26 Revenue',
'dispatch-goods':'Dispatch handles the collection',
'fashwire':'In 2024',
'hawaiian-bros':'Ending the year with 48 restaurants',
'hold-the-magic':'July 2026 was the highest revenue month',
'horrorsection':'in production',
'inahsi':'As of today we are trending',
'ip3':'new Chief Creative Officer',
'jane-west-january-2020':'Available now',
'plain-sight':'2022 Traction Highlights',
'plant-an-app':'We are currently running a pilot referral program',
'popularium':'Q2 2025',
'quickloadz-2022':'We are still making and selling QuickLoadz',
'realtyfeed':'Today, the majority of our revenue is subscription-based',
'reental':'November 2025',
'reflex-protect':"We’ve moved all our manufacturing to Ohio",
'share-scoops-inc':'Our invite-only app is live',
'sienna-sauce-2020':'Sienna Sauce is now available',
'stockcard':'July 4th 2024',
 'teooh':'You can host a 6 person remote team meeting',
'vonmercier':'have been molded and delivered',
'wayzn':'Shipping since 2021'}
PERIODS={'currently-wine':('2026-01-01','2026-03-31'),'fashwire':('2024-01-01','2024-12-31'),'hold-the-magic':('2026-07-01','2026-07-31'),'plain-sight':('2022-01-01','2022-12-31'),'popularium':('2025-04-01','2025-06-30'),'reental':('2025-11-01','2025-11-30')}
EXACT_OVERRIDES={'hawaiian-bros':'2023-12-31','stockcard':'2024-07-04'}
HOLDS={
'aera':'Certification report held pending concrete dated operating activity.',
'altwork':'Bank exposure clarification alone is not operating activity.',
'arka':'Fundraising due diligence is not operating observation.',
'blue':'Token listing/product and shareholder security require distinct scope; no equity-exit inference.',
'chilling':'Campaign completion/administration alone; not company shutdown.',
'compound-reach':'Property/security scope, incomplete parent binding and generic webinar.',
'ecotone-renewables':'Social follow/thank-you request is not operating evidence.',
'fcf-glacier-boyz-2021':'Sports franchise/team and NFT scope require separate adjudication.',
'fig-portfolio':'Multi-game portfolio security is not an individual startup cohort member.',
'dallas-cityfund-a':'Property series account administration; do not merge same-CIK city series.',
'miami-cityfund-a':'Property series account administration; do not merge same-CIK city series.',
'janover-ventures':'Award and fundraising notice held pending concrete operating observation.',
'ready-set-jet':'Certification/press link requires event-date and operating-context review.',
'rheenergise':'Thank-you and video link need substantive review; not automatic observation date.',
 'tracflo':'Fundraising notice alone held; not closing or operating proof.',
'watrfall':'Campaign thanks/perks administration is not operating evidence or closure.'}

def verify_document(candidates,slug,label,expected_name):
 matches=[r for r in candidates if r['campaign_url']=='https://republic.com/'+slug and r['label']==label]
 if len(matches)!=1:raise ValueError('Ambiguous native document reference')
 r=matches[0];raw=gzip.decompress((ROOT/r['source_path']).read_bytes())
 if sha(raw)!=r['source_sha256'] or not raw.startswith(b'%PDF-'):raise ValueError('PDF hash or magic mismatch')
 a=fitz.open(stream=raw,filetype='pdf');b=PdfReader(io.BytesIO(raw))
 pages={}
 for index in [0,1]:
  x=norm(a[index].get_text());y=norm(b.pages[index].extract_text())
  anchor=expected_name if index==0 else 'Crowd'
  if anchor not in x or anchor not in y:raise ValueError('Two PDF parsers disagree on issuer/instrument anchor')
  pages[index+1]={'pymupdf_sha256':sha(x.encode()),'pypdf_sha256':sha(y.encode()),'anchor':anchor}
 result={'campaign_url':r['campaign_url'],'label':label,'source_path':r['source_path'],'source_sha256':r['source_sha256'],'source_url':r['url'],'issuer_name':expected_name,'instrument_family':'SAFE','page_field_checks':pages,'intermediary_cik_is_not_issuer_cik':True,'final_issued_terms_verified':False,'qualifying_priced_followon':False,'estimation_eligible':False,'verification':'Issuer and SAFE family anchors checked with two PDF parsers; selected pages visually reviewed separately.'}
 if slug=='unbanked':
  exact='Effective January 1, 2022, the Company converted to a Delaware corporation and changed its name to Unbanked, Inc.'
  x=norm(a[9].get_text());y=norm(b.pages[9].extract_text())
  if exact not in x or exact not in y or 'Ternio' not in x or 'Ternio' not in y:raise ValueError('Legal-conversion assertion not verified')
  result.update(legal_continuity_verified=True,former_legal_name='Ternio, LLC',conversion_date='2022-01-01',conversion_source_page=10,conversion_anchor='Effective January 1, 2022',conversion_full_assertion_sha256=sha(exact.encode()))
 return result

def main():
 if OUT.exists():raise SystemExit('Refusing adjudication overwrite')
 OUT.mkdir(parents=True)
 before={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/'data').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
 put(OUT/'preserved_before.json',jb(before))
 inputs=json.loads((BASE/'cycle-2-documents-posts/full_post_candidates.json').read_text())
 bodies={};verified={}
 for r in inputs:
  body,meta=verify_body(r);bodies[r['url']]=body;verified[r['url']]=meta
 put(OUT/'verified_full_post_fields.json',jb(list(verified.values())))
 dates={r['source_url']:r for r in readcsv(BASE/'cycle-1-reconciled/republic_us_verified_date_candidates.csv')}
 relations=json.loads((BASE/'cycle-1-reconciled/public_post_candidates.json').read_text());latest={}
 for r in relations:
  if r['url'] not in verified or not r['post_completion'] or dates[r['campaign_url']]['year_in_study']!='True':continue
  old=latest.get(r['campaign_url'])
  if old is None or old['publication_date']<r['publication_date']:latest[r['campaign_url']]=r
 if len(latest)!=47:raise ValueError('Unexpected reviewed latest-report set')
 ledger=[]
 for u,r in sorted(latest.items()):
  key=u.rsplit('/',1)[-1];meta=verified[r['url']];body=bodies[r['url']];d=dates[u]
  row={**meta,'campaign_url':u,'first_live_date':d['first_live_date'],'native_completion_date':d['native_completion_date'],'status':'HOLD','source_evidence_admitted':False,'exact_operating_evidence_date':None,'period_start':None,'period_end':None,'period_crosses_time_zero':False,'estimation_eligible':False,'real_world_survival_certified':False,'census_complete':False,'reason':HOLDS.get(key),'anchor':None}
  if key in ANCHORS:
   m=re.search(re.escape(ANCHORS[key]),body,re.I)
   if not m:raise ValueError('Missing semantic evidence anchor: '+key)
   point=EXACT_OVERRIDES.get(key,r['publication_date'])
   if key in PERIODS:point=None
   if point is not None and not d['native_completion_date']<=point<=r['publication_date']:raise ValueError('Point date outside source chronology')
   row.update(status='VERIFIED_NATIVE_OPERATING_REPORT',source_evidence_admitted=True,exact_operating_evidence_date=point,anchor=m.group(),anchor_start=m.start(),anchor_end=m.end(),reason='Dated issuer report of concrete activity; not independently certified real-world survival. Cohort and economic-round gates remain.')
   if key in PERIODS:
    lo,hi=PERIODS[key]
    if not lo<=hi<=r['publication_date']:raise ValueError('Period date inconsistency')
    row.update(period_start=lo,period_end=hi,period_crosses_time_zero=lo<d['native_completion_date'],reason='Period-bounded operating report. No invented exact date at publication or period-end; not usable as point-censor observation without further evidence.')
   if key=='hawaiian-bros':
    if 'December 31, 2023' not in meta['title']:raise ValueError('Year-end date not explicitly supported')
   if key=='stockcard':row['reason']='Product letter explicitly dated July 4, 2024; platform publication July 5 is not the event date.'
  elif key not in HOLDS:raise ValueError('Unreviewed campaign in latest set: '+key)
  ledger.append(row)
 csvput(OUT/'latest_operating_evidence.csv',ledger);put(OUT/'latest_operating_evidence.json',jb(ledger))
 documents=[]
 for cy in ['cycle-2-documents-posts','cycle-3-bounded-documents-linked-rounds']:
  documents+=json.loads((BASE/cy/'document_candidates.json').read_text())
 reviewed=[verify_document(documents,*args) for args in [('trusst','Trusst Form C.pdf','Trusst Health Inc.'),('unbanked','Unbanked Form C:A #2.pdf','Unbanked, Inc.'),('quickloadz','Quick Loadz Form C .pdf','Quick Loadz Container System, LLC'),('alpha-flow','Alphaflow Form C.pdf','AlphaFlow Inc.')]]
 put(OUT/'native_document_field_review.json',jb(reviewed))
 wind=[r for r in verified.values() if r['title']=='Unbanked will be winding down']
 if len(wind)!=1:raise ValueError('Ambiguous wind-down post')
 wind=wind[0];body=bodies[wind['url']]
 anchor='Today, we are making the unfortunate decision to wind down Unbanked.'
 if anchor not in body or wind['publication_date']!='2023-06-01':raise ValueError('Wind-down announcement not supported')
 new_dates=json.loads((BASE/'cycle-3-bounded-documents-linked-rounds/new_campaign_timelines.json').read_text())
 new=next(r for r in new_dates if r['campaign_url']=='https://republic.com/unbanked')
 if not new['date_fields_verified'] or new['offering_year']!=2022:raise ValueError('New Unbanked round not verified')
 negative={**wind,'event_type':'WIND_DOWN_ANNOUNCED','announcement_date':'2023-06-01','anchor':anchor,'source_evidence_admitted':True,'linked_campaign_url':new['campaign_url'],'linked_campaign_first_live_date':new['first_live_date'],'linked_campaign_completion_date':new['native_completion_date'],'company_continuity_source_sha256':reviewed[1]['source_sha256'],'company_continuity_source_page':10,'old_2019_round_in_study':False,'completed_closure_verified':False,'exact_cessation_date':None,'investor_loss_fraction':None,'investor_payout_date':None,'rate_eligible':False,'reason':'Source-bound legal conversion connects the 2022 issuer to the announcement. Customer withdrawal instructions are not proof of investor cash flows or complete cessation.'}
 put(OUT/'unbanked_winddown_announcement.json',jb(negative))
 union=list(dates.values());new_campaigns=json.loads((BASE/'cycle-3-bounded-documents-linked-rounds/new_campaign_candidates.json').read_text())
 for r in new_campaigns:
  t=next(t for t in new_dates if t['campaign_url']==r['source_url'])
  q={**r,'first_live_date':t.get('first_live_date'),'offering_year':t.get('offering_year'),'date_fields_verified':t.get('date_fields_verified',False),'estimation_eligible':False,'census_complete':False,'status':'NATIVE_SOURCE_FIELDS_WITH_UNRESOLVED_CENSUS_AND_ROUND_GATES'};union.append(q)
 if len({r['source_url'] for r in union})!=125:raise ValueError('Candidate union duplicated')
 csvput(OUT/'republic_us_candidate_union.csv',union)
 unchanged=all((ROOT/p).is_file() and sha((ROOT/p).read_bytes())==h for p,h in before.items())
 if not unchanged:raise AssertionError('Prior evidence changed')
 admitted=[r for r in ledger if r['source_evidence_admitted']]
 summary={'checkpoint':'CP9','execution_version':'0.6.4-dev.research.3','three_substantive_collection_cycles':True,'full_posts_independently_field_verified':len(verified),'latest_year_eligible_campaign_reports_reviewed':len(ledger),'native_operating_reports_admitted_as_source_evidence':len(admitted),'exact_operating_evidence_date_records':sum(r['exact_operating_evidence_date'] is not None for r in admitted),'period_only_operating_reports':sum(r['period_start'] is not None for r in admitted),'latest_report_holds':len(ledger)-len(admitted),'candidate_campaign_union_including_controls':len(union),'launch_completion_pairs_extracted':124,'launch_completion_pairs_fully_source_bound':122,'native_public_PDFs_captured':29,'native_document_issuer_and_SAFE_family_reviews':len(reviewed),'native_legal_conversion_verified':True,'native_winddown_announcements_linked_to_2022_round':1,'completed_closure_events_added':0,'priced_followon_successes_added':0,'prior_data_files_preserved':len(before),'all_prior_data_unchanged':unchanged,'incomplete_native_censuses':['Wefunder','StartEngine','Crowdcube','Republic US'],'public_document_queue_still_unattempted':105,'partial_document_byte_hold':1,'rates_promoted':False,'main_merged':False,'global_research_plateau':False,'phase_complete':False,'classification':'VERIFIED_EMPIRICAL_PROGRESS_RESEARCH_INCOMPLETE','limitation':'No censored-rate estimates are promoted from these case-selected campaign records. Period-only activity reports, unknown outcomes and incomplete populations remain explicit.'}
 put(OUT/'summary.json',jb(summary));print(jb(summary).decode())
if __name__=='__main__':main()
