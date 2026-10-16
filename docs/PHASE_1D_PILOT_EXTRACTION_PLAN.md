# Phase 1D Pilot Extraction Plan — Wefunder 2020–2022

Date: 2026-10-17
Status: DRAFT — accompanies PHASE_1D_CP1_SCOPE_FREEZE.md

## Goal
Execute the frozen Phase 1C contracts on a real, limited Wefunder cohort so that identity, outcomes, censoring, and reporting gates can be stress-tested before scaling to all five platforms and 2020–2025.

## Pilot cohort
- Platform: wefunder
- Offering years: 2020, 2021, 2022 (first-live year)
- Layers: both Layer A (accessible deals) and Layer B (successfully funded/completed)
- Outcome time zero: successful completion/close date for Layer B
- Extraction cutoff: set at the start of CP2 and frozen for the pilot

## Extraction steps (using existing Phase 1C adapters and schemas)
1. Discover campaign/round pages and platform-hosted documents via the Wefunder adapter (search engines are discovery-only; snippets are never evidence).
2. Capture each source with:
   - platform-host boundary enforcement
   - availability state (PUBLIC_VISIBLE / AUTH_REQUIRED / UNAVAILABLE)
   - content SHA-256
   - extraction timestamp
3. Build the deterministic extraction manifest (schema: phase1c-source-manifest-v1) and compute manifest_sha256.
4. Map captures into RoundRecord objects (schema/phase1c_round.schema.json):
   - offering_year = first_live_date.year
   - exactly one primary_field (12 controlled fields + Other/Diversified)
   - instrument_type, legal_name, source_url, source_availability
   - comparable_valuation only when a priced comparable exists (SAFE/convertible caps are not valuations)
5. Flag missing campaigns with missingness markers when core identity/year is otherwise established from the same platform; never impute outcomes.
6. Run identity resolution:
   - auto-match only on exact strong ID or ≥2 independent medium identifiers
   - name-only auto-match prohibited
   - generate cross-platform candidate queue (even in pilot, for later graph use)
   - 100% review of medium/manual matches; stratified 10% audit of strong matches
   - reopen matcher if sampled false-match or false-split >2%
7. Extract typed outcome events and apply the state machine (operating_pre_success, operating_post_success, terminal_success_exit, acquisition_value_unknown, closure, right_censored).
8. Right-censor at last dated platform-hosted evidence affirmatively supporting ongoing operation, capped at extraction date. Silence / stale page / no news ≠ survival or closure.
9. Compute ascertainment coverage and lost-follow-up sensitivity bounds.
10. Run AJ occupancy + success/closure CIF + company-cluster bootstrap on the pilot Layer B set.
11. Produce RQ1 cells (flag LOW_INFORMATION when n<30 or <5 informative events) and any RQ2 cells that pass the n≥30 / ≥5 events / ≥80% ascertainment gate; otherwise pool adjacent years within the maturity block and disclose.

## Pilot success criteria
- Extraction manifest hash is deterministic and reproducible.
- All Phase 1C deterministic gates that can be applied to the pilot data still PASS.
- Identity false-match and false-split rates (from audit) ≤2% or matcher is reopened.
- No outcome is imputed; every Layer B row has an explicit event type or right-censor with dated evidence.
- Reporting cells carry the platform-observed label and do not extrapolate beyond supported follow-up.
- Phase 1B regression remains green.
- Verifier reports PASS (or a concrete contract failure that meets the reopening rule).
- Jev is presented with the verified pilot state for a structured go/no-go on expansion.

## Stop / reopening rules
- If identity-error rate >2%, censoring/ascertainment failure, or a Verifier gate fails for a reason that cannot be fixed inside the existing contracts, stop and submit the failure to Jev before any design change.
- Do not expand beyond Wefunder 2020–2022 until the pilot Verifier + Jev gate passes.

## Outputs expected from the pilot
- data/phase1d_wefunder_pilot_manifest.json (hashed)
- data/phase1d_wefunder_pilot_rounds.csv (or equivalent RoundRecord export)
- evidence/verifier/PHASE_1D_PILOT_VERIFIER.json
- evidence/jev/PHASE_1D_PILOT_DECISION.json
- Updated checkpoints/PHASE_1D_CP2_... once the pilot data freeze is promoted

## Non-negotiables preserved from SKILLS.md and Phase 1C
- Never promote remembered counts or unsourced rates.
- Closure requires explicit evidence.
- 2024–2025 (when later included) are right-censored.
- Company-round is the analytical unit.
- SAFE/convertible caps are not priced valuations.
- Same-platform secondary trading alone is not success.
- Reference-class rates remain anchors only.
