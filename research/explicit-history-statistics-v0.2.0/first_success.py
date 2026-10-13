"""First index-qualifying success from explicit exact multistate histories.

Synthetic-only component. Initial POST interpretation is mandatory. No source
mapping or assumption that a new financing erases prior terminal history.
"""
from dataclasses import dataclass
from enum import Enum
from aj_explicit_history import State, validate, _time


class InitialPostPolicy(str, Enum):
    REJECT = "reject_initial_post_for_incident_only_analysis"
    BASELINE_QUALIFIED = "already_index_qualified_at_entry"


@dataclass(frozen=True)
class FirstEvent:
    round_id: str
    company_id: str
    time: float | None
    cause: str  # success / competing / censored / baseline_qualified


@dataclass(frozen=True)
class SuccessPoint:
    time: float
    at_risk: int
    success_events: int
    competing_events: int
    incident_success_cif: float
    competing_cif: float
    event_free_probability: float


@dataclass(frozen=True)
class SuccessLandmark:
    time: float
    baseline_qualified_fraction: float
    incident_success_cif: float  # unconditional contribution after entry
    ever_qualified_probability: float  # baseline plus incident, NOT incident CIF
    competing_cif: float
    event_free_probability: float
    incident_risk_count_at_entry: int
    risk_at_landmark: int
    prior_unsupported_intervals: tuple[tuple[float, float], ...]
    numerical_support_status: str


def first_events(histories, initial_post_policy: InitialPostPolicy) -> tuple[FirstEvent, ...]:
    validate(histories)
    if not isinstance(initial_post_policy, InitialPostPolicy):
        raise ValueError("explicit_initial_post_policy_required")
    events = []
    for h in histories:
        if h.initial_state not in (State.PRE,State.POST):
            raise ValueError("terminal_initial_state_requires_endpoint_specific_prior_success_history")
        if h.initial_state == State.POST:
            if initial_post_policy == InitialPostPolicy.REJECT:
                raise ValueError("initial_post_not_incident_event_free")
            events.append(FirstEvent(h.round_id,h.company_id,None,"baseline_qualified"))
            continue
        if h.transitions:
            tr = h.transitions[0]
            cause = "success" if tr.destination in (State.POST,State.SUCCESS_EXIT) else "competing"
            events.append(FirstEvent(h.round_id,h.company_id,tr.time,cause))
        else:
            events.append(FirstEvent(h.round_id,h.company_id,h.observation_end,"censored"))
    return tuple(events)


def success_trajectory(histories, initial_post_policy: InitialPostPolicy) -> tuple[SuccessPoint, ...]:
    events = first_events(histories,initial_post_policy)
    incident = [e for e in events if e.cause != "baseline_qualified"]
    free = len(incident)/len(events)
    target = competing = 0.0
    points = []
    for t in sorted({e.time for e in incident if e.cause != "censored"}):
        n = sum(e.time >= t for e in incident)
        d = sum(e.time == t and e.cause == "success" for e in incident)
        other = sum(e.time == t and e.cause == "competing" for e in incident)
        target += free*d/n
        competing += free*other/n
        free *= 1-(d+other)/n
        points.append(SuccessPoint(t,n,d,other,target,competing,free))
    return tuple(points)


def success_at_horizon(histories, horizon, initial_post_policy: InitialPostPolicy) -> SuccessLandmark:
    _time(horizon,"horizon")
    events = first_events(histories,initial_post_policy)
    incident = [e for e in events if e.cause != "baseline_qualified"]
    baseline = sum(e.cause == "baseline_qualified" for e in events)/len(events)
    points = [p for p in success_trajectory(histories,initial_post_policy) if p.time <= horizon]
    target = points[-1].incident_success_cif if points else 0.0
    competing = points[-1].competing_cif if points else 0.0
    free = points[-1].event_free_probability if points else len(incident)/len(events)
    risk = sum(e.time > horizon or (e.time == horizon and e.cause == "censored") for e in incident)
    times = sorted({0.0,horizon} | {e.time for e in incident if e.time <= horizon})
    by_time = {p.time:p for p in points}
    previous_free = len(incident)/len(events)
    gaps = []
    for i,t in enumerate(times[:-1]):
        if t in by_time:
            previous_free = by_time[t].event_free_probability
        if previous_free > 0 and not any(e.time > t for e in incident):
            gaps.append((t,times[i+1]))
    if gaps or (free > 0 and not risk):
        status = "UNSUPPORTED_EVENT_FREE_MASS_PRESENT_OR_PRIOR_GAP"
    elif not incident:
        status = "NO_INCIDENT_RISK_AT_ENTRY_BASELINE_QUALIFIED_ONLY"
    elif free == 0:
        status = "COMPLETE_MODELED_FIRST_EVENT_ABSORPTION"
    else:
        status = "OBSERVED_FIRST_EVENT_RISK_PRESENT_NO_DETECTED_GAP"
    return SuccessLandmark(horizon,baseline,target,baseline+target,competing,free,
                           len(incident),risk,tuple(gaps),status)
