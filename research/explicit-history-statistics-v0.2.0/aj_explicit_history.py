"""Synthetic-verified candidate for the frozen independent-state occupancy target.

No source adapter, default initial state, origin choice, CI or promotion interface.
Input is a reviewed exact-time mathematical history, NOT an evidence assertion.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from random import Random


class State(str, Enum):
    PRE = "operating_pre_success"
    POST = "operating_post_success"
    SUCCESS_EXIT = "terminal_success_exit"
    ACQUISITION_UNKNOWN = "acquisition_value_unknown"
    CLOSURE = "closure"


STATES = tuple(State)
OPERATING = (State.PRE, State.POST)
TERMINAL = (State.SUCCESS_EXIT, State.ACQUISITION_UNKNOWN, State.CLOSURE)
ALLOWED = {(State.PRE, State.POST)} | {(s, d) for s in OPERATING for d in TERMINAL}


@dataclass(frozen=True)
class Transition:
    time: float
    source: State
    destination: State


@dataclass(frozen=True)
class History:
    round_id: str
    company_id: str
    initial_state: State  # Mandatory; never inferred from round number.
    observation_end: float  # Already prepared endpoint, not a raw source field.
    transitions: tuple[Transition, ...] = ()


@dataclass(frozen=True)
class Step:
    time: float
    probabilities: dict[str, float]
    risk_before: dict[str, int]
    risk_at_time_after_events: dict[str, int]
    risk_after_censor: dict[str, int]
    transition_counts: dict[str, int]


@dataclass(frozen=True)
class Landmark:
    time: float
    mathematical_probabilities: dict[str, float]
    independent_operating_probability: float
    risk_at_landmark: dict[str, int]
    # Diagnostics only. These do not assert source adequacy or valid inference.
    unresolved_states_at_landmark: tuple[str, ...]
    prior_unsupported_intervals: tuple[tuple[float, float, tuple[str, ...]], ...]
    numerical_support_status: str
    max_observed_endpoint: float


def _time(value, label):
    try:
        valid = (not isinstance(value, bool) and isinstance(value, (int, float))
                 and isfinite(value) and value >= 0)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{label}_must_be_finite_nonnegative")


def validate(histories: tuple[History, ...] | list[History]) -> None:
    if not histories:
        raise ValueError("empty_histories")
    ids = set()
    for h in histories:
        if not isinstance(h.round_id, str) or not h.round_id.strip():
            raise ValueError("missing_round_id")
        if not isinstance(h.company_id, str) or not h.company_id.strip():
            raise ValueError("missing_company_id")
        if h.round_id in ids:
            raise ValueError("duplicate_economic_round")
        ids.add(h.round_id)
        if not isinstance(h.initial_state, State):
            raise ValueError("explicit_initial_state_required")
        _time(h.observation_end, "observation_end")
        previous = -1.0
        current = h.initial_state
        for tr in h.transitions:
            _time(tr.time, "transition_time")
            if tr.time <= previous:
                raise ValueError("strict_transition_order_required_no_same_subject_ties")
            if tr.time > h.observation_end:
                raise ValueError("transition_after_prepared_observation_end")
            if not isinstance(tr.source, State) or not isinstance(tr.destination, State):
                raise ValueError("explicit_state_enum_required")
            if tr.source != current:
                raise ValueError("transition_source_mismatch")
            if (tr.source, tr.destination) not in ALLOWED:
                raise ValueError("forbidden_transition_including_terminal_exit_or_reversion")
            current = tr.destination
            previous = tr.time


def _risk(histories, current, t, inclusive):
    return {s.value: sum(current[h.round_id] == s and
                         (h.observation_end >= t if inclusive else h.observation_end > t)
                         for h in histories) for s in STATES}


def trajectory(histories: tuple[History, ...] | list[History]) -> list[Step]:
    """Product integral p(t)=p(0-) product(I+dA); events precede tied censors.

    Equal contribution per supplied economic round. Entry is common analysis time
    zero; left truncation, interval transitions and uncertain initial states are
    deliberately outside this exact-history component.
    """
    validate(histories)
    current = {h.round_id: h.initial_state for h in histories}
    p = {s.value: sum(h.initial_state == s for h in histories) / len(histories) for s in STATES}
    events = {}
    for h in histories:
        for tr in h.transitions:
            events.setdefault(tr.time, []).append((h.round_id, tr))
    times = sorted({0.0} | {h.observation_end for h in histories} | set(events))
    result = []
    for t in times:
        risk = _risk(histories, current, t, True)
        counts = {}
        for _, tr in events.get(t, []):
            counts[(tr.source, tr.destination)] = counts.get((tr.source, tr.destination), 0) + 1
        # All increments act on the same pre-event probability vector. In
        # particular a PRE->POST event cannot immediately experience a tied
        # POST->terminal hazard at this timestamp.
        updated = dict(p)
        for source in OPERATING:
            outgoing = sum(n for (s, _), n in counts.items() if s == source)
            n = risk[source.value]
            if outgoing > n:
                raise ValueError("outgoing_events_exceed_observed_risk")
            if outgoing:
                # Exact zero at full depletion avoids a rounding residual being
                # mistaken for unsupported operating mass.
                updated[source.value] = p[source.value] * (1 - outgoing / n)
        for (source, destination), count in sorted(counts.items()):
            n = risk[source.value]
            if n <= 0:
                raise ValueError("event_without_observed_risk")
            updated[destination.value] += p[source.value] * count / n
        p = updated
        for round_id, tr in events.get(t, []):
            current[round_id] = tr.destination
        result.append(Step(t, dict(p), risk, _risk(histories, current, t, True),
                           _risk(histories, current, t, False),
                           {f"{s.value}->{d.value}": n for (s, d), n in counts.items()}))
    return result


def at_horizon(histories, horizon: float) -> Landmark:
    """Expose mathematical value AND state-specific missing-risk diagnostics.

    A finite product-integral value is not evidence of ongoing operation. The
    status is not an adopted empirical support/replicate policy. No silent
    scalar-only reporting interface is supplied.
    """
    _time(horizon, "horizon")
    points = trajectory(histories)
    relevant = [p for p in points if p.time <= horizon]
    last = relevant[-1]
    # At an exact censor time, the subject was still observed through that time.
    risk = last.risk_at_time_after_events if last.time == horizon else last.risk_after_censor
    unresolved = tuple(s.value for s in OPERATING
                       if last.probabilities[s.value] > 0 and risk[s.value] == 0)
    gaps = []
    for i, point in enumerate(relevant):
        end = min(horizon, relevant[i + 1].time if i + 1 < len(relevant) else horizon)
        missing = tuple(s.value for s in OPERATING
                        if point.probabilities[s.value] > 0 and point.risk_after_censor[s.value] == 0)
        if end > point.time and missing:
            gaps.append((point.time, end, missing))
    operating = sum(last.probabilities[s.value] for s in OPERATING)
    if unresolved or gaps:
        status = "UNSUPPORTED_OPERATING_MASS_PRESENT_OR_PRIOR_GAP"
    elif operating == 0:
        status = "COMPLETE_MODELED_ABSORPTION"
    else:
        status = "OBSERVED_STATE_RISK_PRESENT_NO_DETECTED_GAP"
    return Landmark(horizon, dict(last.probabilities), operating, dict(risk), unresolved,
                    tuple(gaps), status, max(h.observation_end for h in histories))


def resample_company_clusters(histories, n_boot: int, seed: int):
    """Whole-company samples; no draw filtering, CI or unsupported-tail policy.

    Clones identify each selected company occurrence, preserving all of its
    economic rounds and their relative contributions. IDs are synthetic only.
    """
    validate(histories)
    if isinstance(n_boot, bool) or not isinstance(n_boot, int) or n_boot < 1:
        raise ValueError("positive_integer_n_boot_required")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("integer_seed_required")
    groups = {}
    for h in histories:
        groups.setdefault(h.company_id, []).append(h)
    companies = sorted(groups)
    rng = Random(seed)
    samples = []
    for _ in range(n_boot):
        sample = []
        for occurrence in range(len(companies)):
            company = rng.choice(companies)
            for h in groups[company]:
                sample.append(History(f"{occurrence}:{h.round_id}", f"{occurrence}:{company}",
                                      h.initial_state, h.observation_end, h.transitions))
        samples.append(tuple(sample))
    return samples
