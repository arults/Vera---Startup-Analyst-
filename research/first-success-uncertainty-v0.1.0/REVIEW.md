# Independent first-success uncertainty review

Verdict: **PASS, limited to the synthetic exact-history mathematical component.**

Reviewed 2026-10-11. This review does not establish empirical calibration, nominal confidence coverage, source identification, or canonical adoption.

## Reviewed version

- `first_success_uncertainty.py` SHA-256: `1348c6d7850f01d2ffcd502ba2877a5dbc26bcd58405dcc7959233ea05121dbe`
- `test_first_success_uncertainty.py` SHA-256: `2bcc132ed31ed1b17487abacd7f375247fd02a505a48ecbc4706a9b212c0a59d`
- Eight copied pre-existing Python source/test files remained byte-identical to the review's initial baseline; checked with `baseline-sha256.txt`.

## Evidence

- Existing component suite: **81 passed** = 51 pre-existing statistical tests + 30 new first-success uncertainty tests.
- Review-owned suite: **13 passed**, separate from the implementation suite.
- Portable isolated rerun: **94 passed**, the same 81 + 13 tests, not an additional independent count. Python 3.12 standard library only, relocated to a new directory, run from `/tmp` with `PYTHONPATH` removed and Python isolated mode.
- The additional 23 previously published lost-follow-up sensitivity tests were not present in the supplied portable component baseline and were not rerun. No claim of a complete repository-wide test pass is made.
- **960 randomized endpoint/horizon cases** were checked against a separately implemented exact-rational weighted first-event estimator. Both public endpoints, all five scalar components, individual-round finite differences, and whole-company finite differences were checked. Largest observed round-score central-difference discrepancy: **6.25e-12**.
- Known-solution checks: fully observed binary proportion with variance p(1-p)/n; a censored competing-risk fixture with point 3/8 and known scores; unequal company clusters with a known aggregate variance of 1/72.
- **514 bootstrap draws** (257 for each endpoint) were reconstructed independently from Python's seeded random selections, checking selected company occurrences, every constituent source round, unequal resampled round totals, and rational-estimator draw values.

## Findings and disposition

1. Target selection is mandatory and explicit. `incident_success_cif` is the all-entry-round unconditional incident contribution; `ever_qualified_probability` adds the explicitly declared baseline-qualified mass. It is not a conditional CIF among only incident-risk entrants.
2. The new analytic calculation differentiates the first-event product integral, including initial baseline/event-free masses. It does not relabel or reuse operating-occupancy IJ output. Company influence is the sum of round-weight derivatives, and reported covariance is the uncorrected sum of company score outer products.
3. First success persists after later closure or acquisition. Initial terminal histories are rejected with the existing endpoint-specific prior-success-history requirement; no ambiguous entry rows are silently omitted.
4. Company bootstrap resamples whole company clusters, preserving every round and distinguishing repeated company occurrences. Undefined and unsupported draws remain visible. Any such draw prevents an interval; no supported subset is cherry-picked.
5. Zero requested replicates, empty input, one cluster, repeated company IDs, duplicate economic round IDs, tied event/censor times, censor tails, complete modeled absorption, baseline qualification, and explicit endpoint/policy behavior were exercised.
6. Combined reports match target, entry policy, histories, horizon, and confidence level by construction. Both available-interval and unavailable-interval branches were checked; disagreement is a reporting diagnostic only.
7. Two reproducible numerical issues found during review were corrected and retested:
   - A valid confidence level immediately below 1 previously rounded the upper inverse-normal argument to 1. Stable lower-tail evaluation now handles it.
   - Five sequential certain-success events previously generated raw scalar 1.0000000000000002, an inverted normal interval, and a spurious nondegenerate percentile interval. The new uncertainty layer now exposes a 64-ulp probability tolerance, withholds boundary/numerically-zero IJ diagnostics, distinguishes exact from numerical bootstrap degeneracy, and retains raw draws. Percentile bound clipping is limited to machine-scale roundoff already checked on all draws. Frozen scalar artifacts were not changed.

## Limits

This is an implementation and numerical-consistency review of prepared exact histories. It does not validate real-world company identities, qualify outcomes from source material, justify censoring assumptions, establish small-cluster adequacy, estimate coverage through simulation, or authorize adoption into an empirical cohort. The pointwise normal interval remains a diagnostic; percentile bootstrap intervals explicitly carry no nominal-coverage guarantee. Declared numerical tolerances are conservative reporting guards, not scientific support thresholds.

No external service reads or writes were used. No private code or data were shared with JEV or any third party.

## Reproduction

Place the five implementation/dependency modules, five implementation test modules, and the three review Python files in one directory. From any other working directory, run:

`env -u PYTHONPATH python -I -m unittest discover -s /absolute/path/to/directory -v`

The review reference and fixture generator use only Python's standard library and the public prepared-history input types. They do not call production first-event extraction, first-success estimation, derivative, bootstrap, or comparison routines to produce expected mathematical values.
