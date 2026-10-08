# SKILLS.md — Vera operational research memory

Version: 0.5.0
Date: 2026-10-08
Phase 1B: **COMPLETE — limited empirical reference class promoted**
Phase 1C: **COMPLETE — multi-platform calibration framework built; full dataset/rates intentionally not run**

## Current system state
Vera now has:
1. a promoted, provenance-bound empirical reference class from Phase 1B; and
2. an executable Phase 1C framework for later censored multi-platform cohort execution across Wefunder, StartEngine, Crowdcube, Republic US and Republic Europe, 2020–2025.

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

## Next execution
The next phase may populate the Phase 1C contracts with the real 2020–2025 platform data. Do not reopen Phase 1C design unless real execution produces a concrete contract failure, identity-error rate >2%, censoring/ascertainment failure, or a Jev/Verifier gate failure.


## Phase 1D — real study execution (target Vera v0.6.0)
Status: IN PROGRESS
Date: 2026-10-08

Execution checkpoints:
1. CP1 source census + coverage manifests — PASS_WITH_SUPPRESSION
2. CP2 normalized rounds + identity graph — IN PROGRESS
3. CP3 outcome tracing + censoring — pending
4. CP4 estimates + Verifier/Jev re-execution loop — pending
5. CP5 plateau/final promotion — pending

CP1 coverage:
- Republic Europe: PASS_NATIVE_ENUMERABLE (2,896 sitemap URLs / 2,073 candidate slugs).
- StartEngine: CENSUS_INCOMPLETE — official directory says 1,539 offerings but per-year complete URL census not recovered.
- Republic US: CENSUS_INCOMPLETE.
- Wefunder: CENSUS_INCOMPLETE.
- Crowdcube: CENSUS_INCOMPLETE.

Jev requires rate suppression for every CENSUS_INCOMPLETE platform-year cell. Search engines may discover canonical platform URLs, but snippets are never evidence. Public extraction of a canonical platform campaign page is acceptable platform evidence.

Current next action:
Normalize and validate the full Republic Europe native universe. Do not substitute funded year for first-live offering year unless a later typed Jev decision explicitly permits it after measured source failure.
