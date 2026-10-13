import copy,json,unittest
from pathlib import Path
import test_historical_plan as historical
import evidence as e
import precision_withdrawal as p
import scoped_review as sc

class PrecisionTests(unittest.TestCase):
 def fixture(self):
  d,root,tmp,h=historical.HistoricalPlanTests().fixture();claim=d['claims'][0];cid=claim['id'];claim['time']={'kind':'point','on':'2024-11-22','basis':'Synthetic unchanged assertion','date_timezone':'PST'}
  html="<div class='js-offerings_update_content_wrapper'><div class='offerings-updates-shared-card__date-wrapper'>Nov 22 2024</div></div><div class='comments-comment__body' id='comment-synthetic'><div title='Nov 22, 2024, 08:29 PM (PST)'>comment</div></div>"
  (root/'original.html').write_text(html);s=d['sources'][0];s['original_sha256']=e.sha(html.encode());s['publication_date']='2024-11-22';s['publication_date_timezone']='PST';s['inspection']['document_reference']='original.html';s['inspection']['document_sha256']=s['original_sha256']
  old=copy.deepcopy(d);(root/'previous.json').write_text(json.dumps(old));(root/'parent.json').write_text(json.dumps(old));hr=d['research_scope']['historical_plan_reassessment'];hr['parent_dataset_sha256']=e.sha((root/'parent.json').read_bytes());hr['original_plan_sha256']=e.sha(e.stable(old['research_plan']))
  claim['time'].update(date_timezone=None,report_time=None,date_precision_note=p.NOTE);s['publication_date_timezone']=None;s['publication_time']=None
  audit={'reviewed_at':'2026-10-03T00:00:00Z','original_html_sha256':s['original_sha256'],'issuer_date_locator':'.js-offerings_update_content_wrapper .offerings-updates-shared-card__date-wrapper','issuer_display_date':'2024-11-22','issuer_exact_time':None,'issuer_timezone':None,'tooltip_dom_matches':[{'attributes':{'title':'Nov 22, 2024, 08:29 PM (PST)'},'ancestor_comment_ids':['comment-synthetic']}]};(root/'audit.json').write_text(json.dumps(audit))
  c={'claim_id':cid,'source_id':s['id'],'previous_dataset_reference':'previous.json','previous_dataset_sha256':e.sha((root/'previous.json').read_bytes()),'original_parent_sha256':hr['parent_dataset_sha256'],'previous_source_snapshot_sha256':e.source_snapshot(old),'corrected_source_snapshot_sha256':e.source_snapshot(d),'corrected_material_sha256':'pending','original_document_reference':'original.html','ownership_audit_reference':'audit.json','ownership_audit_sha256':e.sha((root/'audit.json').read_bytes()),'time_diff':{k:{'old_present':k in old['claims'][0]['time'],'old':old['claims'][0]['time'].get(k),'new':claim['time'].get(k)}for k in ('date_timezone','report_time','date_precision_note')},'reviews':[],'source_time_basis':'hash_bound_inspection_existed_by_audit_not_exact_retrieval'};d['research_scope']['precision_withdrawal']=c
  s['inspection']['review']['inspection_sha256']=sc.inspection_digest(s['inspection']);h.sign(d);self.sign(d,h);return d,old,root,tmp,h
 def sign(self,d,h):
  c=d['research_scope']['precision_withdrawal'];c['corrected_source_snapshot_sha256']=e.source_snapshot(d);c['corrected_material_sha256']=p.material_digest(d);c['reviews']=[{'reviewer':actor,'role':role,'decision':'approve_precision_withdrawal','correction_sha256':p.correction_digest(c),'rationale':'Synthetic correction only','reviewed_at':'2026-10-03T00:00:00Z'}for actor,role in [('synthetic-claim-reviewer','claim_verifier'),('synthetic-reviewer','source_verifier')]];h.sign(d)
 def check(self,d,old,root):return p.validate_withdrawal(d,old,root,{'synthetic-claim-reviewer':['claim_verifier'],'synthetic-reviewer':['source_verifier']},d['source_review'])
 def test_positive_precision_withdrawal(self):
  d,old,root,tmp,h=self.fixture();self.assertTrue(self.check(d,old,root));self.assertEqual(h.runreport(d,root)['released_selected_claims'],1);tmp.cleanup()
 def test_wrong_event_fields_hold(self):
  for field,value in [('on','2024-11-23'),('kind','upper_bound'),('basis','Changed'),('start','2024-01-01'),('end','2024-12-31'),('unexpected',{'nested':'precision'})]:
   d,old,root,tmp,h=self.fixture();d['claims'][0]['time'][field]=value;self.sign(d,h);self.assertFalse(self.check(d,old,root));tmp.cleanup()
 def test_adding_precision_or_freeform_note_holds(self):
  for field,value in [('date_timezone','UTC'),('report_time','12:00'),('date_precision_note','New factual event claim')]:
   d,old,root,tmp,h=self.fixture();d['claims'][0]['time'][field]=value;self.sign(d,h);self.assertFalse(self.check(d,old,root));tmp.cleanup()
 def test_forged_or_stale_hash_holds(self):
  for key in ('previous_dataset_sha256','original_parent_sha256','previous_source_snapshot_sha256','corrected_source_snapshot_sha256','corrected_material_sha256','ownership_audit_sha256'):
   d,old,root,tmp,h=self.fixture();d['research_scope']['precision_withdrawal'][key]='0'*64;self.assertFalse(self.check(d,old,root));tmp.cleanup()
 def test_core_identity_assertion_and_stance_change_hold(self):
  for key in ('identity','assertion','evidence','value'):
   d,old,root,tmp,h=self.fixture();d['claims'][0][key]={'changed':True};self.assertFalse(self.check(d,old,root));tmp.cleanup()
 def test_missing_audit_wrong_day_or_owner_holds(self):
  for key,value in [('issuer_display_date','2024-11-23'),('tooltip_dom_matches',[]),('issuer_timezone','PST')]:
   d,old,root,tmp,h=self.fixture();a=json.loads((root/'audit.json').read_text());a[key]=value;(root/'audit.json').write_text(json.dumps(a));d['research_scope']['precision_withdrawal']['ownership_audit_sha256']=e.sha((root/'audit.json').read_bytes());self.sign(d,h);self.assertFalse(self.check(d,old,root));tmp.cleanup()
 def test_key_deletion_and_same_collector_hold(self):
  d,old,root,tmp,h=self.fixture();del d['claims'][0]['time']['basis'];self.assertFalse(self.check(d,old,root));tmp.cleanup()
  d,old,root,tmp,h=self.fixture();d['claims'][0]['collector']='synthetic-claim-reviewer';self.assertFalse(self.check(d,old,root));tmp.cleanup()
 def test_missing_review_and_unknown_actor_hold(self):
  d,old,root,tmp,h=self.fixture();d['research_scope']['precision_withdrawal']['reviews']=[];self.assertFalse(self.check(d,old,root));tmp.cleanup()

 def test_known_acquisition_after_audit_holds(self):
  d,old,root,tmp,h=self.fixture();d['sources'][0]['retrieved_at']='2026-10-04T00:00:00Z';self.sign(d,h);self.assertFalse(self.check(d,old,root));tmp.cleanup()
 def test_unknown_acquisition_basis_explicit(self):
  d,old,root,tmp,h=self.fixture();del d['research_scope']['precision_withdrawal']['source_time_basis'];self.sign(d,h);self.assertFalse(self.check(d,old,root));tmp.cleanup()
 def test_tooltip_must_contain_withdrawn_zone(self):
  d,old,root,tmp,h=self.fixture();old['claims'][0]['time']['date_timezone']='EST';d['research_scope']['precision_withdrawal']['time_diff']['date_timezone']['old']='EST';self.assertFalse(self.check(d,old,root));tmp.cleanup()

 def test_extra_null_core_field_holds(self):
  d,old,root,tmp,h=self.fixture();d['claims'][0]['unsupported_new_fact']=None;self.sign(d,h);self.assertFalse(self.check(d,old,root));tmp.cleanup()
