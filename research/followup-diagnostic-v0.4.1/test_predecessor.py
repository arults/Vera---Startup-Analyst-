"""Synthetic contract controls, no private data and no semantic authority fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import diagnostic as d

def fixture():
    claim={'id':'synthetic-claim','assertion':'Synthetic delivery statement, not real evidence.','origin_family':'synthetic-one-origin'}
    record={'id':'synthetic-observation','original_claim':claim,'claim_payload_sha256':d.digest(d.canonical(claim)),
        'supplied_dispositions':{'source_attribution':'reviewed_attribution','operating_interpretation':'operating_point',
            'native_scope':{'relation':'same_platform_native','source_original_platform':'platform-a','indexed_platform':'platform-a','original_host':'example.invalid','archive_host':None,'mapping_review_ref':'synthetic-map'},
            'index_round_applicability':[{'round_id':'synthetic-round','entry_date':'2020-01-01','disposition':'supported','rationale':'Synthetic relation only'}],
            'independent_state_applicability':'unresolved'},
        'round_mapping_reason':'Explicit synthetic fixture mapping',
        'review_refs':[{'id':'synthetic-review','fixture_only':True,'artifact_path':'synthetic-review.json','artifact_sha256':'a'*64,'claim_payload_sha256':d.digest(d.canonical(claim))}],
        'source_observed_time':{'kind':'point','on':'2020-06-01','basis':'Supplied synthetic temporal review'},
        'source_dates':{'publication_date':'2020-06-02','as_of_date':None,'retrieved_at':'2021-01-02T12:00:00+01:00','reviewed_at':'2021-01-03T12:00:00Z'},
        'missingness':{},'supplied_holds':[]}
    return {'schema':d.SCHEMA,'synthetic':True,'cutoffs':{'analytical_extraction_cutoff':'2020-12-31','evidence_report_cutoff':'2021-01-04','historical_availability_cutoff':'not_requested'},'observations':[record]}

def project(doc):
    before=copy.deepcopy(doc);out=d.project(doc);assert doc==before
    assert out['projection_only'] and not out['authority_validation_performed']
    assert out['native_censor_date'] is None and not out['estimation_eligible']
    assert 'proposed_last_positive_date' not in json.dumps(out)
    assert out['observations'][0]['original_claim']==doc['observations'][0]['original_claim']
    return out['observations'][0]

class ContractCases(unittest.TestCase):
    def setUp(self):
        self.doc=fixture();self.r=self.doc['observations'][0];self.a=self.r['supplied_dispositions']
    def test_01_one_primary_native_point(self):
        out=project(self.doc);self.assertEqual(out['operating_time_diagnostic'],'operating_point');self.assertEqual(len(out['review_refs']),1);self.assertIsNone(out['native_censor_date'])
    def test_02_round_unknown(self):
        self.a['index_round_applicability']=[];out=project(self.doc);self.assertEqual(out['source_observed_time']['on'],'2020-06-01');self.assertEqual(out['window_relations'],[]);self.assertIn('ROUND_MAPPING_UNRESOLVED',out['holds'])
    def test_03_state_unknown(self):
        out=project(self.doc);self.assertEqual(out['operating_time_diagnostic'],'operating_point');self.assertIn('INDEPENDENT_STATE_MAPPING_UNRESOLVED',out['holds'])
    def test_04_other_study_platform(self):
        self.a['native_scope'].update(source_original_platform='platform-b',relation='unresolved',mapping_review_ref=None);out=project(self.doc);self.assertEqual(out['supplied_dispositions']['native_scope']['relation'],'unresolved');self.assertEqual(out['operating_time_diagnostic'],'operating_point')
    def test_05_archive_copy(self):
        self.a['native_scope']['archive_host']='archive.example.invalid';out=project(self.doc);self.assertEqual(out['supplied_dispositions']['native_scope']['original_host'],'example.invalid');self.assertEqual(out['supplied_dispositions']['native_scope']['relation'],'same_platform_native')
    def test_06_outside_point(self):
        self.a['native_scope']['relation']='outside';out=project(self.doc);self.assertEqual(out['operating_time_diagnostic'],'operating_point');self.assertEqual(out['supplied_dispositions']['native_scope']['relation'],'outside')
    def context(self, kind='administration', assertion='Synthetic administrative record'):
        self.r['original_claim'].update(claim_type=kind,assertion=assertion)
        self.r['claim_payload_sha256']=d.digest(d.canonical(self.r['original_claim']))
        self.r['review_refs'][0]['claim_payload_sha256']=self.r['claim_payload_sha256']
        self.a['operating_interpretation']='non_operating_context';out=project(self.doc);self.assertEqual(out['operating_time_diagnostic'],'non_operating_context');self.assertEqual(out['window_relations'][0]['window_status'],'not_computable_from_operating_time');return out
    def test_07_eligible_only(self):
        out=self.context('platform_status','Synthetic Eligible status only');self.assertEqual(out['original_claim']['claim_type'],'platform_status')
    def test_08_financing_only(self):
        out=self.context('priced_equity','Synthetic funded equity round only');self.assertEqual(out['original_claim']['claim_type'],'priced_equity')
    def test_09_financing_plus_operations(self):
        # A separate supplied operating interpretation is required; no prose classifier.
        out=project(self.doc);self.assertEqual(out['operating_time_diagnostic'],'operating_point');self.assertEqual(len(out['review_refs']),1)
    def test_10_legal_or_plans(self):
        for kind,text in [('legal_active','Synthetic registry active'),('future_plan','Synthetic plans to release next year')]:
            with self.subTest(kind=kind):
                out=self.context(kind,text);self.assertEqual(out['original_claim']['claim_type'],kind)
    def period(self):
        self.a['operating_interpretation']='operating_period';self.r['source_observed_time']={'kind':'activity_period','start':'2020-01-01','end':'2020-03-31','basis':'Synthetic sometime-period review'}
    def test_11_period_sometime(self):
        self.period();out=project(self.doc);self.assertNotIn('on',out['source_observed_time']);self.assertFalse(out['window_relations'][0]['endpoint_observation_inferred'])
    def test_12_period_endpoint_explicit(self):
        self.period();second=copy.deepcopy(self.r);second['id']='explicit-endpoint';second['supplied_dispositions']['operating_interpretation']='operating_point';second['source_observed_time']={'kind':'point','on':'2020-03-31','basis':'Separately supplied endpoint review of same source'};self.doc['observations'].append(second);out=d.project(self.doc);self.assertEqual([r['operating_time_diagnostic'] for r in out['observations']],['operating_period','operating_point']);self.assertEqual(out['observations'][0]['original_claim']['origin_family'],out['observations'][1]['original_claim']['origin_family'])
    def test_13_snapshot_present(self):
        self.r['source_observed_time']['basis']='Supplied reviewed contemporaneous snapshot interpretation';out=project(self.doc);self.assertNotEqual(out['source_observed_time']['on'],out['source_dates']['retrieved_at'][:10])
    def test_14_unknown_time(self):
        self.a['operating_interpretation']='unresolved_time';self.r['source_observed_time']={'kind':'unknown'};out=project(self.doc);self.assertEqual(out['operating_time_diagnostic'],'unresolved_time');self.assertNotIn('on',out['source_observed_time'])
    def test_15_malformed_time(self):
        self.period();self.r['source_observed_time']['end']='2019-12-31';out=project(self.doc);self.assertEqual(out['operating_time_diagnostic'],'invalid_time');self.assertIn('INVALID_OPERATING_TIME',out['holds']);self.assertEqual(out['source_observed_time']['end'],'2019-12-31')
    def test_16_terminal_midpoint(self):
        self.r['source_observed_time']={'kind':'event_interval','start':'2020-01-01','end':'2020-12-31','midpoint':'2020-07-02'};out=self.context();self.assertNotIn('on',out['source_observed_time'])
    def test_17_pre_entry(self):
        self.r['source_observed_time']['on']='2019-12-31';self.assertEqual(project(self.doc)['window_relations'][0]['window_status'],'pre_entry_context')
    def test_18_exact_entry(self):
        self.r['source_observed_time']['on']='2020-01-01';self.assertEqual(project(self.doc)['window_relations'][0]['entry_relation'],'at_entry')
    def test_19_exact_cutoff(self):
        self.r['source_observed_time']['on']='2020-12-31';self.assertEqual(project(self.doc)['window_relations'][0]['cutoff_relation'],'at_cutoff')
    def test_20_post_cutoff(self):
        self.r['source_observed_time']['on']='2021-01-01';out=project(self.doc);self.assertEqual(out['window_relations'][0]['window_status'],'after_window');self.assertEqual(out['source_observed_time']['on'],'2021-01-01')
    def test_21_late_retrospective(self):
        out=d.project(self.doc);self.assertEqual(out['observations'][0]['operating_time_diagnostic'],'operating_point');self.assertFalse(out['historical_availability_evaluated']);self.assertEqual(out['cutoffs']['evidence_report_cutoff'],'2021-01-04')
    def test_22_two_rounds(self):
        rr=copy.deepcopy(self.a['index_round_applicability'][0]);rr.update(round_id='second-round',disposition='unresolved');self.a['index_round_applicability'].append(rr);out=project(self.doc);self.assertEqual(len(out['window_relations']),2);self.assertEqual(len(out['review_refs']),1);self.assertEqual(out['supplied_dispositions']['index_round_applicability'][1]['disposition'],'unresolved')
    def test_23_missing_inspection(self):
        self.a['operating_interpretation']='unresolved_predicate';self.r['supplied_holds']=['BODY_INSPECTION_PENDING'];out=project(self.doc);self.assertIn('BODY_INSPECTION_PENDING',out['holds']);self.assertEqual(out['operating_time_diagnostic'],'unresolved_predicate')
    def test_24_tool_failure(self):
        self.r['missingness']={'route':'tool_failure'};self.a['source_attribution']='held';self.a['operating_interpretation']='unresolved_predicate';out=project(self.doc);self.assertEqual(out['missingness']['route'],'tool_failure');self.assertNotIn('searched_no_relevant_result',str(out['missingness']))
    def test_25_stale_review(self):
        self.r['review_refs'][0]['claim_payload_sha256']='0'*64;out=project(self.doc);self.assertIn('STALE_REVIEW_REFERENCE',out['holds']);self.assertIn('PROJECTOR_DOES_NOT_AUTHENTICATE_REVIEW_AUTHORITY',out['holds'])
    def test_26_preservation(self):
        before=d.canonical(self.doc);project(self.doc);self.assertEqual(d.canonical(self.doc),before)

class InvarianceAndErrors(unittest.TestCase):
    def test_entry_equals_cutoff(self):
        doc=fixture();doc['cutoffs']['analytical_extraction_cutoff']='2020-01-01';doc['observations'][0]['source_observed_time']['on']='2020-01-01';w=project(doc)['window_relations'][0];self.assertEqual(w['entry_relation'],'at_entry');self.assertEqual(w['cutoff_relation'],'at_cutoff')
    def test_unknown_legacy_mapping(self):
        doc=fixture();r=doc['observations'][0];r['supplied_dispositions'].update(source_attribution='pending',operating_interpretation='unresolved_predicate',index_round_applicability=[]);r['review_refs']=[];out=project(doc);self.assertEqual(out['supplied_dispositions']['source_attribution'],'pending');self.assertIn('REVIEW_BINDING_NOT_SUPPLIED',out['holds'])
    def test_bad_point_and_missing_window(self):
        doc=fixture();doc['observations'][0]['source_observed_time']['on']='2020-02-30';self.assertEqual(project(doc)['operating_time_diagnostic'],'invalid_time');doc=fixture();doc['cutoffs']['analytical_extraction_cutoff']=None;self.assertEqual(project(doc)['window_relations'][0]['window_status'],'unresolved')
    def test_cli_success_and_error_byte_invariance(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);bound=base/'source.txt';bound.write_bytes(b'SYNTHETIC source, no real authority');doc=fixture();doc['input_bindings']=[{'path':'source.txt','sha256':d.digest(bound.read_bytes())}];src=base/'input.json';src.write_text(json.dumps(doc));original=src.read_bytes();source_original=bound.read_bytes();out=base/'out.json'
            result=d.run(src,out);self.assertEqual(src.read_bytes(),original);self.assertEqual(bound.read_bytes(),source_original);self.assertFalse(result['estimator_enabled'])
            with self.assertRaises(ValueError):d.run(src,out)
            self.assertEqual(src.read_bytes(),original)
            for mode in ('digest','schema','timezone','shape','json'):
                bad=copy.deepcopy(doc)
                if mode=='digest':bad['input_bindings'][0]['sha256']='0'*64
                if mode=='schema':bad['schema']='wrong'
                if mode=='timezone':bad['observations'][0]['source_dates']['retrieved_at']='2021-01-01T12:00:00'
                if mode=='shape':bad['observations']='bad'
                src.write_text('{' if mode=='json' else json.dumps(bad));raw=src.read_bytes();target=base/(mode+'.json')
                with self.assertRaises((ValueError,KeyError,TypeError)):d.run(src,target)
                self.assertEqual(src.read_bytes(),raw);self.assertEqual(bound.read_bytes(),source_original);self.assertFalse(target.exists())
    def test_output_aliases_rejected(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);src=base/'source.json';src.write_text(json.dumps(fixture()));raw=src.read_bytes()
            symlink=base/'symlink.json';symlink.symlink_to(src)
            hardlink=base/'hardlink.json';os.link(src,hardlink)
            dangling=base/'dangling.json';dangling.symlink_to(base/'absent-target.json')
            for target in (src,symlink,hardlink,dangling):
                with self.subTest(target=target.name):
                    with self.assertRaises(ValueError):d.run(src,target)
                    self.assertEqual(src.read_bytes(),raw)
            self.assertFalse((base/'absent-target.json').exists());self.assertTrue(dangling.is_symlink())

    def test_cli_real_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            src=Path(directory)/'in.json';out=Path(directory)/'new.json';src.write_text(json.dumps(fixture()));raw=src.read_bytes();run=subprocess.run([sys.executable,str(Path(d.__file__)),'--input',str(src),'--output',str(out)],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(src.read_bytes(),raw);self.assertTrue(out.exists())
    def test_no_network_import_or_estimator_wiring(self):
        import ast
        tree=ast.parse(Path(d.__file__).read_text());names=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):names.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):names.append(node.module)
        self.assertFalse(any(any(token in name for token in ('requests','urllib','socket','http','phase1','estimator','subprocess')) for name in names))


class TransparencyRegressions(unittest.TestCase):
    def test_empty_and_incomplete_review_references_visible(self):
        for refs in ([{}],[{'id':'reference-only'}],[{'id':'x','artifact_path':'x','artifact_sha256':'bad','claim_payload_sha256':'0'*64}]):
            with self.subTest(refs=refs):
                doc=fixture();doc['observations'][0]['review_refs']=refs;out=project(doc)
                self.assertIn('REVIEW_REFERENCE_INCOMPLETE',out['holds']);self.assertIn('NO_COMPLETE_REVIEW_REFERENCE',out['holds'])
                self.assertEqual(out['supplied_dispositions']['source_attribution'],'reviewed_attribution')
    def test_complete_reference_is_structure_not_authentication(self):
        out=project(fixture());self.assertEqual(out['review_reference_structure'],[True]);self.assertNotIn('REVIEW_REFERENCE_INCOMPLETE',out['holds']);self.assertFalse(out['review_artifact_files_verified']);self.assertIn('PROJECTOR_DOES_NOT_AUTHENTICATE_REVIEW_AUTHORITY',out['holds'])
    def test_nonsynthetic_missing_dependency_bindings(self):
        for explicit in (False,True):
            doc=fixture();doc['synthetic']=False
            if explicit:doc['input_bindings']=[]
            out=d.project(doc);self.assertIn('DEPENDENCY_FILES_NOT_BOUND',out['diagnostic_holds']);self.assertFalse(out['dependency_binding_diagnostic']['filesystem_verification_performed'])
    def test_project_declared_binding_is_not_filesystem_verification(self):
        doc=fixture();doc['input_bindings']=[{'path':'not-read-by-project','sha256':'b'*64}];out=d.project(doc);self.assertEqual(out['dependency_binding_diagnostic']['declared_count'],1);self.assertFalse(out['dependency_binding_diagnostic']['filesystem_verification_performed']);self.assertEqual(out['dependency_binding_diagnostic']['verified_dependency_hashes'],{})
    def test_run_verified_dependency_does_not_authenticate_review(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);review=base/'review.json';review.write_bytes(b'Synthetic review bytes, no authority')
            doc=fixture();doc['input_bindings']=[{'path':'review.json','sha256':d.digest(review.read_bytes())}];doc['observations'][0]['review_refs'][0].update(artifact_path='review.json',artifact_sha256=d.digest(review.read_bytes()))
            src=base/'in.json';src.write_text(json.dumps(doc));raw=src.read_bytes();reviewraw=review.read_bytes();out=d.run(src,base/'out.json')
            self.assertTrue(out['dependency_binding_diagnostic']['filesystem_verification_performed']);self.assertTrue(out['observations'][0]['review_artifact_files_verified']);self.assertFalse(out['authority_validation_performed']);self.assertEqual(src.read_bytes(),raw);self.assertEqual(review.read_bytes(),reviewraw)
    def test_report_clock_consistency_now_date_compared(self):
        for year in ('2020','2029'):
            doc=fixture();doc['observations'][0]['source_dates']['retrieved_at']=year+'-01-01T12:00:00Z';doc['observations'][0]['source_dates']['reviewed_at']=year+'-01-02T12:00:00Z';out=d.project(doc)
            self.assertTrue(out['evidence_report_consistency_evaluated']);self.assertIn('TEMPORAL_COMPARISONS_ONLY_NOT_FULL_REPORT_VALIDATION',out['diagnostic_holds']);self.assertEqual(out['observations'][0]['operating_time_diagnostic'],'operating_point')
    def test_empty_source_dates_are_visible(self):
        doc=fixture();doc['observations'][0]['source_dates']={};out=project(doc);self.assertEqual(len(out['source_date_fields_missing']),4)
    def test_nontext_and_blank_basis_invalid_without_payload_change(self):
        for basis in (['text'],{'text':'x'},'   ',1):
            doc=fixture();doc['observations'][0]['source_observed_time']['basis']=basis;out=project(doc);self.assertEqual(out['operating_time_diagnostic'],'invalid_time');self.assertEqual(out['source_observed_time']['basis'],basis)
        self.assertEqual(project(fixture())['operating_time_diagnostic'],'operating_point')
    def test_nontext_or_blank_rationale_rejects_with_invariance(self):
        for field in ('round_mapping_reason','per_round_rationale'):
            for value in ({'x':'truthy'},['truthy'],'   '):
                doc=fixture()
                if field=='round_mapping_reason':doc['observations'][0][field]=value
                else:doc['observations'][0]['supplied_dispositions']['index_round_applicability'][0]['rationale']=value
                before=d.canonical(doc)
                with self.assertRaises(ValueError):d.project(doc)
                self.assertEqual(d.canonical(doc),before)
    def test_run_rationale_error_preserves_all_bound_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'source';source.write_bytes(b'synthetic');doc=fixture();doc['input_bindings']=[{'path':'source','sha256':d.digest(source.read_bytes())}];doc['observations'][0]['round_mapping_reason']={'bad':'type'};src=base/'in.json';src.write_text(json.dumps(doc));raw=src.read_bytes()
            with self.assertRaises(ValueError):d.run(src,base/'output.json')
            self.assertEqual(src.read_bytes(),raw);self.assertEqual(source.read_bytes(),b'synthetic');self.assertFalse((base/'output.json').exists())


class ByteBindingRegressions(unittest.TestCase):
    def run_variant(self, mutate_ref, bind=True):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);artifact=base/'review.json';artifact.write_bytes(b'Synthetic artifact bytes; not approval')
            doc=fixture();ref=doc['observations'][0]['review_refs'][0];ref.update(artifact_path='review.json',artifact_sha256=d.digest(artifact.read_bytes()));mutate_ref(ref)
            if bind:doc['input_bindings']=[{'path':'review.json','sha256':d.digest(artifact.read_bytes())}]
            src=base/'input.json';src.write_text(json.dumps(doc));raw=src.read_bytes();artifactraw=artifact.read_bytes();out=d.run(src,base/'output.json');self.assertEqual(src.read_bytes(),raw);self.assertEqual(artifact.read_bytes(),artifactraw);self.assertFalse(out['authority_validation_performed']);self.assertIsNone(out['native_censor_date']);self.assertFalse(out['estimator_enabled']);self.assertEqual(out['observations'][0]['original_claim'],doc['observations'][0]['original_claim']);return out['observations'][0]
    def test_incomplete_claim_reference_has_verified_bytes(self):
        out=self.run_variant(lambda ref:ref.pop('claim_payload_sha256'))
        self.assertTrue(out['review_artifact_files_verified']);self.assertIn('REVIEW_REFERENCE_INCOMPLETE',out['holds']);self.assertIn('NO_COMPLETE_REVIEW_REFERENCE',out['holds']);self.assertNotIn('REVIEW_ARTIFACT_FILES_NOT_VERIFIED',out['holds'])
    def test_missing_reference_id_does_not_hide_verified_bytes(self):
        out=self.run_variant(lambda ref:ref.pop('id'));self.assertTrue(out['review_artifact_files_verified']);self.assertIn('REVIEW_REFERENCE_INCOMPLETE',out['holds'])
    def test_complete_reference_but_unbound_bytes(self):
        out=self.run_variant(lambda ref:None,bind=False);self.assertFalse(out['review_artifact_files_verified']);self.assertEqual(out['review_reference_structure'],[True]);self.assertIn('REVIEW_ARTIFACT_FILES_NOT_VERIFIED',out['holds'])
    def test_stale_claim_digest_with_verified_bytes(self):
        out=self.run_variant(lambda ref:ref.update(claim_payload_sha256='0'*64));self.assertTrue(out['review_artifact_files_verified']);self.assertIn('STALE_REVIEW_REFERENCE',out['holds']);self.assertIn('PROJECTOR_DOES_NOT_AUTHENTICATE_REVIEW_AUTHORITY',out['holds'])
    def test_malformed_path_or_hash_not_verified(self):
        for key,value in [('artifact_path',None),('artifact_path',{}),('artifact_path',[]),('artifact_path','   '),('artifact_path','bad\x00path'),('artifact_sha256','bad'),('artifact_sha256',{}),('artifact_sha256','f'*64)]:
            with self.subTest(key=key,value=value):
                out=self.run_variant(lambda ref:ref.update({key:value}));self.assertFalse(out['review_artifact_files_verified']);self.assertIn('REVIEW_ARTIFACT_FILES_NOT_VERIFIED',out['holds'])
    def test_project_byte_verification_remains_false(self):
        doc=fixture();doc['observations'][0]['review_refs'][0].pop('claim_payload_sha256');out=d.project(doc);self.assertFalse(out['observations'][0]['review_artifact_files_verified']);self.assertFalse(out['dependency_binding_diagnostic']['filesystem_verification_performed'])

if __name__=='__main__':unittest.main()
