# Phase 1D CP6 — Stop-gate audit and repair

Date: 2026-10-09. Execution increment: 0.6.1-dev.audit.1.
Baseline commit: 122c869911d838a8ed77e71b893b8e0104a1dd95.
State at this checkpoint: LOCAL REPAIR VERIFIED; FULL REPOSITORY CI PENDING; GLOBAL RESEARCH PLATEAU NOT DEMONSTRATED.

## Supersession, without erasing history

CP5 and deterministic-a/b/c remain untouched. Their equality supports replay stability, not two substantive research-feedback iterations. CP6 supersedes that plateau/closure assertion only; it does not invalidate the existing dataset or approve any new prior. No startup observations were added during this repair.

## Defects demonstrated from original code

P01: workflow sampled exact_state three consecutive times with no substantive action between them, then declared research plateau.
P02: comparator explicitly accepted quality decreases (the old test accepted 0.5 -> 0.4).
P03: target.write_text overwrote supposedly immutable named snapshots.
P04: missing/empty/nonfinite state and source/label-schema omissions could evade meaningful completeness checks.

## Changes

New fail-closed research gate, strict nine-dimension/nine-label/six-source schema, passing scientific verifier, real byte hashes, chronological linked action receipts, distinct execution/alternative identity, no synthetic/replay artifacts, regression rejection and atomic non-overwrite publication. Legacy acceptance and write CLI retired. Workflow is read-only and explicitly expects old replay snapshots to FAIL the research-plateau criterion.

## Feedback loops performed

Loop 1: 22 local synthetic tests PASS.
Loop 2: execution binding, synthetic/replay rejection and duplicate-work defenses; 32 PASS.
Loop 3: close omissions affecting both compared snapshots; 35 PASS.
Separate challenge A: 10,000 seeded random comparisons, zero property failures.
Separate challenge B: 38 receipt/evidence-field removals, all rejected.
Integration compatibility: 39 local tests PASS.
These are engineering verification activities, not empirical research iterations. Full-repository CI is not claimed until its actual receipt is appended.

## Jev decisions

jev-1.13.0 chose audit, targeted repair, evidence hardening and branch integration with selected-option probability 1.00 and confidence 1.00. It chose limited_verified_execution_plateau_not_demonstrated with probability/confidence 1.00. Last preintegration numeric-promotion yes probability: 0.05. These are decision-model outputs, not calibrated startup probabilities. Full returned distributions are in evidence/jev/PHASE_1D_CP6_AUDIT_DECISIONS.json.

## Data and outstanding work

Preserve Republic Europe's 952 normalized rounds, 796 eligible rows, 63 full-universe qualifying follow-ons (55 eligible per detailed earlier log), low-information labels and suppressed rates. Four other platform censuses remain incomplete. Do not call access blockage a research plateau or treat zero confirmed closures as no failures.

Next: verify integrated branch using full tests, verifier_v4 and the replay audit; save exact run/job IDs and results. Then real evidence work requires a new admissible route or changed source/access conditions and contemporaneous receipts, not unchanged retry loops. Main and the empirical-prior registry remain unchanged.
