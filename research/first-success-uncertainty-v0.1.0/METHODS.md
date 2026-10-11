# First-success endpoint uncertainty v0.1.0

Status: additive, synthetic-verified component candidate. This is **not canonical empirical adoption**, a new source adapter, a cohort result, a replacement of frozen Phase 1C/1D assumptions, or a new investment prior.

This module closes the first-success uncertainty/reporting gap in the existing explicit-history statistics component. It leaves all `explicit-history-statistics-v0.2.0` files unchanged. It supplies a whole-company percentile bootstrap and a **first-event-specific analytic IJ diagnostic**, with a matched comparison report. The operating-occupancy IJ is not repurposed or renamed.

## Dependencies and use

Python 3.10 or newer, standard library only. Put the existing `research/explicit-history-statistics-v0.2.0` directory on `PYTHONPATH` alongside this directory. This small additive directory intentionally does not copy or replace the full v0.2.0 package, including its separate lost-follow-up sensitivity modules.

Example from repository root:

```sh
PYTHONPATH=research/explicit-history-statistics-v0.2.0:research/first-success-uncertainty-v0.1.0 \
  python -m unittest discover -s research/first-success-uncertainty-v0.1.0 -v
```

```python
from first_success import InitialPostPolicy
from first_success_uncertainty import SuccessEndpoint, first_success_uncertainty_report

result = first_success_uncertainty_report(
    reviewed_exact_histories,
    36,
    InitialPostPolicy.BASELINE_QUALIFIED,
    endpoint=SuccessEndpoint.INCIDENT,
    disagreement_threshold=0.05,  # explicit reporting choice, not an adopted cutoff
    n_boot=1000,
    seed=20261011,
    confidence_level=0.95,
)
```

`first_success_cluster_bootstrap` and `first_success_ij_diagnostic` are also available separately. All APIs require an explicit endpoint enum and initial-POST interpretation. Public functions materialize supplied history iterables once. Results are frozen dataclasses, serializable via `dataclasses.asdict` and `json.dumps`.

### Exact dependency binding

The following existing files were checked against commit `f36fb8109786718ee2402447cf86e934e2b8cc2a` in `arults/Vera---Startup-Analyst-`, under `research/explicit-history-statistics-v0.2.0/`:

| File | Git blob SHA-1 |
| --- | --- |
| `aj_explicit_history.py` | `a71beeaed288f89d0886f4d3fd4dd30c0089cbc4` |
| `first_success.py` | `72024eb253c8b5dad9af85e98c87f3edb4c79e99` |
| `aj_ij.py` | `b7044aae48b3d315ed94c3a8af8676659f3a0aaa` |
| `statistical_reporting.py` | `82c8568c42aa5f9e3926a37236c14e2c52d661a9` |

`statistical_reporting.py` provides the draw record, quantile convention and configuration validation; its existing import of `aj_ij.py` remains a transitive dependency. The new analytic calculation does not call `aj_ij_diagnostic`.

## Endpoint contract

Every economic round contributes equally to the point target. Company IDs define dependence clusters, not equal-company point weights. A bootstrap draw samples the original number of companies with replacement and includes **every round** of every selected occurrence; therefore the number of rounds and all-round denominator can change across draws.

- `SuccessEndpoint.INCIDENT`: unconditional first-success CIF contributed **after entry**, with all eligible entry rounds in the denominator. With baseline-qualified rounds present, this is not incidence conditional on being initially event-free.
- `SuccessEndpoint.EVER_QUALIFIED`: baseline-qualified fraction plus that incident contribution. It is not an incident CIF.
- Under `InitialPostPolicy.REJECT`, initial POST histories remain invalid. Under `BASELINE_QUALIFIED`, they contribute baseline qualification and never an incident success event.
- PRE→POST and PRE→SUCCESS_EXIT are first successes. PRE→CLOSURE and PRE→ACQUISITION_UNKNOWN are competing first events. Later transitions after first success do not erase that success or create another one.
- Terminal-at-entry histories still fail with the existing endpoint-specific prior-success-history error. This component does not guess whether they succeeded before entry.
- Exact events tied with censors use the event-before-censor convention. Time-zero incident success remains distinct from baseline qualification.
- Exact-time, common-origin, no-left-truncation and reviewed history requirements are unchanged. Censoring assumptions and empirical source adequacy are not established by these numerical routines.

## Analytic derivation and scope

The diagnostic differentiates the same weighted first-event product integral as the scalar endpoint. The derivation below defines the method; numerical checks include independent weighted-reference finite differences in review.

Let `w_j` be a round weight, `W=sum(w_j)`, `b_j` the baseline-qualified indicator and `i_j=1-b_j`. Initial masses are `B=sum(w_j*b_j)/W` and `F=sum(w_j*i_j)/W`. Incident success `S` and competing first-event mass `C` start at zero. At unit weights, `dB/dw_j=(b_j-B)/N` and `dF/dw_j=(i_j-F)/N`.

At each first-event time, let `Y=sum(w_j*r_j)`, `D_s=sum(w_j*s_j)`, and `D_c=sum(w_j*c_j)`. The indicator `r_j` includes first-event-free rounds with observed endpoint at or after that time; baseline-qualified rounds are excluded. `s_j` and `c_j` indicate the two event causes at that time. Define `q_s=D_s/Y`, `q_c=D_c/Y`. Update simultaneously from pre-event quantities:

- `S_new = S + F*q_s`
- `C_new = C + F*q_c`
- `F_new = F*(1-q_s-q_c)`

Each hazard derivative is `(event_indicator_j*Y - event_count*r_j)/Y^2`. Apply the product rule to the three updates, always using pre-event `F` and its gradient. `B` stays fixed through these updates; the ever-qualified gradient is the sum of baseline and incident gradients. The implementation uses `(D_s+D_c)/Y` for full-depletion arithmetic.

The round derivative for a selected endpoint is aggregated within company: `I_g=sum(j in g, dtheta/dw_j)`. The uncorrected cluster IJ variance is `sum_g(I_g^2)`. Covariance between the exposed baseline, incident, ever-qualified, competing and event-free components is the corresponding sum of company-score outer products. No finite-sample factor is applied. No alternative centering or operating-state occupancy score is substituted.

The reported normal interval is a **pointwise delta-method diagnostic**, bounded to the probability scale, not a guarantee of finite-sample or nominal coverage. It is withheld for unsupported first-event risk, fewer than two companies, probability boundaries, and zero or numerically negligible IJ standard error. It makes no simultaneous-band, calibration or empirical readiness claim.

## Reporting gates

All requested bootstrap draws are retained with selected source companies, source rounds, raw mathematical value, support status and any failure reason. No successful or supported subset supplies an interval. `n_boot=0` or fewer than two companies produces a distinct NOT_RUN disposition and unknown (`None`) draw/degeneracy diagnostics. A failed draw remains in the report, and its undefined value blocks a primary interval.

Primary intervals are withheld when the full sample is unsupported, any draw is undefined or unsupported, fewer than two draws were generated, or the distribution is exactly or numerically degenerate. The selected support policy is conservative and explicit; it is not represented as an empirically adopted support threshold. Complete first-event absorption is supported even past last observation; unresolved event-free mass beyond risk support is not.

Percentiles use linear interpolation at `(B-1)*q`. The primary interval has no nominal coverage guarantee. The matched comparison wrapper constructs both calculations from the same histories, horizon, endpoint, initial policy and confidence level. It compares endpoints only when both intervals exist. Missing comparisons return `None`, never a false “agreement.” The user-supplied maximum-endpoint-difference threshold is an explicit reporting setting; agreement does not establish validity.

### Floating-point boundary handling

The frozen scalar can accumulate machine rounding, for example `1.0000000000000002` after complete success. Raw points and raw draw values remain visible; they are not silently replaced. New reports expose `probability_roundoff_tolerance = 64*math.ulp(1.0)` (approximately `1.42e-14`). This is a numerical safety guard, not an inferential cutoff or estimated error bound.

The analytic diagnostic withholds when the point is within this tolerance of either probability boundary or its standard error is at most this tolerance. Bootstrap exact equality is still separately recorded as `degenerate_distribution`; `numerically_degenerate_distribution` additionally detects a draw range at most this tolerance. Both are unknown if any draw is undefined. Numerically constant distributions cannot produce a false informative interval. Values outside [0,1] by more than the tolerance are undefined; otherwise any tiny quantile-boundary overshoot is clipped to [0,1] with an explicit report label. Finite precision may conservatively withhold very small but genuine variation; this is intentional and is not interpreted as certainty.

## Verification actually executed

The supplied new test module currently contains 30 tests. Together with the copied, unchanged four-file baseline test set, 81 tests pass: 51 baseline + 30 new. The separate 23 lost-follow-up sensitivity tests are **not** included in that local count. No canonical empirical cohort replay or adoption is claimed here.

Tests cover distinct target definitions, hand values and scores, company aggregation, multiple-round/unequal-size clusters, source-ID colons, all-draw retention, deterministic resampling, order invariance, tied causes/censors, time-zero events, initial terminal ambiguity, later closure after success, unsupported original/resampled tails, complete absorption, no-event and baseline-only degeneracy, not-run and undefined draws, matched comparisons, strict threshold behavior, extreme valid confidence levels, serialization, generators, input validation and floating-point full-success boundaries.

Verification commands used on the portable workspace:

```sh
python -m unittest discover -v
python -m py_compile first_success_uncertainty.py test_first_success_uncertainty.py
```

Independent review results and exact test totals should be attached separately rather than inferred from this implementation's own tests. No private entity ledger, prior results or source data are embedded in this package.
