"""Portable isolated validator; no empirical source files are read."""
import hashlib
import json
from pathlib import Path
import sys
import unittest


def main():
    here = Path(__file__).resolve().parent
    bindings = json.loads((here / 'dependency_bindings.json').read_text())
    baseline = (here / bindings['relative_directory']).resolve()
    for name, expected in bindings['git_blob_sha1'].items():
        data = (baseline / name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if actual != expected:
            raise ValueError(f'frozen_dependency_hash_mismatch:{name}:{actual}')
    sys.path[:0] = [str(here), str(baseline)]
    suite = unittest.TestSuite()
    for module in ('test_aj_explicit_history', 'test_aj_ij', 'test_first_success',
                   'test_statistical_reporting', 'test_lost_followup_sensitivity',
                   'test_operating_uncertainty_guards'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print('Scope: 74 frozen baseline + 19 guard tests = 93 synthetic tests; no empirical calibration claim.')
    return 0 if result.wasSuccessful() and result.testsRun == 93 else 1


if __name__ == '__main__':
    raise SystemExit(main())
