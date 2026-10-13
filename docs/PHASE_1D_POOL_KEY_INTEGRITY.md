# RQ2 offering-year key integrity safeguard

Prepared 2026-10-12 against repository commit
`de1f7b9b375618cf92fe12339e420cf07a0f48f1`.

## Demonstrated failures

The previous `pool_adjacent_years` accepted an out-of-scope target year. A
synthetic target of 2019 with a qualifying 2020 cell returned a reportable
2020 pool. The same implementation constructed its year map with a dictionary
comprehension: duplicate year cells silently kept the last cell. Reversing two
conflicting synthetic 2022 cells changed a reportable result into suppression.

These are demonstrated malformed-input failures. No evidence in this change
establishes that an existing empirical report used either malformed input.

## Scoped correction

- Require integer offering-year keys in the frozen 2020–2025 scope. Boolean,
  string and floating-point years are rejected instead of being coerced.
- Validate the target and every supplied cell before selecting a maturity block
  or returning a successful pool.
- Reject repeated year cells, including identical duplicates and duplicates in
  a different maturity block. The caller must resolve their identity; this
  function does not aggregate, discard or select one.
- Preserve all valid unique-cell pooling results, target-neighbor order, count
  semantics, thresholds and the 2023/2024 maturity boundary.

The API already declares `year: int`; the integer-only guard intentionally
rejects previously tolerated `2022.0`. Integer-valued real counts continue to be
accepted under the existing count contract. No source evidence, offering-year
assignment, population, outcome clock, estimator, admission or numerical-prior
promotion is changed.

## Verification

From repository root:

    python -B -m unittest discover -s tests -p 'test_reporting*.py' -v
    python -B -m unittest discover -s tests -p test_phase1c_reporting_graph.py -v

The reporting discovery ran 58 tests: 57 passed and one optional archived-ledger
replay was skipped because its three explicitly required inputs were not
supplied. The 58 include 11 new key-integrity regressions. Six existing
reporting/graph tests also passed. This is not a full-repository or remote-CI
claim. The existing bootstrap-reporting workflow already selects the new test
file and changed source path.

A separate deterministic 6,000-case synthetic differential check found no
change in valid unique-cell outputs. An independent worker verified the exact
base Git blob and candidate bytes, then checked 9,216 valid-input base/candidate
comparisons, 252 duplicate placements/targets and 70 invalid-year/type cases.
These case counts describe software checks, not independent companies or
empirical observations.

The independent reviewer accepted the scoped candidate. A separate JEV 1.13.0
exact-code assessment selected PASS (choice probability 0.83; confidence 0.74;
HOLD 0.16; REJECT 0.01). These are model-review outputs, not investment or
scientific probabilities. Raw requests, results and runnable differential
evidence are retained in the local review bundle; no company data was supplied
in that model call.

Source before correction: Git blob
`cc02b7cbd227fed18492f7c68dbf239af378844a`.
Reviewed source after correction: SHA-256
`588acd09c7b8dda200e459b6e055705e65e15b2758345282f5f4a93ac4583aff`.

Scientific Phase 1D remains incomplete. This guard does not establish source
qualification, research plateau, cohort completeness, empirical accuracy,
nominal interval coverage or return-probability calibration. The active analyst
plugin remains unchanged.
