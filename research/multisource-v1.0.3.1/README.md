# Vera multi-source evidence system

An additive research policy, typed evidence ledger, fail-closed validator, claim adjudicator and dedicated source-coverage audit. Python 3.10+, standard library only. No network calls or external mutations.

Run from this directory:

    python -m unittest discover -s tests -v
    python evidence.py demo.json --as-of 2026-10-10 --output reports

Optional --reviewer-registry accepts an operator-controlled JSON mapping authenticated reviewer IDs to roles (claim_verifier/source_verifier). No registry is shipped with invented approvals. The validator cannot authenticate arbitrary names or receipts. Tests use explicitly synthetic reviewers; those are not real evidence approvals.

## Real-case demonstration
The demo imports three actual earlier records, preserving source URLs and original hashes. Currently Wine reports Q1 2026 activity; Reental reports November 2025 activity; Inlightened's buyer reports a completed acquisition by August 14, 2023. Original native records were already reviewed under their own scope. New augmented claim/entity/predicate and source-coverage reviews are pending and never copied automatically. Unknown original retrieval times remain null. Imported public text has a separate capture hash; original_sha256 records the archived HTML or tool-text receipt as explicitly described in capture_scope. It does not pretend a tool receipt hash is publisher HTML.

Three held observations, no state transition, no censor-date imputation, no rate or numerical-prior promotion. The narrow positive path is executable: independent semantic review can accept a one-buyer source statement despite unknown consideration, and sufficient research plus authorized reviewer roles can release a research finding. It still cannot change native outcomes or calibrate priors.

## Files and reproducibility
- POLICY.md: prospective v1.1.0 amendment, semantics and limits.
- evidence.schema.json: typed exchange contract; evidence.py implements semantic/hash checks.
- evidence.py: public report()/CLI validates first; internal adjudicate() must not be used as approval.
- source_verifier.py: independent structural coverage review, not claim truth.
- RESEARCHER.md, VERIFIER.md, SOURCE_VERIFIER.md: role handoffs.
- rollout-registry.json: required role/version/hash acknowledgements, all pending until actually received.
- demo.json and sources/: public evidence example with new review pending.
- native-pins.json: hashes of unmodified canonical research v0.5.0, frozen spec and prior outcome register.
- tests/: positive/negative semantic, integrity, reviewer-authority, source-coverage, identity/date and reproducibility tests. Synthetic tests are never cohort rows.
- fixtures/critic-cases.json: independently proposed cases with explicit fixture status. CASE_COVERAGE.md maps executable tests and deferred scenarios honestly.

Reports are deterministic and named by their own SHA256; no report is overwritten. Re-running the same input/as-of produces identical bytes. Changed inputs create new reports. Rollback means selecting a prior input/report hash. The full-body importer is intentionally excluded. The bundled demo/CLI/tests are portable; the native-pin test reports a skip if original sibling archives are unavailable. No full native ledger or private tool receipt is included in this publication candidate.

## Source-plan schema
research_plan contains policy, declared_at, retrospective_import, search_cutoff, entities, routes, stopping_rationale and stop_kind. Each entity declares company_id, aliases and identity_basis. Each route names claim_ids, company_ids, claim_types, purpose (primary/contradiction/alternative), source_family (native_platform/direct_party/legal_regulatory/independent_reporting), status, query, searched_at, result/result_class, receipt, aliases_searched, time_scope, source_ids, material status and any reason/adequate_alternative_route_ids. Date-restricted and grouped searches require explicit rationale/per-entity review. Relevant families are assessed, not universally forced to yield a document; not-applicable routes require reviewer-approved exceptions. At least one meaningful outside source search and completed primary/contradiction routes are required.

source_review binds plan_sha256 and coverage_sha256, reviewer/researcher, reviewed_at, verdict, rationale, origin_families_checked, depth_checked, claim_ids and approved_exception_route_ids. Search receipts must remain independently inspectable; a metadata string is not authenticated source content. Unknown original receipt time is visible. The policy calls for JEV support on substantive decisions when allocated, never as a substitute for evidence.

## Publication and limits
The package is an implementation candidate until final independent review. No external publication performed. Original text, corporate identity, source authenticity and semantic entailment require real review. No automated NLP, estimator, exhaustive-search certificate or calibration accuracy is claimed. Historical rows remain unknown where evidence or review is incomplete. Dedicated source verification is mandatory before a released augmented finding.

## Public derivative
This is a separate publication-minimized derivative of the local research candidate. Each source has only a short necessary attributed excerpt, with original URL/hash and full-body archive reference preserved. Full source bodies and private receipts are not bundled. The public package alone cannot reproduce original full-body semantic inspection; re-retrieve or use the separately held original archive for independent review. All real-case approvals remain pending. lineage.json pins the unchanged parent dataset/manifest and derivative hashes. Quoted source text is limited to at most25words per source across source capture and example record; the full-body importer and legacy reports are excluded.

## Normalized public derivative v1
The Inlightened excerpt renders tool citation markup as the original visible link label. This is presentation-only normalization, not a new fetch or certification of clean publisher HTML. lineage.json and the source record bind original archive, parent excerpt, normalized excerpt and dataset hashes. The previous public candidate remains frozen. No review transferred.

## Implementation 1.0.2 and policy 1.1.0
See IMPLEMENTATION_CHANGE.md and SCOPED_SCHEMA.md. The full ledger remains intact; selected claims use independently reviewed contextual closure and material route coverage. Receipt-bound execution windows establish only conservative chronology. Relevant-section inspection requires exact original-document hashes, locators, context and limitations. Historical plan reassessment is explicitly retrospective and never asserts that policy 1.1.0 was preregistered before earlier searches.

The separate private real pilot contains full original proof files and remains outside this public package. Its actual approvals must be supplied by the independent source verifier and semantic reviewer. The bundled public demo remains pending.

## Implementation 1.0.3 precision-withdrawal candidate
See [PRECISION_WITHDRAWAL.md](PRECISION_WITHDRAWAL.md). This local successor adds a narrow independently reviewed metadata-withdrawal contract. No event, identity, predicate or assertion change is allowed. Local independent tests/review passed against exact successor code; final external implementation review remains pending specific permission. Earlier 1.0.2 receipts do not certify changed code.

## Implementation1.0.3.1reporting patch
[OUTPUT_PROVENANCE.md](OUTPUT_PROVENANCE.md) documents the shared report-version invariant. This successor corrects a stale scoped report label; all scientific rules and inputs remain unchanged. Both report paths use the actual shared engine constant.
