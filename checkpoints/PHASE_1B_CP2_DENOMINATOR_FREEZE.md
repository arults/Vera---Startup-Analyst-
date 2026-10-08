# Phase 1B — Checkpoint 2: 2020 Wefunder Denominator Freeze

Date: 2026-10-08
Status: PASS — primary denominator frozen

## Reconstruction
- Initial Wefunder offerings anchored by earliest Form C in 2020: **360**
- Offerings with any Form C-U: **43**
- SEC-positive/final funded offerings admitted: **42**
- Excluded offerings: **318**
- Withdrawals among admitted rows: **0**
- The sole C-U not admitted: T4L INC (020-27165), whose update says only that it was launching a StartEngine campaign.

## Independent verification
GitHub Actions run: `37750379057`
Regression tests: 8/8 PASS.
D01 exact count: PASS
D02 unique offering keys: PASS
D03 Wefunder identifiers: PASS
D04 initial Form C in 2020: PASS
D05 initial SEC evidence: PASS
D06 SEC-confirmed positive funding: PASS
D07 no withdrawals: PASS
D08 chronology: PASS

Frozen manifest SHA-256:
`62468cea323ed6d2732df90cbe5ced04990db907cf908e4939b4128a302f78c8`

## Verifier feedback loop retained
The first verifier attempt passed D01-D07 but failed D08 for seven rows because a later campaign deadline was incorrectly used after a C-U already said final/closed. No gate was waived. Jev selected the repair: explicit C-U close date where present; otherwise the earlier of latest SEC campaign deadline and final/closed C-U filing date. Proxy timing is flagged for CP3 sensitivity analysis.

## Jev promotion decision for CP2
Model: jev-1.13.0
- Freeze 42-row denominator: yes probability 0.79.
- State = `frozen_primary_denominator`: probability 0.95, confidence 0.92.
- Mirror enumeration acceptable with provenance/direct EDGAR identifiers: yes probability 0.80.
- Proceed to outcome research: yes probability 0.78.

## Scope
This checkpoint freezes **cohort membership**, not startup operating outcomes and not a survival probability. Any future membership correction must create a new version and preserve this frozen manifest/hash.

## Next checkpoint
CP3 requires one dated, sourced event/censor record for each of the 42 rows, a primary Kaplan-Meier curve plus preregistered timing/listing sensitivities, and O01-O07 + S01-S03 verifier PASS.
