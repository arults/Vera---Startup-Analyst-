# Explicit-history statistical components v0.2.0

Additive implementation of frozen study obligations, independently checked on synthetic histories. These files do not replace the existing empirical caller or promote held observations, population rates or investment priors.

## Run from repository root

    python -I -B -m unittest discover -s research/explicit-history-statistics-v0.2.0 -p 'test_*.py' -v

The unified relocated suite contains **74 tests** across five test modules. Earlier 38, 51 and 23 test reports overlap this suite and must not be added together. The dedicated exact-head workflow executes this command.

## Included

- Explicit initial-state Aalen–Johansen operating occupancy, including terminal initial mass and state-risk diagnostics
- First-success incidence separate from baseline qualification, preserving success after a later closure
- Whole-company bootstrap of the round-weighted operating statistic, every draw retained, with explicit unavailable/degenerate/unsupported statuses
- Company-grouped analytic IJ operating uncertainty and explicitly configured disagreement diagnostics
- Endpoint-specific hypothetical missing-follow-up histories with original records, administrative limits, extraction caps and blocked rows preserved

## Limits

The primary bootstrap and analytic interval reporter currently covers operating occupancy. It does not complete success/closure endpoint uncertainty or all empirical report integration. Source-to-history qualification, populations, date/entry meanings and supported graph comparisons remain separate requirements. Assumed scenario tails are never newly observed support or proven sharp bounds. Mathematical agreement is not a confidence-coverage or calibration guarantee.

IMPLEMENTATION.md, FIRST_SUCCESS.md and LOST_FOLLOWUP_SENSITIVITY.md preserve the source candidates' detailed contracts; any earlier candidate-folder command in them is historical. Use the relocated command above. METHOD_REFERENCE.md links the primary method documentation and states the cross-library verification limit. MANIFEST.json binds the published files.
