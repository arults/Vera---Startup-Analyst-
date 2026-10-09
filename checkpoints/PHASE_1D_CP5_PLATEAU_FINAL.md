# Phase 1D — Checkpoint 5: Deterministic Plateau & Final State

Date: 2026-10-09  
Status: **COMPLETE — LIMITED VERIFIED EXECUTION / VERA v0.6.0**

## Plateau method

Jev’s ordinal scores fluctuated even when the repository state was unchanged. The final plateau gate therefore used exact research-state dimensions, material labels and content hashes rather than stochastic score movement.

Dimensions frozen:

- denominator-grade platform share: **0.20**
- Republic Europe cohort-year coverage: **0.836134**
- strong identity share among rate-eligible rows: **1.00**
- positive platform follow-up coverage among usable companies: **0.387574**
- closure-audit target coverage: **1.00**
- scientific verifier pass share: **1.00**
- RQ1 reportable share: **0.00**
- RQ2 reportable share: **0.00**
- promoted Phase 1D rate share: **0.00**

## Two consecutive plateau rounds

Workflow run `37899535030` produced three immutable snapshots:

- `deterministic-a` — frozen baseline
- `deterministic-b` — plateau vs A: **PASS**
- `deterministic-c` — plateau vs B: **PASS**

For both comparison rounds:

- improvements above 0.05: **none**
- material label flips: **none**
- source-hash changes: **none**
- missing dimensions: **none**

The user-defined two-consecutive-round plateau condition is satisfied exactly.

## Final Jev gate

- final state `complete_limited_execution`: probability **0.99**
- semantic version `v0.6.0`: probability **1.00**
- promote a new Phase 1D empirical prior: yes probability **0.13** → **NO**
- automatic merge to main: yes probability **0.42** → retained on the Phase 1D branch/PR rather than automatically merged

## Final scientific state

Phase 1D successfully executed the Phase 1C machinery against public platform evidence and demonstrated where the evidence is and is not sufficient:

- Republic Europe has a frozen, reproducible cohort and a verified candidate analysis.
- Four other platforms remain denominator-incomplete and are correctly suppressed.
- Republic Europe candidate estimates remain LOW_INFORMATION and are not promoted.
- The Phase 1B Wefunder 2020 five-year reference class remains Vera’s only promoted empirical survival prior.

## Closure

CP1 source census: PASS_WITH_SUPPRESSION  
CP2 Republic Europe cohort/identity graph: PASS  
CP3 outcomes and evidence review: PASS_WITH_LIMITATIONS  
CP4 candidate v3 and independent verification: PASS / CANDIDATE_ONLY  
CP5 deterministic plateau: PASS

**Phase 1D is closed as a limited verified execution.** Further improvement requires materially new public data or platform access, not repetition of exhausted routes.
