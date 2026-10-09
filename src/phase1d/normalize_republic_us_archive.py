"""Normalize preserved native evidence; never infer cohort membership or outcomes."""
from __future__ import annotations
import argparse, calendar, hashlib, json, re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from src.phase1d.recover_republic_us import canonical_candidate, public_api_url

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'data/phase1d/cp1_republic_us_probe.json'
EXPECTED_GIT_BLOB = '4257d36bb7259b8a9f923a4b050c8d05936eaed5'
MONTHS = {s: i for i, s in enumerate(calendar.month_abbr) if i}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def month_bounds(raw: object) -> tuple[str | None, str | None]:
    if not isinstance(raw, str): return None, None
    m = re.fullmatch(r'([A-Z][a-z]{2}) (\d{4})', raw.strip())
    if not m or m[1] not in MONTHS or not 1900 <= int(m[2]) <= 2100: return None, None
    year, month = int(m[2]), MONTHS[m[1]]
    return f'{year:04d}-{month:02d}-01', f'{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}'


def cents(raw: object) -> int | None:
    if raw is None: return None
    if type(raw) is not int or raw < 0: raise ValueError('non-negative integer cents required')
    return raw


def normalize_row(raw: object, index: int, response_index: int, source_hash: str, captured_at: str, url: str) -> dict:
    if not isinstance(raw, dict): raise ValueError('row is not an object')
    slug = raw.get('slug')
    if not isinstance(slug, str) or not re.fullmatch(r'[A-Za-z0-9._-]+', slug): raise ValueError('invalid slug')
    campaign = canonical_candidate('https://republic.com/' + slug)
    if not campaign: raise ValueError('not a campaign URL candidate')
    if not isinstance(raw.get('name'), str) or not raw['name'].strip(): raise ValueError('missing name')
    lo, hi = month_bounds(raw.get('deadline'))
    row_hash = digest(encoded(raw))
    key = f'{source_hash}:{response_index}:{index}:{row_hash}'
    return {'candidate_id': digest(key.encode()), 'record_kind': 'native_api_candidate_not_validated_round',
        'platform': 'republic_us', 'source_file': SOURCE, 'source_sha256': source_hash,
        'source_captured_at': captured_at, 'source_url': url, 'source_response_index': response_index,
        'source_row_index': index, 'raw_row_sha256': row_hash, 'raw_row': raw,
        'native_slug': slug, 'candidate_url': campaign, 'display_name': raw['name'],
        'canonical_company_id': None, 'verified_round_id': None,
        'identity_status': 'STRONG_IDENTIFIERS_NOT_RECOVERED',
        'instrument_raw': raw.get('instrument'), 'raised_cents': cents(raw.get('raised_cents')),
        'valuation_cap_cents': cents(raw.get('valuation_cap_cents')), 'priced_valuation_cents': None,
        'republic_commission_cents': cents(raw.get('republic_commission_cents')),
        'currency': None, 'discount_raw': raw.get('discount'), 'deadline_raw': raw.get('deadline'),
        'deadline_lower_bound': lo, 'deadline_upper_bound': hi,
        'date_status': 'DEADLINE_MONTH_BOUNDS_ONLY' if lo else 'DEADLINE_UNRESOLVED',
        'first_live_date': None, 'successful_close_date': None, 'offering_year': None,
        'funding_completion_verified': False, 'outcome_state': 'UNKNOWN',
        'estimation_eligible': False, 'duplicate_source_row': False, 'slug_conflict': False}


def normalize(document: dict, source_hash: str) -> tuple[list, list, dict]:
    candidates, rejected, total = [], [], 0
    for ri, response in enumerate(document.get('responses', [])):
        if not public_api_url(response.get('url', '')) or response.get('status') != 200: continue
        body = response.get('body')
        if not isinstance(body, list): raise ValueError('public API body is not a row array')
        for i, raw in enumerate(body):
            total += 1
            try: candidates.append(normalize_row(raw, i, ri, source_hash, document.get('captured_at', ''), response['url']))
            except (ValueError, TypeError) as exc:
                rejected.append({'response_index': ri, 'row_index': i, 'raw_row': raw, 'reason': str(exc)})
    by_slug, hashes = defaultdict(set), Counter(c['raw_row_sha256'] for c in candidates)
    for c in candidates: by_slug[c['native_slug']].add(c['raw_row_sha256'])
    for c in candidates:
        c['duplicate_source_row'] = hashes[c['raw_row_sha256']] > 1
        c['slug_conflict'] = len(by_slug[c['native_slug']]) > 1
    checks = {
        'nonempty_source': total > 0, 'nonempty_candidates': len(candidates) > 0,
        'cardinality_reconciles': total == len(candidates) + len(rejected),
        'all_source_rows_valid': not rejected,
        'candidate_ids_unique': len(candidates) == len({c['candidate_id'] for c in candidates}),
        'raw_hashes_verified': all(digest(encoded(c['raw_row'])) == c['raw_row_sha256'] for c in candidates),
        'source_hashes_bound': all(c['source_sha256'] == source_hash for c in candidates),
        'canonical_campaign_urls': all(canonical_candidate(c['candidate_url']) == c['candidate_url'] for c in candidates),
        'no_name_only_identity_merge': all(c['canonical_company_id'] is None for c in candidates),
        'no_deadline_as_first_live': all(c['first_live_date'] is None and c['offering_year'] is None for c in candidates),
        'no_deadline_as_time_zero': all(c['successful_close_date'] is None for c in candidates),
        'caps_not_priced_valuations': all(c['priced_valuation_cents'] is None for c in candidates),
        'no_outcome_inference': all(c['outcome_state'] == 'UNKNOWN' and not c['funding_completion_verified'] for c in candidates),
        'no_estimation_eligibility': all(c['estimation_eligible'] is False for c in candidates),
        'capture_timestamp_present': all(bool(c['source_captured_at']) for c in candidates)}
    summary = {'source_rows': total, 'candidate_rows': len(candidates), 'rejected_rows': len(rejected),
        'unique_native_slugs': len(by_slug), 'duplicate_source_rows': sum(c['duplicate_source_row'] for c in candidates),
        'conflicting_slugs': sum(len(v) > 1 for v in by_slug.values()),
        'deadline_year_histogram_NOT_cohort_year': dict(sorted(Counter(c['deadline_lower_bound'][:4] if c['deadline_lower_bound'] else 'UNKNOWN' for c in candidates).items())),
        'instrument_histogram': dict(Counter(str(c['instrument_raw']) for c in candidates)),
        'cohort_year_resolved': 0, 'strong_company_ids': 0, 'estimation_eligible': 0,
        'census_status': 'CENSUS_INCOMPLETE', 'rates_promoted': False,
        'new_live_evidence': False, 'source_mode': 'PRESERVED_ARCHIVE_REPROCESSING',
        'gates': {'passed': sum(checks.values()), 'total': len(checks), 'checks': checks},
        'limitations': ['Old public-note portfolio subset is not a 2020-2025 platform denominator.',
            'Deadline bounds are not first-live or successful-close dates.',
            'A native slug is not a strong legal-entity identifier or a validated unique round.',
            'Raw cents retained; currency not independently verified.',
            'No new live collection; prior four-directory recovery returned HTTP 403.']}
    return candidates, rejected, summary


def research_state(summary: dict) -> str:
    if summary.get('capture_count', 0) == 0: return 'ACCESS_BLOCKED' if summary.get('errors') else 'NO_EVIDENCE'
    return 'PARTIAL_NATIVE_EVIDENCE_NOT_CENSUS'


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run-id', required=True); args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.run_id): raise ValueError('invalid run id')
    source = (ROOT / SOURCE).read_bytes()
    git_blob = hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()
    if git_blob != EXPECTED_GIT_BLOB: raise ValueError('archived source changed; refresh approved lineage first')
    candidates, rejected, summary = normalize(json.loads(source), digest(source))
    previous = ROOT / 'data/phase1d/republic_us_recovery/gh-37894313863/summary.json'
    if previous.exists():
        prior = json.loads(previous.read_text())
        summary['live_recovery_status'] = research_state(prior)
        summary['prior_recovery_summary_sha256'] = digest(previous.read_bytes())
    out = ROOT / 'data/phase1d/republic_us_archive' / args.run_id
    if out.exists(): raise ValueError('immutable run directory already exists')
    out.mkdir(parents=True)
    payloads = {'candidates.json': candidates, 'quarantine.json': rejected,
        'resolution_queue.json': [{'candidate_id': c['candidate_id'], 'url': c['candidate_url'],
            'required': ['historical_census_reconciliation', 'strong_legal_entity_id', 'first_live_date',
                'successful_funding_completion_and_date', 'instrument_currency_and_terms', 'dated_outcome_evidence']}
            for c in candidates], 'summary.json': summary}
    for name, value in payloads.items(): (out / name).write_bytes(encoded(value))
    (out / 'manifest.json').write_bytes(encoded({'run_id': args.run_id, 'created_at': datetime.now(timezone.utc).isoformat(),
        'source_file': SOURCE, 'source_git_blob': git_blob, 'source_sha256': digest(source),
        'script_sha256': digest(Path(__file__).read_bytes()),
        'files': {name: digest((out / name).read_bytes()) for name in payloads}}))
    print(json.dumps(summary, sort_keys=True))
    if summary['gates']['passed'] != summary['gates']['total']: raise SystemExit(2)
if __name__ == '__main__': main()
