# SKILLS.md — Vera operational research memory

Version: 0.3.5 / Phase 1B CP1
Date: 2026-10-08

## Current milestone
SEC cohort reconstruction -> denominator freeze -> dated outcomes/censoring -> Kaplan-Meier -> independent Verifier -> Jev promotion gate.

## Non-negotiables
- Never promote a remembered count without an immutable row manifest and source evidence.
- Never convert missing evidence into survival.
- Preserve failed, superseded and rejected approaches in docs/ITERATION_LOG.md.
- Current/promoted empirical files contain only Verifier-passing claims.
- Save CP1 rules/repo, CP2 denominator, CP3 outcomes+KM, CP4 final promotion as durable checkpoints.

## Historical state
A prior session reported 42 funded companies for the 2020 Wefunder cohort. The exact row manifest was not durably preserved. Treat 42 as HISTORICAL_CLAIM_NOT_PROMOTED until reconstructed independently.

## Cohort
Wefunder Portal LLC; CIK 0001670254; SEC portal file 007-00033. Anchor to earliest Form C in 2020; key by issuer CIK + SEC offering file number; consolidate amendments; exclude final withdrawals; primary funded inclusion requires direct SEC successful-close/positive-proceeds evidence.

## Survival
Time zero = confirmed funding close. Failures are shutdown/dissolution/bankruptcy/liquidation/clearly ceased operations. Acquisition is non-failure terminal censoring. Public listing gets primary censor-at-listing plus sensitivity continuation. Unknown status is censored at last independently confirmed active date. Cutoff 2026-10-08.

## Current status
CP1 PASS. CP2 PASS / FROZEN. The primary 2020 Wefunder funded denominator is 42 offerings, independently reconstructed from 360 initial 2020 Wefunder Form C offerings; 43 had any C-U and one non-success C-U (T4L) was excluded. Manifest SHA-256: 62468cea323ed6d2732df90cbe5ced04990db907cf908e4939b4128a302f78c8.

Independent GitHub verifier run 37750379057: 8/8 tests PASS and D01-D08 PASS. Jev chose frozen_primary_denominator with probability 0.95 / confidence 0.92; freeze yes probability 0.79; mirror use acceptable probability 0.80; proceed to outcomes probability 0.78.

CP3 outcomes + Kaplan-Meier IN PROGRESS. No survival prior is promoted yet.

## Research-input sources
- `docs/WEFUNDER_JEV_RESEARCH_INPUT.md`: reusable diligence/model-design learnings from live Wefunder + JEV analyses. Treat as a provenance-tagged research memo, not an empirical prior. Re-verify company-specific claims against current sources before use; no raw JEV probability is promoted without calibration/Verifier/JEV gates.
