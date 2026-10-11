"""Read-only, exact-release Crua issuer-identity view. No arbitrary approvals."""
from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import types

BASE = 'research/company-register-v0.1.0'
RELEASE = 'research/company-register-v0.1.1'
SNAPSHOT = 'e1991e3d924f44dbc3b7964c06c428c5f5af49ef'
RULES = 'phase1c-spec-717e7be8-register-v1'
GATE_CHANGES = {'identity': 'VERIFIED_ISSUER_IDENTITY',
                'identity_qa': 'VERIFIED_SELECTED_MATCHES'}
# These byte digests are release authority, not caller-supplied status fields.
# Updated only by a separately reviewed versioned release.
PINNED_FILES = {'research/company-register-v0.1.0/inspect_register.py': 'e964f980063a0486ae5efea4abad1e9df0779355a2308d58a2e5161351354112', 'research/company-register-v0.1.0/generated/artifact_hashes.json': '8fbc1a941fe6b8466b5b7fb2a5617e3743481d62ff2740a46e81e3ef492e4ae8', 'research/company-register-v0.1.0/source_manifest.json': '0a96dc4cb01a4c0399734b9cae56b97f5133538983b30dcf7382a42015932994', 'docs/PHASE_1C_SPEC.md': '7b15477eddab724ff03a4191da8de687f8f2b1c035965176cfe4deb12a05144e', 'research/company-register-v0.1.1/evidence/FILE_HASHES.json': '42d0636f568d19f281847e452265239eb912dcb9caeeba43b577ac6f978e86c1', 'research/company-register-v0.1.1/evidence/ISSUER_IDENTITY_FACTS.json': '391bf5b290488137939e9bc6b7b2f4f4db8f7bbdad3303e7cb889dddfaa7a1b3', 'research/company-register-v0.1.1/evidence/REGISTER_BINDINGS.json': 'a4c994019eb5d6a03246abc5e7b0a7322b20e288c9b53eb356a9ac1ee7afea7b', 'research/company-register-v0.1.1/evidence/REVIEW.md': '30362d4f0e085c508b331a21aa75ff1c0510c66e972701e0e02cb93509c33214', 'research/company-register-v0.1.1/evidence/REVIEW_RECEIPT.json': '49f74dd5d6f9f54e01fadf5f87199417492ac7aa3a6f21271e017cf0b4f7bae1', 'research/company-register-v0.1.1/evidence/VALIDATION.json': 'd7a0300c79fc64e48d6e645c0e6f0828101b20d5afd0de2951fc327f19752d94'}
MAX_INPUT_BYTES = 4 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_hash(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_regular(root, relative):
    """Bounded regular-file read; reject traversal, symlinks and FIFOs."""
    root = Path(root).resolve()
    parts = Path(relative).parts
    require(parts and not Path(relative).is_absolute() and '..' not in parts,
            'unsafe input path')
    path = root
    for part in parts:
        path = path / part
        require(not path.is_symlink(), 'symlink input: ' + relative)
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode),
                'nonregular input: ' + relative)
        raw = stream.read(MAX_INPUT_BYTES + 1)
    require(len(raw) <= MAX_INPUT_BYTES, 'oversized input: ' + relative)
    return raw


def pinned_read(root, relative, expected):
    raw = read_regular(root, relative)
    require(digest(raw) == expected, 'stale or mismatched input: ' + relative)
    return raw


class SnapshotPath:
    """In-memory paths let the unchanged v0.1.0 reader consume checked bytes."""
    def __init__(self, files, name=''):
        self.files, self.name = files, name

    def __truediv__(self, name):
        return SnapshotPath(self.files, name)

    def read_bytes(self):
        return self.files[self.name]

    def read_text(self):
        return self.read_bytes().decode('utf-8')


def load_inputs(root):
    require(bool(PINNED_FILES), 'release pins absent')
    checked = {p: pinned_read(root, p, sha) for p, sha in PINNED_FILES.items()}
    hashes = json.loads(checked[BASE + '/generated/artifact_hashes.json'])
    generated = {name: pinned_read(root, BASE + '/generated/' + name, sha)
                 for name, sha in hashes.items()}
    generated['artifact_hashes.json'] = checked[BASE + '/generated/artifact_hashes.json']
    # Execute only the already hash-checked immutable reader, never a mutable
    # module import. All its file reads use this checked in-memory snapshot.
    reader = types.ModuleType('pinned_register_reader')
    exec(compile(checked[BASE + '/inspect_register.py'], BASE + '/inspect_register.py',
                 'exec'), reader.__dict__)
    tables = {name: reader.read_table(SnapshotPath(generated), name)
              for name in reader.TABLES}
    source_config = json.loads(checked[BASE + '/source_manifest.json'])
    require(tables['manifest']['requirements'] == source_config['requirements'],
            'manifest policy binding mismatch')
    require(tables['manifest']['requirements_version'] == RULES, 'stale policy version')
    sources = {}
    for source in source_config['sources']:
        raw = pinned_read(root, source['path'], source['sha256'])
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        require(blob == source['git_blob'], 'source Git blob mismatch')
        rows = (json.loads(raw) if source['adapter'] == 'us_offering' else
                list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))))
        require(len(rows) == source['expected_rows'], 'source row count mismatch')
        sources[source['path']] = {'config': source, 'rows': rows}
    evidence = {Path(p).name: json.loads(raw) for p, raw in checked.items()
                if p.startswith(RELEASE + '/evidence/') and p.endswith('.json')}
    verify_native_evidence(root, evidence)
    return tables, sources, evidence


def verify_native_evidence(root, evidence):
    """Require the archived native proof; external context is never read here."""
    receipt, facts = evidence['REVIEW_RECEIPT.json'], evidence['ISSUER_IDENTITY_FACTS.json']
    policy = receipt['gate_evidence_policy']
    observations = unique_index(facts['observations'], 'source_round_key')
    allowed = unique_index(receipt['gate_evidence_allowlist'], 'source_round_key')
    require(set(observations) == set(allowed) and len(allowed) == 6,
            'native evidence allowlist mismatch')
    native_texts = {}
    for key, fact in observations.items():
        archive, permit = fact['archive'], allowed[key]
        require(permit['url'] == fact['source_url'] and
                permit['url'].startswith('https://europe.republic.com/') and
                permit['content_sha256'] == archive['content_sha256'] and
                permit['text_sha256'] == archive['text_sha256'], 'native source pin mismatch')
        files = {x['path']: x['git_blob_sha'] for x in fact['git_blob_bindings']}
        require(set(files) == {archive['capture_path'], archive['text_path']},
                'native archive file set mismatch')
        decoded = {}
        for path, expected_blob in files.items():
            raw = read_regular(root, path)
            actual_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            require(actual_blob == expected_blob, 'native archive blob mismatch: ' + path)
            if path == archive['capture_path']:
                require(digest(raw) == archive['capture_gzip_sha256'], 'native compressed hash mismatch')
            decoded[path] = gzip.decompress(raw)
        require(digest(decoded[archive['capture_path']]) == archive['content_sha256'],
                'native content hash mismatch')
        require(digest(decoded[archive['text_path']]) == archive['text_sha256'],
                'native text hash mismatch')
        text = decoded[archive['text_path']].decode('utf-8')
        require(len(text) == archive['text_chars'], 'native text length mismatch')
        native_texts[key] = text
    native_predicates(observations, native_texts, policy)


def native_predicates(observations, native_texts, policy):
    anchors = set(policy['native_anchor_set'])
    unsuffixed = set(policy['native_unsuffixed_set'])
    require(len(anchors) == 4 and len(unsuffixed) == 2 and not anchors & unsuffixed and
            anchors | unsuffixed == set(observations) == set(native_texts),
            'incomplete native match chain')
    require(policy['external_source_policy_expanded'] is False, 'source policy expansion')
    for key, fact in observations.items():
        text = ' '.join(native_texts[key].split())
        for value in ['553249', '26 Nov 2014', 'www.cruaoutdoors.com', 'Tralee', 'Ireland', 'Crua Outdoors']:
            require(value in text, 'missing native match predicate: ' + key)
        require(fact['incorporation_date_iso'] == '2014-11-26' and
                fact['company_domain_normalized'] == 'cruaoutdoors.com' and
                fact['location_native'] == ['Tralee', 'Ireland'], 'native combined-match mismatch')
        if key in anchors:
            require(fact['company_number_native'] == '553249(Ireland)' and
                    '553249(Ireland)' in text and fact['trading_name_clause'] in text and
                    'Thermo Tents Limited' in fact['trading_name_clause'],
                    'missing explicit native legal-issuer anchor')
        else:
            require(fact['company_number_native'] == '553249', 'unsuffixed number mismatch')


def unique_index(rows, key):
    result = {x[key]: x for x in rows}
    require(len(result) == len(rows), 'duplicate ' + key)
    return result


def validate_selection(tables, sources, evidence):
    receipt = evidence['REVIEW_RECEIPT.json']
    bindings = evidence['REGISTER_BINDINGS.json']
    facts = evidence['ISSUER_IDENTITY_FACTS.json']
    require(receipt['snapshot_commit'] == bindings['snapshot_commit'] == SNAPSHOT,
            'snapshot mismatch')
    require(receipt['status'] == 'VERIFIED_BOUNDED_IDENTITY_EVIDENCE', 'unreviewed receipt')
    require(receipt['application_status'] == 'NOT_APPLIED_BY_THIS_REVIEW',
            'unexpected source application status')
    require(bindings['requirements'] == tables['manifest']['requirements'],
            'review policy mismatch')
    require(receipt['scope_counts']['independently_reviewed_campaign_issuer_matches'] == 6,
            'match scope mismatch')
    records = unique_index(tables['records'], 'record_id')
    assessments = unique_index(tables['assessments'], 'assessment_id')
    lineage = unique_index(tables['lineage'], 'lineage_id')
    selected = receipt['target_allowlist']
    require(len(selected) == len(unique_index(selected, 'assessment_id')) == 16,
            'target assessment set mismatch')
    selected_ids = {x['record_id'] for x in selected}
    require(len(selected_ids) == 8, 'record scope mismatch')
    require({x['assessment_id'] for x in selected} ==
            {x['assessment_id'] for x in tables['assessments'] if x['record_id'] in selected_ids},
            'incomplete record assessment coverage')
    require({r['record_id'] for r in bindings['records']} == selected_ids,
            'binding record set mismatch')
    require(sorted(bindings['assessments'], key=lambda x: x['assessment_id']) ==
            sorted((assessments[x['assessment_id']] for x in selected), key=lambda x: x['assessment_id']),
            'binding assessment object mismatch')
    observations = unique_index(facts['observations'], 'source_round_key')
    require(len(observations) == 6, 'evidence campaign count mismatch')
    used_lineages = set()
    for target in selected:
        r = records[target['record_id']]
        a = assessments[target['assessment_id']]
        require(canonical_hash(r) == target['baseline_record_sha256'], 'record object mismatch')
        require(canonical_hash(a) == target['baseline_assessment_sha256'], 'assessment object mismatch')
        require(r['record_type'] == target['record_type'] and r['source_key'] == target['source_key'],
                'record key/type mismatch')
        require(a['record_id'] == r['record_id'] and a['scope'] == target['source_scope'] and
                a['requirements_version'] == target['requirements_version'] == RULES,
                'assessment scope mismatch')
        require(a['gates'] == target['baseline_gates'], 'baseline gates mismatch')
        require(target['permitted_derived_gate_changes'] ==
                {k: {'from': a['gates'][k], 'to': v} for k, v in GATE_CHANGES.items()},
                'unpermitted gate change')
        require(a['completion_status'] == 'unclassified' and
                a['completion_counts_established'] is False and a['empirical_promotion'] is False,
                'completion or promotion mismatch')
        expected_lines = [lineage[lid] for lid in r['lineage_ids']
                          if sources[lineage[lid]['source_path']]['config']['scope'] == a['scope']]
        require(sorted(target['source_bindings'], key=lambda x: x['lineage_id']) ==
                sorted(expected_lines, key=lambda x: x['lineage_id']),
                'incomplete scoped lineage coverage')
        for line in expected_lines:
            require(line == lineage[line['lineage_id']], 'lineage object mismatch')
            require(r['record_id'] in line['record_ids'], 'lineage target mismatch')
            source = sources[line['source_path']]
            require(source['config']['source_commit'] == line['source_commit'] and
                    source['config']['sha256'] == line['source_sha256'], 'source lineage pin mismatch')
            require(type(line['row_number']) is int and 1 <= line['row_number'] <= len(source['rows']),
                    'invalid source ordinal')
            row = source['rows'][line['row_number'] - 1]
            require(canonical_hash(row) == line['row_sha256'], 'logical source row mismatch')
            fact = observations[row['round_id']]
            require(fact['original_logical_row'] == line['row_number'] and
                    fact['existing_company_key'] == row['canonical_company_id'],
                    'evidence row/company mismatch')
            if source['config']['adapter'] == 'eu_round':
                require(fact['source_url'] == row['campaign_url'], 'evidence URL mismatch')
            require(fact['company_number_normalized'] == '553249' and
                    fact['jurisdiction_supported'] == 'Ireland', 'issuer evidence mismatch')
            if r['record_type'] == 'round':
                require(r['source_key'] == row['round_id'], 'round source key mismatch')
            else:
                require(r['record_type'] == 'company_key' and
                        r['source_key'] == row['canonical_company_id'], 'company source key mismatch')
            used_lineages.add(line['lineage_id'])
    require(len(used_lineages) == 12 and used_lineages ==
            {x['lineage_id'] for x in bindings['lineage']}, 'source lineage set mismatch')
    require(sorted(bindings['lineage'], key=lambda x: x['lineage_id']) ==
            sorted((lineage[x] for x in used_lineages), key=lambda x: x['lineage_id']),
            'bound lineage differs')
    expected_edges = [x for x in tables['crosswalk'] if x['lineage_id'] in used_lineages]
    require(canonical_hash(bindings['crosswalk']) == canonical_hash(expected_edges),
            'crosswalk mismatch')
    require(sum(records[x]['record_type'] == 'company_key' for x in selected_ids) == 2 and
            sum(records[x]['record_type'] == 'round' for x in selected_ids) == 6,
            'unit counts mismatch')
    return receipt, selected, records, assessments


def build_view(root):
    """All-or-nothing view: a failed binding emits HOLD and no verified rows."""
    try:
        tables, sources, evidence = load_inputs(root)
        receipt, selected, records, assessments = validate_selection(tables, sources, evidence)
        views = []
        for target in selected:
            original = copy.deepcopy(assessments[target['assessment_id']])
            reviewed = copy.deepcopy(original)
            reviewed['gates'].update(GATE_CHANGES)
            views.append({'original': original, 'reviewed': reviewed,
                          'review_metadata': {'receipt_id': receipt['receipt_id'],
                                              'baseline_assessment_sha256': target['baseline_assessment_sha256'],
                                              'original_identity_gates': {k: original['gates'][k] for k in GATE_CHANGES},
                                              'lineage_ids': [x['lineage_id'] for x in target['source_bindings']]}})
        return {'view_version': 'company-register-reviewed-view/0.1.1',
                'status': 'VERIFIED_SELECTED_MATCHES', 'snapshot_commit': SNAPSHOT,
                'scope': 'Six campaign-to-issuer links only; round identity means issuer attribution, not economic-round equivalence.',
                'identity_semantics': copy.deepcopy(receipt['identity_semantics']),
                'independent_matches': 6, 'assessment_applications': 16,
                'company_key_records': 2, 'source_round_records': 6,
                'records': [copy.deepcopy(records[x]) for x in sorted({t['record_id'] for t in selected})],
                'assessments': views, 'completion_status': 'unclassified',
                'completion_counts_established': False, 'verified_complete': None, 'partial': None,
                'empirical_promotion': False, 'canonical_data_changed': False,
                'global_identity_qa': 'NOT_ASSESSED',
                'source_boundary': 'Native campaign evidence supports the selected issuer links. External registry facts are context only; no outcome, censor or round decision is derived.'}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {'view_version': 'company-register-reviewed-view/0.1.1', 'status': 'HOLD',
                'reason': str(error), 'assessments': [], 'records': [],
                'completion_status': 'unclassified', 'completion_counts_established': False,
                'verified_complete': None, 'partial': None, 'empirical_promotion': False,
                'canonical_data_changed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    result = build_view(args.root)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result['status'] == 'VERIFIED_SELECTED_MATCHES' else 2


if __name__ == '__main__':
    raise SystemExit(main())
