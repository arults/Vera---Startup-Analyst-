"""Synthetic tests; no actual entity data are embedded here."""
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from preparation_audit import (
    REQUIREMENTS, PRIORITIES, DAYS_PER_MONTH, audit_rows, audit_file,
    write_audit, sha_bytes,
)


def row(**changes):
    from datetime import date
    value = dict(round_id='synthetic-round', canonical_company_id='synthetic-company',
        platform='republic_europe', offering_year='2020', offering_year_status='BOUNDED_YEAR',
        completion_date='2020-01-01', censor_date='2022-01-01', last_positive_date='2022-01-01',
        followup_months=str((date(2022,1,1)-date(2020,1,1)).days/DAYS_PER_MONTH),
        success_date='', success_type='', success_evidence_url='', success_evidence_sha256='',
        closure_date='', terminal_event_type='', terminal_event_interval_start='',
        terminal_event_interval_end='', terminal_event_midpoint_for_primary='', terminal_event_date_status='')
    value.update(changes)
    return value


def codes(result):
    return {g['code'] for g in result['rows'][0]['gaps']}


def inspect(value):
    return audit_rows([value], source_sha256='0'*64)


class PreparationAuditTests(unittest.TestCase):
    def test_base_shape_is_reviewable_never_eligible(self):
        result = inspect(row())
        item=result['rows'][0]
        self.assertEqual(item['mechanical_input_status'],'FLAT_SCHEMA_PARSEABLE_FOR_REVIEW')
        self.assertEqual(item['evidence_eligibility'],'NOT_DETERMINED')
        self.assertEqual(item['prepared_history_status'],'NOT_CONSTRUCTED')
        self.assertIsNone(result['summary']['eligible_row_count'])
        self.assertIsNone(result['summary']['ineligible_row_count'])
        self.assertEqual(result['summary']['states_or_event_times_synthesized'],0)
        self.assertEqual(codes(result),{r['reason'] for r in REQUIREMENTS.values()})

    def test_supplied_review_labels_are_not_self_authenticating(self):
        base=row()
        for requirement in REQUIREMENTS.values():
            for field in requirement['review_fields']:
                base[field]='APPROVED'
        base['reviewed_initial_state']='operating_pre_success'
        result=inspect(base)
        self.assertEqual(result['rows'][0]['evidence_eligibility'],'NOT_DETERMINED')
        self.assertEqual(codes(result),{r['reason'] for r in REQUIREMENTS.values()})
        for requirement in result['rows'][0]['requirements'].values():
            self.assertEqual(requirement['review_status'],'NOT_ADJUDICATED_BY_SCHEMA_AUDIT')

    def test_no_automatic_pre_or_post_from_success_presence(self):
        for value in [row(),row(success_date='2021-01-01',success_type='qualified_priced_followon',success_evidence_url='https://example.com/synthetic',success_evidence_sha256='a'*64)]:
            result=inspect(value)
            self.assertIn('INITIAL_STATE_REVIEW_NO_AUTOMATIC_PRE_OR_POST',codes(result))
            self.assertIn('INDEX_QUALIFICATION_AND_TARGET_REVIEW',codes(result))
            self.assertNotIn('initial_state',result['rows'][0])
            self.assertEqual(result['summary']['prepared_histories_created'],0)

    def test_funded_date_and_identity_are_not_inferred(self):
        result=inspect(row())
        self.assertIn('FUNDED_CLOCK_AND_ROUND_IDENTITY_REVIEW',codes(result))
        self.assertTrue(result['rows'][0]['requirements']['round_identity_and_funded_origin']['existing_field_presence']['completion_date']['populated'])

    def test_tied_success_terminal_refuses_automatic_cause(self):
        result=inspect(row(success_date='2021-01-01',terminal_event_midpoint_for_primary='2021-01-01',terminal_event_type='TERMINAL_SUCCESS_EXIT'))
        self.assertIn('TIED_SUCCESS_TERMINAL_REQUIRES_TYPED_REVIEW',codes(result))
        self.assertEqual(result['summary']['states_or_event_times_synthesized'],0)

    def test_interval_not_mapped_to_midpoint_or_boundary(self):
        value=row(terminal_event_type='ACQUISITION_VALUE_UNKNOWN',terminal_event_interval_start='2021-01-01',terminal_event_interval_end='2021-12-31',terminal_event_midpoint_for_primary='2021-07-02',terminal_event_date_status='INTERVAL_KNOWN_YEAR_ONLY')
        frozen=copy.deepcopy(value);result=inspect(value)
        self.assertIn('TERMINAL_INTERVAL_NOT_EXACT',codes(result))
        self.assertIn('UNKNOWN_VALUE_ACQUISITION_NOT_AUTOMATIC_SUCCESS_OR_CLOSURE',codes(result))
        self.assertEqual(value,frozen)
        self.assertNotIn('transitions',result['rows'][0])

    def test_unknown_terminal_label_not_auto_converted(self):
        for terminal in ['', 'UNKNOWN_TERMINAL', 'terminal_other']:
            result=inspect(row(terminal_event_type=terminal,terminal_event_midpoint_for_primary='2021-01-01'))
            self.assertIn('UNRECOGNIZED_TERMINAL_TYPE_REQUIRES_REVIEW',codes(result))

    def test_source_collection_boundaries(self):
        cases=[
            ({'round_id':''},'MISSING_ROUND_ID'),
            ({'canonical_company_id':''},'MISSING_COMPANY_ID'),
            ({'completion_date':''},'MISSING_COMPLETION_DATE'),
            ({'censor_date':''},'MISSING_OBSERVATION_DATE'),
            ({'success_date':'2019-12-01'},'DATE_BEFORE_ORIGIN'),
            ({'terminal_event_interval_start':'2021-12-31','terminal_event_interval_end':'2021-01-01'},'REVERSED_TERMINAL_INTERVAL'),
            ({'success_date':'2022-02-01'},'FINANCING_BEYOND_AFFIRMATIVE_OPERATION'),
            ({'closure_date':'2022-02-01'},'EVENT_BEYOND_SUPPLIED_CENSOR'),
            ({'followup_months':'1'},'FOLLOWUP_DATE_NUMERIC_MISMATCH'),
            ({'success_date':'2021-01-01'},'SUCCESS_SOURCE_BINDING_INCOMPLETE'),
            ({'offering_year_status':'YEAR_UNRESOLVED','offering_year':''},'OFFERING_YEAR_UNRESOLVED'),
            ({'offering_year':'2019'},'OFFERING_YEAR_OUTSIDE_STUDY_SCOPE'),
        ]
        for change,code in cases:
            with self.subTest(code=code):
                self.assertIn(code,codes(inspect(row(**change))))

    def test_exact_calendar_date_validation(self):
        for value in ['20210101','2021-W01-1','2021-02-30',True,20210101,'2021-01']:
            with self.subTest(value=value):
                self.assertIn('INVALID_DATE',codes(inspect(row(success_date=value))))

    def test_bad_followup_types_not_coerced(self):
        for value in ['nan','inf','-1',True,{},float('inf')]:
            with self.subTest(value=str(value)):
                # JSON serialization is deliberately strict for non-JSON numeric inputs.
                if isinstance(value,float):
                    with self.assertRaises(ValueError):
                        inspect(row(followup_months=value))
                else:
                    self.assertIn('INVALID_FOLLOWUP',codes(inspect(row(followup_months=value))))

    def test_repeated_company_rounds_preserved_and_duplicate_round_flagged(self):
        values=[row(round_id='r1'),row(round_id='r2'),row(round_id='r1')]
        result=audit_rows(values,source_sha256='0'*64)
        self.assertEqual(len(result['rows']),3)
        self.assertEqual([r['source_row_ordinal_1based'] for r in result['rows']],[1,2,3])
        self.assertEqual(result['summary']['gap_affected_row_counts']['DUPLICATE_ROUND_ID'],2)
        self.assertEqual(result['rows'][1]['mechanical_input_status'],'FLAT_SCHEMA_PARSEABLE_FOR_REVIEW')

    def test_missing_schema_and_blank_value_are_different(self):
        first=audit_rows([row()],source_sha256='0'*64)
        value=row(reviewed_initial_state='')
        second=audit_rows([value],source_sha256='0'*64)
        self.assertIn('reviewed_initial_state',first['summary']['requirements_schema_map']['initial_state']['review_fields_absent'])
        self.assertIn('reviewed_initial_state',second['summary']['requirements_schema_map']['initial_state']['review_fields_present'])
        field=second['rows'][0]['requirements']['initial_state']['review_field_presence']['reviewed_initial_state']
        self.assertEqual(field,{'in_schema':True,'populated':False})
        self.assertEqual(second['rows'][0]['evidence_eligibility'],'NOT_DETERMINED')

    def test_deterministic_no_mutation_and_all_row_accounting(self):
        values=[row(round_id='r1'),row(round_id='r2',offering_year_status='YEAR_UNRESOLVED')]
        before=copy.deepcopy(values)
        first=audit_rows(values,source_sha256='1'*64)
        self.assertEqual(first,audit_rows(values,source_sha256='1'*64))
        self.assertEqual(values,before)
        self.assertEqual(first['summary']['input_rows'],first['summary']['output_dispositions'])
        self.assertEqual(first['targeted_review_queue'][0]['round_id_as_supplied'],'r2')

    def test_empty_inventory_has_no_eligibility_claim(self):
        result=audit_rows([],source_sha256='0'*64)
        self.assertEqual(result['summary']['input_rows'],0)
        self.assertEqual(result['rows'],[])
        self.assertIsNone(result['summary']['eligible_row_count'])

    def test_all_hold_codes_have_executable_fixtures(self):
        values=[row(),row(round_id=''),row(canonical_company_id=''),row(completion_date=''),row(censor_date=''),row(success_date='nonsense'),row(followup_months='nan'),row(success_date='2019-01-01'),row(terminal_event_interval_start='2022-01-01',terminal_event_interval_end='2021-01-01'),row(success_date='2021-01-01',terminal_event_midpoint_for_primary='2021-01-01'),row(terminal_event_type='ACQUISITION_VALUE_UNKNOWN'),row(success_date='2022-03-01'),row(followup_months='1'),row(offering_year_status='UNKNOWN'),row(terminal_event_type='ALIEN'),row(offering_year='2019')]
        result=audit_rows(values,source_sha256='0'*64)
        seen={gap['code'] for item in result['rows'] for gap in item['gaps']}
        self.assertTrue(set(PRIORITIES)<=seen,set(PRIORITIES)-seen)
        self.assertTrue({r['reason'] for r in REQUIREMENTS.values()}<=seen)

    def test_immutable_outputs_true_noop_and_conflict_fails_before_writes(self):
        result=inspect(row())
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'audit'
            manifest=write_audit(out,result,{'ledger_sha256':'0'*64})
            before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in out.iterdir()}
            self.assertEqual(manifest,write_audit(out,result,{'ledger_sha256':'0'*64}))
            self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in out.iterdir()})
            modified=copy.deepcopy(result);modified['summary']['new']='different'
            with self.assertRaisesRegex(ValueError,'immutable_output_conflict'):
                write_audit(out,modified,{'ledger_sha256':'0'*64})
            self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in out.iterdir()})
            for name,digest in manifest['outputs'].items():
                self.assertEqual(sha_bytes((out/name).read_bytes()),digest)
            restored=[json.loads(line) for line in (out/'row-dispositions.jsonl').read_text().splitlines()]
            self.assertEqual(restored,result['rows'])

    def test_file_input_hash_pin_and_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'synthetic.csv';value=row()
            with source.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(value));writer.writeheader();writer.writerow(value)
            raw=source.read_bytes();digest=sha_bytes(raw)
            with self.assertRaisesRegex(ValueError,'input_ledger_hash_mismatch'):
                audit_file(source,'bad',root/'must-not-exist')
            self.assertFalse((root/'must-not-exist').exists())
            manifest=audit_file(source,digest,root/'versioned-output')
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(manifest['source_bindings']['ledger_sha256'],digest)
            self.assertFalse(manifest['eligibility_adjudicated'])

    def test_malformed_csv_columns_and_width_fail_closed(self):
        for payload in [b'round_id,round_id\na,b\n',b'round_id,canonical_company_id\na\n',b'round_id\na,b\n',b'']:
            with tempfile.TemporaryDirectory() as directory:
                source=Path(directory)/'bad.csv';source.write_bytes(payload)
                with self.assertRaises(ValueError):
                    audit_file(source,sha_bytes(payload),Path(directory)/'output')
                self.assertFalse((Path(directory)/'output').exists())


if __name__=='__main__':
    unittest.main()
