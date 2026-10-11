import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import preparation_audit as a

class IndependentPreparationReview(unittest.TestCase):
    def audit(self,rows):return a.audit_rows(rows,source_sha256='synthetic')
    def row(self,**extra):
        r={'round_id':'r','canonical_company_id':'c','completion_date':'2021-01-01','censor_date':'2022-01-01','last_positive_date':'2022-01-01','offering_year':'2021','offering_year_status':'BOUNDED_YEAR'}
        r.update(extra);return r
    def assert_unadjudicated(self,result,count):
        s=result['summary'];self.assertEqual(s['input_rows'],count);self.assertEqual(s['output_dispositions'],count)
        self.assertIsNone(s['eligible_row_count']);self.assertIsNone(s['ineligible_row_count'])
        self.assertEqual(s['prepared_histories_created'],0);self.assertEqual(s['states_or_event_times_synthesized'],0)
        for row in result['rows']:
            self.assertEqual(row['prepared_history_status'],'NOT_CONSTRUCTED')
            self.assertEqual(row['evidence_eligibility'],'NOT_DETERMINED')
            for req in row['requirements'].values():self.assertEqual(req['review_status'],'NOT_ADJUDICATED_BY_SCHEMA_AUDIT')
    def test_missing_and_fully_populated_review_fields_never_adjudicate(self):
        full=self.row()
        for req in a.REQUIREMENTS.values():
            for field in req['review_fields']:full[field]='APPROVED'
        full.update(reviewed_initial_state='PRE',reviewed_exact_transition_sequence='[]',initial_post_policy='baseline_qualified',prepared_history_disposition='ELIGIBLE')
        r=self.audit([{},full]);self.assert_unadjudicated(r,2)
        self.assertEqual(r['rows'][1]['mechanical_input_status'],'FLAT_SCHEMA_PARSEABLE_FOR_REVIEW')
        for row in r['rows']:
            self.assertTrue(set(req['reason'] for req in a.REQUIREMENTS.values()) <= {x['code'] for x in row['gaps']})
    def test_prior_terminal_success_later_financing_never_reset(self):
        r=self.audit([self.row(success_date='2020-01-01',closure_date='2020-12-31',terminal_event_type='CLOSURE')])
        self.assert_unadjudicated(r,1)
        gaps=r['rows'][0]['gaps'];self.assertEqual(sum(x['code']=='DATE_BEFORE_ORIGIN' for x in gaps),2)
        self.assertFalse(any(k in r['rows'][0] for k in ('initial_state','transitions','event_time','history')))
    def test_duplicate_ids_preserve_all_rows(self):
        rows=[self.row(),self.row(censor_date='2023-01-01'),self.row(round_id='another')]
        r=self.audit(rows);self.assert_unadjudicated(r,3)
        self.assertEqual([x['source_row_ordinal_1based'] for x in r['rows']],[1,2,3])
        self.assertEqual(r['summary']['gap_affected_row_counts']['DUPLICATE_ROUND_ID'],2)
        for source,result in zip(rows,r['rows']):self.assertEqual(result['source_row_sha256'],a.sha_bytes(a.canonical_bytes(source)))
    def test_ties_intervals_unknown_values_and_censor_conflicts(self):
        row=self.row(success_date='2023-01-01',closure_date='2023-01-01',terminal_event_midpoint_for_primary='2023-01-01',terminal_event_interval_start='2022-01-01',terminal_event_interval_end='2024-01-01',terminal_event_date_status='INTERVAL_KNOWN_YEAR_ONLY',terminal_event_type='ACQUISITION_VALUE_UNKNOWN')
        result=self.audit([row]);self.assert_unadjudicated(result,1)
        codes={x['code'] for x in result['rows'][0]['gaps']}
        self.assertTrue({'TIED_SUCCESS_TERMINAL_REQUIRES_TYPED_REVIEW','TERMINAL_INTERVAL_NOT_EXACT','UNKNOWN_VALUE_ACQUISITION_NOT_AUTOMATIC_SUCCESS_OR_CLOSURE','FINANCING_BEYOND_AFFIRMATIVE_OPERATION','EVENT_BEYOND_SUPPLIED_CENSOR'} <= codes)
        self.assertEqual(result['summary']['gap_occurrence_counts']['EVENT_BEYOND_SUPPLIED_CENSOR'],3)
        self.assertEqual(result['summary']['gap_affected_row_counts']['EVENT_BEYOND_SUPPLIED_CENSOR'],1)
    def test_invalid_and_disagreeing_dates_not_selected(self):
        result=self.audit([self.row(followup_months='999'),self.row(round_id='bad',followup_months='nan',success_date='2021',terminal_event_interval_start='2023-01-01',terminal_event_interval_end='2022-01-01')])
        self.assert_unadjudicated(result,2)
        self.assertIn('FOLLOWUP_DATE_NUMERIC_MISMATCH',{x['code'] for x in result['rows'][0]['gaps']})
        self.assertTrue({'INVALID_FOLLOWUP','INVALID_DATE','REVERSED_TERMINAL_INTERVAL'} <= {x['code'] for x in result['rows'][1]['gaps']})
    def test_repeated_company_success_flags_do_not_qualify(self):
        rows=[self.row(round_id='a',success_date='2021-06-01',success_type='qualified_priced_followon',success_evidence_url='https://example.invalid',success_evidence_sha256='synthetic'),self.row(round_id='b'),self.row(round_id='c',canonical_company_id='different')]
        result=self.audit(rows);self.assert_unadjudicated(result,3)
        counts=result['summary']['gap_affected_row_counts']
        self.assertEqual(counts['MULTI_ROUND_COMPANY_REQUIRES_INDEX_SPECIFIC_ENTRY_REVIEW'],2)
        self.assertEqual(counts['SUCCESS_EVENT_LABEL_REQUIRES_INDEX_EVIDENCE_REVIEW'],1)
        self.assertEqual(len(result['targeted_review_queue']),2)
    def test_known_year_outside_scope_is_not_unknown(self):
        result=self.audit([self.row(offering_year='2026')]);self.assert_unadjudicated(result,1)
        codes={x['code'] for x in result['rows'][0]['gaps']}
        self.assertIn('OFFERING_YEAR_OUTSIDE_STUDY_SCOPE',codes)
        self.assertNotIn('OFFERING_YEAR_UNRESOLVED',codes)
    def test_input_hash_guard_and_csv_width_errors(self):
        for data in (b'round_id,round_id\nr,r\n',b'round_id,canonical_company_id\nr\n',b'round_id\nr,c\n'):
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/'ledger.csv';p.write_bytes(data);out=Path(td)/'out'
                with self.assertRaises(ValueError):a.audit_file(p,a.sha_bytes(data),out)
                self.assertEqual(p.read_bytes(),data);self.assertFalse(out.exists())
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'ledger.csv';p.write_bytes(b'round_id\nr\n');out=Path(td)/'out'
            with self.assertRaisesRegex(ValueError,'input_ledger_hash_mismatch'):a.audit_file(p,'wrong',out)
            self.assertFalse(out.exists())
    def test_immutable_rerun_conflict_and_private_bindings(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'ledger.csv';out=Path(td)/'out';rows=[self.row()]
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            data=p.read_bytes();manifest=a.audit_file(p,a.sha_bytes(data),out)
            before={x.name:x.read_bytes() for x in out.iterdir()}
            a.audit_file(p,a.sha_bytes(data),out)
            self.assertEqual(before,{x.name:x.read_bytes() for x in out.iterdir()})
            self.assertEqual(p.read_bytes(),data)
            for name,digest in manifest['outputs'].items():self.assertEqual(a.sha_bytes((out/name).read_bytes()),digest)
            self.assertFalse(manifest['eligibility_adjudicated']);self.assertFalse(manifest['canonical_outputs_modified'])
            self.assertEqual(len((out/'row-dispositions.jsonl').read_text().splitlines()),1)
            (out/'targeted-review-queue.json').write_text('conflict')
            conflicted={x.name:x.read_bytes() for x in out.iterdir()}
            with self.assertRaisesRegex(ValueError,'immutable_output_conflict'):a.audit_file(p,a.sha_bytes(data),out)
            self.assertEqual(conflicted,{x.name:x.read_bytes() for x in out.iterdir()})
            self.assertEqual(p.read_bytes(),data)

if __name__=='__main__':unittest.main(verbosity=2)
