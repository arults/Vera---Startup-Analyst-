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

## 2026-10-08 — CP2 denominator freeze decision

The repaired 42-row manifest passed all denominator gates in GitHub Actions run 37750379057. SHA-256: `62468cea323ed6d2732df90cbe5ced04990db907cf908e4939b4128a302f78c8`.

Jev decision:
- freeze denominator: yes probability 0.79;
- CP2 state `frozen_primary_denominator`: probability 0.95, confidence 0.92;
- SEC-data mirror use acceptable with provenance/direct EDGAR identifiers: yes probability 0.80;
- proceed to outcomes rather than more denominator search: yes probability 0.78.

The remembered historical 42 is now superseded by an independently reconstructed 42-row manifest. The equality of counts is corroboration, not a selection criterion.


## 2026-10-08 — CP3 outcomes + survival

### Evidence rules admitted
- Jev selected independent-first outcome evidence with probability 1.00 / confidence 1.00.
- Company-controlled evidence is allowed only after documented independent-search exhaustion and is marked lower confidence; current-site fallback selected with probability 0.99 / confidence 0.98.
- If no later reliable evidence exists, right-censor at the last dated SEC filing. Jev selected this rule with probability 1.00 / confidence 1.00.
- Early right-censoring does not by itself block the study; Jev block probability was only 0.08.

### Research corrections preserved
- Earlier working hypotheses that eCarra and SapientX had shut down were **not promoted**. The CP3 evidence search did not substantiate those failure claims; eCarra is censored at dated 2022 independent operating evidence and SapientX at dated 2026 product evidence.
- Curastory was initially headed toward an active censor, but a failure-first sweep found its 2026-08-27 Chapter 7 filing. It was correctly reclassified as a failure before the curve was frozen.
- Acquisition/successor events for Envel and GroGuru remain non-failure censors; BOXABL is a listing censor.

### Failed implementation attempts retained
1. GitHub Actions run 37765870945 — package import path failed.
2. GitHub Actions run 37766008386 — a repair accidentally wrote literal newline escape characters into Python source.
3. GitHub Actions run 37766514445 — the negative KM unit-test fixture itself used mathematically valid product-limit arithmetic and was corrected.

No evidence or statistical gate was weakened to make these runs pass. Final CP3 verifier run 37766586864 passed 13/13 tests and D01–D08, O01–O07, S01–S03.

### CP3 promotion boundary
Jev selected `pass_limited_5y` with probability 1.00 / confidence 1.00. Five-year promotion eligibility: 0.79 yes. Six-year promotion: only 0.08 yes, so the six-year tail remains sensitivity-only.

## 2026-10-08 — CP4 final promotion / Vera v0.4.0

### Promoted
- A **limited Wefunder 2020 five-year operating-survival reference class**.
- Primary KM: 93.01%, 95% CI 74.40%–98.24%, 12 at risk at five years.
- Late-bound time-zero sensitivity: 92.57%, 95% CI 73.07%–98.12%, 8 at risk.
- Cohort definition, at-risk counts, censoring, source hashes, outcome limitations and sensitivity remain attached to the registry entry.

### Passed over / rejected
1. **Promote the six-year tail.** Rejected: primary at-risk n=3, late-bound n=1; Jev yes probability 0.08.
2. **Store only the 93.01% point estimate.** Rejected; Jev selected primary + sensitivity with probability 1.00.
3. **Promote the entire 1–6 year curve equally.** Rejected; tail support is materially weaker.
4. **Substitute the Wefunder survival number directly for P(company succeeds), P(PMF) or P(financing survives).** Rejected; Jev yes probability 0.06.
5. **Call this Vera v1.0.0.** Rejected; Jev selected v0.4.0 with probability 0.98 / confidence 0.97.
6. **Keep it as v0.3.6 only.** Passed over; Jev assigned 0.02 probability versus 0.98 for v0.4.0.

Final registry-integrity CI run 37766937563 passed 18/18 tests and the full Phase 1B verifier. Phase 1B completion yes probability from Jev: 0.73; final state `complete_limited_reference_class` selected with probability 1.00 / confidence 1.00.


## 2026-10-08 — Phase 1C build loop

Phase 1C was implemented as an executable framework only. Full five-platform data collection and final rates were explicitly excluded by Jev (executable_framework probability 1.00). Target version v0.5.0 was selected with probability 0.79.

### Build → Verify → Feedback → Rebuild iterations
1. Initial framework: schemas, identity resolver, graph, state machine, AJ occupancy, reporting gates and CI.
2. Verifier feedback prioritized explicit success/closure competing-risk estimands (0.64). Added CIF + clustered bootstrap orchestration.
3. Next verifier prioritized source adapters/provenance (0.73). Added five adapters, host boundaries, availability states and manifest hashing.
4. Next verifier prioritized identity candidate generation (0.57). Added blocking, cross-platform candidate queue, mandatory medium/manual review and strong-match audit.
5. Next verifier prioritized pooling/report contracts with probability 1.00. Added adjacent-year pooling executor, native-vs-graph bias report and structured platform-observed result contract.
6. Final implementation verifier required deterministic-verifier hardening with probability 1.00. Expanded to 25 fail-closed gates.

### Failed / corrected approaches preserved
- **Typed-node verifier bug:** first full verifier expected 41 decision IDs because it demanded superseded D15/D27/D29 as well as replacement nodes. Corrected to the final 39-node authority; no typed-coverage rule was weakened.
- **Candidate test assumption:** a test expected only one cross-platform candidate even though a second identity shared two medium identifiers (domain + founder). The algorithm was correct; the test was changed to require both candidates and mandatory review, reducing false-split risk.
- **Partial connector write:** a transport disconnect occurred during the pooling/report rebuild. Branch state was inspected before retry; already-written files were retained and only missing files were created.
- **Weak verifier assertion caught before CI:** an initial competing-cause gate was too permissive. It was strengthened to a synthetic fixture where success CIF must exceed closure CIF.

### Current verified state before plateau
GitHub Actions run 37776384631: 45/45 tests PASS and 25/25 Phase 1C deterministic gates PASS. Phase 1B regression remains green (run 37776384486). Jev round 6 selected final documentation as the only next action with probability 1.00 and no material design-node flip with probability 1.00.
