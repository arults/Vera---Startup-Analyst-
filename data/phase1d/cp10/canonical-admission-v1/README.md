# Canonical research admission adapter

This package admits exactly two previously reviewed observed Republic rounds to a **versioned local research ledger**. It does not perform generic source adjudication, admit other candidates, change production priors, compute rates, or establish Phase 1D completion.

The admitted research rows are Phantom Phood's Series 2023 Crowd SAFE and Stock Card's Series 2022 Crowd SAFE. Their exact native campaign, legal issuer, instrument, launch, successful aggregate completion and source-field claims have an independent semantic review and a factual JEV decision. The adapter requires those specific decisions and source hashes; JEV alone is never sufficient.

## Inputs and portability

Install this package at `data/phase1d/cp10/canonical-admission-v1/`. The root test-discovery shim belongs at `tests/test_phase1d_canonical_admission.py`.

Small review/decision/matrix inputs are bundled under `inputs/`. Original campaign HTML, timeline JSON and PDFs are loaded from the existing repository-relative capture paths in `inputs/frozen-input-manifest.json`; gzip captures are decoded and checked against the reviewed raw SHA-256. Original captures are never modified or duplicated into this package.

The original accepted matrix and decisions contained executor-local provenance paths. Portable derivatives change only those path strings. Their original hashes remain explicit lineage. `inputs/portable-normalization-report.json` records every changed JSON pointer and old-string digest. A separate independent normalization attestation binds the new portable bytes and checks semantic equivalence; the old review is not claimed to certify different bytes automatically.

There are no runtime workspace-absolute paths or third-party Python dependencies. The small schema checker supports exactly the keywords used in the pinned Phase 1C schema and fails closed on new keywords. It is not a general JSON Schema implementation.

## Run

From the repository root:

```sh
python data/phase1d/cp10/canonical-admission-v1/scripts/admission_adapter.py --source-root .
python -m unittest discover -s tests
```

Focused tests:

```sh
python -m unittest discover -s data/phase1d/cp10/canonical-admission-v1/tests -v
```

The adapter also discovers a repository ancestor containing `data/phase1d`. An explicit `--source-root` is preferred in CI. For independent local verification without a checkout, `--source-map` accepts an external mapping from repository paths to existing relative local artifacts; those raw bytes must still match the frozen hashes. Such convenience maps are not part of the published package or authorization.

## Stage and scope preservation

- Source integrity, reviewed company identity, observed economic-round binding, native launch/completion, aggregate funded status and field classification pass before local canonical research admission.
- Unknown outcomes, incomplete historical coverage and suppressed estimation remain separate later-stage fields. They do not erase accepted identity or financing facts.
- The canonical `valuation_cap` and `comparable_valuation` fields are both null. Original offered SAFE caps live under `offered_valuation_cap`, with source hash, PDF page, exact anchor and nonoperative scope. Existing `RoundRecord` consumers therefore cannot accidentally receive offered caps as final operative terms.
- Phantom's three amount displays remain distinct: hero USD 39,645; footer USD 39,646; native milestone USD 39,645.69. No display-rounding mechanism or audited net-cash amount is inferred.
- Phantom's possible concurrent outside offering remains a conditional uncertainty. It is not manufactured as an actual round or merged with the observed financing.
- Empty cohost/amendment bridges mean no positive relation established in this bounded review. They are not proof of global absence, and do not create `SameRoundEvidence` for graph code.
- Original source fields and exact quote/page anchors remain attached. The adapter authenticates upstream semantic review rather than claiming a fresh legal/financial audit.

## Immutable outputs

The current portable release is `releases/v0.3.0/canonical-research-ledger.json`. It contains canonical companies and rounds, a stage ledger and explicit unresolved ledger. Publication uses atomic creation and never overwrites an existing different release. Identical replay is a no-op; nonidentical output conflicts fail closed.

Two rows are admitted to the research ledger. Production admission, estimator eligibility, historical census completeness, rate/prior promotion, global plateau and Phase 1D completion stay false.

## Tests and limits

The focused suite tests exact input/review/source binding, wrong or missing approvals, extra/unreviewed rows, source mutation, duplicate representations, altered identity/date/funding/cap/cohost scope, immutable concurrent writes and identical replay. Adversarial semantic changes to these frozen rows are rejected at the exact-input boundary. This does not claim that the adapter can independently interpret arbitrary new offerings, distinguish arbitrary tranches or adjudicate future rounds. New cases require new reviewed inputs and a versioned extension.

Older local draft releases remain preserved outside the portable publication manifest. Only the current release and explicitly listed portable files are proposed for repository integration.

## Final acceptance

The v0.3.0 adapter and ledger passed 45 focused tests, 34 independent checks, 302 finite reference-schema parity cases, and fresh repository-layout CLI/default-discovery replay. The ledger is byte-identical across local-map and repository-path modes. This is local verification, not remote CI.

A predecessor JEV receipt bound an earlier integer-check implementation. Its historical boundary remains explicit. The one-line parity correction received independent successor review and a new final JEV receipt that names the current exact code hash. The successor choice was accepted with probability 0.99 and confidence 0.98. These are model judgments, not empirical confidence intervals or percentages of Phase 1D completed.

`final-acceptance.json` binds the current code, input manifest, unchanged ledger, independent successor review and actual final JEV receipt. `portable-package-manifest.json` enumerates only portable publication files. No remote changes have been made by this workpiece.
