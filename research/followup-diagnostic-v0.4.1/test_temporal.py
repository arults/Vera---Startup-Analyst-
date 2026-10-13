import copy,json,tempfile,unittest
from pathlib import Path
import diagnostic as d
from test_predecessor import fixture

class TemporalCases(unittest.TestCase):
    def setUp(self):
        self.doc=fixture(); self.r=self.doc['observations'][0]
        self.doc['cutoffs']['historical_availability_cutoff']='2020-07-01T00:00:00Z'
    def out(self):
        before=copy.deepcopy(self.doc); result=d.project(self.doc)
        self.assertEqual(before,self.doc)
        self.assertFalse(result['authority_validation_performed']);self.assertFalse(result['estimator_enabled']);self.assertIsNone(result['native_censor_date'])
        row=result['observations'][0]
        self.assertEqual(row['source_observed_time'],self.r['source_observed_time'])
        self.assertEqual(row['supplied_dispositions'],self.r['supplied_dispositions'])
        return row
    def history(self): return self.out()['historical_availability_diagnostic']
    def witness(self,instant='2020-07-01T00:00:00Z'):
        self.r['supplied_availability_witness']={'observed_available_at':instant,'claim_payload_sha256':self.r['claim_payload_sha256'],'review_ref_id':'synthetic-review','basis':'Hypothetical version-specific availability observation'}
    def test_missing_witness_late_retrieval_unknown(self): self.assertEqual(self.history()['status'],'unknown_no_version_bound_witness')
    def test_publication_before_cutoff_does_not_establish_version(self): self.assertEqual(self.history()['status'],'unknown_no_version_bound_witness')
    def test_equal_witness(self):
        self.witness();h=self.history();self.assertEqual(h['status'],'supplied_version_witness_on_or_before_cutoff');self.assertFalse(h['witness_bytes_verified']);self.assertFalse(h['authority_validated'])
    def test_offset_equal(self):
        self.witness('2020-07-01T02:00:00+02:00');self.assertEqual(self.history()['status'],'supplied_version_witness_on_or_before_cutoff')
    def test_late_witness_unknown_not_unavailable(self):
        self.witness('2021-01-01T00:00:00Z');self.assertEqual(self.history()['status'],'unknown_witness_after_cutoff');self.assertFalse(self.history()['first_availability_inferred'])
    def test_naive_witness(self):
        self.witness('2020-06-01T00:00:00');self.assertEqual(self.history()['status'],'invalid_or_unbound_witness')
    def test_stale_claim(self):
        self.witness();self.r['supplied_availability_witness']['claim_payload_sha256']='b'*64;self.assertEqual(self.history()['status'],'invalid_or_unbound_witness')
    def test_stale_review(self):
        self.witness();self.r['review_refs'][0]['claim_payload_sha256']='b'*64;self.assertEqual(self.history()['status'],'invalid_or_unbound_witness')
    def test_duplicate_review_ambiguous(self):
        self.witness();self.r['review_refs']*=2;self.assertEqual(self.history()['status'],'invalid_or_unbound_witness')
    def test_missing_review(self):
        self.witness();self.r['review_refs']=[];self.assertEqual(self.history()['status'],'invalid_or_unbound_witness')
    def test_no_request_remains_not_requested(self):
        self.witness();self.doc['cutoffs']['historical_availability_cutoff']='not_requested';self.assertEqual(self.history()['status'],'not_requested')
    def test_all_source_dates_unknown(self):
        self.r['source_dates']={};report=self.out()['evidence_report_temporal_diagnostic'];self.assertEqual(len(report['unknown_fields']),5)
    def test_report_utc_rollover_after(self):
        self.r['source_dates']['retrieved_at']='2021-01-04T23:30:00-02:00';self.assertIn('retrieved_at',self.out()['evidence_report_temporal_diagnostic']['post_report_fields'])
    def test_report_utc_rollover_before(self):
        self.r['source_dates']['retrieved_at']='2021-01-05T00:30:00+02:00';self.assertEqual(self.out()['evidence_report_temporal_diagnostic']['date_relations']['retrieved_at'],'at_cutoff')
    def test_late_report_date_keeps_retrospective_point(self):
        self.r['source_dates']['reviewed_at']='2030-01-01T00:00:00Z';self.assertEqual(self.out()['operating_time_diagnostic'],'operating_point')
    def test_period_straddles_no_endpoint_or_transaction_gate(self):
        self.r['supplied_dispositions']['operating_interpretation']='operating_period';self.r['source_observed_time']={'kind':'activity_period','start':'2020-12-01','end':'2021-02-01','basis':'Synthetic attributed nontransaction activity sometime in period'}
        row=self.out();self.assertEqual(row['operating_time_diagnostic'],'operating_period');self.assertEqual(row['evidence_report_temporal_diagnostic']['activity_relation']['status'],'straddles_cutoff');self.assertFalse(row['evidence_report_temporal_diagnostic']['activity_relation']['endpoint_observation_inferred'])
    def test_unknown_activity_not_replaced_by_retrieval(self):
        self.r['supplied_dispositions']['operating_interpretation']='unresolved_time';self.r['source_observed_time']={'kind':'unknown'};self.assertEqual(self.out()['source_observed_time'],{'kind':'unknown'})
    def test_malformed_witness_preserved(self):
        self.r['supplied_availability_witness']='unknown';self.assertEqual(self.history()['status'],'invalid_witness')
    def test_independent_cutoffs(self):
        a=self.out();self.doc['cutoffs']['historical_availability_cutoff']='2030-01-01T00:00:00Z';b=self.out();self.assertEqual(a['window_relations'],b['window_relations']);self.assertEqual(a['evidence_report_temporal_diagnostic'],b['evidence_report_temporal_diagnostic'])
    def test_run_binds_witness_bytes_without_authority(self):
        self.witness()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);raw=b'{"synthetic":true}\n';(p/'review.json').write_bytes(raw)
            ref=self.r['review_refs'][0];ref.update(artifact_path='review.json',artifact_sha256=d.digest(raw))
            self.doc['input_bindings']=[{'path':'review.json','sha256':d.digest(raw)}]
            inp=p/'input.json';inp.write_text(json.dumps(self.doc));before=inp.read_bytes()
            out=d.run(inp,p/'output.json');h=out['observations'][0]['historical_availability_diagnostic']
            self.assertTrue(h['witness_bytes_verified']);self.assertFalse(h['authority_validated']);self.assertEqual(before,inp.read_bytes());self.assertEqual(raw,(p/'review.json').read_bytes())
            with self.assertRaises(ValueError):d.run(inp,p/'output.json')
    def test_run_hash_mismatch_fails_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'review.json').write_text('wrong');self.doc['input_bindings']=[{'path':'review.json','sha256':'a'*64}];(p/'input.json').write_text(json.dumps(self.doc));before=(p/'input.json').read_bytes()
            with self.assertRaises(ValueError):d.run(p/'input.json',p/'output.json')
            self.assertFalse((p/'output.json').exists());self.assertEqual(before,(p/'input.json').read_bytes())

if __name__=='__main__': unittest.main()
