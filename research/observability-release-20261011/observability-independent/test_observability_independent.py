"""Independent synthetic fault checks; pass the target vera_observability.py path."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
PATH=sys.argv.pop(1) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else str(Path(__file__).with_name('vera_observability.py'))
spec=importlib.util.spec_from_file_location('vo_independent',PATH);o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
class Checks(unittest.TestCase):
 def setUp(self):self.events=[];self.attempt='a1';self.refs={k:'ver:v1' for k in o.REF_KEYS}
 def e(self,kind,**kw):
  n=len(self.events)+1;event=dict(schema_version=o.SCHEMA,event_id=f'e{n}',run_id='r',attempt_id=self.attempt,seq=n,at=f'2026-10-11T00:{n//60:02}:{n%60:02}Z',kind=kind,**kw);self.events.append(event);return event
 def start(self,synthetic=True,evals=False,axis='engineering',scope='component'):
  manifest={k:{'applicability':'required' if k=='research' else 'not_applicable','reason_code':None if k=='research' else 'NOT_USED_BY_DECLARED_MODE'} for k in o.COMPONENTS}
  expected={'check':{'component':'research','quality_axis':axis,'scope':scope}} if evals else {}
  return self.e('run_start',synthetic=synthetic,expected_components=manifest,expected_evals=expected,refs=copy.deepcopy(self.refs),metrics_ref=None,integration_scope='explicit_local_adapter')
 def span(self,sid='s',parent=None,retry=None,refs=None):return self.e('span_start',span_id=sid,parent_span_id=parent,component='research',retry_of=retry,metrics_attempt_id=None,refs=copy.deepcopy(self.refs if refs is None else refs))
 def endspan(self,sid='s',status='completed',code='NONE'):return self.e('span_end',span_id=sid,execution_status=status,error_code=code)
 def evaluation(self,axis='engineering',scope='component',sid='s',status='pass',refs=None):
  return self.e('eval_result',result=dict(schema_version=o.EVAL_SCHEMA,eval_id='check',component='research',span_id=sid,status=status,quality_axis=axis,scope=scope,reviewer_basis='deterministic_check',refs=copy.deepcopy(self.refs if refs is None else refs),evidence_ref='ver:evidence',reason_code='NONE' if status=='pass' else 'ASSERTION_FAILED',jev=None))
 def finish(self,status='completed',capture='complete'):return self.e('run_end',execution_status=status,capture_status=capture)
 def row(self):return o.aggregate(self.events)['runs'][0]
 def invalid(self):
  try:r=self.row()
  except o.TraceError:return
  self.assertEqual(r['telemetry_health'],'invalid',r)
 def test_valid_component_completion(self):
  self.start();self.span();self.endspan();self.finish();r=self.row();self.assertEqual(r['telemetry_health'],'healthy');self.assertEqual(r['quality']['research']['status'],'not_evaluated')
 def test_valid_matched_component_eval(self):
  self.start(evals=True);self.span();self.endspan();self.evaluation();self.finish();r=self.row();self.assertEqual(r['quality']['engineering']['status'],'passed_declared_checks')
 def test_stale_artifact_eval_not_pass(self):
  self.start(evals=True);self.span();self.endspan();refs=dict(self.refs,artifact='ver:stale');self.evaluation(refs=refs);self.finish();self.invalid()
 def test_stale_model_eval_not_pass(self):
  self.start(evals=True);self.span();self.endspan();refs=dict(self.refs,model='ver:stale');self.evaluation(refs=refs);self.finish();self.invalid()
 def test_component_eval_requires_span(self):
  self.start(evals=True);self.span();self.endspan();self.evaluation(sid=None);self.finish();self.invalid()
 def test_synthetic_research_disallowed(self):
  self.start(evals=True,axis='research');self.span();self.endspan();self.evaluation(axis='research');self.finish();self.invalid()
 def test_generic_research_disallowed(self):
  self.start(synthetic=False,evals=True,axis='research',scope='generic_method');self.span();self.endspan();self.evaluation(axis='research',scope='generic_method');self.finish();self.invalid()
 def test_failed_engineering_does_not_imply_failed_execution(self):
  self.start(evals=True);self.span();self.endspan();self.evaluation(status='fail');self.finish();r=self.row();self.assertEqual(r['execution_outcome'],'completed');self.assertEqual(r['quality']['engineering']['status'],'failed')
 def test_missing_eval_cannot_capture_complete(self):
  self.start(evals=True);self.span();self.endspan();self.finish();self.invalid()
 def test_missing_component_cannot_complete(self):
  self.start();self.finish();self.invalid()
 def test_blocked_partial_without_span_is_partial(self):
  self.start();self.finish('blocked','partial');r=self.row();self.assertEqual(r['telemetry_health'],'partial');self.assertEqual(r['execution_outcome'],'blocked')
 def test_distinct_closed_retry_recovers(self):
  self.start();self.span();self.endspan(status='failed',code='TIMEOUT');self.span('s2',retry='s');self.endspan('s2');self.finish();r=self.row();self.assertEqual(r['telemetry_health'],'healthy');self.assertEqual(r['components']['research']['recovered_attempts'],1)
 def test_open_retry_cannot_hide_missing_span_end(self):
  self.start();self.span();self.span('s2',retry='s');self.endspan('s2');self.finish();self.invalid()
 def test_completed_span_cannot_be_retried(self):
  self.start();self.span();self.endspan();self.span('s2',retry='s');self.endspan('s2');self.finish();self.invalid()
 def test_resumed_open_span_keeps_partial_telemetry(self):
  self.start();self.span();self.finish('blocked','partial');self.attempt='a2';self.e('run_resume',resumes_attempt_id='a1');self.span('s2',retry='s');self.endspan('s2');self.finish(capture='partial');r=self.row();self.assertEqual(r['telemetry_health'],'partial');self.assertIn('s',r['missing_span_end_ids'])
 def test_premature_capture_claim_not_repaired_by_later_eval(self):
  self.start(evals=True);self.span();self.endspan();self.finish('blocked','complete');self.attempt='a2';self.e('run_resume',resumes_attempt_id='a1');self.evaluation();self.finish();self.invalid()
 def test_duplicate_delivery_idempotent(self):
  self.start();self.span();self.endspan();self.finish();r=o.aggregate(self.events+copy.deepcopy(self.events));self.assertEqual(r['duplicate_deliveries'],len(self.events));self.assertEqual(r['runs'][0]['telemetry_health'],'healthy')
 def test_conflicting_delivery_rejected(self):
  self.start();d=copy.deepcopy(self.events[0]);d['synthetic']=False;self.events.append(d);self.invalid()
 def test_sequence_gap_invalid(self):
  self.start();self.span();self.events[-1]['seq']=3;self.endspan();self.finish();self.invalid()
 def test_clock_reversal_invalid(self):
  self.start();self.span();self.endspan();self.events[-1]['at']='2026-10-11T00:00:00Z';self.finish();self.invalid()
 def test_orphan_parent_invalid(self):
  self.start();self.span(parent='missing');self.endspan();self.finish();self.invalid()
 def test_child_outlives_parent_invalid(self):
  self.start();self.span('parent');self.span('child',parent='parent');self.endspan('parent');self.endspan('child');self.finish();self.invalid()
 def test_unsafe_link_rejected(self):
  self.start();self.events[0]['metrics_ref']='../private.html';self.invalid()
 def test_raw_payload_field_rejected(self):
  self.start();self.events[0]['raw_prompt']='SYNTHETIC-PRIVATE-PAYLOAD';self.invalid()
 def test_exception_text_is_not_persisted(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'trace.jsonl';r=o.RunRecorder(o.Ledger(path),'privacy-run');r.start(self.refs,synthetic=True)
   try:
    with r.span('research'):raise ValueError('SYNTHETIC-SECRET-MARKER')
   except ValueError:pass
   self.assertNotIn('SYNTHETIC-SECRET-MARKER',path.read_text());self.assertIn('INVALID_INPUT',path.read_text())
if __name__=='__main__':unittest.main(verbosity=2)
