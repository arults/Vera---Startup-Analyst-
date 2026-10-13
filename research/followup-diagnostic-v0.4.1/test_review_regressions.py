import json,tempfile,unittest
from pathlib import Path
import test_temporal
import diagnostic as d

class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.case=test_temporal.TemporalCases();self.case.setUp();self.case.witness('2025-01-01T00:00:00Z');self.doc=self.case.doc
    def row(self):return self.case.out()
    def test_witness_after_report_before_historical(self):
        self.doc['cutoffs']['historical_availability_cutoff']='2026-01-01T00:00:00Z';r=self.row()
        self.assertEqual(r['historical_availability_diagnostic']['status'],'supplied_version_witness_on_or_before_cutoff')
        self.assertIn('availability_witness_observed_available_at',r['evidence_report_temporal_diagnostic']['post_report_fields'])
        self.assertIn('SUPPLIED_SOURCE_CLOCK_AFTER_REPORT_CUTOFF',r['holds'])
    def test_witness_after_report_no_historical_request(self):
        self.doc['cutoffs']['historical_availability_cutoff']='not_requested';r=self.row()
        self.assertEqual(r['historical_availability_diagnostic']['status'],'not_requested')
        self.assertIn('availability_witness_observed_available_at',r['evidence_report_temporal_diagnostic']['post_report_fields'])
    def test_unbound_witness_still_report_compared(self):
        self.case.r['supplied_availability_witness']['claim_payload_sha256']='b'*64
        self.assertIn('availability_witness_observed_available_at',self.row()['evidence_report_temporal_diagnostic']['post_report_fields'])
    def test_date_only_witness_not_midnight(self):
        self.case.r['supplied_availability_witness']['observed_available_at']='2020-06-01'
        r=self.row();self.assertEqual(r['evidence_report_temporal_diagnostic']['date_relations']['availability_witness_observed_available_at'],'invalid_instant')
        self.assertEqual(r['historical_availability_diagnostic']['status'],'invalid_or_unbound_witness')
    def test_min_max_utc_overflow(self):
        for instant in ['0001-01-01T00:00:00+01:00','9999-12-31T23:59:00-01:00']:
            with self.subTest(instant=instant):
                self.case.r['source_dates']['retrieved_at']=instant;r=self.row()
                self.assertEqual(r['evidence_report_temporal_diagnostic']['date_relations']['retrieved_at'],'unrepresentable_UTC_date')
                self.assertIn('SUPPLIED_CLOCK_UTC_DATE_UNREPRESENTABLE',r['holds'])
    def test_witness_overflow_retains_payload(self):
        self.case.r['supplied_availability_witness']['observed_available_at']='0001-01-01T00:00:00+01:00'
        self.assertEqual(self.row()['evidence_report_temporal_diagnostic']['date_relations']['availability_witness_observed_available_at'],'unrepresentable_UTC_date')
    def test_entity_source_binding_explicitly_not_evaluated(self):
        r=self.row()
        self.assertFalse(r['historical_availability_diagnostic']['entity_source_binding_evaluated'])
        self.assertFalse(r['evidence_report_temporal_diagnostic']['entity_source_binding_evaluated'])
    def test_extreme_date_run_preserves_bytes(self):
        self.case.r['source_dates']['retrieved_at']='0001-01-01T00:00:00+01:00'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);inp=p/'input.json';inp.write_text(json.dumps(self.doc));raw=inp.read_bytes()
            result=d.run(inp,p/'output.json');self.assertEqual(raw,inp.read_bytes());self.assertTrue((p/'output.json').exists())
            self.assertIn('SUPPLIED_CLOCK_UTC_DATE_UNREPRESENTABLE',result['observations'][0]['holds'])

if __name__=='__main__':unittest.main()
