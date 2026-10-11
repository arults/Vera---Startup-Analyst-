"""Analytic infinitesimal-jackknife diagnostic for explicit-history AJ.

Equal-round point target; round-weight derivatives aggregated by company.
Normal limits are diagnostics, not finite-sample or simultaneous coverage claims.
No empirical source adapter or bootstrap interval is supplied.
"""
from dataclasses import dataclass
from math import sqrt, isfinite
from statistics import NormalDist
from aj_explicit_history import State, STATES, OPERATING, validate, at_horizon


@dataclass(frozen=True)
class IJDiagnostic:
    mathematical_probabilities: dict[str,float]
    round_gradients: dict[str,dict[str,float]]
    company_gradients: dict[str,dict[str,float]]
    covariance: dict[str,dict[str,float]]
    operating_variance: float
    operating_standard_error: float
    confidence_level: float
    normal_diagnostic_interval: tuple[float,float] | None
    interval_status: str
    numerical_support_status: str
    company_count: int
    finite_sample_correction: str = "none_uncorrected_IJ"


def aj_ij_diagnostic(histories, horizon, confidence_level=0.95):
    """Differentiate the empirical initial distribution and every AJ increment.

    Each derivative is d p / d w_j at all round weights w_j=1. The point remains
    round-weighted. A company's influence is the sum for its rounds; covariance
    is the sum of outer products of company influences, without n/(n-1).
    """
    if (isinstance(confidence_level,bool) or not isinstance(confidence_level,(float,int))
        or not 0 < confidence_level < 1):
        raise ValueError("confidence_level_must_be_between_zero_and_one")
    landmark = at_horizon(histories,horizon)
    histories = sorted(histories,key=lambda h:h.round_id)
    n = len(histories)
    current = [h.initial_state for h in histories]
    p = {s:sum(h.initial_state == s for h in histories)/n for s in STATES}
    grad = {s:[((h.initial_state == s)-p[s])/n for h in histories] for s in STATES}
    events = {}
    for j,h in enumerate(histories):
        for tr in h.transitions:
            if tr.time <= horizon:
                events.setdefault(tr.time,[]).append((j,tr))
    for t,at_t in sorted(events.items()):
        risks = {s:[int(current[j]==s and h.observation_end>=t) for j,h in enumerate(histories)] for s in STATES}
        counts = {}
        for j,tr in at_t:
            counts.setdefault((tr.source,tr.destination),[0]*n)[j] = 1
        updated = dict(p)
        dupdated = {s:list(v) for s,v in grad.items()}
        # Diagonal and off-diagonal terms use the same pre-event p and gradient.
        for source in OPERATING:
            outgoing = [sum(v[j] for (s,_),v in counts.items() if s==source) for j in range(n)]
            d = sum(outgoing)
            if not d:
                continue
            y = sum(risks[source])
            q = d/y
            dq = [(outgoing[j]*y-d*risks[source][j])/(y*y) for j in range(n)]
            updated[source] = p[source]*(1-q)
            dupdated[source] = [grad[source][j]*(1-q)-p[source]*dq[j] for j in range(n)]
        for (source,destination),indicator in sorted(counts.items()):
            d = sum(indicator)
            y = sum(risks[source])
            q = d/y
            dq = [(indicator[j]*y-d*risks[source][j])/(y*y) for j in range(n)]
            updated[destination] += p[source]*q
            for j in range(n):
                dupdated[destination][j] += grad[source][j]*q+p[source]*dq[j]
        p,grad = updated,dupdated
        for j,tr in at_t:
            current[j] = tr.destination
    round_gradients = {h.round_id:{s.value:grad[s][j] for s in STATES} for j,h in enumerate(histories)}
    company = {}
    for j,h in enumerate(histories):
        company.setdefault(h.company_id,{s.value:0.0 for s in STATES})
        for s in STATES:
            company[h.company_id][s.value] += grad[s][j]
    covariance = {a.value:{b.value:sum(g[a.value]*g[b.value] for g in company.values())
                           for b in STATES} for a in STATES}
    # Sum projected company scores directly to avoid negative variance caused
    # by cancellation of positive/negative off-diagonal covariance entries.
    variance = sum(sum(g[s.value] for s in OPERATING)**2 for g in company.values())
    se = sqrt(variance)
    interval = None
    if 'UNSUPPORTED' in landmark.numerical_support_status:
        status = "WITHHELD_NUMERICAL_STATE_RISK_GAP"
    elif len(company) < 2:
        status = "WITHHELD_FEWER_THAN_TWO_COMPANY_CLUSTERS"
    elif variance == 0 or landmark.independent_operating_probability in (0.0,1.0):
        status = "WITHHELD_BOUNDARY_OR_ZERO_IJ_VARIANCE_NOT_INFORMATIVE_COVERAGE"
    else:
        z = -NormalDist().inv_cdf((1-confidence_level)/2)
        point = landmark.independent_operating_probability
        interval = (max(0.0,point-z*se),min(1.0,point+z*se))
        status = "NORMAL_DELTA_DIAGNOSTIC_ONLY"
    return IJDiagnostic({s.value:p[s] for s in STATES},round_gradients,company,covariance,
                        variance,se,confidence_level,interval,status,
                        landmark.numerical_support_status,len(company))
