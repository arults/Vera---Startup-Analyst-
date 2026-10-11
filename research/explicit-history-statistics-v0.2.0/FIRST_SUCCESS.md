# First-qualifying-success CIF, exact-history candidate

**Synthetic-only additive implementation. No empirical data or estimates.**

This successor implements the frozen first-qualifying-success endpoint separately from current-state occupancy. One index-qualified success remains a first success after subsequent closure; an unknown-value acquisition before success competes rather than becoming success. A direct valued success exit is counted once. The first-event competing probability is not the full multistate closure probability: it excludes later closure after success.

## Commands

Python 3.10+, no nonstandard packages:

    python -m unittest discover -s frozen-first-success-candidate-v1 -p 'test_*.py' -v

Run from the package's parent, or `python -m unittest -v` inside it. Thirty tests pass, including 800 fully observed first-success landmark checks, 500 rational-matrix occupancy comparisons, malformed histories, ties, first-success then closure, and huge-integer clean rejection.

## Explicit initial-state semantics

`InitialPostPolicy` is mandatory. `REJECT` requires incident event-free entry and rejects an initial POST history. `BASELINE_QUALIFIED` is an explicit caller declaration that initial POST means already qualified relative to this index-round endpoint at entry. It reports:

- baseline-qualified fraction;
- incident-success CIF contribution after entry, with denominator/mass normalized to all supplied rounds, not just the initially event-free subset;
- ever-qualified probability, the sum of those two quantities.

Baseline prevalence is never labeled incident CIF. A PRE→success transition at time zero is an incident time-zero event, distinct from baseline POST. An initial POST→terminal-success transition is not another first success. The component does not infer whether prior company success qualifies relative to a later index round, or whether a new clock resets a success state.

A PRE history's first transition is a target if it enters POST or terminal success, otherwise a competing terminal event. All later transitions remain validated but do not erase its first event. Events occur before tied censors, consistently with the occupancy component.

## Occupancy successor changes

The included occupancy engine differs from the earlier synthetic candidate in two bounded ways:

1. Arbitrarily large Python integers that cannot be represented by the finite-number check fail cleanly with ValueError, rather than leaking OverflowError.
2. All five explicit initial states are supported, including terminal initial mass. Terminal initial states have no outgoing transitions. This avoids silently excluding non-independent-at-entry funded rounds from the original Layer-B target.

The first-success API cannot infer prior success from terminal occupancy alone. It therefore rejects terminal initial states pending endpoint-specific baseline history; it does not drop those rounds or modify the original target. A closure or unknown-value acquisition at entry could have followed earlier success, so neither “never succeeded” nor “already succeeded” is implied. Occupancy remains available for such explicitly supplied terminal state histories.

## Support and remaining obligations

Each first-success landmark returns its numerical event-free-risk support diagnostics. Complete modeled first-event absorption is distinct from an unobserved residual tail. These diagnostics do not establish source adequacy, noninformative censoring, or population identification. No point-only empirical reporting adapter is provided.

The first-success component does not resolve actual source/history mappings, interval-dated events, origin or observation semantics. It does not implement primary bootstrap intervals, analytic intervals, lost-follow-up assignment sensitivity, graph comparisons, or an empirical release. Those frozen obligations remain where applicable. Ordinary implementation of the frozen target does not require a new target-selection permission.

All records in tests are synthetic. No private records, raw research context, external calls, source admission, canonical edits or promoted rates are included. The module's correct conditional arithmetic is not full scientific or Phase 1D completion.
