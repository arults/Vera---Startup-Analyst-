"""Read a committed completion-register table without third-party packages."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

TABLES = ('progress', 'manifest', 'records', 'lineage', 'crosswalk', 'evidence', 'assessments', 'conflicts', 'source_coverage')


def read_table(directory, table):
    if table not in TABLES:
        raise ValueError('unknown table')
    name = table + ('.json' if table in {'progress', 'manifest'} else '.jsonl.gz.b64')
    raw = (directory/name).read_bytes()
    hashes = json.loads((directory/'artifact_hashes.json').read_text())
    if hashlib.sha256(raw).hexdigest() != hashes[name]:
        raise ValueError('artifact hash mismatch: ' + name)
    if name.endswith('.b64'):
        return [json.loads(line) for line in gzip.decompress(base64.b64decode(raw, validate=False)).decode().splitlines()]
    return json.loads(raw)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent/'generated')
    p.add_argument('--table', choices=TABLES, default='progress')
    p.add_argument('--limit', type=int)
    args = p.parse_args()
    result = read_table(args.directory, args.table)
    if args.limit is not None:
        if args.limit < 0 or not isinstance(result, list):
            p.error('limit must be nonnegative and table must be a list')
        result = result[:args.limit]
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
