# Phase 1D — Checkpoint 4A: Republic Europe Verified Candidate Estimates

Date: 2026-10-09
Status: **VERIFIED CANDIDATE / NOT PROMOTED**

## Inputs
- Frozen Republic Europe funded-round universe: 952
- Bounded-year rate-eligible rounds: 796
- Unique rate-eligible companies: 679
- Outcome ledger authority: `cp3_republic_europe_outcome_ledger_v3.csv`
- Qualified follow-on successes in bounded cohort: 55
- Explicit closures: 0
- Acquisition-value-unknown terminal rows: 2 (Zeigo)

## Candidate estimates
All estimates are explicitly labelled `platform_observed`.

Example 2020 cohort:
- 24m success CIF: 15.90% (cluster bootstrap 95%: 8.18%–24.66%)
- 24m independent-operating survival: 98.59% (95%: 95.65%–100%)
- 24m closure CIF observed: 0%; one-sided support-set upper bound: 4.19%
- 60m success CIF: 24.52% (95%: 15.23%–34.11%)
- 60m independent-operating survival: 97.18% (95%: 91.04%–100%)
- 60m closure support-set upper bound: 4.87%

Zeigo is a 2022 acquisition-value-unknown terminal event. Primary survival uses the labelled 2022-07-02 midpoint approximation with 2022-01-01 / 2022-12-31 sensitivity.

## Information quality
- 17 platform-year/horizon cells are estimable.
- Every estimable RQ1 cell is flagged LOW_INFORMATION because support is <80% and/or event counts are sparse.
- No RQ2 platform×field cell passes the frozen n>=30 / >=5 informative event / >=80% ascertainment gate; field rates are suppressed.

## Deterministic verification
GitHub Actions run `37886717240`:
- 27/27 Phase 1D gates PASS.
- CP4 candidate v1 is explicitly invalidated due the superseded ledger-v2 Zeigo follow-up error.
- No rate files exist for Wefunder, StartEngine, Republic US or Crowdcube while their denominators remain incomplete.

## Jev execution round 1
- Republic Europe tables remain `candidate_only`: probability 0.86.
- Full Phase 1D promotion: probability 0.
- No frozen Phase 1C design flip: probability 0.88.
- Highest expected-value next step: attempt Wefunder denominator recovery via Wefunder's own explore API.

This checkpoint is durable evidence, not a promoted empirical reference class.
