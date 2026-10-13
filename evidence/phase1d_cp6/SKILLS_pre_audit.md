# SKILLS.md — Vera operational research memory

Branch version: 0.6.0
Date: 2026-10-09
Phase 1B: **COMPLETE — limited empirical reference class promoted**
Phase 1C: **COMPLETE — multi-platform calibration framework built**
Phase 1D: **COMPLETE — limited verified execution; no new empirical rate promoted**

## Current system state

Vera now has:

1. the promoted Phase 1B Wefunder 2020 five-year operating-survival reference class;
2. the Phase 1C executable multi-platform calibration framework; and
3. a completed Phase 1D execution package showing exactly which 2020–2025 public-platform evidence is sufficient and which platform cells must remain suppressed.

Phase 1D final authority:

- `checkpoints/PHASE_1D_CP4_VERIFIED_CANDIDATE_V3.md`
- `checkpoints/PHASE_1D_CP5_PLATEAU_FINAL.md`
- `evidence/verifier/PHASE_1D_CP4_POST_CLOSURE_VERIFIER.json`
- `evidence/jev/PHASE_1D_DETERMINISTIC_PLATEAU.json`
- `evidence/jev/PHASE_1D_FINAL_DECISION.json`

## Non-negotiables

- Never promote remembered counts, incomplete denominators or unsourced rates.
- Never convert missing evidence into survival or closure.
- Closure requires explicit platform evidence; no news, stale page, Not eligible status or zero valuation is not closure.
- 2024–2025 are right-censored; crude success/closure proportions are invalid.
- Company-round is the analytical unit; repeat rounds remain linked by canonical company.
- Qualified follow-on success requires a comparable priced valuation at least 1.5× the index round; valuation caps are not priced valuations.
- Same-platform secondary trading alone is not success.
- Search snippets are discovery only, never evidence.
- Successful CI/integrity gates do not prove census completeness or evidence availability.
- Never repeatedly retry an unchanged HTTP403/access-blocked route and call it new research.
- Preserve every failed, superseded and rejected approach in `docs/ITERATION_LOG.md`.
- Reference-class rates are anchors/bounds, not startup-specific causal probabilities.

## Phase 1B promoted empirical reference class

Registry: `reference_classes/wefunder_2020_operating_survival.json`

- denominator: 42 SEC-confirmed funded Wefunder offerings anchored to initial Form C in 2020;
- promoted five-year operating survival: **93.01%**;
- 95% CI: **74.40%–98.24%**;
- at risk at five years: **12**;
- late-bound sensitivity: **92.57%**, 95% CI **73.07%–98.12%**, at risk **8**.

Six-year output remains non-promoted. Direct substitution into P(company succeeds), P(PMF), P(financing survives) or another company-specific probability is prohibited.

## Phase 1C frozen architecture

- Layer A: all publicly launched accessible deals for coverage/selection analysis.
- Layer B: funded/completed rounds for investor-outcome estimation.
- Unit: economic company-round.
- Offering year: first-live year; outcome time zero: successful close/completion.
- Taxonomy: 12 primary fields plus Other/Diversified; one primary field plus controlled tags.
- Identity: strong ID or at least two independent medium identifiers; name-only auto-match prohibited.
- Estimators: Aalen–Johansen / competing risks, company-cluster bootstrap, analytic diagnostic interval.
- Horizons: 12/24/36/60 months only when supported.
- RQ2 gate: n≥30, at least five informative events and at least 80% ascertainment; otherwise adjacent-year pooling within maturity block or suppression.
- Results must remain `platform_observed` unless the evidence scope changes.

Do not reopen Phase 1C unless execution exposes a concrete contract failure, identity-error rate above 2%, censoring/ascertainment failure or Verifier/Jev gate failure.

## Phase 1D final execution state

### Platform denominator coverage

- Republic Europe: **PASS_NATIVE_ENUMERABLE**.
- Wefunder: **CENSUS_INCOMPLETE**; 149-row recent/listed native archive recovers 0/42 known 2020 cohort members; rates suppressed.
- Republic US: **CENSUS_INCOMPLETE**; verified 144-row archive has zero resolved cohort years, zero strong legal IDs and zero estimation-eligible rows; native recovery returned zero candidates; rates suppressed.
- StartEngine: **CENSUS_INCOMPLETE**; browser and exact observed public endpoints were access-blocked; rates suppressed.
- Crowdcube: **CENSUS_INCOMPLETE**; rates suppressed.

No rate may be computed or promoted for a `CENSUS_INCOMPLETE` platform-year cell.

### Republic Europe cohort

- normalized funded rounds: **952**;
- bounded-year/rate-eligible rows: **796**;
- year-unresolved/suppressed rows: **156**;
- canonical companies: **789**;
- usable-year counts: 2020 **184**, 2021 **191**, 2022 **181**, 2023 **142**, 2024 **47**, 2025 **51**;
- strong canonical legal ID coverage among rate-eligible rows: **100%**;
- repeat-company NEXT_ROUND edges: **163**;
- same-economic-round duplicate candidates: **0**.

Exact first-live dates were unavailable. Republic Europe offering year is assigned only when platform approval and funded dates bound the same calendar year; the exact first-live date remains null.

### Outcomes and identity

- qualified priced-follow-on successes: **63**;
- confirmed closures: **0**;
- terminal non-closure events: **2**;
- reviewed identity matches accepted: **5**;
- accepted Eligible pages adding positive follow-up: **2**;
- positive follow-up coverage among usable companies: **38.76%**;
- 22 ambiguous identity candidates remain held.

The 13 Not eligible + zero-valuation businesses were exhaustively reviewed through 41 Republic Europe captures. Fourteen phrase candidates were contractual liquidation/default language, not observed closures. Zero-valuation status remains an unresolved adverse signal only.

### Candidate v3

- RQ1 cells: **24**;
- estimable RQ1 cells: **17**;
- LOW_INFORMATION RQ1 cells: **24/24**;
- RQ2 cells: **60**;
- reportable RQ2 cells: **0**;
- maximum point-estimate change from candidate v2: **0.06928**.

Candidate v3 is retained as a verified low-information research artifact and supersedes v2 methodologically. It is not a promoted empirical prior.

### Verification and plateau

- final scientific workflow run: `37899158528`;
- tests: **179/179 PASS**;
- scientific gates: **43/43 PASS**;
- deterministic plateau workflow run: `37899535030`;
- plateau rounds `deterministic-b` and `deterministic-c`: both PASS;
- no dimension improvement above 0.05;
- no material label flip;
- no source-hash change.

Final Jev:

- state `complete_limited_execution`: probability **0.99**;
- version `v0.6.0`: probability **1.00**;
- promote a new Phase 1D prior: yes probability **0.13** → no;
- automatic merge to main: yes probability **0.42** → keep the completed package on the Phase 1D branch/PR pending deliberate merge.

## Next action

Phase 1D is closed. Do not repeat exhausted access routes. Further calibration improvement requires materially new public platform access, an authorized export, additional platform-hosted closure/outcome disclosures, or later follow-up time sufficient to move cells out of LOW_INFORMATION status.
