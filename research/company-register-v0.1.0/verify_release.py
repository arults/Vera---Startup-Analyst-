"""Verify stored artifact hashes, source bytes and a clean portable regeneration."""
import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
inspector_spec = importlib.util.spec_from_file_location('inspect_register', BASE/'inspect_register.py')
inspector = importlib.util.module_from_spec(inspector_spec)
inspector_spec.loader.exec_module(inspector)
TABLES, read_table = inspector.TABLES, inspector.read_table
spec = importlib.util.spec_from_file_location('register', BASE/'src/phase1d/completion_register.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def verify(root):
    config = json.loads((BASE/'source_manifest.json').read_text())
    result = module.build(root, config)
    stored = BASE/'generated'
    expected_hashes = json.loads((stored/'artifact_hashes.json').read_text())
    if set(expected_hashes) != {p.name for p in stored.iterdir() if p.name != 'artifact_hashes.json'}:
        raise ValueError('artifact file set mismatch')
    for name, expected in expected_hashes.items():
        if hashlib.sha256((stored/name).read_bytes()).hexdigest() != expected:
            raise ValueError('stored artifact digest mismatch: ' + name)
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        module.write_outputs(output, result)
        for table in TABLES:
            if read_table(output, table) != read_table(stored, table):
                raise ValueError('regenerated logical table differs: ' + table)
        exact = all((output/name).read_bytes() == (stored/name).read_bytes() for name in expected_hashes)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
        module.write_outputs(output, result)
        if before != {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}:
            raise ValueError('repeat import is not idempotent')
    return {'status': 'PASS', 'loaded_rows': result['manifest']['loaded_rows'],
            'tables_verified': len(TABLES), 'exact_compressed_bytes_match': exact,
            'logical_tables_match': True, 'empirical_promotion': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify(args.root), sort_keys=True))


if __name__ == '__main__':
    main()
