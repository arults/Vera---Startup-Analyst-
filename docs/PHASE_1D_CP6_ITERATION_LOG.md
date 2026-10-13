# Phase 1D CP6 — Append-only correction log

2026-10-09; baseline 122c869911d838a8ed77e71b893b8e0104a1dd95. This adds to, and does not rewrite, docs/ITERATION_LOG.md or CP5.

## Recovery and correction

Conversation summary was stale. Live branch had already reached a limited v0.6.0 execution package. Reading actual source exposed a faulty plateau declaration, despite a successful scientific workflow. Jev selected targeted stop-gate repair rather than restarting or discarding the dataset.

## Build → critique → rebuild

1. Built a distinct evidence-backed research stop gate. 22 tests passed.
2. Critique found relabeled/reused execution and synthetic evidence loopholes. Bound execution/verification to receipts, rejected synthetic/replay metadata, required unique execution hashes. 32 tests passed.
3. Critique found removal of the same labels or source references from all snapshots could hide missingness. Froze expected label/source schemas. 35 tests passed.
4. Independent numerical challenge implementation compared 10,000 seeded random pairs against an explicit no-regression/threshold oracle; no discrepancies.
5. A different challenge removed each required receipt field and evidence reference field across both rounds (38 mutations); all failed closed.
6. Retired legacy writer and acceptance path, retained safe ID compatibility, added four regression tests: 39 local tests passed.

## Rejected approaches

- Accept prior Jev approval as a substitute for checking actual workflow behavior.
- Count three no-op snapshots as two research-feedback iterations.
- Count deterioration as plateau merely because no positive gain exceeded 0.05.
- Reuse an execution under a new alternative ID.
- Allow test fixtures or replay metadata to establish empirical research completion.
- Overwrite old snapshot files on rerun.
- Replace incomplete historical denominators with current visible listings.
- Claim full CI or new empirical observations from local engineering checks.

## Preservation and scope

Original SKILLS blob is retained under evidence/phase1d_cp6/SKILLS_pre_audit.md. All raw data, prior checkpoint snapshots and historical Jev decisions are unchanged. No main merge or empirical-prior promotion. The code repair's checks do not prove global research exhaustion; new admissible evidence remains necessary.
