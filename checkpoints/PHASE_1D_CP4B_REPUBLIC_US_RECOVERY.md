# Phase 1D CP4B — Republic US recovery / execution iteration 2

Date: 2026-10-09
Execution increment: **0.6.0-dev.r2** (not a promoted release)
Study state: **INCOMPLETE / UNPROMOTED — no full-study plateau**
Checkpoint state: **ACCEPTED FOR ENGINEERING AND ARCHIVED CANDIDATES ONLY**

## Actual work completed
The newer Wefunder Jev decision superseded the stale instruction to retry Wefunder: 149 currently visible API rows, with no matches to the known 2020 cohort, remain unsuitable as the historical denominator. Jev routed this iteration to Republic US.

The legacy Republic US probe had four concrete defects: company-profile recognition was unreachable; page counts were cumulative across seeds; URL-only deduplication could discard distinct response bodies; and scrolling was not an explicit pagination audit. A separate bounded public collector and 19 adversarial tests were added without overwriting previous evidence. Run-scoped manifests, append-only checkpoints and content-addressed full captures support recovery after interruption.

### Live run: blocked, not successful research
GitHub Actions run **37894313863** completed its program and persistence, and **82/82 regression tests passed**, but all four native directory requests returned **HTTP 403**. It produced **zero new captures and zero new candidates**. Its 10/10 capture-integrity checks do not establish evidence availability or census completeness.

Evidence: `data/phase1d/republic_us_recovery/gh-37894313863/summary.json` and the associated tests, errors, checkpoints and workflow artifact. Scientific status: **ACCESS_BLOCKED**. Do not repeat identical blocked requests without changed authorized access or a materially different evidentiary route.

### Feedback -> rebuild -> re-execute
Jev selected reprocessing of the previously preserved public API archive rather than restarting data collection or treating green CI as data success. A source-bound normalizer and 19 more adversarial tests were added. It explicitly separates source availability from integrity checks and does not convert deadline months into launch/close dates, caps into priced valuations, names into canonical legal identities, or missing outcomes into survival/closure.

Archive-normalization run **37894925070**, code commit `feb512d846f51080617533c483f5d4552bcf0245`, persisted outputs at commit `12911af88137516c211c4a48bb5f7800ba1fa66b`:
- **101/101 total regression tests PASS**, including 38 newly added tests in this continuation.
- **144 archived native candidate records** normalized; 144 unique slugs; zero rejected rows, exact duplicate rows or conflicting slugs.
- **15/15 normalization/provenance gates PASS**, including non-empty source and non-empty candidates.
- Raw-row evidence, source hashes, an empty quarantine and a **144-item resolution queue** are preserved.
- **Zero validated cohort years, zero strong legal-entity IDs and zero estimation-eligible records.**

This is improved organization and auditability of existing evidence, **not 144 newly discovered or verified funded rounds**. Deadline-year counts are 2016:5, 2017:14, 2018:38, 2019:38 and 2020:49. These are not first-live cohort years and do not cover the study's 2021–2025 cohorts.

## Durable lineage
Output directory: `data/phase1d/republic_us_archive/gh-37894925070-1/`.
Files: `candidates.json`, `quarantine.json`, `resolution_queue.json`, `summary.json`, `manifest.json`, `tests.txt`, `code_sha256.txt`.
The workflow also uploaded an independent 90-day artifact copy; the repository is the persistent checkpoint.

Source archive: `data/phase1d/cp1_republic_us_probe.json`.
Source Git blob: `4257d36bb7259b8a9f923a4b050c8d05936eaed5`.
Source SHA-256: `0cfea3138ddbbfcb3f66c4ab1fd755a1b2ad88eaa7720cbfbe9a1714f60c80dd`.
Normalizer SHA-256: `e4238c2402d2fe2d7742fbd4d675c619851a5d0244942894ed4dacea8a3aa72e`.
Candidate output SHA-256: `7823a4b2128fcc1e1235bc40d15fcc6f5173e7733426d91989346d37a6a89de9`.

## Jev and Verifier gate
All four Jev evaluations, input summaries and returned probability distributions are saved in `evidence/jev/PHASE_1D_CP4_ROUND2_RECOVERY.json`.

Final Jev choice: **accept_candidate_checkpoint**, selected-choice probability **1.00**, confidence **1.00**.
Full-study state: **blocked_incomplete_not_plateau**, probability **1.00**, confidence **1.00**.
Next priority: **historical_source_and_dates**, probability **1.00**, confidence **1.00**.
These are model decision judgments, not empirical company-success probabilities. Verification consists of the executed deterministic tests/gates plus Jev review; it is not a claim of an independent human audit.

## Overall study remains incomplete
Republic Europe remains at the prior 952-row funded universe / 796 bounded-year cohort, ledger v3 and provisional candidate estimates; the prior 27/27 execution gates do not remove LOW_INFORMATION status. No RQ2 field cell passes its frozen publication gate.

**Wefunder, Republic US, StartEngine and Crowdcube still have incomplete historical denominators.** Their platform-wide outcome rates remain suppressed. Phase 1B's limited promoted reference class and Phase 1C's framework are unchanged. No main-branch merge or release promotion occurred.

## Exact resumption point
Read this checkpoint and the saved Jev gate before acting on older next-action text. Do not rerun the old Wefunder visible-list probe as a historical census, or the same four Republic US403 requests without a changed access condition.

Next unresolved work is a reproducible historical census using permitted platform-native sources or an authorized export, reconciled against the existing discovery manifests. After coverage is defensible, resolve legal-entity IDs, first-live dates and successful funding completion dates from the saved queue before building outcomes or estimating rates. Existing source and candidate files are input evidence, not a replacement denominator.
