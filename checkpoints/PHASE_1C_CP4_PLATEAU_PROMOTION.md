# Phase 1C — Checkpoint 4: Plateau & Framework Promotion

Date: 2026-10-08
Status: **COMPLETE — Vera v0.5.0 structural execution framework**

## Closure
Phase 1C built the executable multi-platform calibration framework for:
- Wefunder
- StartEngine
- Crowdcube
- Republic US
- Republic Europe
- offering cohorts 2020–2025

It intentionally did **not** collect the full real dataset and did **not** compute final platform/field outcome rates.

## Verified framework
- 39 final typed D01–D39 decision nodes.
- Two-layer cohort architecture.
- Company-round schema and five platform source adapters.
- Provenance capture + deterministic extraction-manifest hashing.
- High-precision identity resolution, cross-platform candidate queue and QA audit.
- Same-round co-host and NEXT_ROUND graph.
- Native-only vs graph-aware bias reporting.
- Typed survival/success/closure/acquisition-value-unknown states.
- Aalen–Johansen state occupancy and success/closure CIF primitives.
- Company-cluster bootstrap + analytic diagnostic intervals.
- RQ1 low-information reporting and RQ2 field-cell/pooling gates.
- Adjacent-year pooling that cannot silently cross the 2023/2024 maturity boundary.
- Structured result contract requiring platform-observed label, censoring, ascertainment and support horizon.
- Scope guard preventing full dataset/final rates during Phase 1C.

## Deterministic verification
GitHub Actions run 37776384631:
- 45/45 tests PASS.
- 25/25 Phase 1C deterministic gates PASS.
- overall Phase 1C gate PASS.

Phase 1B regression run 37776384486: PASS.

## Jev build loop
Eight implementation-verifier rounds were run. Material feedback caused four rebuilds:
1. explicit competing-risk estimands;
2. platform source adapters/provenance;
3. identity candidate/review pipeline;
4. pooling/report contracts;
then deterministic-verifier hardening.

Round 6 found no material code gap and selected final documentation with probability 1.00; material design-node flip = none with probability 1.00.

## Plateau
Round 7:
- plateau vs round 6: yes probability 0.77;
- no design-node flip: probability 0.99.

Round 8:
- plateau vs round 7: yes probability 0.86;
- no design-node flip: probability 0.96.

Two consecutive plateau rounds satisfy the user-defined stop rule.

## Promotion boundary
v0.5.0 promotes the **framework**, not empirical multi-platform rates.
The existing v0.4.0 Wefunder 2020 limited reference class remains the only promoted empirical survival prior until the later execution phase gathers and verifies the multi-platform cohorts.
