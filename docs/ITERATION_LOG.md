# Vera Iteration / Rejection Log

This file preserves ideas, approaches and intermediate states that **did not enter the promoted current model**. Rejection is part of the audit trail, not deletion.

## 2026-10-08 — Phase 1B CP1

### Kept in current methodology
- Initial Form C date in calendar 2020 anchors the Wefunder cohort.
- Offering identity = issuer CIK + SEC file number; amendments do not create new observations.
- Primary funded denominator requires direct SEC evidence of successful close / positive proceeds.
- Final withdrawals are excluded.
- Survival time zero = confirmed funding close.
- Shutdown/dissolution/bankruptcy/liquidation/clearly ceased operations = failure.
- Acquisition is a non-failure terminal outcome and is censored at acquisition in the primary KM curve.
- Missing later evidence is censored at last independently confirmed activity; silence never becomes survival through cutoff.
- Public-listing treatment requires sensitivity analysis because Jev confidence was low on whether to censor at listing.
- Only Verifier-passing empirical claims may enter promoted/current Vera priors.

### Passed over / rejected
1. **Promote the remembered denominator of 42.** Rejected until row-level SEC evidence is rebuilt. Jev yes probability: 0.14.
2. **Use only 2020 filings.** Rejected because 2020 C-U can belong to a 2019 offering and late-2020 offerings can close later; lookback/follow-up are required.
3. **Treat Wefunder campaign pages as equal to SEC closing evidence.** Rejected for the primary denominator; platform data may be corroborative only.
4. **Treat acquisitions as failures.** Rejected for operating-survival estimand.
5. **Assume companies survive to 2026 when later evidence is missing.** Rejected; right-censor at last independent observation.
6. **Collapse historical iterations into v1.0.** Rejected; it would erase learning provenance.
7. **Keep only the latest implementation.** Rejected; prior rules, failures and reversals are part of model governance.
8. **Save only one final Phase-1B commit.** Rejected; Jev chose four durable checkpoints with 0.99 probability.
9. **Commit after every company.** Rejected as excessive noise; checkpoints occur at methodological/evidence gates instead.

## Promotion discipline
A rule or empirical result can move from this log into the promoted reference-class registry only after its evidence requirements pass the independent Verifier and the resulting verified state is submitted to Jev for a structured promotion decision.

## 2026-10-08 — CP2 verifier feedback: chronology defect

### Failed approach preserved
The first denominator manifest used the cleaned dataset's final campaign deadline whenever the C-U did not spell out a close date. The independent verifier rejected this because seven rows had a deadline *after* a C-U that already described the raise as final/closed.

### Repair admitted by Jev
- Rejected: `deadline_always`.
- Selected: explicit C-U close date when present; otherwise `min(latest SEC deadline, final/closed C-U filing date)`.
- Jev confidence: 1.00; probability of selected rule: 1.00.
- Timing sensitivity retained: yes probability 0.79.
- Denominator-membership change: yes probability only 0.19; the 42 rows stay unchanged.

This failure is retained as evidence that row count alone is not sufficient for a denominator freeze; chronology is a separate gate.
