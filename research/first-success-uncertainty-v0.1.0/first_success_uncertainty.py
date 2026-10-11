"""Synthetic-only first-success uncertainty for reviewed exact histories.

Equal-round targets; company-cluster bootstrap is primary. The analytic method
is a direct IJ derivative of the FIRST-EVENT product integral, not operating-state
occupancy. Intervals are pointwise diagnostics with no nominal coverage promise.
"""
from dataclasses import dataclass
from enum import Enum
from math import isfinite, sqrt, ulp
from statistics import NormalDist

from aj_explicit_history import resample_company_clusters
from first_success import InitialPostPolicy, first_events, success_at_horizon
from statistical_reporting import BootstrapDraw, _probability, percentile_linear


class SuccessEndpoint(str, Enum):
    INCIDENT = "incident_success_cif"
    EVER_QUALIFIED = "ever_qualified_probability"


# Floating-point guard only; never an empirical support or inference cutoff.
PROBABILITY_ROUNDOFF_TOLERANCE = 64 * ulp(1.0)


COMPONENTS = ("baseline_qualified_fraction", "incident_success_cif",
              "ever_qualified_probability", "competing_cif", "event_free_probability")


@dataclass(frozen=True)
class FirstSuccessIJDiagnostic:
    endpoint: str
    horizon: float
    initial_post_policy: str
    point: float
    mathematical_probabilities: dict[str, float]
    round_gradients: dict[str, dict[str, float]]
    company_gradients: dict[str, dict[str, float]]
    covariance: dict[str, dict[str, float]]
    variance: float
    standard_error: float
    confidence_level: float
    normal_diagnostic_interval: tuple[float, float] | None
    interval_status: str
    numerical_support_status: str
    company_count: int
    finite_sample_correction: str = "none_uncorrected_IJ"
    method: str = "direct_first_event_product_integral_round_weight_derivative_company_aggregation"
    probability_roundoff_tolerance: float = PROBABILITY_ROUNDOFF_TOLERANCE


@dataclass(frozen=True)
class FirstSuccessBootstrapReport:
    endpoint: str
    horizon: float
    initial_post_policy: str
    confidence_level: float
    point: float
    baseline_qualified_fraction: float
    incident_success_cif: float
    ever_qualified_probability: float
    full_sample_support_status: str
    requested_replicates: int
    completed_replicates: int
    seed: int
    company_count: int
    round_count: int
    baseline_qualified_count: int
    incident_risk_count_at_entry: int
    first_success_event_count: int
    competing_event_count: int
    unsupported_draw_count: int | None
    undefined_draw_count: int | None
    degenerate_distribution: bool | None
    numerically_degenerate_distribution: bool | None
    execution_status: str
    interval_status: str
    primary_interval: tuple[float, float] | None
    draws: tuple[BootstrapDraw, ...]
    percentile_convention: str = "linear_interpolation_at_(B-1)*q"
    target_weighting: str = "equal_round_unconditional_all_entry_round_denominator"
    probability_roundoff_tolerance: float = PROBABILITY_ROUNDOFF_TOLERANCE
    interval_probability_bounds: str = "clip_roundoff_only_to_zero_one_raw_draws_retained"


@dataclass(frozen=True)
class FirstSuccessUncertaintyReport:
    primary: FirstSuccessBootstrapReport
    analytic: FirstSuccessIJDiagnostic
    disagreement_threshold: float
    endpoint_max_absolute_difference: float | None
    material_disagreement: bool | None
    comparison_status: str
    comparison_rule: str = "max_absolute_interval_endpoint_difference_strictly_exceeds_threshold"


def _endpoint(endpoint):
    if not isinstance(endpoint, SuccessEndpoint):
        raise ValueError("explicit_success_endpoint_enum_required")
    return endpoint.value


def first_success_ij_diagnostic(histories, horizon, initial_post_policy, *,
                                endpoint, confidence_level=.95):
    """Differentiate baseline mass, free mass, and both first-event hazards.

    At unit round weights, each score is d theta / d w_j. Clusters are companies:
    their scores sum across all rounds, and covariance sums score outer products.
    Censors tied with events remain in the pre-event risk set. Prior successes
    are baseline mass, never incident events. Post-success transitions are ignored.
    """
    name = _endpoint(endpoint)
    _probability(confidence_level, "confidence_level", strict=True)
    histories = tuple(histories)
    landmark = success_at_horizon(histories, horizon, initial_post_policy)
    events = sorted(first_events(histories, initial_post_policy), key=lambda e: e.round_id)
    n = len(events)
    baseline_indicators = [int(e.cause == "baseline_qualified") for e in events]
    baseline = sum(baseline_indicators) / n
    free = 1 - baseline
    db = [(v - baseline) / n for v in baseline_indicators]
    df = [-v for v in db]
    success = competing = 0.0
    ds = [0.0] * n
    dc = [0.0] * n
    times = sorted({e.time for e in events if e.cause in ("success", "competing")
                    and e.time <= horizon})
    for t in times:
        risk = [int(e.cause != "baseline_qualified" and e.time >= t) for e in events]
        target = [int(e.time == t and e.cause == "success") for e in events]
        other = [int(e.time == t and e.cause == "competing") for e in events]
        y, d, c = sum(risk), sum(target), sum(other)
        qs, qc = d / y, c / y
        dqs = [(target[j] * y - d * risk[j]) / (y * y) for j in range(n)]
        dqc = [(other[j] * y - c * risk[j]) / (y * y) for j in range(n)]
        # Every derivative uses the pre-event mass and gradient.
        ds = [ds[j] + df[j] * qs + free * dqs[j] for j in range(n)]
        dc = [dc[j] + df[j] * qc + free * dqc[j] for j in range(n)]
        df = [df[j] * (1 - (d + c) / y) - free * (dqs[j] + dqc[j]) for j in range(n)]
        success += free * qs
        competing += free * qc
        free *= 1 - (d + c) / y
    values = dict(zip(COMPONENTS, (baseline, success, baseline + success, competing, free)))
    gradients = dict(zip(COMPONENTS, (db, ds, [db[j] + ds[j] for j in range(n)], dc, df)))
    rounds = {e.round_id: {k: gradients[k][j] for k in COMPONENTS} for j, e in enumerate(events)}
    companies = {}
    for j, e in enumerate(events):
        g = companies.setdefault(e.company_id, dict.fromkeys(COMPONENTS, 0.0))
        for k in COMPONENTS:
            g[k] += gradients[k][j]
    covariance = {a: {b: sum(g[a] * g[b] for g in companies.values()) for b in COMPONENTS}
                  for a in COMPONENTS}
    variance = covariance[name][name]
    se = sqrt(variance)
    point = getattr(landmark, name)
    interval = None
    if "UNSUPPORTED" in landmark.numerical_support_status:
        status = "WITHHELD_NUMERICAL_FIRST_EVENT_RISK_GAP"
    elif len(companies) < 2:
        status = "WITHHELD_FEWER_THAN_TWO_COMPANY_CLUSTERS"
    elif (se <= PROBABILITY_ROUNDOFF_TOLERANCE or
          point <= PROBABILITY_ROUNDOFF_TOLERANCE or
          point >= 1 - PROBABILITY_ROUNDOFF_TOLERANCE):
        status = "WITHHELD_BOUNDARY_OR_ZERO_IJ_VARIANCE_NOT_INFORMATIVE_COVERAGE"
    else:
        z = -NormalDist().inv_cdf((1 - confidence_level) / 2)
        interval = (max(0.0, point - z * se), min(1.0, point + z * se))
        status = "NORMAL_DELTA_DIAGNOSTIC_ONLY"
    return FirstSuccessIJDiagnostic(name, horizon, initial_post_policy.value, point, values,
        rounds, companies, covariance, variance, se, confidence_level, interval, status,
        landmark.numerical_support_status, len(companies))


def first_success_cluster_bootstrap(histories, horizon, initial_post_policy, *, endpoint,
                                     n_boot=1000, seed=0, confidence_level=.95):
    name = _endpoint(endpoint)
    _probability(confidence_level, "confidence_level", strict=True)
    if isinstance(n_boot, bool) or not isinstance(n_boot, int) or n_boot < 0:
        raise ValueError("nonnegative_integer_replicate_count_required")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("integer_seed_required")
    histories = tuple(histories)
    point = success_at_horizon(histories, horizon, initial_post_policy)
    events = first_events(histories, initial_post_policy)
    companies = len({h.company_id for h in histories})
    metadata = dict(endpoint=name, horizon=horizon, initial_post_policy=initial_post_policy.value,
        confidence_level=confidence_level, point=getattr(point, name),
        baseline_qualified_fraction=point.baseline_qualified_fraction,
        incident_success_cif=point.incident_success_cif,
        ever_qualified_probability=point.ever_qualified_probability,
        full_sample_support_status=point.numerical_support_status,
        requested_replicates=n_boot, seed=seed, company_count=companies, round_count=len(histories),
        baseline_qualified_count=sum(e.cause == "baseline_qualified" for e in events),
        incident_risk_count_at_entry=point.incident_risk_count_at_entry,
        first_success_event_count=sum(e.cause == "success" and e.time <= horizon for e in events),
        competing_event_count=sum(e.cause == "competing" and e.time <= horizon for e in events))
    if n_boot == 0 or companies < 2:
        status = "NOT_RUN_ZERO_REPLICATES_REQUESTED" if n_boot == 0 else "NOT_RUN_INSUFFICIENT_COMPANY_CLUSTERS"
        return FirstSuccessBootstrapReport(**metadata, completed_replicates=0,
            unsupported_draw_count=None, undefined_draw_count=None, degenerate_distribution=None,
            numerically_degenerate_distribution=None,
            execution_status=status, interval_status="WITHHELD_BOOTSTRAP_NOT_RUN", primary_interval=None, draws=())
    draws = []
    for index, sample in enumerate(resample_company_clusters(histories, n_boot, seed)):
        picked = {}
        for h in sample:
            occurrence, company = h.company_id.split(":", 1)
            picked[int(occurrence)] = company
        ids = tuple(h.round_id.split(":", 1)[1] for h in sample)
        try:
            result = success_at_horizon(sample, horizon, initial_post_policy)
            value = getattr(result, name)
            if not isfinite(value):
                raise ValueError("nonfinite_bootstrap_statistic")
            if value < -PROBABILITY_ROUNDOFF_TOLERANCE or value > 1 + PROBABILITY_ROUNDOFF_TOLERANCE:
                raise ValueError("bootstrap_probability_outside_roundoff_bounds")
            status, reason = result.numerical_support_status, None
        except (ValueError, ArithmeticError) as error:
            value, status = None, "UNDEFINED_BOOTSTRAP_STATISTIC"
            reason = f"{type(error).__name__}:{error}"
        draws.append(BootstrapDraw(index, tuple(picked[i] for i in sorted(picked)), ids, value, status, reason))
    undefined = sum(d.mathematical_value is None for d in draws)
    unsupported = sum("UNSUPPORTED" in d.numerical_support_status for d in draws)
    values = [d.mathematical_value for d in draws if d.mathematical_value is not None]
    degenerate = min(values) == max(values) if not undefined else None
    numerical_degenerate = (max(values) - min(values) <= PROBABILITY_ROUNDOFF_TOLERANCE) if not undefined else None
    interval = None
    if "UNSUPPORTED" in point.numerical_support_status:
        status = "WITHHELD_FULL_SAMPLE_FIRST_EVENT_RISK_GAP"
    elif undefined:
        status = "WITHHELD_UNDEFINED_BOOTSTRAP_DRAWS"
    elif unsupported:
        status = "WITHHELD_UNSUPPORTED_BOOTSTRAP_DRAWS"
    elif n_boot < 2:
        status = "WITHHELD_FEWER_THAN_TWO_REPLICATES"
    elif degenerate:
        status = "WITHHELD_DEGENERATE_BOOTSTRAP_DISTRIBUTION"
    elif numerical_degenerate:
        status = "WITHHELD_NUMERICALLY_DEGENERATE_BOOTSTRAP_DISTRIBUTION"
    else:
        alpha = 1 - confidence_level
        interval = tuple(max(0.0, min(1.0, percentile_linear(values, q)))
                         for q in (alpha / 2, 1 - alpha / 2))
        status = "PERCENTILE_BOOTSTRAP_INTERVAL_NO_NOMINAL_COVERAGE_GUARANTEE"
    return FirstSuccessBootstrapReport(**metadata, completed_replicates=len(draws),
        unsupported_draw_count=unsupported, undefined_draw_count=undefined,
        degenerate_distribution=degenerate, numerically_degenerate_distribution=numerical_degenerate, execution_status="RUN_ALL_REQUESTED_DRAWS_RETAINED",
        interval_status=status, primary_interval=interval, draws=tuple(draws))


def first_success_uncertainty_report(histories, horizon, initial_post_policy, *, endpoint,
                                     disagreement_threshold, n_boot=1000, seed=0, confidence_level=.95):
    """Compare only matched first-success target, policy, sample, horizon and level.

    Difference threshold is mandatory reporting configuration, not a validated
    cutoff. Missing intervals produce no comparison; agreement proves no coverage.
    """
    _probability(disagreement_threshold, "disagreement_threshold")
    histories = tuple(histories)
    primary = first_success_cluster_bootstrap(histories, horizon, initial_post_policy,
        endpoint=endpoint, n_boot=n_boot, seed=seed, confidence_level=confidence_level)
    analytic = first_success_ij_diagnostic(histories, horizon, initial_post_policy,
        endpoint=endpoint, confidence_level=confidence_level)
    p, a = primary.primary_interval, analytic.normal_diagnostic_interval
    if p is None or a is None:
        return FirstSuccessUncertaintyReport(primary, analytic, disagreement_threshold,
            None, None, "NOT_COMPARABLE_INTERVAL_UNAVAILABLE")
    difference = max(abs(p[0] - a[0]), abs(p[1] - a[1]))
    return FirstSuccessUncertaintyReport(primary, analytic, disagreement_threshold,
        difference, difference > disagreement_threshold, "COMPARABLE_MATCHED_FIRST_SUCCESS_ENDPOINT")
