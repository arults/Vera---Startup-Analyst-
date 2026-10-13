# Operating uncertainty numerical-guard checkpoint

Prepared 2026-10-12. This adds a separately imported research component; it does
not switch existing empirical callers, qualify real histories or promote a rate.

## Demonstrated implementation defects

Five synthetic companies that remain operating after PRE-to-POST transitions
have exact occupancy one. Floating-point accumulation in the frozen reporter
can produce a raw point slightly above one, a percentile interval extending
above one, and an inverted analytic interval. A second example has each company
contribute one operating round and one closure round: every company resample
has exact occupancy one half, yet machine-sized differences produce apparent
bootstrap variation and a nonzero analytic standard error.

The new [numerical-guard package](../research/operating-uncertainty-guards-v0.1.0/README.md)
delegates to the frozen estimator, sampler and analytic derivative. It retains
raw points, draws, identities, gradients and covariance. It withholds uncertainty
that is indistinguishable at the disclosed 64-ulp absolute probability tolerance,
preserves existing unsupported/undefined/not-run priorities, and clips final
percentile bounds only after domain checks. Gross invalid values raise rather
than becoming plausible probabilities. The absolute tolerance may withhold
genuinely nonzero machine-scale variation; it does not prove exact zero variance.

## Verification and review

- Pinned dependency validator: 93 passed, comprising 74 existing frozen tests
  and 19 new guard tests. The new tests include 90 exact-rational history/horizon
  comparisons and 1,080 separately reconstructed company resamples.
- Isolated relocation, unchanged source bytes/no bytecode, and tampered/missing
  dependency controls: three subprocess tests passed. Their internal rerun is
  not extra independent test coverage.
- Eight separately authored independent controls passed. They reproduce the
  defects, verify raw evidence preservation, and cover ordinary intervals,
  support/not-run/exact-degeneracy precedence and generator inputs.
- All 29 originally recovered pinned source/document files remained unchanged.
  Ten frozen source/test dependencies are checked by Git blob hash before import.

The first exact-code JEV 1.13.0 review selected PASS with weak support
(PASS 0.58; HOLD 0.41; confidence 0.37), while isolated dependency validation was
unfinished. After the rational-oracle, fail-closed injection, dependency and
isolation checks were completed and independently rerun, a targeted second
review selected PASS (0.99; HOLD 0.01; confidence 0.98). It also explicitly
rejected the claim that existing empirical callers were repaired or calibrated
(NO 1.0). These are model-review outputs, not empirical probabilities or
validation of nominal interval coverage. Full receipts are retained separately.

Reviewed guard source SHA-256:
`0f71a80f29e5afc0c9cc719fdf7269396734da59333250f4d01e9f0aae87dfd2`.
The package manifest binds its candidate files; its frozen dependency reference
is repository commit `de1f7b9b375618cf92fe12339e420cf07a0f48f1`.

## Adoption boundary

Consumers must explicitly import the new component. Existing imports of the
frozen statistical reporter retain the documented numerical defect; no
automatic caller migration is included. A caller migration needs its own
matched-input integration review, without changing source or cohort semantics.
Remote CI must be checked against the exact publication commit separately.

Scientific Phase 1D, evidence-to-history qualification, endpoint-specific
observation, population completeness and calibration remain open. No active
analyst plugin, empirical ledger, production admission or numerical prior was
changed by this checkpoint.
