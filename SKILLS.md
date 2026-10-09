# SKILLS.md — Vera operational research memory

Promoted version: 0.5.0
Execution increment: 0.6.0-dev.r2 (NOT a promoted release)
Date: 2026-10-09
Phase 1B: **COMPLETE — limited empirical reference class promoted**
Phase 1C: **COMPLETE — multi-platform calibration framework built; full dataset/rates intentionally not run in Phase 1C**
Phase 1D: **INCOMPLETE / UNPROMOTED — partial execution, four historical denominators incomplete**

## Current system state
Vera now has:
1. a promoted, provenance-bound empirical reference class from Phase 1B;
2. an executable Phase 1C framework for censored multi-platform cohort execution across Wefunder, StartEngine, Crowdcube, Republic US and Republic Europe, 2020–2025; and
3. Phase 1D Republic Europe provisional candidate estimates plus an audited Republic US archive-candidate checkpoint. Neither is a promoted full-study result.

Current continuation authority: `checkpoints/PHASE_1D_CP4B_REPUBLIC_US_RECOVERY.md` and `evidence/jev/PHASE_1D_CP4_ROUND2_RECOVERY.json`. Older instructions to normalize Republic Europe from scratch or retry Wefunder's visible API census are superseded. Historical decisions and rejected approaches remain preserved.

## Non-negotiables
- Never promote remembered counts or unsourced rates.
- Never convert missing evidence into survival or closure.
- Closure requires explicit evidence; no news/stale page is not closure.
- 2024–2025 are right-censored; crude success/closure proportions are invalid.
- Company-round is the analytical unit; repeat rounds remain linked by canonical company.
- Cross-platform qualified follow-ons can credit predecessor success and also start a new later-round clock.
- SAFE/convertible caps are not priced valuations.
- Same-platform secondary trading alone is not success.
- A reference-class rate is an anchor/bound, not a startup-specific causal probability.
- Preserve failed/rejected approaches in docs/ITERATION_LOG.md.
- Full multi-platform rates may be promoted only after later execution, deterministic verification and Jev promotion.
- Successful CI and capture-integrity checks do not prove evidence availability or census completeness. Zero captures must be NO_EVIDENCE or ACCESS_BLOCKED, never research success.
- Archived-source reprocessing is not new live evidence. Deadline month, first-live date and successful close are different fields.
- Do not repeatedly retry the same HTTP403 path without changed authorized access or a materially different evidentiary route. Never bypass access controls.

## Phase 1B promoted reference class
Registry: `reference_classes/wefunder_2020_operating_survival.json`
- cohort n = 42 successfully funded Wefunder offerings anchored to 2020 initial Form C;
- promoted 5-year operating survival = 93.01%;
- 95% CI = 74.40%–98.24%;
- at risk at 5 years = 12;
- late-bound sensitivity = 92.57%, 95% CI 73.07%–98.12%, at risk 8.
Six-year output remains non-promoted and direct substitution into company-specific success probabilities is prohibited.

## Phase 1C architecture
Design authority:
- `docs/PHASE_1C_SPEC.md`
- `decisions/PHASE_1C_DECISIONS.json`

Cohorts:
- Layer A = all publicly launched accessible deals for coverage/selection analysis.
- Layer B = successfully funded/completed rounds for investor-outcome estimation.
- offering year = first-live year;
- outcome time zero = successful close/completion.

Taxonomy:
- 12 primary analytical fields + Other/Diversified;
- exactly one primary field + seven versioned controlled tag dimensions;
- raw platform-native tags retained.

Identity:
- exact strong ID or >=2 independent medium identifiers for auto-match;
- name-only match prohibited;
- 100% review of medium/manual matches;
- stratified 10% audit of strong matches;
- reopen matcher if sampled false-match or false-split >2%.

Outcomes:
- survival = independent operating-state occupancy;
- success = first typed qualifying event;
- closure = explicit confirmed terminal failure;
- acquisition with unknown consideration is terminal but success UNKNOWN.

Statistics:
- Aalen–Johansen / competing-risk multistate framework;
- company-cluster bootstrap primary uncertainty;
- analytic diagnostic interval;
- 12/24/36/60-month landmarks only when supported + maximum supported follow-up;
- platform-observed ascertainment label and lost-follow-up sensitivity bounds.

RQ2 cell gate:
- n>=30;
- >=5 informative events;
- >=80% ascertainment;
- otherwise adjacent-year pooling within maturity block; no silent 2023/2024 boundary crossing.

## Phase 1C verification
- 45/45 unit/adversarial tests PASS.
- 25/25 deterministic gates PASS.
- Phase 1C CI run: `37776384631`.
- Phase 1B regression run on Phase 1C branch: `37776384486` PASS.
- Jev implementation rounds: 8.
- Plateau rounds: 7 and 8.
- Round 7 plateau probability 0.77; no-flip probability 0.99.
- Round 8 plateau probability 0.86; no-flip probability 0.96.

Do not reopen Phase 1C design unless real execution produces a concrete contract failure, identity-error rate >2%, censoring/ascertainment failure, or a Jev/Verifier gate failure.

## Phase 1D — real study execution (target Vera v0.6.0)
Status: INCOMPLETE / UNPROMOTED
Date: 2026-10-09

Execution checkpoints:
1. CP1 source census + coverage manifests — PASS_WITH_SUPPRESSION; four platform censuses still incomplete.
2. CP2 — Republic Europe bounded-year cohort FROZEN; other platforms not frozen.
3. CP3 — Republic Europe outcome ledger v3 traced; low information remains; other platform outcomes not ready.
4. CP4 — Republic Europe candidate v2 previously passed 27/27 execution gates; CP4B Republic US archived-candidate increment verified and checkpointed.
5. CP5 — full-study plateau/final promotion NOT reached. Access blocks are not statistical convergence.

Coverage:
- Republic Europe: native enumeration recorded 2,896 sitemap URLs / 2,073 candidate slugs; 952 funded rounds, 796 bounded-year rows, 156 year-unresolved/suppressed. Ledger v3 has 55 qualifying follow-on successes in bounded-year rows and 2 Zeigo acquisition-value-unknown terminal rows; no explicit closures were invented. Candidate rates remain LOW_INFORMATION; no RQ2 field cell passes its frozen gate.
- StartEngine: CENSUS_INCOMPLETE. CP1 recorded an official directory total of 1,539 offerings but no complete year-specific in-scope URL census.
- Republic US: CENSUS_INCOMPLETE. New live recovery returned four HTTP403s and zero captures; 144 existing public-note archive rows were normalized as candidates, not historical funded rounds.
- Wefunder: CENSUS_INCOMPLETE. Previously recovered 149 native API rows / 144 Portal LLC rows do not match the known 42-row 2020 cohort and cannot establish historical coverage.
- Crowdcube: CENSUS_INCOMPLETE.

Jev requires rate suppression for every CENSUS_INCOMPLETE platform-year cell. Search engines may discover canonical platform URLs, but snippets are never evidence. Public extraction of a canonical platform campaign page is acceptable platform evidence.

## CP4B execution and recovery
- Live run `37894313863`: 82/82 regression tests PASS, but 0 new captures and 4 HTTP403 errors. Research state ACCESS_BLOCKED, regardless of green workflow/integrity status.
- Archive normalization run `37894925070`: 101/101 total regression tests PASS, including 38 new tests; 15/15 normalization gates PASS.
- Saved output: `data/phase1d/republic_us_archive/gh-37894925070-1/`.
- 144 source-bound archived candidates; 0 rejects, duplicates or slug conflicts; 144-item resolution queue; source and output hashes retained.
- 0 resolved first-live cohort years, 0 strong legal-entity IDs and 0 estimation-eligible rows. Deadline-year counts 2016–2020 are NOT offering-year assignments.
- Final Jev accepts candidate checkpoint only: probability 1.00, confidence 1.00; overall study remains incomplete/not plateau: probability 1.00, confidence 1.00. These are model decision judgments, not empirical outcome probabilities.

## Current next action
Recover and reconcile a defensibly enumerable historical census from permitted platform-native sources or an authorized export, using existing discovery manifests rather than restarting. Then resolve legal-entity IDs, first-live dates and successful funding completion dates from the saved queue before outcome estimation. Do not substitute the 144-row old Republic Note subset for the 2020–2025 denominator, reinterpret deadline dates, or rerun unchanged blocked paths as though they were a new strategy.
