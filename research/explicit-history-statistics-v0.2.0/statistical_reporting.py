"""Company-cluster percentile bootstrap and matched analytic diagnostic report.

All generated draws are retained. A withheld interval is a reporting disposition,
not a new inferential coverage claim. No actual source adapter is included.
"""
from dataclasses import dataclass
from math import floor, isfinite
from aj_explicit_history import TERMINAL, at_horizon, resample_company_clusters
from aj_ij import IJDiagnostic, aj_ij_diagnostic


@dataclass(frozen=True)
class BootstrapDraw:
    index: int
    sampled_company_ids: tuple[str,...]
    source_round_ids: tuple[str,...]
    mathematical_value: float | None
    numerical_support_status: str
    failure_reason: str | None


@dataclass(frozen=True)
class PrimaryBootstrapReport:
    endpoint: str
    horizon: float
    confidence_level: float
    point: float
    full_sample_support_status: str
    requested_replicates: int
    completed_replicates: int
    seed: int
    company_count: int
    round_count: int
    transition_count: int
    terminal_transition_count: int
    initial_terminal_count: int
    zero_terminal_transitions: bool
    unsupported_draw_count: int | None
    undefined_draw_count: int | None
    degenerate_distribution: bool | None
    execution_status: str
    interval_status: str
    primary_interval: tuple[float,float] | None
    draws: tuple[BootstrapDraw,...]
    percentile_convention: str = "linear_interpolation_at_(B-1)*q"


@dataclass(frozen=True)
class OperatingUncertaintyReport:
    primary: PrimaryBootstrapReport
    analytic: IJDiagnostic
    disagreement_threshold: float
    endpoint_max_absolute_difference: float | None
    material_disagreement: bool | None
    comparison_status: str
    comparison_rule: str = "max_absolute_interval_endpoint_difference_strictly_exceeds_threshold"


def _probability(value,label,strict=False):
    valid_type = not isinstance(value,bool) and isinstance(value,(int,float))
    if not valid_type or not (0 < value < 1 if strict else 0 <= value <= 1):
        raise ValueError(f"invalid_{label}")


def percentile_linear(values,q):
    """Empirical quantile with position (B-1)q and linear interpolation."""
    _probability(q,"quantile")
    if not values:
        raise ValueError("empty_quantile_sample")
    for x in values:
        try:
            valid = not isinstance(x,bool) and isinstance(x,(int,float)) and isfinite(x)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("nonfinite_quantile_sample")
    xs = sorted(values)
    pos = (len(xs)-1)*q
    low = floor(pos)
    high = min(len(xs)-1,low+1)
    fraction = pos-low
    return (1-fraction)*xs[low]+fraction*xs[high]


def operating_cluster_bootstrap(histories,horizon,n_boot=1000,seed=0,confidence_level=.95):
    _probability(confidence_level,"confidence_level",strict=True)
    if isinstance(n_boot,bool) or not isinstance(n_boot,int) or n_boot < 0:
        raise ValueError("nonnegative_integer_replicate_count_required")
    if isinstance(seed,bool) or not isinstance(seed,int):
        raise ValueError("integer_seed_required")
    point = at_horizon(histories,horizon)
    companies = len({h.company_id for h in histories})
    metadata = dict(endpoint="independent_operating_state_occupancy",horizon=horizon,
        confidence_level=confidence_level,point=point.independent_operating_probability,
        full_sample_support_status=point.numerical_support_status,
        requested_replicates=n_boot,seed=seed,company_count=companies,round_count=len(histories),
        transition_count=sum(t.time<=horizon for h in histories for t in h.transitions),
        terminal_transition_count=sum(t.time<=horizon and t.destination in TERMINAL for h in histories for t in h.transitions),
        initial_terminal_count=sum(h.initial_state in TERMINAL for h in histories))
    metadata['zero_terminal_transitions'] = metadata['terminal_transition_count']==0
    if n_boot==0 or companies<2:
        status = "NOT_RUN_ZERO_REPLICATES_REQUESTED" if n_boot==0 else "NOT_RUN_INSUFFICIENT_COMPANY_CLUSTERS"
        return PrimaryBootstrapReport(**metadata,completed_replicates=0,
            unsupported_draw_count=None,undefined_draw_count=None,degenerate_distribution=None,
            execution_status=status,interval_status="WITHHELD_BOOTSTRAP_NOT_RUN",primary_interval=None,draws=())
    draws = []
    for index,sample in enumerate(resample_company_clusters(histories,n_boot,seed)):
        picked = {}
        for h in sample:
            occurrence,company = h.company_id.split(':',1)
            picked[int(occurrence)] = company
        ids = tuple(h.round_id.split(':',1)[1] for h in sample)
        try:
            result = at_horizon(sample,horizon)
            value = result.independent_operating_probability
            if not isfinite(value):
                raise ValueError("nonfinite_bootstrap_statistic")
            status = result.numerical_support_status
            reason = None
        except (ValueError,ArithmeticError) as error:
            value = None
            status = "UNDEFINED_BOOTSTRAP_STATISTIC"
            reason = f"{type(error).__name__}:{error}"
        draws.append(BootstrapDraw(index,tuple(picked[i] for i in sorted(picked)),ids,value,status,reason))
    undefined = sum(d.mathematical_value is None for d in draws)
    unsupported = sum('UNSUPPORTED' in d.numerical_support_status for d in draws)
    values = [d.mathematical_value for d in draws if d.mathematical_value is not None]
    # No incomplete subset is used to compute an interval or assert degeneracy.
    degenerate = (min(values)==max(values)) if not undefined else None
    interval = None
    if 'UNSUPPORTED' in point.numerical_support_status:
        interval_status = "WITHHELD_FULL_SAMPLE_STATE_RISK_GAP"
    elif undefined:
        interval_status = "WITHHELD_UNDEFINED_BOOTSTRAP_DRAWS"
    elif unsupported:
        interval_status = "WITHHELD_UNSUPPORTED_BOOTSTRAP_DRAWS"
    elif n_boot<2:
        interval_status = "WITHHELD_FEWER_THAN_TWO_REPLICATES"
    elif degenerate:
        interval_status = "WITHHELD_DEGENERATE_BOOTSTRAP_DISTRIBUTION"
    else:
        alpha = 1-confidence_level
        interval = (percentile_linear(values,alpha/2),percentile_linear(values,1-alpha/2))
        interval_status = "PERCENTILE_BOOTSTRAP_INTERVAL_NO_NOMINAL_COVERAGE_GUARANTEE"
    return PrimaryBootstrapReport(**metadata,completed_replicates=len(draws),
        unsupported_draw_count=unsupported,undefined_draw_count=undefined,
        degenerate_distribution=degenerate,execution_status="RUN_ALL_REQUESTED_DRAWS_RETAINED",
        interval_status=interval_status,primary_interval=interval,draws=tuple(draws))


def operating_uncertainty_report(histories,horizon,*,disagreement_threshold,
                                 n_boot=1000,seed=0,confidence_level=.95):
    """Matched endpoint, histories, landmark and confidence level by construction.

    Threshold is a required reporting configuration, not a frozen-spec number.
    Neither a mismatch nor agreement establishes inferential validity.
    """
    _probability(disagreement_threshold,"disagreement_threshold")
    primary = operating_cluster_bootstrap(histories,horizon,n_boot,seed,confidence_level)
    analytic = aj_ij_diagnostic(histories,horizon,confidence_level)
    p = primary.primary_interval
    a = analytic.normal_diagnostic_interval
    if p is None or a is None:
        return OperatingUncertaintyReport(primary,analytic,disagreement_threshold,None,None,
                                           "NOT_COMPARABLE_INTERVAL_UNAVAILABLE")
    difference = max(abs(p[0]-a[0]),abs(p[1]-a[1]))
    return OperatingUncertaintyReport(primary,analytic,disagreement_threshold,difference,
        difference>disagreement_threshold,"COMPARABLE_MATCHED_OPERATING_ENDPOINT")
