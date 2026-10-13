"""Additive, fail-closed source inventory; never a rate or population promotion.

Python 3.10+, standard library only. See docs/COMPLETION_REGISTER_V1.md.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

VERSION = 'completion-register/1.0.0'
RULES = 'phase1c-spec-717e7be8-register-v1'
SOURCE_COMMIT = '717e7be8f6ee672815f69ef8d8885ff9a555055d'
SPEC_BLOB = 'fb62fb062274cf51b8090f91990c3181dc99bdb2'
GATES = ('identity', 'economic_round', 'cohort_year', 'funded_time_zero',
         'field_taxonomy', 'outcome_followup', 'cross_platform_graph', 'identity_qa')
ADAPTERS = {'wf_funded', 'eu_round', 'eu_outcome', 'wf_event', 'us_offering', 'discovery'}
EXPECTED_INPUTS = {'data/phase1d/cp2_republic_europe_rounds_normalized.csv': ('eu_round', 952, '30c0c41c63e371c17571b9d4388720c3f25dbfd4aa6a73421f29ddbe952e73d4', '18af1ddafadebdd673209ad9b85a4df445440fcf'), 'data/phase1d/cp7/analysis-cp8-verified/republic_europe_outcome_ledger_v5.csv': ('eu_outcome', 952, 'b31a7a1e60a11ab94f40ad32c68cb632ae20a7fc7a37b58b29e1bcc869ef5dbe', '8d15721a66b6a46ef92f6a139303d9f327930f84'), 'data/phase1d/cp7/analysis-cp8-verified/wefunder_public_profile_event_candidates.csv': ('wf_event', 65, '20c466c83e96d361c3a2ef17640433b479cdcf551773a0970a2de7d7bd8ad5ef', '9c7c9204923191d3857057689cd30df85201e29a'), 'data/phase1d/cp1_tavily_candidates_us.csv': ('discovery', 220, 'ccb4af63998aebdb32686126f8a73d1342a7989dd372d685a4576a4174d2c76b', 'f47ac20fe2979718bea8ad468f9ef47cd7307914'), 'data/phase1d/cp1_tavily_candidates_eu_web.csv': ('discovery', 66, '621f39a8d80374bf901060844402796286902e99e6f5174d25648b9f216d3413', 'f52d6268c610970dc2ad68d31661a93d1353f7ed'), 'data/cohort_manifest.csv': ('wf_funded', 42, '62468cea323ed6d2732df90cbe5ced04990db907cf908e4939b4128a302f78c8', '45d143961d73585dcbe8f7534463ea7362513249'), 'data/phase1d/cp10/collection-2-campaigns-large-docs/native_campaign_candidates.json': ('us_offering', 568, '1fe6501749a18029eff67b44ebd613234b6c4408f57f98cb6b601f458a02cc50', 'b8997b8e19c80746a42f400b4667590de0dc592f')}



def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sid(kind, *parts):
    return kind + ':' + digest(canonical(parts).encode())[:32]


def safe_path(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('source path must be relative')
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('source path escapes root')
    return path


def read_source(root, source):
    for name, pattern in [('sha256', r'[0-9a-f]{64}'), ('git_blob', r'[0-9a-f]{40}'),
                          ('source_commit', r'[0-9a-f]{40}')]:
        if not re.fullmatch(pattern, source.get(name, '')):
            raise ValueError('invalid ' + name)
    if source.get('adapter') not in ADAPTERS:
        raise ValueError('unknown adapter')
    raw = safe_path(root, source['path']).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if digest(raw) != source['sha256'] or blob != source['git_blob']:
        raise ValueError('source hash mismatch: ' + source['path'])
    text = raw.decode('utf-8-sig')
    if source['adapter'] == 'us_offering':
        rows = json.loads(text)
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError('JSON source must be array of objects')
    else:
        reader = csv.DictReader(io.StringIO(text, newline=''))
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)):
            raise ValueError('missing or duplicate CSV headers')
        rows = list(reader)
        if any(None in r or any(v is None for v in r.values()) for r in rows):
            raise ValueError('ragged CSV row')
    if len(rows) != source.get('expected_rows'):
        raise ValueError('source row count mismatch: ' + source['path'])
    return rows


class Register:
    def __init__(self):
        self.records = {}
        self.lineage = []
        self.crosswalk = []
        self.conflicts = []
        self.observations = []
        self.seen_rows = {}
        self.seen_lineage_ids = set()
        self.claims = defaultdict(lambda: defaultdict(set))

    def record(self, kind, platform, key, *, jurisdiction='', identity='unresolved', label=''):
        if key is None or str(key).strip() == '':
            raise ValueError('empty source identifier for ' + kind)
        rid = sid(kind, platform, jurisdiction, str(key))
        value = {'record_id': rid, 'record_type': kind, 'platform': platform,
                 'jurisdiction': jurisdiction, 'source_key': str(key), 'identity_status': identity,
                 'labels': [], 'lineage_ids': [], 'source_scopes': []}
        rec = self.records.setdefault(rid, value)
        self.claims[rid]['identity_status'].add(identity)
        if label and label not in rec['labels']:
            rec['labels'].append(label)
        return rid

    def link(self, source_id, target_id, relation, basis, lineage_id):
        self.crosswalk.append({'source_record_id': source_id, 'target_record_id': target_id,
                               'relation': relation, 'basis': basis, 'lineage_id': lineage_id,
                               'assertion_status': 'source_asserted' if basis != 'US_SEC_CIK' else 'strong_identifier'})

    def ingest(self, source, rows):
        for number, row in enumerate(rows, 1):
            rowhash = digest(canonical(row).encode())
            lid = sid('lineage', source['source_commit'], source['path'], number, rowhash)
            if lid in self.seen_lineage_ids:
                continue
            self.seen_lineage_ids.add(lid)
            entry = {'lineage_id': lid, 'source_path': source['path'], 'source_commit': source['source_commit'],
                     'source_sha256': source['sha256'], 'row_number': number, 'row_sha256': rowhash,
                     'record_ids': [], 'disposition': 'unresolved', 'reason': ''}
            duplicate_key = (source['path'], rowhash)
            duplicate_of = self.seen_rows.get(duplicate_key)
            self.seen_rows.setdefault(duplicate_key, lid)
            try:
                ids, reason = self.adapt(source['adapter'], row, lid)
                entry['record_ids'] = sorted(set(ids))
                entry['reason'] = reason
                entry['disposition'] = 'linked' if not reason else 'unresolved'
                if duplicate_of:
                    entry.update(disposition='duplicate', duplicate_of=duplicate_of,
                                 reason='exact_duplicate_source_row')
                for rid in set(ids):
                    self.records[rid]['lineage_ids'].append(lid)
                    self.records[rid]['source_scopes'].append(source['scope'])
            except (ValueError, KeyError, TypeError) as exc:
                entry.update(disposition='quarantined', reason='invalid_source_row:' + str(exc))
            self.lineage.append(entry)
            # Source observations point to immutable rows. They do not re-adjudicate claims.
            self.observations.append({'evidence_id': sid('evidence', lid), 'lineage_id': lid,
                                      'record_ids': entry['record_ids'],
                                      'evidence_status': 'preserved_source_assertion_not_reverified',
                                      'source_status': row.get('row_status', row.get('status', row.get('classification', row.get('outcome_ascertainment_status', row.get('validation_status', ''))))),
                                      'source_estimation_eligible': row.get('estimation_eligible'),
                                      'source_outcome': {k: row[k] for k in ('success_date', 'success_type', 'closure_date', 'closure_type', 'last_positive_date', 'censor_date', 'terminal_event_type', 'current_eligible_evidence', 'evidence_trace') if k in row}})

    def adapt(self, adapter, r, lid):
        ids = []
        required = {'wf_funded': ('issuer_cik', 'offering_key'), 'eu_round': ('canonical_company_id', 'round_id'),
                    'eu_outcome': ('canonical_company_id', 'round_id'), 'wf_event': ('source_native_company_id', 'source_event_ordinal'),
                    'us_offering': ('native_offering_id',), 'discovery': ('url', 'platform')}[adapter]
        for field in required:
            if r.get(field) is None or str(r[field]).strip() == '':
                raise ValueError('missing required source key: ' + field)
        if adapter == 'wf_funded':
            cik = str(r['issuer_cik']).strip()
            if not re.fullmatch(r'\d{1,10}', cik) or int(cik) == 0:
                raise ValueError('invalid SEC CIK')
            company = self.record('company', 'sec', cik.zfill(10), jurisdiction='US', identity='strong_identifier', label=r.get('issuer_name', ''))
            offering = self.record('offering', 'wefunder', r['offering_key'])
            ids = [company, offering]
            self.link(offering, company, 'issuer', 'US_SEC_CIK', lid)
            self.claims[offering]['company'].add(company)
            for field in ('initial_form_c_date', 'funding_close_date'):
                if r.get(field):
                    self.claims[offering][field].add(str(r[field]))
            return ids, 'frozen_membership_preserved_outcome_research_not_assessed'
        if adapter in {'eu_round', 'eu_outcome'}:
            key = r['canonical_company_id']
            fallback = 'name:' in key or 'name-' in key or key.startswith('reurope-company:name')
            company = self.record('company_key', 'republic_europe', key,
                                  identity='name_fallback' if fallback else 'source_identifier_jurisdiction_unverified', label=r.get('campaign_name', ''))
            round_id = self.record('round', 'republic_europe', r['round_id'])
            ids = [company, round_id]
            self.link(round_id, company, 'source_company_key', 'source_key_only_no_legal_merge', lid)
            self.claims[round_id]['company'].add(company)
            for field in ('offering_year', 'completion_date', 'primary_field', 'censor_date', 'last_positive_date'):
                if r.get(field):
                    self.claims[round_id][field].add(str(r[field]))
            for field in ('outcome_ascertainment_status', 'success_date', 'success_type', 'closure_date', 'closure_type',
                          'terminal_event_type', 'terminal_event_interval_start', 'terminal_event_interval_end',
                          'terminal_event_success_value', 'current_eligible_evidence'):
                if field in r:
                    self.claims[round_id][field].add(str(r[field]))
            return ids, 'name_only_identity' if fallback else 'legal_jurisdiction_and_research_gates_unverified'
        if adapter == 'wf_event':
            if not str(r['source_native_company_id']).isdigit() or not str(r['source_event_ordinal']).isdigit():
                raise ValueError('invalid native profile or event identifier')
            profile = self.record('profile', 'wefunder', r['source_native_company_id'], identity='platform_native_candidate', label=r.get('company_name', ''))
            event = self.record('profile_event', 'wefunder', canonical([r['source_native_company_id'], r['source_event_ordinal']]))
            self.link(event, profile, 'profile_event', 'native_profile_id_not_economic_round', lid)
            return [profile, event], 'candidate_not_company_or_economic_round'
        if adapter == 'us_offering':
            if not str(r['native_offering_id']).isdigit() or int(r['native_offering_id']) <= 0:
                raise ValueError('invalid native offering identifier')
            offering = self.record('offering', 'republic_us', r['native_offering_id'])
            if r.get('offering_year'):
                self.claims[offering]['offering_year'].add(str(r['offering_year']))
            return [offering], 'issuer_coissuer_and_economic_round_identity_unresolved'
        if adapter == 'discovery':
            if not isinstance(r['platform'], str) or not isinstance(r['url'], str):
                raise ValueError('invalid discovery platform or URL')
            url = r['url'].strip()
            if not re.match(r'^https?://[^/\s]+', url):
                raise ValueError('invalid discovery URL')
            rid = self.record('discovery_url', r['platform'], url)
            return [rid], 'discovery_only_not_admissible_evidence'
        raise ValueError('unknown adapter')

    def finalize(self):
        self.conflicts = []
        for rid, fields in sorted(self.claims.items()):
            for field, values in sorted(fields.items()):
                if len(values) > 1:
                    self.conflicts.append({'conflict_id': sid('conflict', rid, field, sorted(values)),
                                           'record_id': rid, 'field': field, 'values': sorted(values),
                                           'status': 'unresolved', 'reason': 'incompatible_source_assertions_no_precedence_applied'})
        conflicting = {c['record_id'] for c in self.conflicts}
        for entry in self.lineage:
            if conflicting.intersection(entry['record_ids']):
                entry.update(disposition='quarantined', reason='crosswalk_or_field_conflict')
        memberships = defaultdict(set)
        for link in self.crosswalk:
            memberships[link['target_record_id']].add(self.records[link['source_record_id']]['platform'])
        assessments = []
        for rid, rec in sorted(self.records.items()):
            rec['platform_memberships'] = sorted(memberships[rid] or {rec['platform']})
            for field in ('labels', 'lineage_ids', 'source_scopes'):
                rec[field] = sorted(set(rec[field]))
            gates = {gate: 'not_assessed' for gate in GATES}
            if rec['identity_status'] == 'strong_identifier':
                gates['identity'] = 'supported_strong_identifier'
            mapping = {'offering_year': 'cohort_year', 'completion_date': 'funded_time_zero',
                       'funding_close_date': 'funded_time_zero', 'primary_field': 'field_taxonomy',
                       'censor_date': 'outcome_followup', 'last_positive_date': 'outcome_followup'}
            for field, gate in mapping.items():
                if self.claims[rid].get(field):
                    gates[gate] = 'source_asserted_unadjudicated'
            # Full study completion is not inferred from metadata availability.
            status = 'unclassified'
            reasons = ['full_research_gate_adjudication_not_loaded']
            if rid in conflicting:
                reasons.append('unresolved_conflicting_source_assertions')
            for scope in rec['source_scopes']:
                assessments.append({'assessment_id': sid('assessment', RULES, rid, scope),
                                    'record_id': rid, 'scope': scope, 'requirements_version': RULES,
                                    'completion_status': status, 'gates': gates,
                                    'unresolved_reasons': reasons, 'completion_counts_established': False,
                                    'original_unit_of_analysis': 'economic_company_round', 'empirical_promotion': False})
        counts = Counter((p, r['record_type']) for r in self.records.values() for p in r['platform_memberships'])
        progress = []
        for (platform, kind), total in sorted(counts.items()):
            progress.append({'platform': platform, 'unit': kind, 'loaded_unique_records': total,
                             'verified_complete': None, 'partial': None, 'unclassified': total,
                             'completion_counts_established': False,
                             'denominator_scope': 'loaded_inputs_only_not_full_population'})
        return {'records': sorted(self.records.values(), key=lambda r: r['record_id']),
                'lineage': sorted(self.lineage, key=lambda r: r['lineage_id']),
                'crosswalk': sorted(self.crosswalk, key=canonical),
                'evidence': sorted(self.observations, key=lambda r: r['evidence_id']),
                'assessments': assessments, 'conflicts': self.conflicts, 'progress': progress}


def build(root, config):
    if config.get('schema_version') != VERSION or not config.get('sources'):
        raise ValueError('invalid or empty input configuration')
    requirements = config.get('requirements', {})
    if requirements.get('source_commit') != SOURCE_COMMIT or requirements.get('git_blob') != SPEC_BLOB:
        raise ValueError('unsupported study requirements revision')
    spec_raw = safe_path(root, requirements['path']).read_bytes()
    spec_blob = hashlib.sha1(b'blob ' + str(len(spec_raw)).encode() + b'\0' + spec_raw).hexdigest()
    if spec_blob != SPEC_BLOB or digest(spec_raw) != requirements.get('sha256'):
        raise ValueError('requirements source hash mismatch')
    if any(s.get('source_commit') != SOURCE_COMMIT or not s.get('scope') for s in config['sources']):
        raise ValueError('source commit or scope mismatch')
    paths = [s['path'] for s in config['sources']]
    if set(paths) != set(EXPECTED_INPUTS):
        raise ValueError('missing or unexpected source in versioned seven-input release')
    for source in config['sources']:
        if (source['adapter'], source['expected_rows'], source['sha256'], source['git_blob']) != EXPECTED_INPUTS[source['path']]:
            raise ValueError('source does not match frozen input contract')
    if len(paths) != len(set(paths)):
        raise ValueError('duplicate source paths')
    reg = Register()
    reconciled = []
    coverage = []
    for source in sorted(config['sources'], key=lambda s: s['path']):
        rows = read_source(root, source)
        if source['adapter'] == 'eu_round':
            eligible = [r for r in rows if r.get('offering_year') in {str(y) for y in range(2020, 2026)}]
            coverage.append({'source_path': source['path'], 'unit': 'source_round', 'rows': len(rows),
                             'offering_year_2020_2025_rows': len(eligible),
                             'offering_year_2020_2025_company_keys': len({r['canonical_company_id'] for r in eligible}),
                             'name_fallback_company_keys': len({r['canonical_company_id'] for r in rows if r.get('company_id_normalization_status') == 'NAME_FALLBACK'}),
                             'meaning': 'source assertions preserved; no new cohort admission'})
        if source['adapter'] == 'eu_outcome':
            coverage.append({'source_path': source['path'], 'unit': 'source_outcome_row',
                             'outcome_statuses': dict(sorted(Counter(r['outcome_ascertainment_status'] for r in rows).items())),
                             'current_eligible_evidence': dict(sorted(Counter(r['current_eligible_evidence'] for r in rows).items())),
                             'meaning': 'unchanged source assertions, not re-adjudicated'})
        if source['adapter'] == 'us_offering':
            coverage.append({'source_path': source['path'], 'unit': 'source_offering',
                             'source_year_in_study_true': sum(r.get('year_in_study') is True for r in rows),
                             'company_identity_verified': sum(r.get('company_economic_round_identity_verified') is True for r in rows),
                             'meaning': 'source assertions only; offering identifiers are not companies'})
        before = len(reg.lineage)
        reg.ingest(source, rows)
        reconciled.append({'path': source['path'], 'input_rows': len(rows), 'lineage_rows': len(reg.lineage) - before})
    result = reg.finalize()
    result['source_coverage'] = coverage
    result['manifest'] = {'schema_version': VERSION, 'requirements_version': RULES,
                          'input_configuration_sha256': digest(canonical(config).encode()),
                          'sources': sorted(config['sources'], key=lambda s: s['path']),
                          'requirements': requirements,
                          'reconciliation': reconciled,
                          'dispositions': dict(sorted(Counter(r['disposition'] for r in result['lineage']).items())),
                          'loaded_rows': len(result['lineage']), 'full_population_migrated': False,
                          'prior_rates_changed': False, 'empirical_promotion': False,
                          'limitations': ['No company union across overlapping Wefunder frames.',
                                          'EU company keys retain source identity; legal jurisdiction is not inferred.',
                                          'Raw-profile counts reported elsewhere are not loaded rows.',
                                          'No review receipts loaded; verified_complete is not established.',
                                          'No cross-platform economic-round merge performed.']}
    assert sum(x['input_rows'] for x in reconciled) == len(result['lineage'])
    return result


def write_outputs(output, result):
    """Immutable outputs: identical reruns are no-ops, changed bytes fail closed."""
    payloads = {}
    for name, value in result.items():
        ext = '.json' if name in {'manifest', 'progress'} else '.jsonl'
        raw = ((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n') if ext == '.json'
               else ''.join(canonical(row) + '\n' for row in value)).encode()
        if ext == '.jsonl':
            buffer = io.BytesIO()
            with gzip.GzipFile(filename='', mode='wb', fileobj=buffer, mtime=0) as stream:
                stream.write(raw)
            raw = base64.b64encode(buffer.getvalue()) + b'\n'
            ext += '.gz.b64'
        payloads[name + ext] = raw
    payloads['artifact_hashes.json'] = (json.dumps({n: digest(v) for n, v in sorted(payloads.items())}, indent=2, sort_keys=True) + '\n').encode()
    output.mkdir(parents=True, exist_ok=True)
    for name, raw in payloads.items():
        path = output / name
        if path.exists() and path.read_bytes() != raw:
            raise ValueError('refusing to overwrite changed artifact: ' + name)
    for name, raw in payloads.items():
        path = output / name
        if path.exists():
            continue
        fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=output)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, path)
        finally:
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    # Prevent accidental placement over immutable source inputs.
    if any(safe_path(args.root, s['path']).is_relative_to(args.output.resolve()) for s in config['sources']):
        parser.error('output directory may not contain source inputs')
    result = build(args.root, config)
    write_outputs(args.output, result)
    print(json.dumps({'loaded_rows': result['manifest']['loaded_rows'], 'verified_complete': None,
                      'full_population_migrated': False, 'empirical_promotion': False}, sort_keys=True))


if __name__ == '__main__':
    main()
