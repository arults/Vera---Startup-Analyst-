# SKILLS.md — Vera operational research memory

Version: 0.4.0
Date: 2026-10-08
Phase 1B: **COMPLETE — limited empirical reference class promoted**

## Current system state
Vera's research/calibration architecture now includes its first verified empirical reference class. The 2020 Wefunder funded cohort has been reconstructed, frozen, outcome-traced, analyzed with censoring-aware Kaplan-Meier, independently verified, sensitivity-tested, and promoted through Jev.

## Non-negotiables
- Never promote a remembered count without immutable row evidence and source provenance.
- Never convert missing evidence into survival; right-censor at the last supported observation.
- Preserve failed, superseded and rejected approaches in `docs/ITERATION_LOG.md`.
- Promoted empirical files contain only Verifier-passing and Jev-promoted claims.
- A reference-class rate is an anchor/bound, not an automatic startup-specific probability.
- Always carry uncertainty, applicability and censoring information with a base rate.

## Promoted reference class — Wefunder 2020
Registry: `reference_classes/wefunder_2020_operating_survival.json`

Cohort:
- Wefunder Portal LLC, intermediary CIK 0001670254.
- Earliest Form C in calendar 2020.
- Direct SEC successful-close / positive-proceeds evidence required.
- Frozen denominator: **42** offerings.
- Manifest SHA-256: `62468cea323ed6d2732df90cbe5ced04990db907cf908e4939b4128a302f78c8`.
- Outcomes SHA-256: `7f87d79c2a24bf748a6751180fed4cc286b678e0621d4fcbe8ec8b38b2afb5fc`.

Outcome state:
- 35 active/right-censored.
- 4 failures.
- 2 acquisition censors.
- 1 public-listing censor.

Promoted horizon:
- **5-year operating survival: 93.01%**
- 95% CI: **74.40%–98.24%**
- At risk at 5 years: **12**
- Late-bound funding-date sensitivity: **92.57%**, 95% CI **73.07%–98.12%**, at risk **8**.

Not promoted:
- Six-year tail: underpowered (primary n-risk 3; late-bound n-risk 1).
- Point-estimate-only representation.
- Direct substitution into P(company succeeds), P(PMF), P(financing survives), or other startup-specific causal probabilities.

## Applicability
Before using the Wefunder prior, Vera must check platform/cohort comparability, stage/age, sector/business model, capital intensity, geography/regulation, financing structure and horizon. If applicability is weak, widen uncertainty or use the result as a loose bound rather than a prior.

## Verification
CP3 GitHub Actions run `37766586864`: 13/13 tests PASS; D01–D08, O01–O07, S01–S03 PASS.
CP4 registry-integrity run `37766937563`: **18/18 tests PASS**; full Phase 1B verifier PASS.

Jev CP4:
- final state `complete_limited_reference_class`: probability 1.00, confidence 1.00.
- version `v0.4.0`: probability 0.98, confidence 0.97.
- full-context registry representation: probability 1.00, confidence 1.00.
- direct substitution allowed: yes probability 0.06.
- Phase 1B complete: yes probability 0.73.

## Historical / research modules retained
- `docs/WEFUNDER_JEV_RESEARCH_INPUT.md`: provenance-tagged diligence/model-design learnings; not itself an empirical prior.
- `docs/REM_PROBABILISTIC_CAPTURE_ENGINE.md`: REM v3 probabilistic market-capture methodology; numeric outputs remain evidence/calibration gated.
- `docs/TAM_VERIFICATION_ENGINE.md`: multi-method TAM triangulation and verification rules.

## Next phase
Phase 1B is closed. The next empirical-calibration step should add independent cohorts/years and sector/stage stratification before increasing the weight of reference-class priors in company analyses.
