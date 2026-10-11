"""Read-only ledger preparation audit. Never builds histories or decides eligibility."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
from collections import Counter
from datetime import date

VERSION = 'preparation-disposition-audit-v0.1.0'
DAYS_PER_MONTH = 30.4375
# Numeric follow-up is often a six-decimal storage representation; this is only
# a discrepancy inventory tolerance, not a timing or evidence acceptance rule.
FOLLOWUP_COMPARISON_TOLERANCE_MONTHS = 0.000001
REQUIREMENTS = {
    'round_identity_and_funded_origin': {
        'existing_fields': ['round_id', 'canonical_company_id', 'completion_date', 'evidence_trace'],
        'review_fields': ['reviewed_economic_round_identity', 'funded_position_evidence', 'origin_convention_review'],
        'reason': 'FUNDED_CLOCK_AND_ROUND_IDENTITY_REVIEW',
        'next_action': 'Bind the economic round, funded/completed position and chosen origin to reviewed evidence; do not infer them from populated keys or a date.'},
    'initial_state': {
        'existing_fields': ['completion_date', 'success_date', 'terminal_event_type'],
        'review_fields': ['reviewed_initial_state', 'initial_state_evidence', 'entry_eligibility_review'],
        'reason': 'INITIAL_STATE_REVIEW_NO_AUTOMATIC_PRE_OR_POST',
        'next_action': 'Review independence and index-specific success state at entry. Neither a blank success field nor a financing automatically supplies PRE/POST.'},
    'index_success_and_target': {
        'existing_fields': ['success_date', 'success_type', 'success_valuation_multiple', 'success_evidence_url', 'success_evidence_sha256'],
        'review_fields': ['index_qualification_review', 'initial_post_policy', 'selected_success_endpoint'],
        'reason': 'INDEX_QUALIFICATION_AND_TARGET_REVIEW',
        'next_action': 'Review the success predicate against this index round and explicitly distinguish incident contribution from baseline-plus-incident qualification.'},
    'typed_event_chronology': {
        'existing_fields': ['success_date', 'closure_date', 'terminal_event_type', 'terminal_event_interval_start', 'terminal_event_interval_end', 'terminal_event_midpoint_for_primary'],
        'review_fields': ['reviewed_exact_transition_sequence', 'same_subject_tie_resolution', 'event_precision_review'],
        'reason': 'TYPED_EXACT_CHRONOLOGY_REVIEW',
        'next_action': 'Review typed first events, precision and sequence without replacing unknown/interval facts by automatic transitions.'},
    'endpoint_observation': {
        'existing_fields': ['last_positive_date', 'censor_date', 'followup_months', 'terminal_event_evidence_url', 'evidence_trace'],
        'review_fields': ['endpoint_specific_observation_review', 'administrative_extraction_limit', 'source_availability_review'],
        'reason': 'ENDPOINT_OBSERVATION_AND_CUTOFF_REVIEW',
        'next_action': 'Separate affirmative operation, event-specific endpoints and administrative limit; do not extend follow-up automatically.'},
    'cohort_assignment': {
        'existing_fields': ['offering_year', 'offering_year_status', 'platform'],
        'review_fields': ['cohort_membership_review', 'prepared_history_disposition'],
        'reason': 'COHORT_AND_DISPOSITION_REVIEW',
        'next_action': 'Retain every row and its unresolved dispositions; do not present a selected exact-history subset as the original cohort.'},
}
DATE_FIELDS = ('completion_date', 'success_date', 'closure_date', 'last_positive_date', 'censor_date',
               'terminal_event_interval_start', 'terminal_event_interval_end', 'terminal_event_midpoint_for_primary')
PRIORITIES = {'MISSING_ROUND_ID': 100, 'MISSING_COMPANY_ID': 100, 'DUPLICATE_ROUND_ID': 100,
 'INVALID_DATE': 100, 'INVALID_FOLLOWUP': 100, 'DATE_BEFORE_ORIGIN': 95,
 'REVERSED_TERMINAL_INTERVAL': 95, 'TIED_SUCCESS_TERMINAL_REQUIRES_TYPED_REVIEW': 90,
 'TERMINAL_INTERVAL_NOT_EXACT': 85, 'UNKNOWN_VALUE_ACQUISITION_NOT_AUTOMATIC_SUCCESS_OR_CLOSURE': 85,
 'FINANCING_BEYOND_AFFIRMATIVE_OPERATION': 80, 'EVENT_BEYOND_SUPPLIED_CENSOR': 80,
 'FOLLOWUP_DATE_NUMERIC_MISMATCH': 75, 'UNRECOGNIZED_TERMINAL_TYPE_REQUIRES_REVIEW': 75, 'MISSING_COMPLETION_DATE': 70,
 'MISSING_OBSERVATION_DATE': 70, 'SUCCESS_SOURCE_BINDING_INCOMPLETE': 60,
 'SUCCESS_EVENT_LABEL_REQUIRES_INDEX_EVIDENCE_REVIEW': 55,
 'MULTI_ROUND_COMPANY_REQUIRES_INDEX_SPECIFIC_ENTRY_REVIEW': 45,
 'OFFERING_YEAR_UNRESOLVED': 50, 'OFFERING_YEAR_OUTSIDE_STUDY_SCOPE': 50}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')


def present(value):
    return value is not None and str(value).strip() != ''


def audit_rows(rows: list[dict], *, source_sha256: str, fieldnames=None) -> dict:
    """Inspect facts as supplied; review-required is not a judgment of ineligibility."""
    fields = list(fieldnames) if fieldnames is not None else sorted({key for row in rows for key in row})
    duplicate_ids = {key for key, count in Counter(str(row.get('round_id', '')) for row in rows).items()
                     if key and count > 1}
    company_counts = Counter(str(row.get('canonical_company_id', '')) for row in rows if present(row.get('canonical_company_id')))
    records = []
    for index, row in enumerate(rows):
        reasons = []
        mechanical = []
        def add(code, detail, affected_fields=(), *, shape_error=False):
            reasons.append({'code': code, 'detail': detail, 'fields': list(affected_fields),
                            'priority': PRIORITIES.get(code, 20),
                            'kind': 'MECHANICAL_INPUT_GAP' if shape_error else 'REVIEW_OR_EVIDENCE_GAP'})
            if shape_error:
                mechanical.append(code)
        if not present(row.get('round_id')):
            add('MISSING_ROUND_ID', 'No economic-round identifier supplied.', ['round_id'], shape_error=True)
        if not present(row.get('canonical_company_id')):
            add('MISSING_COMPANY_ID', 'No company dependence-cluster identifier supplied.', ['canonical_company_id'], shape_error=True)
        if str(row.get('round_id', '')) in duplicate_ids:
            add('DUPLICATE_ROUND_ID', 'Repeated identifier is retained; no deduplication or new identity is inferred.', ['round_id'], shape_error=True)
        dates = {}
        for field in DATE_FIELDS:
            value = row.get(field)
            if not present(value):
                continue
            try:
                if not isinstance(value, str):
                    raise ValueError('date must be a string')
                parsed = date.fromisoformat(value)
                if parsed.isoformat() != value:
                    raise ValueError('calendar ISO YYYY-MM-DD required')
                dates[field] = parsed
            except (ValueError, TypeError):
                add('INVALID_DATE', 'Supplied date is not an exact ISO date; preserve original value for review.', [field], shape_error=True)
        if not present(row.get('completion_date')):
            add('MISSING_COMPLETION_DATE', 'A missing origin date is not time zero.', ['completion_date'], shape_error=True)
        if not present(row.get('censor_date')):
            add('MISSING_OBSERVATION_DATE', 'No supplied endpoint date; do not fabricate it from another event.', ['censor_date'], shape_error=True)
        origin = dates.get('completion_date')
        if origin:
            for field, value in dates.items():
                if field != 'completion_date' and value < origin:
                    add('DATE_BEFORE_ORIGIN', 'A pre-origin fact requires preserved history and origin/entry review; do not reset it away.', ['completion_date', field])
        numeric = None
        if present(row.get('followup_months')):
            try:
                raw = row['followup_months']
                if isinstance(raw, bool):
                    raise ValueError('boolean follow-up')
                numeric = float(raw)
                if not math.isfinite(numeric) or numeric < 0:
                    raise ValueError('nonfinite or negative follow-up')
            except (ValueError, TypeError, OverflowError):
                numeric = None
                add('INVALID_FOLLOWUP', 'Supplied follow-up is not finite nonnegative numeric data.', ['followup_months'], shape_error=True)
        if numeric is not None and origin and dates.get('censor_date'):
            date_months = (dates['censor_date'] - origin).days / DAYS_PER_MONTH
            if abs(numeric - date_months) > FOLLOWUP_COMPARISON_TOLERANCE_MONTHS:
                add('FOLLOWUP_DATE_NUMERIC_MISMATCH', 'Supplied numeric and date-derived follow-up differ; neither is silently selected.', ['completion_date', 'censor_date', 'followup_months'])
        start, end = dates.get('terminal_event_interval_start'), dates.get('terminal_event_interval_end')
        if start and end and start > end:
            add('REVERSED_TERMINAL_INTERVAL', 'Supplied terminal interval is reversed.', ['terminal_event_interval_start', 'terminal_event_interval_end'], shape_error=True)
        status = str(row.get('terminal_event_date_status', '')).upper()
        if ((start or end) and (not start or not end or start != end)) or 'INTERVAL' in status or 'YEAR_ONLY' in status:
            add('TERMINAL_INTERVAL_NOT_EXACT', 'Interval endpoints and midpoint remain source/scenario facts; no exact transition is generated.', ['terminal_event_interval_start', 'terminal_event_interval_end', 'terminal_event_midpoint_for_primary', 'terminal_event_date_status'])
        success = dates.get('success_date')
        terminal_dates = [dates.get(field) for field in ('closure_date', 'terminal_event_midpoint_for_primary', 'terminal_event_interval_start', 'terminal_event_interval_end')]
        if success and success in terminal_dates:
            add('TIED_SUCCESS_TERMINAL_REQUIRES_TYPED_REVIEW', 'Date equality cannot choose competing versus qualifying terminal success or within-day order.', ['success_date', 'closure_date', 'terminal_event_midpoint_for_primary'])
        if 'ACQUISITION' in str(row.get('terminal_event_type', '')).upper() and ('UNKNOWN' in str(row.get('terminal_event_type', '')).upper() or str(row.get('terminal_event_success_value', '')).upper() == 'UNKNOWN'):
            add('UNKNOWN_VALUE_ACQUISITION_NOT_AUTOMATIC_SUCCESS_OR_CLOSURE', 'Retain the unknown-value terminal label. Review a typed competing endpoint; do not infer success, closure or a complete state history.', ['terminal_event_type', 'terminal_event_success_value'])
        terminal_type = str(row.get('terminal_event_type', '')).upper()
        terminal_present = any(present(row.get(field)) for field in ('terminal_event_type', 'terminal_event_interval_start', 'terminal_event_interval_end', 'terminal_event_midpoint_for_primary'))
        if terminal_present and terminal_type not in {'ACQUISITION_VALUE_UNKNOWN', 'TERMINAL_SUCCESS_EXIT', 'CLOSURE'}:
            add('UNRECOGNIZED_TERMINAL_TYPE_REQUIRES_REVIEW', 'Do not convert an absent or unrecognized terminal label to success, closure or a generic transition.', ['terminal_event_type'])
        if success and dates.get('last_positive_date') and success > dates['last_positive_date']:
            add('FINANCING_BEYOND_AFFIRMATIVE_OPERATION', 'Success attribution alone cannot extend affirmative operation or establish POST.', ['success_date', 'last_positive_date'])
        if dates.get('censor_date'):
            for field in ('success_date', 'closure_date', 'terminal_event_midpoint_for_primary'):
                if dates.get(field) and dates[field] > dates['censor_date']:
                    add('EVENT_BEYOND_SUPPLIED_CENSOR', 'Endpoint-specific observation review required; neither cap nor automatic extension is chosen.', [field, 'censor_date'])
        if present(row.get('success_date')):
            add('SUCCESS_EVENT_LABEL_REQUIRES_INDEX_EVIDENCE_REVIEW', 'Existing success/source labels are available for targeted review, not fresh proof of the index-specific predicate or initial state.', ['success_date', 'success_type', 'success_valuation_multiple', 'success_evidence_url', 'success_evidence_sha256'])
        if company_counts.get(str(row.get('canonical_company_id', '')), 0) > 1:
            add('MULTI_ROUND_COMPANY_REQUIRES_INDEX_SPECIFIC_ENTRY_REVIEW', 'Preserve all rounds and clustering; review each index origin/qualification without resetting prior company history.', ['canonical_company_id', 'round_id', 'completion_date'])
        if present(row.get('success_date')) and not all(present(row.get(field)) for field in ('success_type', 'success_evidence_url', 'success_evidence_sha256')):
            add('SUCCESS_SOURCE_BINDING_INCOMPLETE', 'Success date lacks one or more source/type bindings; no predicate is inferred.', ['success_type', 'success_evidence_url', 'success_evidence_sha256'])
        year = str(row.get('offering_year', ''))
        if row.get('offering_year_status') != 'BOUNDED_YEAR' or len(year) != 4 or not year.isdigit():
            add('OFFERING_YEAR_UNRESOLVED', 'Keep row in the disposition register without substituting completion year.', ['offering_year', 'offering_year_status'])
        elif year not in {str(y) for y in range(2020, 2026)}:
            add('OFFERING_YEAR_OUTSIDE_STUDY_SCOPE', 'A supplied bounded year is outside 2020-2025; retain the row and review scope rather than calling the year unknown.', ['offering_year', 'offering_year_status'])
        requirements = {}
        for key, requirement in REQUIREMENTS.items():
            requirements[key] = {
                'existing_field_presence': {field: {'in_schema': field in fields, 'populated': present(row.get(field))} for field in requirement['existing_fields']},
                'review_field_presence': {field: {'in_schema': field in fields, 'populated': present(row.get(field))} for field in requirement['review_fields']},
                'review_status': 'NOT_ADJUDICATED_BY_SCHEMA_AUDIT',
            }
            add(requirement['reason'], requirement['next_action'], requirement['review_fields'])
        records.append({
            'source_row_ordinal_1based': index + 1,
            'source_row_sha256': sha_bytes(canonical_bytes(row)),
            'round_id_as_supplied': row.get('round_id'),
            'company_id_as_supplied': row.get('canonical_company_id'),
            'mechanical_input_status': 'REQUIRES_INPUT_REPAIR' if mechanical else 'FLAT_SCHEMA_PARSEABLE_FOR_REVIEW',
            'prepared_history_status': 'NOT_CONSTRUCTED',
            'evidence_eligibility': 'NOT_DETERMINED',
            'requirements': requirements,
            'gaps': sorted(reasons, key=lambda x: (-x['priority'], x['code'], x['fields'])),
            'max_targeted_review_priority': max((reason['priority'] for reason in reasons), default=0),
        })
    counts = Counter(reason['code'] for item in records for reason in item['gaps'])
    affected_rows = Counter(code for item in records for code in {reason['code'] for reason in item['gaps']})
    summary = {
        'audit_version': VERSION, 'source_sha256': source_sha256,
        'input_rows': len(rows), 'output_dispositions': len(records),
        'eligible_row_count': None, 'ineligible_row_count': None,
        'eligibility_assessment': 'NOT_PERFORMED; missing review fields are not evidence of ineligibility',
        'prepared_histories_created': 0, 'states_or_event_times_synthesized': 0,
        'mechanical_status_counts': dict(sorted(Counter(r['mechanical_input_status'] for r in records).items())),
        'gap_occurrence_counts': dict(sorted(counts.items())),
        'gap_affected_row_counts': dict(sorted(affected_rows.items())),
        'requirements_schema_map': {key: {
            'existing_fields_present': [field for field in value['existing_fields'] if field in fields],
            'existing_fields_absent': [field for field in value['existing_fields'] if field not in fields],
            'review_fields_present': [field for field in value['review_fields'] if field in fields],
            'review_fields_absent': [field for field in value['review_fields'] if field not in fields],
            'next_action': value['next_action'],
        } for key, value in REQUIREMENTS.items()},
        'priority_interpretation': 'Review triage only; numbers do not measure statistical readiness, evidence quality, or investment merit.',
        'followup_comparison_tolerance_months': FOLLOWUP_COMPARISON_TOLERANCE_MONTHS,
    }
    queue = [{'source_row_ordinal_1based': item['source_row_ordinal_1based'],
              'round_id_as_supplied': item['round_id_as_supplied'],
              'max_targeted_review_priority': item['max_targeted_review_priority'],
              'targeted_gap_codes': sorted({r['code'] for r in item['gaps'] if r['code'] in PRIORITIES})}
             for item in records if any(r['code'] in PRIORITIES for r in item['gaps'])]
    queue.sort(key=lambda x: (-x['max_targeted_review_priority'], x['source_row_ordinal_1based']))
    return {'summary': summary, 'rows': records, 'targeted_review_queue': queue}


def _immutable_write(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f'immutable_output_conflict:{path.name}')
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    try:
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError(f'immutable_output_conflict:{path.name}')
    finally:
        temporary.unlink()


def write_audit(output_dir: Path, audit: dict, source_bindings: dict) -> dict:
    payloads = {
        'summary.json': canonical_bytes(audit['summary']),
        'row-dispositions.jsonl': b''.join(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8') + b'\n' for row in audit['rows']),
        'targeted-review-queue.json': canonical_bytes(audit['targeted_review_queue']),
    }
    manifest = {'audit_version': VERSION, 'source_bindings': source_bindings,
                'private_identifier_bearing_files': ['row-dispositions.jsonl', 'targeted-review-queue.json'],
                'canonical_outputs_modified': False, 'eligibility_adjudicated': False,
                'outputs': {name: sha_bytes(payload) for name, payload in payloads.items()}}
    payloads['manifest.json'] = canonical_bytes(manifest)
    for name, payload in payloads.items():
        path = output_dir/name
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f'immutable_output_conflict:{name}')
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        _immutable_write(output_dir/name, payload)
    return manifest


def audit_file(ledger: Path, expected_sha256: str, output_dir: Path) -> dict:
    before = ledger.read_bytes()
    if sha_bytes(before) != expected_sha256:
        raise ValueError('input_ledger_hash_mismatch')
    reader = csv.DictReader(io.StringIO(before.decode('utf-8'), newline=''))
    rows = list(reader)
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError('missing_or_duplicate_csv_columns')
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError('malformed_csv_row_width')
    audit = audit_rows(rows, source_sha256=expected_sha256, fieldnames=reader.fieldnames)
    if ledger.read_bytes() != before:
        raise ValueError('input_changed_during_audit')
    return write_audit(output_dir, audit, {
        'ledger_filename': ledger.name, 'ledger_sha256': expected_sha256,
        'audit_code_sha256': sha_bytes(Path(__file__).read_bytes()),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--expected-ledger-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_file(args.ledger, args.expected_ledger_sha256, args.output_dir), sort_keys=True))


if __name__ == '__main__':
    main()
