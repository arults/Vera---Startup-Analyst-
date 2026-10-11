"""Synthetic only: no network, private company records or scientific outputs."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('vera_metrics', Path(__file__).with_name('vera_metrics.py'))
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def event(event_type, second, eid=None, **fields):
    if event_type == 'memory_sample':
        fields.update(method='fixture', platform='synthetic', measurement_start=None, measurement_end=f'2026-10-11T00:00:{second:02d}Z')
    return dict(schema_version=m.SCHEMA, event_id=eid or event_type+str(second), run_id='r1', at=f'2026-10-11T00:00:{second:02d}+00:00', type=event_type, **fields)


def fixture():
    return [event('run_start', 0, company_id='synthetic-company', analysis_mode='STANDARD', cache_state='cold', synthetic=True, collection_source='fixture'),
            event('worker_start', 1, worker_id='root', parent_worker_id=None),
            event('attempt_start', 2, attempt_id='a1', worker_id='root', kind='model', name='analysis', provider='fixture', model='fixture-model', usage_scope='exclusive'),
            event('attempt_end', 8, attempt_id='a1', status='completed', token_usage={'input_tokens': 1000, 'cached_input_tokens': 400, 'output_tokens': 500, 'input_includes_cached': True, 'source': 'fixture'}, prices={'currency': 'USD', 'uncached_input_per_million': '2', 'cached_input_per_million': '1', 'output_per_million': '8', 'price_version': 'synthetic-v1', 'source': 'fixture'}),
            event('run_end', 10, status='completed', capture_status='complete', data_cutoff='2026-10-11T00:00:10Z', final_response_included=True)]


def row(events=None):
    return m.aggregate(fixture() if events is None else events)['runs'][0]


class LedgerTests(unittest.TestCase):
    def test_cached_subset_is_not_added_twice(self):
        r = row()
        self.assertEqual([r['tokens'][k]['known_subtotal'] for k in m.TOKEN_FIELDS], [600, 400, 500])
        self.assertEqual(r['costs'][0]['complete_total'], '0.0056')

    def test_exclusive_input_convention(self):
        f = fixture(); f[3]['token_usage']['input_includes_cached'] = False
        self.assertEqual(row(f)['tokens']['uncached_input_tokens']['known_subtotal'], 1000)

    def test_unknown_cache_does_not_mean_zero(self):
        f = fixture(); f[3]['token_usage']['cached_input_tokens'] = None
        r = row(f)
        self.assertIsNone(r['tokens']['uncached_input_tokens']['known_subtotal'])
        self.assertIsNone(r['tokens']['cached_input_tokens']['known_subtotal'])
        self.assertEqual(r['costs'][0]['known_subtotal'], '0.004')
        self.assertIsNone(r['costs'][0]['complete_total'])

    def test_wholly_missing_usage_is_null(self):
        f = fixture(); f[3]['token_usage'] = None; f[3]['prices'] = None
        r = row(f)
        self.assertIsNone(r['tokens']['output_tokens']['known_subtotal'])
        self.assertFalse(r['cost_complete']); self.assertEqual(r['cost_unknown_attempts'], 1)

    def test_zero_is_only_zero_when_observed(self):
        f = fixture(); f[3]['token_usage'].update(input_tokens=0, cached_input_tokens=0, output_tokens=0)
        r = row(f); self.assertEqual(r['tokens']['output_tokens']['known_subtotal'], 0)
        self.assertEqual(r['costs'][0]['complete_total'], '0')

    def test_unknown_zero_rate_is_not_needed_for_observed_zero_tokens(self):
        f = fixture(); f[3]['token_usage']['output_tokens'] = 0; f[3]['prices']['output_per_million'] = None
        self.assertTrue(row(f)['cost_complete'])

    def test_missing_rate_partial_subtotal(self):
        f = fixture(); f[3]['prices']['output_per_million'] = None
        self.assertEqual(row(f)['costs'][0]['known_subtotal'], '0.0016')
        self.assertFalse(row(f)['cost_complete'])

    def test_final_response_pending_keeps_full_usage_partial(self):
        f = fixture(); f[-1]['final_response_included'] = False
        self.assertFalse(row(f)['tokens']['output_tokens']['complete'])
        self.assertFalse(row(f)['cost_complete'])

    def test_partial_capture_keeps_known_metrics_partial(self):
        f = fixture(); f[-1]['capture_status'] = 'partial'
        self.assertEqual(row(f)['tokens']['output_tokens']['status'], 'partial')

    def test_duplicate_events_are_idempotent(self):
        f = fixture(); r = m.aggregate(f+copy.deepcopy(f))
        self.assertEqual(r['duplicate_event_count'], 5)
        self.assertEqual(r['runs'][0]['attempt_count'], 1)

    def test_duplicate_attempt_receipt_with_new_event_id_single_counts(self):
        f = fixture(); e = copy.deepcopy(f[3]); e['event_id'] = 'replay'; f.append(e)
        self.assertEqual(row(f)['attempt_count'], 1)
        self.assertEqual(row(f)['tokens']['output_tokens']['known_subtotal'], 500)

    def test_conflicting_duplicate_event_rejected(self):
        f = fixture(); e = copy.deepcopy(f[3]); e['status'] = 'failed'
        with self.assertRaises(m.MetricsError): row(f+[e])

    def test_conflicting_attempt_receipt_rejected(self):
        f = fixture(); e = copy.deepcopy(f[3]); e.update(event_id='other', status='failed')
        with self.assertRaises(m.MetricsError): row(f+[e])

    def test_parallel_wall_is_not_sum(self):
        f = fixture(); start = copy.deepcopy(f[2]); end = copy.deepcopy(f[3])
        start.update(event_id='start2', attempt_id='a2'); end.update(event_id='end2', attempt_id='a2')
        r = row(f+[start,end]); self.assertEqual(r['wall_seconds'], 10); self.assertEqual(r['summed_attempt_seconds'], 12)

    def test_retry_is_new_attempt_and_failed_attempt_cost_counted(self):
        f = fixture(); f[3]['status'] = 'failed'; start = copy.deepcopy(f[2]); end = copy.deepcopy(f[3])
        start.update(event_id='retry-start', attempt_id='retry'); end.update(event_id='retry-end', attempt_id='retry', status='completed')
        r = row(f+[start,end]); self.assertEqual(r['attempt_count'], 2); self.assertEqual(r['costs'][0]['complete_total'], '0.0112')

    def test_provider_request_reused_under_different_attempt_rejected(self):
        f = fixture(); f[2]['provider_request_id'] = 'req'; start = copy.deepcopy(f[2]); start.update(event_id='another', attempt_id='a2')
        with self.assertRaises(m.MetricsError): row(f+[start])

    def test_resumed_run_cumulative_and_includes_pause_in_wall(self):
        f = fixture(); f[-1]['status'] = 'cancelled'
        f += [event('run_resume',20), event('run_end',30,status='completed',capture_status='complete',data_cutoff='2026-10-11T00:00:30Z',final_response_included=True)]
        r = row(f); self.assertEqual(r['wall_seconds'],30); self.assertEqual(r['resumes'],1); self.assertEqual(r['attempt_count'],1)

    def test_open_resumed_run_has_no_fabricated_end(self):
        f = fixture()+[event('run_resume',20)]
        self.assertEqual(row(f)['status'],'running'); self.assertIsNone(row(f)['wall_seconds'])

    def test_attempt_in_pause_is_invalid(self):
        f = fixture()+[event('run_resume',20)]
        f[2]['at']='2026-10-11T00:00:15Z'
        with self.assertRaises(m.MetricsError): row(f)

    def test_open_attempt_cannot_have_complete_capture(self):
        f = fixture(); f.pop(3)
        with self.assertRaises(m.MetricsError): row(f)

    def test_open_attempt_partial_is_retained(self):
        f = fixture(); f.pop(3); f[-1]['capture_status']='partial'
        r=row(f); self.assertEqual(r['open_attempt_count'],1); self.assertIsNone(r['tokens']['output_tokens']['known_subtotal'])

    def test_cancelled_unknown_attempt_not_free(self):
        f = fixture(); f[3].update(status='cancelled',token_usage=None,prices=None); f[-1]['status']='cancelled'
        r=row(f); self.assertFalse(r['cost_complete']); self.assertEqual(r['attempt_status_counts']['cancelled'],1)

    def test_tool_fees_missing_make_model_subtotal_incomplete(self):
        f=fixture()+[event('attempt_start',3,attempt_id='tool',worker_id='root',kind='tool',name='search',usage_scope='exclusive'),event('attempt_end',4,attempt_id='tool',status='completed')]
        r=row(f); self.assertEqual(r['tool_attempt_count'],1); self.assertEqual(r['costs'][0]['known_subtotal'],'0.0056'); self.assertFalse(r['cost_complete'])

    def test_jev_token_price_does_not_cover_service_fee(self):
        f=fixture(); f[2]['kind']='jev'; r=row(f)
        self.assertEqual(r['tool_attempt_count'],1); self.assertFalse(r['cost_complete']); self.assertEqual(r['attempts'][0]['cost']['expected_components'],4)

    def test_tool_wrapper_cannot_repeat_model_tokens(self):
        f=fixture(); f[2]['kind']='tool'
        with self.assertRaises(m.MetricsError): row(f)

    def test_wrapper_excluded_from_leaf_dispatch_count(self):
        f=fixture(); f[2].update(kind='tool',dispatch_role='wrapper'); f[3].update(token_usage=None,prices=None)
        r=row(f); self.assertEqual(r['tool_attempt_count'],0); self.assertEqual(r['wrapper_attempt_count'],1)

    def test_parent_worker_and_attempt_do_not_rollup_child_twice(self):
        f=fixture()+[event('worker_start',2,'w2',worker_id='child',parent_worker_id='root')]
        f[2]['worker_id']='child'; r=row(f); self.assertEqual(r['worker_count'],2); self.assertEqual(r['tokens']['output_tokens']['known_subtotal'],500)

    def test_inclusive_rollup_rejected(self):
        f=fixture(); f[2]['usage_scope']='inclusive'
        with self.assertRaises(m.MetricsError): row(f)

    def test_worker_cycle_rejected(self):
        f=fixture(); f[1]['parent_worker_id']='root'
        with self.assertRaises(m.MetricsError): row(f)

    def test_missing_worker_rejected(self):
        f=fixture(); f[2]['worker_id']='absent'
        with self.assertRaises(m.MetricsError): row(f)

    def test_missing_parent_attempt_rejected(self):
        f=fixture(); f[2]['parent_attempt_id']='absent'
        with self.assertRaises(m.MetricsError): row(f)

    def test_negative_and_noninteger_tokens_rejected(self):
        for value in (-1, True, 1.5, float('nan'), float('inf'), '7'):
            with self.subTest(value=value):
                f=fixture(); f[3]['token_usage']['output_tokens']=value
                with self.assertRaises(m.MetricsError): row(f)

    def test_cached_exceeds_inclusive_input_rejected(self):
        f=fixture(); f[3]['token_usage']['cached_input_tokens']=1001
        with self.assertRaises(m.MetricsError): row(f)

    def test_bad_money_rejected(self):
        for value in ('-1','NaN','Infinity','1e999','1e-999',1.0,True):
            with self.subTest(value=value):
                f=fixture(); f[3]['prices']['output_per_million']=value
                with self.assertRaises(m.MetricsError): row(f)

    def test_ambiguous_cost_and_prices_rejected(self):
        f=fixture(); f[3]['cost']={'currency':'USD','amount':'1','complete':True,'basis':'invoice'}
        with self.assertRaises(m.MetricsError): row(f)

    def test_negative_memory_rejected(self):
        f=fixture()+[event('memory_sample',5,worker_id='root',process_id='p1',scope='process_lifetime',peak_rss_bytes=-1)]
        with self.assertRaises(m.MetricsError): row(f)

    def test_process_peaks_never_summed(self):
        f=fixture()+[event('memory_sample',5,worker_id='root',process_id='p1',scope='run_isolated_process',peak_rss_bytes=100,context_tokens=300,storage_bytes=800),event('memory_sample',6,worker_id='root',process_id='p2',scope='run_isolated_process',peak_rss_bytes=200)]
        r=row(f)['memory']; self.assertEqual(r['max_observed_isolated_process_peak_rss_bytes'],200); self.assertIsNone(r['simultaneous_total_peak_rss_bytes'])
        self.assertEqual(r['processes'][0]['context_tokens_max'],300); self.assertEqual(r['processes'][0]['storage_bytes_max'],800)

    def test_lifetime_peak_not_claimed_as_run_peak(self):
        f=fixture()+[event('memory_sample',5,worker_id='root',process_id='p1',scope='process_lifetime',peak_rss_bytes=200)]
        self.assertIsNone(row(f)['memory']['max_observed_isolated_process_peak_rss_bytes'])

    def test_unknown_memory_stays_null(self):
        self.assertIsNone(row()['memory']['max_observed_isolated_process_peak_rss_bytes'])
        self.assertEqual(row()['memory']['workers_with_rss'],0)

    def test_mixed_currencies_not_added(self):
        f=fixture()+[event('attempt_start',3,attempt_id='tool',worker_id='root',kind='tool',name='search',usage_scope='exclusive'),event('attempt_end',4,attempt_id='tool',status='completed',cost={'currency':'EUR','amount':'1','complete':True,'basis':'invoice'})]
        r=row(f); self.assertEqual(len(r['costs']),2); self.assertFalse(r['cost_complete']); self.assertTrue(all(c['complete_total'] is None for c in r['costs']))

    def test_unordered_shards_same_result(self):
        self.assertEqual(row(),row(list(reversed(fixture()))))

    def test_negative_duration_rejected(self):
        f=fixture(); f[3]['at']='2026-10-11T00:00:01Z'
        with self.assertRaises(m.MetricsError): row(f)

    def test_naive_timestamp_rejected(self):
        f=fixture(); f[0]['at']='2026-10-11T00:00:00'
        with self.assertRaises(m.MetricsError): row(f)

    def test_offset_timestamps_resolve_same_instant(self):
        f=fixture(); f[0]['at']='2026-10-11T01:00:00+01:00'
        self.assertEqual(row(f)['wall_seconds'],10)

    def test_data_cutoff_rejects_later_events(self):
        f=fixture(); f[-1]['data_cutoff']='2026-10-11T00:00:03Z'
        with self.assertRaises(m.MetricsError): row(f)

    def test_private_payload_fields_rejected(self):
        for key in ('prompt','response','tool_arguments','api_key','exception'):
            f=fixture(); f[2][key]='not allowed'
            with self.assertRaises(m.MetricsError): row(f)

    def test_groups_do_not_mix_mode_cache_status_or_synthetic(self):
        all_events=[]
        for index, changes in enumerate(({}, {'analysis_mode':'DEEP'},{'cache_state':'warm'},{'synthetic':False})):
            f=fixture(); f[0].update(changes)
            for e in f: e['run_id']=f'r{index}'; e['event_id']=f'{index}-'+e['event_id']
            all_events+=f
        r=m.aggregate(all_events); self.assertEqual(len(r['groups']),4); self.assertTrue(all(g['n_runs']==1 for g in r['groups']))

    def test_average_complete_n_excludes_unknown_and_partial(self):
        f=fixture(); second=copy.deepcopy(f)
        for e in second: e['run_id']='r2'; e['event_id']='other-'+e['event_id']
        second[3]['token_usage']=None; second[3]['prices']=None
        g=m.aggregate(f+second)['groups'][0]; self.assertEqual(g['n_runs'],2); self.assertEqual(g['metrics']['output_tokens']['n'],1); self.assertEqual(g['metrics']['output_tokens']['mean'],500)

    def test_ledger_reopen_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger.jsonl'; ledger=m.Ledger(path)
            for e in fixture(): ledger.emit(e)
            ledger=m.Ledger(path); self.assertFalse(ledger.emit(fixture()[0])); self.assertEqual(len(m.read_events([path])),5)

    def test_truncated_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger.jsonl'; path.write_text('{"unfinished":')
            with self.assertRaises(m.MetricsError): m.Ledger(path)

    def test_nan_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger.jsonl'; path.write_text('{"x":NaN}\n')
            with self.assertRaises(m.MetricsError): m.read_events([path])

    def test_adapter_records_failure_without_exception_payload(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger.jsonl'; recorder=m.RunRecorder(m.Ledger(path),'adapter').start('synthetic','SCREEN',synthetic=True)
            with self.assertRaisesRegex(RuntimeError,'private payload'):
                with recorder.attempt('tool','fixture'):
                    raise RuntimeError('private payload')
            recorder.finish('failed','partial'); data=path.read_text()
            self.assertNotIn('private payload',data); self.assertEqual(m.aggregate(m.read_events([path]))['runs'][0]['attempt_status_counts']['failed'],1)

    def test_adapter_records_cancel_and_rethrows(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger'; recorder=m.RunRecorder(m.Ledger(path),'adapter').start('synthetic','SCREEN',synthetic=True)
            with self.assertRaises(KeyboardInterrupt):
                with recorder.attempt('tool','fixture'): raise KeyboardInterrupt()
            recorder.finish('cancelled','partial')
            self.assertEqual(m.aggregate(m.read_events([path]))['runs'][0]['attempt_status_counts']['cancelled'],1)

    def test_cli_preserves_exit_status_and_emits_report_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); command=[sys.executable,'-I','-B',str(Path(m.__file__)),'run-command','--ledger',str(p/'run.jsonl'),'--run-id','command','--company-id','synthetic','--mode','SCREEN','--synthetic','--output-dir',str(p/'report'),'--',sys.executable,'-I','-B','-c','raise SystemExit(7)']
            result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual(result.returncode,7,result.stderr); self.assertIn('| Company / run |',result.stdout)
            data=json.loads((p/'report/metrics.json').read_text()); r=data['runs'][0]
            self.assertEqual(r['status'],'failed'); self.assertFalse(r['final_response_included']); self.assertEqual(r['wrapper_attempt_count'],1)
            self.assertTrue((p/'report/dashboard.html').is_file())

    def test_cli_missing_command_emits_no_false_success(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); result=subprocess.run([sys.executable,'-I','-B',str(Path(m.__file__)),'run-command','--ledger',str(p/'run.jsonl'),'--run-id','command','--company-id','synthetic','--mode','SCREEN','--synthetic','--output-dir',str(p/'report'),'--','/nonexistent/vera-command'],capture_output=True,text=True)
            self.assertEqual(result.returncode,127,result.stderr)
            self.assertEqual(json.loads((p/'report/metrics.json').read_text())['runs'][0]['status'],'failed')

    def test_inclusive_total_survives_unknown_cache_split(self):
        f=fixture(); f[3]['token_usage']['cached_input_tokens']=None
        r=row(f); self.assertEqual(r['tokens']['total_input_tokens']['known_subtotal'],1000)
        self.assertEqual(r['tokens']['total_tokens']['known_subtotal'],1500)
        self.assertTrue(r['tokens']['total_tokens']['complete']); self.assertFalse(r['tokens']['uncached_input_tokens']['complete'])

    def test_total_exclusive_input_requires_cached_count(self):
        f=fixture(); f[3]['token_usage'].update(input_includes_cached=False,cached_input_tokens=None)
        self.assertIsNone(row(f)['tokens']['total_tokens']['known_subtotal'])

    def test_cutoff_latency_separate_from_closure(self):
        f=fixture(); f[-1]['at']='2026-10-11T00:00:20Z'
        r=row(f); self.assertEqual(r['wall_seconds'],10); self.assertEqual(r['closure_wall_seconds'],20)

    def test_model_and_collection_scopes_split_cohorts(self):
        original=fixture(); all_events=[]
        for i in range(4):
            f=copy.deepcopy(original)
            for e in f: e['event_id']=f'{i}-'+e['event_id']; e['run_id']=f'run-{i}'
            if i==1: f[2]['model_version']='v2'
            if i==2: f[0]['collection_source']='manual'
            if i==3: f[-1]['final_response_included']=False
            all_events+=f
        self.assertEqual(len(m.aggregate(all_events)['groups']),4)

    def test_group_coverage_and_quantiles(self):
        g=m.aggregate(fixture())['groups'][0]
        self.assertEqual(g['metrics']['wall_seconds']['p95'],10)
        self.assertEqual(g['metrics']['total_tokens']['missing_count'],0)
        self.assertEqual(g['metrics']['tool_calls']['n'],1)

    def test_zero_unobserved_tools_are_unknown(self):
        f=fixture(); f[-1]['capture_status']='unavailable'
        r=row(f); self.assertIsNone(r['tool_calls']['known_subtotal']); self.assertIsNone(r['tool_calls']['distinct_tool_count'])

    def test_distinct_tools_differs_from_retries(self):
        f=fixture()
        for n in range(2):
            f += [event('attempt_start',3,f's{n}',attempt_id=f't{n}',worker_id='root',kind='tool',name='search',usage_scope='exclusive'),event('attempt_end',4,f'e{n}',attempt_id=f't{n}',status='completed')]
        r=row(f); self.assertEqual(r['tool_calls']['known_subtotal'],2); self.assertEqual(r['tool_calls']['distinct_tool_count'],1)

    def test_memory_group_preserves_scope_method_and_platform(self):
        f=fixture()+[event('memory_sample',5,worker_id='root',process_id='p',scope='process_lifetime',peak_rss_bytes=123)]
        g=m.aggregate(f)['groups'][0]['memory_peak_groups'][0]
        self.assertEqual((g['scope'],g['method'],g['platform']),('process_lifetime','fixture','synthetic'))
        self.assertEqual(g['n'],1); self.assertEqual(g['mean'],123)

    def test_memory_measurement_end_must_match_observation(self):
        f=fixture()+[event('memory_sample',5,worker_id='root',process_id='p',scope='process_lifetime',peak_rss_bytes=123)]
        f[-1]['measurement_end']='2026-10-11T00:00:06Z'
        with self.assertRaises(m.MetricsError): row(f)

    def test_blocked_status_kept_separate(self):
        f=fixture(); f[-1]['status']='blocked'
        self.assertEqual(m.aggregate(f)['groups'][0]['status'],'blocked')

    def test_all_cost_basis_provenance_retained(self):
        f=fixture(); f[3]['prices']=None; f[3]['cost']={'currency':'USD','amount':'2.25','complete':True,'basis':'invoice','price_version':None}
        r=row(f); self.assertEqual(r['costs'][0]['complete_total'],'2.25'); self.assertEqual(r['costs'][0]['basis'],['invoice'])

    def test_partial_invoice_is_known_subtotal_only(self):
        f=fixture(); f[3]['prices']=None; f[3]['cost']={'currency':'USD','amount':'2.25','complete':False,'basis':'invoice'}
        r=row(f); self.assertIsNone(r['costs'][0]['complete_total']); self.assertEqual(r['costs'][0]['known_subtotal'],'2.25')

    def test_no_charge_cannot_be_positive(self):
        f=fixture(); f[3]['prices']=None; f[3]['cost']={'currency':'USD','amount':'1','complete':True,'basis':'explicit_no_charge'}
        with self.assertRaises(m.MetricsError): row(f)

    def test_empty_ledger_has_no_invented_runs(self):
        report=m.aggregate([]); self.assertEqual(report['runs'],[]); self.assertEqual(report['groups'],[])

    def test_unknown_fields_rejected_at_all_levels(self):
        f=fixture(); f[3]['token_usage']['prompt']='forbidden'
        with self.assertRaises(m.MetricsError): row(f)

    def test_same_request_across_company_runs_rejected(self):
        f=fixture(); f[2]['provider_request_id']='same-request'; other=copy.deepcopy(f)
        for e in other: e['run_id']='other-run'; e['event_id']='other-'+e['event_id']
        with self.assertRaises(m.MetricsError): m.aggregate(f+other)

    def test_price_groups_exclude_incompatible_from_missing_denominator(self):
        f=fixture(); other=copy.deepcopy(f)
        for e in other: e['run_id']='other-run'; e['event_id']='other-'+e['event_id']
        other[3]['prices']['price_version']='synthetic-v2'
        groups=m.aggregate(f+other)['groups'][0]['costs']
        self.assertEqual(len(groups),2)
        for g in groups:
            self.assertEqual((g['n'],g['eligible_n'],g['missing_count'],g['excluded_incompatible_count']),(1,1,0,1))

    def test_memory_groups_exclude_incompatible_denominator(self):
        f=fixture()+[event('memory_sample',5,worker_id='root',process_id='p',scope='process_lifetime',peak_rss_bytes=1)]
        other=copy.deepcopy(f)
        for e in other: e['run_id']='other-run'; e['event_id']='other-'+e['event_id']
        other[-1]['scope']='run_isolated_process'
        groups=m.aggregate(f+other)['groups'][0]['memory_peak_groups']
        for g in groups:
            self.assertEqual((g['n'],g['eligible_n'],g['missing_count'],g['excluded_incompatible_count']),(1,1,0,1))

    def test_table_shows_cutoff_final_response_and_memory_provenance(self):
        f=fixture()+[event('memory_sample',5,worker_id='root',process_id='p',scope='process_lifetime',peak_rss_bytes=1)]
        f[4]['final_response_included']=False
        table=m.render_table(m.aggregate(f))
        for expected in ('Data cutoff','excluded','process_lifetime; fixture; synthetic','Total tokens'):
            self.assertIn(expected,table)

    def test_ledger_replay_not_affected_by_mutating_original_event(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger'; ledger=m.Ledger(path); e=fixture()[3]; ledger.emit(e)
            e['token_usage']['output_tokens']=999
            with self.assertRaises(m.MetricsError): ledger.emit(e)

    def test_example_reports_reproduce_exactly(self):
        base=Path(__file__).parent/'examples'; report=m.aggregate(m.read_events([base/'synthetic.jsonl']))
        self.assertEqual(report,json.loads((base/'metrics.json').read_text()))
        self.assertEqual(m.render_table(report),(base/'metrics.md').read_text())
        self.assertEqual(m.render_html(report),(base/'dashboard.html').read_text())
        self.assertTrue(all(r['synthetic'] for r in report['runs']))

    def test_event_schema_lists_only_supported_event_types(self):
        schema=json.loads(Path(__file__).with_name('event.schema.json').read_text())
        self.assertEqual({item['properties']['type']['const'] for item in schema['oneOf']},set(m.FIELDS))
        self.assertTrue(all(item['additionalProperties'] is False for item in schema['oneOf']))

    def test_partial_cost_table_retains_billing_basis(self):
        f=fixture(); f[3]['prices']['output_per_million']=None
        self.assertIn('known subtotal only; estimate',m.render_table(m.aggregate(f)))
        f[3]['prices']=None; f[3]['cost']={'currency':'USD','amount':'1','complete':False,'basis':'invoice'}
        self.assertIn('known subtotal only; invoice',m.render_table(m.aggregate(f)))

    def test_report_has_mandatory_table_and_static_dashboard(self):
        r=m.aggregate(fixture()); self.assertIn('Input uncached',m.render_table(r)); self.assertIn('process',m.render_table(r).lower()) if r['runs'][0]['memory']['processes'] else None
        self.assertIn('<table>',m.render_html(r)); self.assertNotIn('<script',m.render_html(r))


if __name__=='__main__': unittest.main()
