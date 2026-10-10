"""Explicit reviewed withdrawal of unsupported timestamp precision; no event edits."""
import copy,json,re,datetime as dt
from html.parser import HTMLParser
from evidence import sha,stable,safe_path,source_snapshot,timestamp
NOTE='Issuer report date is retained; exact issuer publication time and timezone are unknown. A separate comment timestamp is excluded.'

def material_digest(data):
 d=copy.deepcopy(data);d.pop('source_review',None)
 d.get('research_scope',{}).pop('precision_withdrawal',None)
 for c in d.get('claims',[]):c.pop('reviews',None)
 return sha(stable(d))

def correction_digest(c):return sha(stable({k:v for k,v in c.items() if k!='reviews'}))

class OwnershipParser(HTMLParser):
 def __init__(self):super().__init__();self.stack=[];self.issuer=[];self.comments=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);anc=[x[1] for x in self.stack]
  if a.get('title') and any('comments-comment__body' in x.get('class','').split() for x in anc):self.comments.append({'title':a['title'],'ancestor_ids':[x['id']for x in anc if x.get('id')]})
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append((tag,a))
 def handle_startendtag(self,tag,attrs):pass
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:self.stack=self.stack[:i];break
 def handle_data(self,text):
  classes=[x[1].get('class','').split() for x in self.stack]
  if any('js-offerings_update_content_wrapper'in x for x in classes) and any('offerings-updates-shared-card__date-wrapper'in x for x in classes) and not any('comments-comment__body'in x for x in classes):self.issuer.append(text)

def permitted(old,new):
 if not isinstance(old,dict) or not isinstance(new,dict):return False
 expected=copy.deepcopy(old)
 if not isinstance(old.get('date_timezone'),str) or not old['date_timezone'].strip() or 'report_time'in old or 'date_precision_note'in old:return False
 expected.update(date_timezone=None,report_time=None,date_precision_note=NOTE)
 return new==expected

def validate_withdrawal(data,parent,root,registry,source_review):
 try:
  c=data['research_scope']['precision_withdrawal'];cid=c['claim_id'];oldraw=safe_path(root,c['previous_dataset_reference']).read_bytes()
  if sha(oldraw)!=c['previous_dataset_sha256']:return False
  old=json.loads(oldraw);oc=next(x for x in old['claims']if x['id']==cid);nc=next(x for x in data['claims']if x['id']==cid);pc=next(x for x in parent['claims']if x['id']==cid)
  if oc['time']!=pc['time'] or not permitted(oc['time'],nc['time']):return False
  if c['original_parent_sha256']!=data['research_scope']['historical_plan_reassessment']['parent_dataset_sha256']:return False
  if c['previous_source_snapshot_sha256']!=source_snapshot(old) or c['corrected_source_snapshot_sha256']!=source_snapshot(data) or c['corrected_material_sha256']!=material_digest(data):return False
  diff={k:{'old_present':k in oc['time'],'old':oc['time'].get(k),'new':nc['time'].get(k)}for k in set(oc['time'])|set(nc['time'])if (k in oc['time'])!=(k in nc['time'])or oc['time'].get(k)!=nc['time'].get(k)}
  if c['time_diff']!=diff:return False
  core_excluded={'time','reviews','predicate_review'}
  if {k:v for k,v in oc.items()if k not in core_excluded}!={k:v for k,v in nc.items()if k not in core_excluded}:return False
  op={k:v for k,v in oc.get('predicate_review',{}).items()if k!='rationale'};np={k:v for k,v in nc.get('predicate_review',{}).items()if k!='rationale'}
  if op!=np:return False
  # Correction cannot smuggle changes to other claims or graph relationships.
  old_claims={x['id']:x for x in old['claims']};new_claims={x['id']:x for x in data['claims']}
  if set(old_claims)!=set(new_claims):return False
  for other_id,prior in old_claims.items():
   current=new_claims[other_id];excluded={'reviews','predicate_review'}|({'time'}if other_id==cid else set())
   if {k:v for k,v in prior.items()if k not in excluded}!={k:v for k,v in current.items()if k not in excluded}:return False
   if {k:v for k,v in prior.get('predicate_review',{}).items()if k!='rationale'}!={k:v for k,v in current.get('predicate_review',{}).items()if k!='rationale'}:return False
  auditraw=safe_path(root,c['ownership_audit_reference']).read_bytes()
  if sha(auditraw)!=c['ownership_audit_sha256']:return False
  a=json.loads(auditraw);s=next(x for x in data['sources']if x['id']==c['source_id']);prior_source=next(x for x in old['sources']if x['id']==c['source_id'])
  if prior_source['original_sha256']!=s['original_sha256'] or s['id'] not in [x['source_id']for x in nc['evidence']]:return False
  raw=safe_path(root,c['original_document_reference']).read_bytes()
  if sha(raw)!=a['original_html_sha256'] or sha(raw)!=s['original_sha256']:return False
  if a['issuer_display_date']!=nc['time']['on'] or a['issuer_exact_time']is not None or a['issuer_timezone']is not None:return False
  if a['issuer_date_locator']!='.js-offerings_update_content_wrapper .offerings-updates-shared-card__date-wrapper':return False
  parser=OwnershipParser();parser.feed(raw.decode('utf-8'));day=dt.date.fromisoformat(nc['time']['on']);display=' '.join(' '.join(parser.issuer).split())
  if display!=day.strftime('%b')+' '+str(day.day)+' '+str(day.year):return False
  matches=a['tooltip_dom_matches']
  withdrawn_zone=oc['time']['date_timezone'].split()[0]
  if not re.fullmatch(r'[A-Z]{2,5}',withdrawn_zone):return False
  if not matches or not all(re.search(r'\b'+re.escape(withdrawn_zone)+r'\b',m['attributes']['title']) and any(x['title']==m['attributes']['title'] and set(m['ancestor_comment_ids'])<=set(x['ancestor_ids']) and m['ancestor_comment_ids'] for x in parser.comments)for m in matches):return False
  if s.get('publication_date')!=nc['time']['on'] or s.get('publication_date_timezone')is not None or s.get('publication_time')is not None:return False
  reviews=c['reviews'];roles=set();actors=set();audit_time=timestamp(a['reviewed_at'])
  if s.get('retrieved_at') is not None or s.get('retrieval_timing') is not None:
   from timing import bounds
   _,acquired_by,_=bounds(s,'retrieved_at','retrieval_timing',root)
   if acquired_by>audit_time:return False
  elif c.get('source_time_basis')!='hash_bound_inspection_existed_by_audit_not_exact_retrieval':return False
  for r in reviews:
   actor=r['reviewer'];role=r['role']
   if actor in {nc.get('collector'),source_review.get('researcher')}:return False
   if timestamp(r['reviewed_at'])>timestamp(source_review['reviewed_at']):return False
   if role not in {'claim_verifier','source_verifier'} or role not in registry.get(actor,[]) or r['decision']!='approve_precision_withdrawal' or r['correction_sha256']!=correction_digest(c) or not r['rationale'] or timestamp(r['reviewed_at'])<audit_time:return False
   if role=='source_verifier' and actor!=source_review.get('reviewer'):return False
   if role=='claim_verifier' and not any(x.get('reviewer')==actor and x.get('decision')=='accept' for x in nc.get('reviews',[])):return False
   roles.add(role);actors.add(actor)
  return roles=={'claim_verifier','source_verifier'} and len(actors)>=2
 except (KeyError,ValueError,TypeError,StopIteration,OSError,AttributeError):return False
