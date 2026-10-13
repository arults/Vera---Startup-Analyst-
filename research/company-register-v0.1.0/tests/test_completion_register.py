import base64
import copy
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import pathlib
import tempfile
import subprocess
import sys
import unittest

BASE = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('register', BASE / 'src/phase1d/completion_register.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def source(adapter='discovery'):
    return {'path': 'fixture.csv', 'source_commit': m.SOURCE_COMMIT, 'sha256': 'a'*64,
            'scope': 'synthetic_test_only', 'adapter': adapter}


def eu(**overrides):
    row = {'canonical_company_id': 'source:123', 'round_id': 'round:1', 'campaign_name': 'Example',
           'offering_year': '2020', 'completion_date': '2020-06-01'}
    row.update(overrides)
    return row


class RegisterTests(unittest.TestCase):
    def test_isolated_verifier_cli_imports(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(BASE/'verify_release.py'), '--help'],
                                capture_output=True, text=True, cwd='/tmp')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_isolated_inspector_cli(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(BASE/'inspect_register.py'), '--limit', '1'],
                                capture_output=True, text=True, cwd='/tmp')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)), 1)

    def test_stable_scoped_ids(self):
        self.assertEqual(m.sid('company', 'US', '12'), m.sid('company', 'US', '12'))
        self.assertNotEqual(m.sid('company', 'US', '12'), m.sid('company', 'GB', '12'))

    def test_distinct_jurisdictions(self):
        r = m.Register()
        a = r.record('company', 'registry', '123', jurisdiction='US')
        b = r.record('company', 'registry', '123', jurisdiction='GB')
        self.assertNotEqual(a, b)

    def test_names_do_not_merge(self):
        r = m.Register()
        a = r.record('company_key', 'p', 'one', label='Same Name')
        b = r.record('company_key', 'p', 'two', label='Same Name')
        self.assertNotEqual(a, b)

    def test_duplicate_lineage_preserved(self):
        r = m.Register()
        row = {'url': 'https://example.com/a', 'platform': 'p'}
        r.ingest(source(), [row, row])
        out = r.finalize()
        self.assertEqual(len(out['lineage']), 2)
        self.assertEqual(len(out['records']), 1)
        self.assertEqual(sum(x['disposition'] == 'duplicate' for x in out['lineage']), 1)

    def test_conflicting_identity_quarantines_both(self):
        r = m.Register()
        r.ingest(source('eu_round'), [eu(), eu(canonical_company_id='other:456')])
        out = r.finalize()
        self.assertTrue(out['conflicts'])
        self.assertTrue(all(x['disposition'] == 'quarantined' for x in out['lineage']))

    def test_conflicting_outcomes_queued(self):
        r = m.Register()
        r.ingest(source('eu_outcome'), [eu(closure_date='', terminal_event_type=''),
                                       eu(closure_date='2024-01-01', terminal_event_type='closure')])
        out = r.finalize()
        self.assertIn('closure_date', {c['field'] for c in out['conflicts']})
        self.assertEqual(len(out['evidence']), 2)

    def test_identity_status_change_not_first_wins(self):
        r = m.Register()
        r.record('company', 'p', '1', identity='strong_identifier')
        r.record('company', 'p', '1', identity='unresolved')
        self.assertIn('identity_status', {c['field'] for c in r.finalize()['conflicts']})

    def test_invalid_row_still_has_lineage(self):
        r = m.Register()
        r.ingest(source('eu_round'), [eu(round_id='')])
        out = r.finalize()
        self.assertEqual(out['lineage'][0]['disposition'], 'quarantined')
        self.assertEqual(out['records'], [])

    def test_name_fallback_never_legal_identity(self):
        r = m.Register()
        r.ingest(source('eu_round'), [eu(canonical_company_id='reurope-name:abc')])
        self.assertIn('name_fallback', {x['identity_status'] for x in r.finalize()['records']})

    def test_wf_platform_membership_from_issuer_link(self):
        r = m.Register()
        r.ingest(source('wf_funded'), [{'issuer_cik': '123', 'offering_key': '123|1'}])
        out = r.finalize()
        companies = [x for x in out['progress'] if x['unit'] == 'company']
        self.assertEqual(companies[0]['platform'], 'wefunder')
        self.assertEqual(companies[0]['loaded_unique_records'], 1)

    def test_completion_unknown_not_zero(self):
        r = m.Register()
        r.ingest(source('eu_round'), [eu()])
        out = r.finalize()
        self.assertTrue(all(p['verified_complete'] is None and p['partial'] is None for p in out['progress']))
        self.assertTrue(all(a['completion_status'] == 'unclassified' for a in out['assessments']))

    def test_profile_event_not_round_or_company(self):
        r = m.Register()
        r.ingest(source('wf_event'), [{'source_native_company_id': '12', 'source_event_ordinal': '0'}])
        self.assertEqual({v['record_type'] for v in r.finalize()['records']}, {'profile', 'profile_event'})

    def test_linked_cik_not_auto_promoted(self):
        r = m.Register()
        r.ingest(source('us_offering'), [{'native_offering_id': 2, 'fields': {'filing_cik_from_platform_links': '123'}}])
        self.assertEqual({v['record_type'] for v in r.finalize()['records']}, {'offering'})

    def test_unknown_acquisition_not_success(self):
        r = m.Register()
        r.ingest(source('eu_outcome'), [eu(terminal_event_type='acquisition_value_unknown', success_date='')])
        e = r.finalize()['evidence'][0]['source_outcome']
        self.assertEqual(e['terminal_event_type'], 'acquisition_value_unknown')
        self.assertEqual(e['success_date'], '')

    def test_repeated_finalize_and_build_deterministic(self):
        r = m.Register()
        r.ingest(source('eu_round'), [eu()])
        self.assertEqual(m.canonical(r.finalize()), m.canonical(r.finalize()))

    def test_repeated_import_is_noop(self):
        r = m.Register()
        r.ingest(source('eu_round'), [eu(), eu()])
        first = m.canonical(r.finalize())
        r.ingest(source('eu_round'), [eu(), eu()])
        self.assertEqual(first, m.canonical(r.finalize()))

    def test_conflicting_finalize_deterministic(self):
        r = m.Register()
        r.ingest(source('eu_round'), [eu(), eu(offering_year='2021')])
        self.assertEqual(m.canonical(r.finalize()), m.canonical(r.finalize()))

    def test_read_source_hash_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw = b'url,platform\nhttps://example.com,p\n'
            (root/'input.csv').write_bytes(raw)
            s = dict(source(), path='input.csv', expected_rows=1, sha256=m.digest(raw),
                     git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
            self.assertEqual(len(m.read_source(root, s)), 1)
            (root/'input.csv').write_bytes(raw + b'\n')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                m.read_source(root, s)

    def test_wrong_expected_row_count(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); raw = b'url,platform\nhttps://example.com,p\n'
            (root/'input.csv').write_bytes(raw)
            s = dict(source(), path='input.csv', expected_rows=2, sha256=m.digest(raw),
                     git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
            with self.assertRaisesRegex(ValueError, 'row count'):
                m.read_source(root, s)

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            m.safe_path(pathlib.Path('/tmp/root'), '../secret')

    def test_omitted_source_rejected(self):
        cfg = json.loads((BASE/'source_manifest.json').read_text())
        cfg['sources'].pop()
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root/'docs').mkdir()
            (root/'docs/PHASE_1C_SPEC.md').write_bytes((BASE/'tests/fixtures/PHASE_1C_SPEC.md').read_bytes())
            with self.assertRaisesRegex(ValueError, 'missing or unexpected source'):
                m.build(root, cfg)

    def test_changed_spec_rejected(self):
        cfg = json.loads((BASE/'source_manifest.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root/'docs').mkdir()
            (root/'docs/PHASE_1C_SPEC.md').write_text('changed requirements')
            with self.assertRaisesRegex(ValueError, 'requirements source hash mismatch'):
                m.build(root, cfg)

    def test_immutable_idempotent_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d)
            result = {'records': [{'x': 1}], 'progress': [], 'manifest': {'v': 1}}
            m.write_outputs(path, result)
            first = {p.name: p.read_bytes() for p in path.iterdir()}
            m.write_outputs(path, result)
            self.assertEqual(first, {p.name: p.read_bytes() for p in path.iterdir()})
            payload = gzip.decompress(base64.b64decode(first['records.jsonl.gz.b64']))
            self.assertEqual(json.loads(payload), {'x': 1})
            result['records'] = [{'x': 2}]
            with self.assertRaisesRegex(ValueError, 'refusing to overwrite'):
                m.write_outputs(path, result)
            self.assertEqual(first, {p.name: p.read_bytes() for p in path.iterdir()})


if __name__ == '__main__':
    unittest.main()
