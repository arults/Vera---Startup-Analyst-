# Phase 1B — Checkpoint 4: Final Promotion

Date: 2026-10-08  
Status: **COMPLETE — Vera v0.4.0**

## Final promotion
Phase 1B promotes Vera's first verified empirical reference class:

**2020 Wefunder successfully funded cohort — five-year operating survival**

- Frozen funded denominator: **42**
- Outcome records: **42/42**
- Observed failures: **4**
- Primary 5-year Kaplan-Meier survival: **93.01%**
- 95% CI: **74.40%–98.24%**
- At risk at 5 years: **12**
- Late-bound funding-date sensitivity: **92.57%**
- Sensitivity 95% CI: **73.07%–98.12%**
- Sensitivity at risk: **8**

Registry: `reference_classes/wefunder_2020_operating_survival.json`

## What is not promoted
- Six-year survival is sensitivity-only because primary at-risk n=3 and late-bound at-risk n=1.
- The 93.01% point estimate may not be detached from its confidence interval, risk set, censoring and cohort definition.
- The Wefunder survival prior may not be directly substituted for P(company succeeds), P(PMF), P(financing survives), or another startup-specific causal probability.

## Independent verification
CP3 run `37766586864`:
- 13/13 tests PASS
- D01–D08 PASS
- O01–O07 PASS
- S01–S03 PASS
- manifest SHA-256 `62468cea323ed6d2732df90cbe5ced04990db907cf908e4939b4128a302f78c8`
- outcomes SHA-256 `7f87d79c2a24bf748a6751180fed4cc286b678e0621d4fcbe8ec8b38b2afb5fc`

CP4 registry-integrity run `37766937563`:
- **18/18 tests PASS**
- promoted registry values match the frozen outputs and verifier hashes
- full Phase 1B verifier still PASS

## Jev final gate
Model: `jev-1.13.0`

- final state `complete_limited_reference_class`: probability **1.00**, confidence **1.00**
- semantic version `v0.4.0`: probability **0.98**, confidence **0.97**
- registry contents = five-year estimate with full context: probability **1.00**, confidence **1.00**
- allow direct substitution into company-specific success probability: yes probability **0.06**
- mark Phase 1B complete: yes probability **0.73**

## Closure
CP1 rules/repository freeze: PASS  
CP2 SEC denominator freeze: PASS  
CP3 sourced outcomes + censoring-aware KM: PASS  
CP4 Verifier + Jev promotion: PASS

**Phase 1B is closed.**

The next calibration work should expand across independent Wefunder years/cohorts and then stage/sector strata before Vera increases the weight assigned to empirical base-rate priors.
