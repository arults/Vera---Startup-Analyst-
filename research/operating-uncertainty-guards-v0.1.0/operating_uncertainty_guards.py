"""Additive numerical guards for synthetic explicit-history operating uncertainty.

The frozen estimator, company draws, scores and raw values are unchanged. The
64-ulp tolerance is a floating-point reporting guard, not a scientific cutoff.
"""
from dataclasses import dataclass, fields
from math import isfinite, ulp

from aj_explicit_history import at_horizon
from aj_ij import IJDiagnostic, aj_ij_diagnostic as _frozen_ij
from statistical_reporting import (
    OperatingUncertaintyReport, PrimaryBootstrapReport, _probability,
    operating_cluster_bootstrap as _frozen_bootstrap,
)


PROBABILITY_ROUNDOFF_TOLERANCE = 64 * ulp(1.0)


@dataclass(frozen=True)
class GuardedOperatingBootstrapReport(PrimaryBootstrapReport):
    numerically_degenerate_distribution: bool | None = None
    probability_roundoff_tolerance: float = PROBABILITY_ROUNDOFF_TOLERANCE
    interval_probability_bounds: str = "clip_roundoff_only_to_zero_one_raw_draws_retained"


@dataclass(frozen=True)
class GuardedOperatingIJDiagnostic(IJDiagnostic):
    mathematical_operating_probability: float = 0.0
    probability_roundoff_tolerance: float = PROBABILITY_ROUNDOFF_TOLERANCE


def _fields(report):
    return {field.name: getattr(report, field.name) for field in fields(report)}


def _check_probability(value, label):
    if (not isfinite(value) or value < -PROBABILITY_ROUNDOFF_TOLERANCE
            or value > 1 + PROBABILITY_ROUNDOFF_TOLERANCE):
        raise ValueError(f"{label}_outside_roundoff_probability_bounds")


def operating_cluster_bootstrap(histories, horizon, n_boot=1000, seed=0,
                                confidence_level=.95):
    """Retain the frozen report and draws; guard numerical-only degeneracy.

    Existing unsupported/undefined/NOT_RUN/fewer-replicate dispositions keep
    precedence. An exact constant distribution retains its exact status. Only
    the interval is bounded; raw point and draw values are never rounded away.
    """
    raw = _frozen_bootstrap(tuple(histories), horizon, n_boot, seed, confidence_level)
    _check_probability(raw.point, "operating_point")
    values = [draw.mathematical_value for draw in raw.draws
              if draw.mathematical_value is not None]
    for value in values:
        _check_probability(value, "operating_bootstrap_draw")
    numerical_degenerate = None
    if raw.completed_replicates and raw.undefined_draw_count == 0:
        numerical_degenerate = max(values) - min(values) <= PROBABILITY_ROUNDOFF_TOLERANCE
    updates = _fields(raw)
    if raw.primary_interval is not None:
        if numerical_degenerate:
            updates.update(primary_interval=None,
                           interval_status="WITHHELD_NUMERICALLY_DEGENERATE_BOOTSTRAP_DISTRIBUTION")
        else:
            updates["primary_interval"] = tuple(max(0.0, min(1.0, bound))
                                                 for bound in raw.primary_interval)
    return GuardedOperatingBootstrapReport(**updates,
        numerically_degenerate_distribution=numerical_degenerate)


def aj_ij_diagnostic(histories, horizon, confidence_level=.95):
    """Keep company IJ scores/covariance; withhold boundary roundoff intervals."""
    histories = tuple(histories)
    raw = _frozen_ij(histories, horizon, confidence_level)
    point = at_horizon(histories, horizon).independent_operating_probability
    _check_probability(point, "operating_point")
    updates = _fields(raw)
    if raw.normal_diagnostic_interval is not None and (
            raw.operating_standard_error <= PROBABILITY_ROUNDOFF_TOLERANCE
            or point <= PROBABILITY_ROUNDOFF_TOLERANCE
            or point >= 1 - PROBABILITY_ROUNDOFF_TOLERANCE):
        updates.update(normal_diagnostic_interval=None,
            interval_status="WITHHELD_BOUNDARY_OR_ZERO_IJ_VARIANCE_NOT_INFORMATIVE_COVERAGE")
    return GuardedOperatingIJDiagnostic(**updates,
        mathematical_operating_probability=point)


def operating_uncertainty_report(histories, horizon, *, disagreement_threshold,
                                 n_boot=1000, seed=0, confidence_level=.95):
    """Compare only the matched guarded operating intervals when available."""
    _probability(disagreement_threshold, "disagreement_threshold")
    histories = tuple(histories)
    primary = operating_cluster_bootstrap(histories, horizon, n_boot, seed, confidence_level)
    analytic = aj_ij_diagnostic(histories, horizon, confidence_level)
    p, a = primary.primary_interval, analytic.normal_diagnostic_interval
    if p is None or a is None:
        return OperatingUncertaintyReport(primary, analytic, disagreement_threshold,
            None, None, "NOT_COMPARABLE_INTERVAL_UNAVAILABLE")
    difference = max(abs(p[0] - a[0]), abs(p[1] - a[1]))
    return OperatingUncertaintyReport(primary, analytic, disagreement_threshold,
        difference, difference > disagreement_threshold, "COMPARABLE_MATCHED_OPERATING_ENDPOINT")
