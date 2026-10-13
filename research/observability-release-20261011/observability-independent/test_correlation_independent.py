"""Independent synthetic join coverage and generated-artifact checks."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
BASE=Path(__file__).resolve().parent
BENCH=Path(sys.argv.pop(1)) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else BASE/'synthetic_benchmark.py'
METRICS=Path(sys.argv.pop(1)) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else BASE.parent/'run-metrics-v0.1.0'/'vera_metrics.py'
sys.path.insert(0,str(BENCH.parent))
spec=importlib.util.spec_from_file_location('b_correlation',BENCH);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);m=b.load_metrics(METRICS)
class Checks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);b.run_case(b.CASES[0],self.path,metrics=m)
  self.obs=b.vo.aggregate(b.vo.read_events(self.path/'trace.jsonl'));self.events=m.read_events([self.path/'metrics.jsonl']);self.metrics=m.aggregate(self.events)
 def tearDown(self):self.tmp.cleanup()
 def join(self):return b.vo.correlate_metrics(self.obs,self.events,self.metrics,self.path,expected_dashboard=m.render_html(self.metrics).encode())['runs'][0]
 def test_complete_verified_join(self):
  r=self.join();self.assertEqual(r['metrics_correlation']['status'],'matched');self.assertEqual(r['metrics_correlation']['report_content_verification'],'verified_generated_bytes')
 def test_unreferenced_metric_attempt_remains_partial(self):
  st=copy.deepcopy(next(e for e in self.events if e['type']=='attempt_start'));en=copy.deepcopy(next(e for e in self.events if e['type']=='attempt_end' and e['attempt_id']==st['attempt_id']))
  for event in [st,en]:event['event_id']+='-extra';event['attempt_id']='extra-attempt'
  self.events += [st,en];self.metrics=m.aggregate(self.events);m.write_report(self.metrics,self.path/'metrics');r=self.join()
  self.assertEqual(r['metrics_correlation']['status'],'matched_declared_refs');self.assertEqual(r['telemetry_health'],'partial');self.assertEqual(r['metrics_correlation']['unreferenced_attempt_ids'],['extra-attempt'])
 def test_duplicate_attribution_rejected(self):
  spans=[s for s in self.obs['runs'][0]['spans'] if s['start']['metrics_attempt_id']]
  spans[1]['start']['metrics_attempt_id']=spans[0]['start']['metrics_attempt_id'];r=self.join();self.assertEqual(r['metrics_correlation']['status'],'mismatch');self.assertEqual(r['telemetry_health'],'invalid')
 def test_missing_reference_rejected(self):
  span=next(s for s in self.obs['runs'][0]['spans'] if s['start']['metrics_attempt_id']);span['start']['metrics_attempt_id']='missing-attempt';r=self.join();self.assertEqual(r['metrics_correlation']['status'],'mismatch')
 def test_wrong_dashboard_bytes_rejected(self):
  (self.path/'metrics'/'dashboard.html').write_text('stale synthetic report');r=self.join();self.assertEqual(r['metrics_correlation']['status'],'mismatch');self.assertEqual(r['metrics_correlation']['report_content_verification'],'unverified')
 def test_missing_metrics_run_rejected(self):
  self.events=[];self.metrics=m.aggregate([]);r=self.join();self.assertEqual(r['metrics_correlation']['status'],'mismatch')
if __name__=='__main__':unittest.main(verbosity=2)
