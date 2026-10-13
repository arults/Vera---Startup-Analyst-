# Preparation/disposition audit v0.1.0

A read-only bridge inventory for the Phase 1D flat outcome ledger. It identifies what must be reviewed before constructing exact histories for the first-success component. It is not a source adapter, eligibility classifier, estimator, source-collection authorization, or canonical-reporting change.

## Contract

Every source row receives one disposition with its original ordinal, supplied round/company IDs, normalized-row hash, field-presence map and explicit gaps. No deduplication, cohort dropping, new identity, state assignment, date selection, transition generation, event reclassification or follow-up extension occurs.

The report separates:

- Mechanical status: whether the supplied flat fields parse for review, or require input repair.
- Requirement presence: whether relevant fields exist in the schema and are populated on this row.
- Evidence eligibility: always `NOT_DETERMINED`; aggregate eligible and ineligible counts are null.
- Prepared history: always `NOT_CONSTRUCTED`.

Populated review-looking columns are not self-authenticating. This schema audit does not approve them. The six universal review requirements remain `NOT_ADJUDICATED_BY_SCHEMA_AUDIT` even when a row is structurally clean. They do not mean every row is ineligible, false, or in need of new source collection.

## Explicit non-inference boundaries

- Never infer initial PRE from blank success fields or initial POST from financing labels.
- Never infer funded/completed positions, round identity or an origin convention from an ID/date alone.
- Never resolve tied success/terminal dates by precedence or turn them automatically into terminal success.
- Never replace interval dates by midpoints, starts, ends, or fabricated exact times.
- Never map unknown-value acquisition to automatic success or closure, or unknown terminal labels to a generic transition.
- Never let a later financing extend affirmative operation or overwrite a supplied observation endpoint.
- Never reset prior company history for a later round or treat prior success as automatically qualified against the new index.
- Never infer offering year from completion year or silently discard out-of-scope/unresolved rows.

Malformed dates, duplicate/missing IDs, invalid follow-up and contradictory temporal fields are inventoried. Exact calendar dates require YYYY-MM-DD. Numeric-versus-date follow-up is compared using the current caller's 30.4375 days/month and a disclosed 0.000001-month representation tolerance. This tolerance is only a discrepancy inventory rule; passing it does not validate timing or source evidence. Known bounded years outside 2020–2025 have a separate scope-review code rather than being called unknown.

## Prioritizing source review

The targeted queue highlights concrete existing facts requiring adjudication: interval or unknown-value terminals; tied events; source/date contradictions; missing source bindings; existing success labels requiring index-specific checks; unresolved offering year; and multi-round company entry context. Priority integers determine a reproducible triage order only. They are not evidence-quality scores, inference gates, urgency judgments or investment recommendations.

First inspect already-linked sources for the flagged fact. Collect new source evidence only when the existing material cannot resolve it. Reuse verified source facts without treating their labels as proof of every entry/state predicate. Handle universal origin, initial-state, target and observation requirements through a bounded review protocol; do not start 952 undifferentiated source searches.

## Running

Standard library only, Python 3.10 or newer.

    python -m unittest discover -s research/preparation-audit-v0.1.0 -v

Audit an authorized frozen input into a separate versioned directory:

    python research/preparation-audit-v0.1.0/preparation_audit.py \
      --ledger /path/to/authorized-ledger.csv \
      --expected-ledger-sha256 EXACT_SHA256 \
      --output-dir /path/to/separate/versioned-audit

The CLI verifies the exact raw input hash, validates CSV width/schema, checks the source bytes again after audit, and writes only the selected output directory. Use a new output directory when inputs or implementation change. The tool never defaults to a canonical data directory.

## Evidence outputs and privacy

- `summary.json`: all-row counts, occurrence versus affected-row gap counts, schema requirement map and non-adjudication caveats.
- `row-dispositions.jsonl`: one record per source row, including supplied entity identifiers. Private under the source ledger's permissions.
- `targeted-review-queue.json`: row references and reasons for targeted review. Also private under source permissions.
- `manifest.json`: exact ledger and audit-code hashes, output hashes, privacy flags and scope.

All payloads are serialized and conflicts checked before publication. Each new file publishes atomically without replacing existing data. Identical reruns are byte/mtime no-ops. Different existing outputs cause a conflict instead of being overwritten. An interruption between file publications may leave a partial directory; the manifest publishes last and is the completeness marker. Rerunning identical inputs completes missing files without overwriting existing matching ones.

The approved repository package includes code, synthetic tests, this documentation and the compact aggregate/hash/ordinal-only reference packet described below. Do not commit actual ledgers, identifier-bearing audit output or private source evidence. This task did not submit actual private input to JEV.

## Verification scope

The supplied implementation suite has 18 tests. Every declared targeted reason and all six universal requirements have executable synthetic coverage. Tests cover positive flat-schema parsing without fabricated eligibility, missing-versus-empty fields, claimed approvals remaining unadjudicated, hold reasons, all-row accounting, deterministic output, input preservation, strict CSV parsing, exact hashes, immutable write/no-op behavior and conflicts.

The actual archived v5 run was separately hash-bound and privately checked. Every input received a disposition. Numerical modules and canonical caller outputs were not edited or invoked to produce new estimates. Independent review is separate from this implementation's tests.

## Compact reference-run inventory

The `reference-run` directory contains only the aggregate summary, hash bindings and a compact ordinal-only targeted queue for the frozen v5 input. The queue includes 398 distinct source-row ordinals; categories overlap: 70 success-label reviews, 287 rows across 124 repeated companies, 156 unresolved offering years, and two interval/unknown-value terminal rows. Ordinals resolve only against the exact source SHA-256 in the packet. They are pseudonymous source-linked references, not anonymous data; keep the packet within the existing source/repository permissions, with no implied unrestricted redistribution. The compact queue roundtrips exactly to the corresponding fields in the complete local queue; raw round/company identifiers and the full 952-row dispositions are omitted.

All 952 flat rows parse for review. Both eligible and ineligible counts remain undetermined. The 554 rows outside the targeted queue still have the same six unadjudicated preparation requirements; their absence from the queue is not approval. Full row dispositions can be reproduced by running the pinned audit code against the pinned existing ledger. The binding file records the hashes of the complete local outputs without embedding them. No full bootstrap sidecars are included.


## Durable independent checks and scoped CI

`test_independent_preparation.py` is the reviewer's unchanged nine-test file. The portable suite is 27 tests: 18 implementation plus nine independent checks. `verify_reference_run.py` checks the exact audit-code and existing v5 ledger hashes, reproduces the complete audit only in an output directory outside the repository, compares every full output hash and the summary, roundtrips the compact ordinal queue, and confirms input preservation and byte/mtime no-op behavior. It prints no entity identifiers.

The accompanying workflow is scoped to the phase-1d push paths for this package, its pinned source ledger and the workflow itself. It has read-only contents permission, checks HEAD equals GITHUB_SHA, runs the 27 tests and the reproduction verifier, and does not upload private artifacts. Remote CI success must be verified against the actual published commit; local verification alone is not a remote-CI claim.
