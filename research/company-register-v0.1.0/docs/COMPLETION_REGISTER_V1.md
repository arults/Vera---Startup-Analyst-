# Additive completion register v1

This is a source inventory and research-gate visibility layer. It does not replace
any existing dataset, report, cohort membership, outcome, estimator, or rate.
The seven input tables contain 2,865 rows at commit
`717e7be8f6ee672815f69ef8d8885ff9a555055d`. Other repository populations have not
been migrated. The unavailable 985-profile raw archive is not synthesized.

## Study contract and completion semantics

The pinned `docs/PHASE_1C_SPEC.md` defines the primary unit as an **economic
company-round**, with separate accessible-deal and funded/completed layers.
Its identity, first-live offering-year, funded time-zero, field, typed outcome,
platform-observed follow-up, cross-round graph, and identity-QA requirements inform
the component matrix. They are not replaced by CSV field presence. The spec has no
universal company-level “research complete” predicate. This version deliberately
cannot certify full completion: `completion_status=unclassified`, and aggregate
`verified_complete` / `partial` counts are **null**, not zero.

Each assessment is scoped to a record, source frame, and versioned requirements.
`not_assessed` means that the gate has not been adjudicated by this importer.
`source_asserted_unadjudicated` means source metadata exists, not that a research
gate passed. `supported_strong_identifier` is limited to the issuer CIK on the
frozen US SEC-derived Wefunder manifest. Prior verified or candidate source claims
remain preserved with their source row and status; missing current gate evaluation
neither erases nor contradicts them. This module never consumes external completion
certificates, changes requirements, promotes a prior, or asserts research plateau.

The stricter importer uses only a strong identifier **and explicit jurisdiction**
for legal company identity. It does not implement the spec's medium-ID route,
which needs independent identifiers and second-review evidence not imported here.
European numeric source keys are preserved without guessing legal jurisdiction.

## Tables and schema

All strings are UTF-8. Source-table row numbers are 1-based logical data records
(header excluded); JSON row numbers are 1-based array positions. CSV quoted
newlines do not change logical row numbering. Unknown fields in original source
rows remain accessible through the exact frozen path, commit, and row locator.

- `records`: stable `record_id`, explicit `record_type`, original source key,
  identity namespace in `platform`, explicit/unknown `jurisdiction`,
  `identity_status`, labels, supporting lineage IDs, source scopes, and derived
  `platform_memberships`. Types are company, company_key, offering, round, profile,
  profile_event, and discovery_url. A source round is not automatically a verified
  economic round. SEC is an identity namespace, not a sixth crowdfunding platform;
  Wefunder association is derived from issuer links.
- `lineage`: one row per loaded original row, including exact duplicates and invalid
  rows. It records source commit/path/SHA-256, original logical-row SHA-256,
  record links, and a disposition of linked, unresolved, duplicate, or quarantined.
  An unresolved row can have supported source-level links while lacking legal or
  research resolution. Invalid rows receive a reason; they are never silently lost.
- `crosswalk`: directional source-record/target-record association, relation,
  evidence basis, lineage, and source-asserted/strong-identifier status. No fuzzy
  name matches, domain-only matches, cross-platform round merges, or guessed issuer
  links are performed. US linked CIKs pending issuer/coissuer validation stay pending.
- `evidence`: immutable source-observation pointers, original source status,
  estimation-eligibility assertion where present, and typed outcome assertions.
  A pointer is not a claim that this release has fetched or reverified every URL.
  The original complete row is bound through lineage and preserved source bytes.
- `assessments`: record + source-scope + requirements-version, component gate map,
  unresolved reasons, original unit, and explicit no-promotion / unclassified status.
- `conflicts`: incompatible source assertions on the same source record, with all
  competing values. Both lineages are quarantined; neither latest-row wins nor a
  numerical outcome is substituted. Labels are retained as aliases, not merged
  identities. Conflicts detected in this release are a diagnostic queue, not an
  exhaustive identity audit.
- `progress`: counts by originating platform and **unit**, scoped to loaded inputs.
  Units are never added into a supposed unique-company total. Null completion counts
  carry `completion_counts_established=false`.
- `source_coverage`: descriptive, recomputed source counts, including 796 European
  year-resolved rows / 676 keys, six name fallbacks, and original outcome categories.
- `manifest`: exact input contract, requirements provenance, reconciliation,
  dispositions, limitations, and explicit `full_population_migrated=false`.

## Identity, lineage and idempotence

Record IDs hash the record type, namespace, jurisdiction, and stable source key.
Lineage IDs also bind source commit, path, logical row number, and canonical row
hash. Record IDs survive repeated imports; lineage intentionally changes if source
bytes or row ordering change. Exact repeated imports in one register are no-ops;
exact duplicate *rows in a source* retain distinct lineage and duplicate disposition.
No inference of legal equivalence follows from reused names or numeric keys in
different jurisdictions. Conflicting identity states are queued, not silently chosen.

This release pins all seven source paths, expected row counts, SHA-256 hashes,
Git blob hashes, source commit, and the requirements source blob. Missing, altered,
substituted, duplicate, extra, or partially supplied source contracts fail closed.
Adding a new source is a new versioned release, not a silent change to this one.
Original files are opened read-only. Output cannot contain an input path, and
changed existing artifacts are never overwritten. Identical output writes are
no-ops, including their modification time. No dates depend on wall clock time.

## Compact portable storage

Large logical tables use deterministic gzip, base64-encoded into UTF-8
`*.jsonl.gz.b64` files, so Git publication requires no special binary transport.
No observation is omitted to achieve compression. A hash manifest covers stored
bytes. `inspect_register.py` verifies the hash and decodes with the Python standard
library. `verify_release.py` checks original hashes, regenerates every logical
table, compares it with the committed tables, and tests no-op repeat writes.
It reports exact compressed-byte agreement separately because zlib implementations
may encode identical content differently. Logical-table equality is mandatory.

## Acceptance and remaining gates

The implementation is acceptable only when unit tests and independent source-bound
regeneration pass. This is infrastructure acceptance, not study acceptance.
Completion remains open pending legal jurisdiction/issuer reconciliation, original
population design and eligibility adjudication, economic-round and co-host review,
platform-hosted outcome/follow-up review, identity QA, and the existing scientific
report/uncertainty gates. No company-level completion standard is invented here.
