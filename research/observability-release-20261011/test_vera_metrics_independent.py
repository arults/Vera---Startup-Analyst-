"""Read-only independent synthetic conformance checks against selected release."""
import copy, importlib.util, json, sys, unittest
from pathlib import Path
PATH=sys.argv.pop(1) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else str(Path(__file__).with_name('vera_metrics.py'))
spec=importlib.util.spec_from_file_location('vm',PATH);vm=importlib.util.module_from_spec(spec);spec.loader.exec_module(vm)
class Checks(unittest.TestCase):
 def setUp(self): self.n=0
 def e(self,typ,t,**kw):
  self.n+=1
  return dict(schema_version=vm.SCHEMA,event_id=f'e{self.n}',run_id='test',at=f'2026-10-11T00:{t//60:02}:{t%60:02}Z',type=typ,**kw)
 def base(self):return [self.e('run_start',0,company_id='synthetic-company',analysis_mode='STANDARD',cache_state='cold',synthetic=True,collection_source='fixture'),self.e('worker_start',1,worker_id='w',parent_worker_id=None)]
 def attempt(self,aid,t=2,kind='model',**kw):return self.e('attempt_start',t,attempt_id=aid,worker_id='w',kind=kind,name='test-'+kind,usage_scope='exclusive',**kw)
 def stop(self,aid,t=3,usage=True,cost=None):
  u={'input_tokens':100,'cached_input_tokens':20,'output_tokens':10,'input_includes_cached':True,'source':'provider'} if usage is True else usage
  return self.e('attempt_end',t,attempt_id=aid,status='completed',token_usage=u,cost=cost)
 def finish(self,t=10,cutoff=None,**kw):return self.e('run_end',t,status=kw.get('status','completed'),capture_status=kw.get('capture','complete'),data_cutoff=f'2026-10-11T00:{(cutoff if cutoff is not None else t)//60:02}:{(cutoff if cutoff is not None else t)%60:02}Z',final_response_included=kw.get('final',True))
 def report(self,ev):return vm.aggregate(ev)
 def row(self,ev):return self.report(ev)['runs'][0]
 def test_idempotent_replayed_events(self):
  ev=self.base()+[self.attempt('a'),self.stop('a'),self.finish()];r=self.report(ev+copy.deepcopy(ev));self.assertEqual(r['runs'][0]['attempt_count'],1);self.assertEqual(r['duplicate_event_count'],len(ev))
 def test_conflicting_event_fails(self):
  ev=self.base();d=copy.deepcopy(ev[0]);d['company_id']='another'
  with self.assertRaises(vm.MetricsError):self.report(ev+[d])
 def test_distinct_retry_counts(self):
  r=self.row(self.base()+[self.attempt('a'),self.stop('a'),self.attempt('b',4),self.stop('b',5),self.finish()]);self.assertEqual(r['model_attempt_count'],2);self.assertEqual(r['tokens']['output_tokens']['known_subtotal'],20)
 def test_cache_subset_not_double_counted(self):
  r=self.row(self.base()+[self.attempt('a'),self.stop('a'),self.finish()]);self.assertEqual(r['tokens']['uncached_input_tokens']['known_subtotal'],80);self.assertEqual(r['tokens']['cached_input_tokens']['known_subtotal'],20)
 def test_unknown_not_zero(self):
  r=self.row(self.base()+[self.attempt('a'),self.stop('a',usage=None),self.finish()]);self.assertIsNone(r['tokens']['output_tokens']['known_subtotal']);self.assertFalse(r['cost_complete'])
 def test_partial_cost_not_total(self):
  cost={'currency':'USD','amount':'1.2','complete':True,'basis':'invoice','price_version':None}
  r=self.row(self.base()+[self.attempt('a'),self.stop('a',cost=cost),self.attempt('b',4),self.stop('b',5),self.finish()]);self.assertFalse(r['cost_complete']);self.assertEqual(r['costs'][0]['known_subtotal'],'1.2');self.assertIsNone(r['costs'][0]['complete_total'])
 def test_parallel_time_not_sum(self):
  r=self.row(self.base()+[self.attempt('a',2),self.attempt('b',2),self.stop('a',9),self.stop('b',9),self.finish()]);self.assertEqual(r['wall_seconds'],10);self.assertEqual(r['summed_attempt_seconds'],14)
 def test_resume_includes_pause(self):
  r=self.row(self.base()+[self.attempt('a'),self.stop('a'),self.finish(10,status='blocked',capture='partial'),self.e('run_resume',30),self.attempt('b',32),self.stop('b',33),self.finish(40)]);self.assertEqual(r['wall_seconds'],40);self.assertEqual(r['resumes'],1)
 def test_pending_has_no_completed_latency(self):
  r=self.row(self.base()+[self.attempt('a')]);self.assertIsNone(r['wall_seconds']);self.assertEqual(r['status'],'running')
 def test_invalid_cache_rejected(self):
  u={'input_tokens':1,'cached_input_tokens':2,'output_tokens':0,'input_includes_cached':True,'source':'provider'}
  with self.assertRaises(vm.MetricsError):self.report(self.base()+[self.attempt('a'),self.stop('a',usage=u),self.finish()])
 def test_unknown_extra_payload_rejected(self):
  ev=self.base();ev[0]['raw_prompt']='PRIVATE CONTENT'
  with self.assertRaises(vm.MetricsError):self.report(ev)
 def test_negative_counter_rejected(self):
  u={'input_tokens':-1,'cached_input_tokens':0,'output_tokens':0,'input_includes_cached':True,'source':'provider'}
  with self.assertRaises(vm.MetricsError):self.report(self.base()+[self.attempt('a'),self.stop('a',usage=u),self.finish()])
 def test_nan_cost_rejected(self):
  c={'currency':'USD','amount':'NaN','complete':True,'basis':'invoice','price_version':None}
  with self.assertRaises(vm.MetricsError):self.report(self.base()+[self.attempt('a'),self.stop('a',cost=c),self.finish()])
 def test_inclusive_rollup_rejected(self):
  a=self.attempt('a');a['usage_scope']='inclusive'
  with self.assertRaises(vm.MetricsError):self.report(self.base()+[a])
 def test_open_attempt_complete_rejected(self):
  with self.assertRaises(vm.MetricsError):self.report(self.base()+[self.attempt('a'),self.finish()])
 def test_non_finite_counter_rejected(self):
  u={'input_tokens':float('inf'),'cached_input_tokens':0,'output_tokens':0,'input_includes_cached':True,'source':'provider'}
  with self.assertRaises(vm.MetricsError):self.report(self.base()+[self.attempt('a'),self.stop('a',usage=u),self.finish()])
 def test_provider_request_double_attribution_rejected(self):
  ev=self.base()+[self.attempt('a',provider='p',provider_request_id='q'),self.stop('a'),self.attempt('b',4,provider='p',provider_request_id='q'),self.stop('b',5),self.finish()]
  with self.assertRaises(vm.MetricsError):self.report(ev)
 def test_cutoff_separate_from_closure(self):
  r=self.row(self.base()+[self.attempt('a'),self.stop('a'),self.finish(20,cutoff=10)]);self.assertEqual(r['wall_seconds'],10);self.assertEqual(r['closure_wall_seconds'],20)
 def test_total_survives_unknown_cache_split(self):
  u={'input_tokens':100,'cached_input_tokens':None,'output_tokens':10,'input_includes_cached':True,'source':'provider'}
  r=self.row(self.base()+[self.attempt('a'),self.stop('a',usage=u),self.finish()]);self.assertEqual(r['tokens']['total_tokens']['known_subtotal'],110);self.assertIsNone(r['tokens']['uncached_input_tokens']['known_subtotal'])
 def test_model_versions_not_pooled(self):
  ev=self.base()+[self.attempt('a',model_version='v1'),self.stop('a'),self.finish()];ev2=copy.deepcopy(ev)
  for e in ev2:
   e['run_id']+='-2';e['event_id']+='-2'
   if e['type']=='attempt_start':e['model_version']='v2'
  self.assertEqual(len(self.report(ev+ev2)['groups']),2)
 def test_unavailable_tools_remain_null(self):
  r=self.row(self.base()+[self.finish(capture='unavailable',final=False)]);self.assertIsNone(r['tool_calls']['known_subtotal'])
 def test_memory_peaks_never_summed(self):
  ev=self.base()
  for i,size in enumerate([100,200]):
   ev.append(self.e('memory_sample',2+i,worker_id='w',process_id='p'+str(i),scope='run_isolated_process',peak_rss_bytes=size,context_tokens=1000,storage_bytes=300,method='fixture',platform='synthetic',measurement_start='2026-10-11T00:00:01Z',measurement_end=f'2026-10-11T00:00:0{2+i}Z'))
  r=self.row(ev+[self.finish()]);self.assertEqual(r['memory']['max_observed_isolated_process_peak_rss_bytes'],200);self.assertIsNone(r['memory']['simultaneous_total_peak_rss_bytes'])
 def test_estimated_cache_price_no_double_charge(self):
  stop=self.stop('a');stop['prices']={'currency':'USD','price_version':'v1','source':'fixture','uncached_input_per_million':'10','cached_input_per_million':'1','output_per_million':'20'}
  r=self.row(self.base()+[self.attempt('a'),stop,self.finish()]);self.assertEqual(float(r['costs'][0]['known_subtotal']),0.00102);self.assertEqual(r['costs'][0]['basis'],['estimate'])
 def test_cross_run_request_double_attribution_rejected(self):
  ev=self.base()+[self.attempt('a',provider='p',provider_request_id='q'),self.stop('a'),self.finish()];ev2=copy.deepcopy(ev)
  for e in ev2:e['run_id']+='-2';e['event_id']+='-2'
  with self.assertRaises(vm.MetricsError):self.report(ev+ev2)
 def test_price_subgroup_denominator(self):
  cost={'currency':'USD','amount':'1','complete':True,'basis':'invoice','price_version':'v1'}
  ev=self.base()+[self.attempt('a'),self.stop('a',cost=cost),self.finish()];ev2=copy.deepcopy(ev)
  for e in ev2:
   e['run_id']+='-2';e['event_id']+='-2'
   if e['type']=='attempt_end':e['cost']['price_version']='v2'
  groups=self.report(ev+ev2)['groups'];self.assertEqual(len(groups),1)
  for subgroup in groups[0]['costs']:
   self.assertEqual(subgroup['eligible_n'],1);self.assertEqual(subgroup['missing_count'],0);self.assertEqual(subgroup['excluded_incompatible_count'],1)
 def test_table_discloses_final_cutoff(self):
  table=vm.render_table(self.report(self.base()+[self.finish(capture='partial',final=False)]))
  for word in ['Data cutoff','final response','excluded','fixture']:self.assertIn(word,table)
if __name__=='__main__':unittest.main(verbosity=2)
