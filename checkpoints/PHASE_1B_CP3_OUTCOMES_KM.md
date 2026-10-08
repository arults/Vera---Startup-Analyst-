# Phase 1B — Checkpoint 3: Outcomes + Censoring-Aware Survival

Date: 2026-10-08  
Status: **PASS — limited five-year reference class**

## Frozen inputs
- Denominator: 42 SEC-positive 2020 Wefunder offerings.
- Manifest SHA-256: `62468cea323ed6d2732df90cbe5ced04990db907cf908e4939b4128a302f78c8`
- Outcomes rows: 42/42.
- Outcomes SHA-256: `7f87d79c2a24bf748a6751180fed4cc286b678e0621d4fcbe8ec8b38b2afb5fc`

## Outcome state
- 35 active/right-censored
- 4 failures
- 2 acquisition censors
- 1 public-listing censor

## Primary result
At 5 years:
- Kaplan-Meier operating survival = **93.01%**
- 95% CI = **74.40%–98.24%**
- at risk = **12**
- cumulative failures = **2**
- cumulative censors = **28**

Late-bound funding-date sensitivity:
- survival = **92.57%**
- 95% CI = **73.07%–98.12%**
- at risk = **8**

Six-year estimates are not promoted: primary at-risk n=3 and late-bound n=1.

## Independent Verifier
GitHub Actions run `37766586864`:
- 13/13 regression/adversarial tests PASS.
- D01–D08 PASS.
- O01–O07 PASS.
- S01–S03 PASS.
- Overall promotion gate: PASS.

Three earlier failed CI attempts are preserved in verifier evidence. No gate was waived:
1. import-path defect;
2. literal-newline patch defect;
3. incorrect negative-test fixture.

## Jev CP3 gate
Model: `jev-1.13.0`
- CP3 state `pass_limited_5y`: probability **1.00**, confidence **1.00**.
- Five-year estimate eligible for CP4 promotion: yes probability **0.79**.
- Six-year estimate eligible for promotion: yes probability **0.08**.
- Carry primary + sensitivity together: probability **1.00**, confidence **1.00**.

## Next checkpoint
CP4 decides the promoted Vera version and reference-class registry contents. It may promote the five-year limited prior only with cohort definition, confidence interval, at-risk count, censoring and sensitivity attached. Six-year output remains non-promoted.
