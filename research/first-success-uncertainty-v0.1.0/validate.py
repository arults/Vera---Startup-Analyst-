"""Portable, isolated validator for the additive first-success package."""
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
    # Explicit paths make this independent of working directory and PYTHONPATH.
    sys.path[:0] = [str(here), str(baseline)]
    suite = unittest.TestSuite()
    for module in ('test_aj_explicit_history', 'test_first_success', 'test_aj_ij', 'test_statistical_reporting',
                   'test_first_success_uncertainty', 'test_independent_review'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print('Scope: 51 frozen baseline + 30 implementation + 13 independent review = 94 tests; sensitivity suite excluded.')
    return 0 if result.wasSuccessful() and result.testsRun == 94 else 1


if __name__ == '__main__':
    raise SystemExit(main())
