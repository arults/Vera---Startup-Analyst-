# Phase 1D — Checkpoint 1: Scope + Pilot Freeze

Date: 2026-10-17
Status: DRAFT — awaiting Jev promotion decision and independent verifier review

## Purpose
Freeze the scope, success criteria, non-goals, and pilot boundary for Phase 1D before any real multi-platform data collection begins.

Phase 1D executes the already-frozen Phase 1C framework on real data. It does **not** reopen Phase 1C design unless real execution produces a concrete contract failure, identity-error rate >2%, censoring/ascertainment failure, or a Jev/Verifier gate failure.

## In-scope for Phase 1D
- Populate Layer A (accessible-deal census) and Layer B (successfully funded/completed rounds) for the five Phase 1C platforms: Wefunder, StartEngine, Crowdcube, Republic US, Republic Europe.
- Offering years 2020–2025 (2024–2025 remain right-censored by construction).
- Source captures with content hashes, availability states (PUBLIC_VISIBLE / AUTH_REQUIRED / UNAVAILABLE), and deterministic extraction-manifest hashing.
- Identity resolution, cross-platform candidate queue, mandatory review of medium/manual matches, and stratified audit of strong matches.
- Typed outcome events and state-machine application.
- Aalen–Johansen occupancy + competing-risk CIF with company-cluster bootstrap.
- RQ1 / RQ2 reporting under existing contracts (cell gates, adjacent-year pooling without silent 2023/2024 boundary cross, platform-observed labels, no unsupported-horizon extrapolation).
- Deterministic Verifier gates + Jev structured promotion before any new rates enter the reference-class registry.

## Non-goals (remain out of scope)
- Claiming causal platform effects.
- Final IRR / MOIC distributions or company-specific success probabilities.
- Using inaccessible paid databases.
- Publishing mature 5-year outcomes for 2024–2025 cohorts.
- Promoting any multi-platform rate before Verifier PASS + Jev promotion.
- Reopening Phase 1C design without a concrete execution failure that meets the SKILLS.md reopening rule.

## Pilot boundary (recommended start)
Begin with a single-platform pilot to surface contract failures early:
- Platform: Wefunder (builds on Phase 1B lineage and existing SEC evidence patterns).
- Offering years for pilot: 2020–2022 (sufficient maturity for early landmarks while remaining right-censored where needed).
- Expand to remaining platforms and years only after pilot Verifier + Jev gates pass.

## Success criteria for CP1
- This scope document and the pilot extraction plan are committed.
- Phase 1D workflow skeleton exists and can run the existing Phase 1C verifier as a regression guard.
- Explicit pilot success criteria and stop rules are written.
- Jev is asked for a structured decision on whether to freeze this scope and begin pilot extraction.

## Artifacts produced at CP1
- checkpoints/PHASE_1D_CP1_SCOPE_FREEZE.md (this file)
- docs/PHASE_1D_PILOT_EXTRACTION_PLAN.md
- .github/workflows/phase1d.yml (skeleton)

## Next gate
After Jev promotion of this scope, proceed to CP2 (data collection & provenance freeze) on the Wefunder pilot only.
