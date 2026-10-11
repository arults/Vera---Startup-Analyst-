import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
spec = importlib.util.spec_from_file_location('reviewed_view', BASE/'inspect_reviewed.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReviewedViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables, cls.sources, cls.evidence = m.load_inputs(ROOT)
        cls.happy = m.build_view(ROOT)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)/'repo'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__', 'reports'))

    def tearDown(self):
        self.temp.cleanup()

    def assertHold(self, root=None):
        result = m.build_view(root or self.root)
        self.assertEqual(result['status'], 'HOLD')
        self.assertEqual(result['assessments'], [])
        self.assertEqual(result['records'], [])
        self.assertFalse(result['completion_counts_established'])
        self.assertFalse(result['empirical_promotion'])
        self.assertIsNone(result['verified_complete'])
        return result

    def test_happy_exact_counts_and_no_gate_overreach(self):
        v = self.happy
        self.assertEqual(v['status'], 'VERIFIED_SELECTED_MATCHES')
        self.assertEqual((v['independent_matches'], v['assessment_applications']), (6, 16))
        self.assertEqual((v['company_key_records'], v['source_round_records']), (2, 6))
        for pair in v['assessments']:
            original, reviewed = pair['original'], pair['reviewed']
            expected = copy.deepcopy(original)
            expected['gates'].update(m.GATE_CHANGES)
            self.assertEqual(reviewed, expected)
            self.assertEqual(reviewed['gates']['economic_round'], original['gates']['economic_round'])
            self.assertEqual(reviewed['completion_status'], 'unclassified')
            self.assertFalse(reviewed['completion_counts_established'])
            self.assertEqual(pair['review_metadata']['original_identity_gates'],
                             {k: original['gates'][k] for k in m.GATE_CHANGES})
        self.assertEqual(v['global_identity_qa'], 'NOT_ASSESSED')
        self.assertIsNone(v['verified_complete'])
        self.assertIsNone(v['partial'])

    def test_original_records_and_all_ids_preserved(self):
        originals = {x['record_id']: x for x in self.tables['records']}
        for row in self.happy['records']:
            self.assertEqual(row, originals[row['record_id']])
            self.assertEqual(row['jurisdiction'], '')
        keys = {x['source_key'] for x in self.happy['records'] if x['record_type'] == 'company_key'}
        self.assertEqual(keys, {'reurope-company:553249', 'reurope-company:553249IRELAND'})
        self.assertEqual(len({x['source_key'] for x in self.happy['records'] if x['record_type'] == 'round'}), 6)

    def test_every_pinned_file_missing_or_stale_fails_closed(self):
        for relative in m.PINNED_FILES:
            with self.subTest(relative=relative):
                p = self.root/relative
                original = p.read_bytes()
                p.unlink()
                self.assertHold()
                p.write_bytes(original + b' ')
                self.assertHold()
                p.write_bytes(original)

    def test_all_table_mutations_fail_closed(self):
        generated = self.root/m.BASE/'generated'
        hashes = json.loads((generated/'artifact_hashes.json').read_text())
        for name in hashes:
            with self.subTest(table=name):
                p = generated/name
                original = p.read_bytes()
                p.write_bytes(original + b' ')
                self.assertHold()
                p.write_bytes(original)

    def test_rehashing_baseline_manifest_cannot_self_authorize(self):
        generated = self.root/m.BASE/'generated'
        p = generated/'assessments.jsonl.gz.b64'
        p.write_bytes(p.read_bytes() + b' ')
        hashes = json.loads((generated/'artifact_hashes.json').read_text())
        hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        (generated/'artifact_hashes.json').write_text(json.dumps(hashes))
        self.assertHold()

    def test_every_original_source_changed_fails_closed(self):
        for source in self.sources:
            with self.subTest(source=source):
                p = self.root/source
                original = p.read_bytes()
                p.write_bytes(original + b'\n')
                self.assertHold()
                p.write_bytes(original)

    def test_every_native_capture_missing_or_stale_fails_closed(self):
        for fact in self.evidence['ISSUER_IDENTITY_FACTS.json']['observations']:
            for binding in fact['git_blob_bindings']:
                with self.subTest(capture=binding['path']):
                    p = self.root/binding['path']
                    original = p.read_bytes()
                    p.unlink()
                    self.assertHold()
                    p.write_bytes(original + b'\n')
                    self.assertHold()
                    p.write_bytes(original)

    def test_external_context_cannot_replace_native_proof(self):
        p = self.root/self.evidence['ISSUER_IDENTITY_FACTS.json']['observations'][0]['archive']['capture_path']
        p.unlink()
        self.assertTrue((self.root/m.RELEASE/'evidence/ISSUER_IDENTITY_FACTS.json').exists())
        self.assertHold()

    def test_native_validation_does_not_consume_external_context(self):
        evidence = copy.deepcopy(self.evidence)
        evidence['ISSUER_IDENTITY_FACTS.json'].pop('independent_registry_identity')
        evidence['ISSUER_IDENTITY_FACTS.json'].pop('cro_filing_context')
        evidence['REVIEW_RECEIPT.json'].pop('outside_study_context_urls')
        m.verify_native_evidence(self.root, evidence)

    def test_arbitrary_receipt_verified_status_cannot_self_authorize(self):
        p = self.root/m.RELEASE/'evidence/REVIEW_RECEIPT.json'
        r = json.loads(p.read_text())
        r['target_allowlist'][0]['permitted_derived_gate_changes']['economic_round'] = {'from': 'not_assessed', 'to': 'VERIFIED'}
        p.write_text(json.dumps(r))
        self.assertHold()

    def test_historical_receipt_not_accepted(self):
        p = self.root/m.RELEASE/'evidence/REVIEW_RECEIPT.json'
        r = json.loads(p.read_text())
        r['receipt_id'] = r['receipt_id'].replace('v0.1.1', 'v0.1.0')
        p.write_text(json.dumps(r))
        self.assertHold()

    def test_semantic_target_mutations_rejected(self):
        mutations = [
            lambda t: t.update(assessment_id='assessment:outside-allowlist'),
            lambda t: t.update(record_id='round:other'),
            lambda t: t.update(source_scope='other_scope'),
            lambda t: t.update(requirements_version='changed-policy'),
            lambda t: t.update(source_key='reurope:another-round'),
            lambda t: t['source_bindings'].pop(),
            lambda t: t['source_bindings'][0].update(row_number=1),
            lambda t: t['source_bindings'][0].update(row_sha256='0'*64),
            lambda t: t['source_bindings'][0].update(source_path='../other.csv'),
            lambda t: t['baseline_gates'].update(economic_round='VERIFIED'),
        ]
        for mutate in mutations:
            e = copy.deepcopy(self.evidence)
            mutate(e['REVIEW_RECEIPT.json']['target_allowlist'][0])
            with self.assertRaises((ValueError, KeyError)):
                m.validate_selection(self.tables, self.sources, e)

    def test_company_key_any_match_is_insufficient(self):
        e = copy.deepcopy(self.evidence)
        target = next(x for x in e['REVIEW_RECEIPT.json']['target_allowlist'] if
                      x['record_type'] == 'company_key' and len(x['source_bindings']) > 1)
        target['source_bindings'] = target['source_bindings'][:1]
        with self.assertRaisesRegex(ValueError, 'lineage coverage'):
            m.validate_selection(self.tables, self.sources, e)

    def test_missing_duplicate_or_extra_assessment_rejected(self):
        for change in ['remove', 'duplicate', 'extra']:
            e = copy.deepcopy(self.evidence)
            targets = e['REVIEW_RECEIPT.json']['target_allowlist']
            if change == 'remove': targets.pop()
            elif change == 'duplicate': targets[-1] = copy.deepcopy(targets[0])
            else: targets.append(copy.deepcopy(targets[0]))
            with self.assertRaises(ValueError):
                m.validate_selection(self.tables, self.sources, e)

    def test_changed_logical_row_rejected_even_if_file_loader_is_skipped(self):
        sources = copy.deepcopy(self.sources)
        first = self.evidence['REVIEW_RECEIPT.json']['target_allowlist'][0]['source_bindings'][0]
        sources[first['source_path']]['rows'][first['row_number']-1]['campaign_name'] = 'Other'
        with self.assertRaisesRegex(ValueError, 'logical source row'):
            m.validate_selection(self.tables, sources, self.evidence)

    def test_view_does_not_mutate_inputs_and_is_deterministic(self):
        before = {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.root.rglob('*') if p.is_file()}
        one, two = m.build_view(self.root), m.build_view(self.root)
        self.assertEqual(one, two)
        after = {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_symlink_and_fifo_rejected_without_hanging(self):
        relative = next(iter(m.PINNED_FILES))
        p = self.root/relative
        p.unlink()
        p.symlink_to(ROOT/relative)
        self.assertHold()
        p.unlink()
        os.mkfifo(p)
        self.assertHold()

    def test_path_traversal_rejected(self):
        for path in ['../secret', '/etc/passwd']:
            with self.assertRaises(ValueError): m.read_regular(self.root, path)

    def test_cli_isolated_read_only_and_missing_input_exit(self):
        cmd = [sys.executable, '-I', '-B', str(BASE/'inspect_reviewed.py'), '--root', str(self.root)]
        good = subprocess.run(cmd, capture_output=True, text=True, cwd='/tmp', timeout=10)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)['status'], 'VERIFIED_SELECTED_MATCHES')
        (self.root/m.RELEASE/'evidence/REVIEW_RECEIPT.json').unlink()
        bad = subprocess.run(cmd, capture_output=True, text=True, cwd='/tmp', timeout=10)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(json.loads(bad.stdout)['status'], 'HOLD')


if __name__ == '__main__':
    unittest.main()
