"""Reproduce the pinned audit in disposable output; never upload row artifacts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root, output):
    root, output = root.resolve(), output.resolve()
    if output == root or root in output.parents:
        raise ValueError('verification_output_must_be_outside_repository')
    package = Path(__file__).resolve().parent
    reference = package/'reference-run'
    binding = json.loads((reference/'input-output-bindings.json').read_text())
    code = package/'preparation_audit.py'
    if digest(code) != binding['audit_code_sha256']:
        raise ValueError('audit_code_hash_mismatch')
    source_relative = Path(binding['source_ledger_repo_path'])
    if source_relative.is_absolute() or '..' in source_relative.parts:
        raise ValueError('invalid_source_repository_path')
    source = root/source_relative
    if digest(source) != binding['source_ledger_sha256']:
        raise ValueError('source_ledger_hash_mismatch')
    for filename, hash_field in [('summary.json','public_summary_sha256'),
                                  ('priority-queue.json','public_priority_queue_sha256')]:
        if digest(reference/filename) != binding[hash_field]:
            raise ValueError('reference_packet_hash_mismatch:'+filename)
    spec = importlib.util.spec_from_file_location('verified_preparation_audit',code)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = (source.read_bytes(),source.stat().st_mtime_ns)
    manifest = module.audit_file(source,binding['source_ledger_sha256'],output)
    if manifest['outputs'] != binding['complete_local_output_sha256']:
        raise ValueError('complete_reproduced_output_hashes_differ')
    if set(p.name for p in output.iterdir()) != set(manifest['outputs']) | {'manifest.json'}:
        raise ValueError('unexpected_reproduced_output_set')
    for filename, expected in manifest['outputs'].items():
        if Path(filename).name != filename or digest(output/filename) != expected:
            raise ValueError('reproduced_output_hash_mismatch:'+filename)
    if (output/'summary.json').read_bytes() != (reference/'summary.json').read_bytes():
        raise ValueError('reproduced_summary_differs')
    summary = json.loads((output/'summary.json').read_text())
    if summary['input_rows'] != 952 or summary['output_dispositions'] != 952:
        raise ValueError('source_row_accounting_changed')
    if summary['eligible_row_count'] is not None or summary['ineligible_row_count'] is not None:
        raise ValueError('unexpected_eligibility_claim')
    rows = [json.loads(line) for line in (output/'row-dispositions.jsonl').read_text().splitlines()]
    if len(rows) != 952 or any(r['evidence_eligibility'] != 'NOT_DETERMINED' or r['prepared_history_status'] != 'NOT_CONSTRUCTED' for r in rows):
        raise ValueError('unexpected_row_disposition')
    queue = json.loads((output/'targeted-review-queue.json').read_text())
    compact = json.loads((reference/'priority-queue.json').read_text())
    if compact['source_sha256'] != binding['source_ledger_sha256']:
        raise ValueError('queue_source_hash_mismatch')
    restored = [{'source_row_ordinal_1based':row[0], 'max_targeted_review_priority':row[1],
                 'targeted_gap_codes':[compact['gap_codebook'][i] for i in row[2]]} for row in compact['rows']]
    expected = [{key:row[key] for key in ('source_row_ordinal_1based','max_targeted_review_priority','targeted_gap_codes')} for row in queue]
    if restored != expected or len({row[0] for row in compact['rows']}) != len(queue):
        raise ValueError('compact_priority_queue_roundtrip_mismatch')
    snapshot = {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in output.iterdir()}
    module.audit_file(source,binding['source_ledger_sha256'],output)
    if snapshot != {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in output.iterdir()}:
        raise ValueError('identical_audit_rerun_not_noop')
    if before != (source.read_bytes(),source.stat().st_mtime_ns):
        raise ValueError('source_bytes_or_mtime_changed')
    print('Verified pinned code/input, all full output hashes, 952 undetermined dispositions, compact queue roundtrip, and immutable rerun. No private artifacts uploaded.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    verify(args.root,args.output)
