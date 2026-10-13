"""Separate subprocess checks; not imported recursively by validate.py."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / 'explicit-history-statistics-v0.2.0'


class IsolatedValidationTests(unittest.TestCase):
    def prepare(self, root):
        research = root / 'relocated' / 'research'
        candidate = research / HERE.name
        baseline = research / BASELINE.name
        shutil.copytree(HERE, candidate, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(BASELINE, baseline, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        return candidate, baseline

    def run_validator(self, root, candidate):
        trap = root / 'shadow'
        trap.mkdir()
        (trap / 'aj_explicit_history.py').write_text("raise AssertionError('untrusted_path_shadow_loaded')\n")
        return subprocess.run([sys.executable, '-I', '-B', str(candidate / 'validate.py')],
            cwd=root, env=dict(os.environ, PYTHONPATH=str(trap)), capture_output=True,
            text=True, timeout=60)

    def test_relocated_isolated_validation_preserves_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, _ = self.prepare(root)
            before = {p.relative_to(root / 'relocated'): p.read_bytes()
                      for p in (root / 'relocated').rglob('*') if p.is_file()}
            result = self.run_validator(root, candidate)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Ran 93 tests', result.stderr)
            after = {p.relative_to(root / 'relocated'): p.read_bytes()
                     for p in (root / 'relocated').rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            self.assertFalse(list((root / 'relocated').rglob('*.pyc')))

    def test_tampered_dependency_fails_before_test_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, baseline = self.prepare(root)
            source = baseline / 'aj_explicit_history.py'
            source.write_bytes(source.read_bytes() + b'\n# synthetic tamper\n')
            result = self.run_validator(root, candidate)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('frozen_dependency_hash_mismatch:aj_explicit_history.py', result.stderr)
            self.assertNotIn('Ran 93 tests', result.stderr)

    def test_missing_dependency_fails_before_test_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, baseline = self.prepare(root)
            (baseline / 'aj_ij.py').unlink()
            result = self.run_validator(root, candidate)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('FileNotFoundError', result.stderr)
            self.assertNotIn('Ran 93 tests', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
