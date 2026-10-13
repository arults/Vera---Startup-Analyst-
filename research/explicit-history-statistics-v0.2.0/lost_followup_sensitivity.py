"""Assumption-indexed lost-follow-up histories. No observations or rate estimator.

Endpoint-local hypothetical scenarios are not identification bounds, authenticated
follow-up, supported empirical estimates, or company-consistent calendar paths.
"""
from dataclasses import dataclass
from enum import Enum
from aj_explicit_history import History, Transition, State, OPERATING, TERMINAL, validate, _time
from first_success import InitialPostPolicy


class Endpoint(str, Enum):
    OPERATING = "independent_operating_occupancy"
    SUCCESS = "first_index_qualifying_success"
    CLOSURE = "confirmed_closure_cif"


class Direction(str, Enum):
    OPTIMISTIC = "optimistic_for_investor_endpoint"
    ADVERSE = "adverse_for_investor_endpoint"


class FollowupKind(str, Enum):
    LOST = "lost_to_platform_followup"
    ADMINISTRATIVE = "administrative_censor"
    TERMINAL = "known_terminal_history"


@dataclass(frozen=True)
class PreparedFollowup:
    history: History
    kind: FollowupKind
    hard_limit: float  # Prepared administrative/extraction cap, never extended.


@dataclass(frozen=True)
class Assignment:
    original: History
    hypothetical: History
    status: str
    assumption: str | None
    hypothetical_tail_start_exclusive: float | None
    hypothetical_tail_end_inclusive: float | None


@dataclass(frozen=True)
class Scenario:
    endpoint: Endpoint
    direction: Direction
    horizon: float
    extraction_limit: float
    initial_post_policy: InitialPostPolicy | None
    assignments: tuple[Assignment, ...]
    complete: bool  # No blocked rows, NOT inferential or empirical support.
    interpretation: str = "HYPOTHETICAL_ENDPOINT_LOCAL_SCENARIO_NOT_OBSERVED_NOT_IDENTIFICATION_BOUND"


def _current(h):
    return h.transitions[-1].destination if h.transitions else h.initial_state


def _unchanged(h, status):
    return Assignment(h, h, status, None, None, None)


def _qualified(h):
    return h.initial_state == State.POST or any(
        t.destination in (State.POST, State.SUCCESS_EXIT) for t in h.transitions)


def build_scenario(records, *, endpoint, direction, horizon, extraction_limit,
                   assignment_times, initial_post_policy=None):
    """Return a separate hypothetical packet, preserving every supplied round.

    Event-assignment times must be explicitly supplied for exactly the rows that
    need hypothetical events. No automatic midpoint, epsilon, calendar mapping,
    source admission, interval estimation, or empirical output is performed.
    """
    records = tuple(records)
    validate(tuple(r.history for r in records))
    if not isinstance(endpoint, Endpoint) or not isinstance(direction, Direction):
        raise ValueError("explicit_endpoint_and_direction_required")
    _time(horizon, "horizon")
    _time(extraction_limit, "extraction_limit")
    if horizon > extraction_limit:
        raise ValueError("requested_horizon_beyond_hard_extraction_limit")
    if endpoint == Endpoint.SUCCESS:
        if not isinstance(initial_post_policy, InitialPostPolicy):
            raise ValueError("explicit_initial_post_policy_required_for_success")
    elif initial_post_policy is not None:
        raise ValueError("initial_post_policy_applies_only_to_success")
    if not isinstance(assignment_times, dict):
        raise ValueError("explicit_assignment_time_mapping_required")
    for r in records:
        h = r.history
        _time(r.hard_limit, "hard_limit")
        if h.observation_end > r.hard_limit or r.hard_limit > extraction_limit:
            raise ValueError("observation_endpoint_and_hard_limits_inconsistent")
        if not isinstance(r.kind, FollowupKind):
            raise ValueError("explicit_followup_kind_required")
        terminal = _current(h) in TERMINAL
        if (r.kind == FollowupKind.TERMINAL) != terminal:
            raise ValueError("followup_kind_conflicts_with_known_terminal_state")
        if r.kind == FollowupKind.ADMINISTRATIVE and h.observation_end != r.hard_limit:
            raise ValueError("administrative_censor_must_equal_prepared_hard_limit")
        if r.kind == FollowupKind.LOST and h.observation_end >= r.hard_limit:
            raise ValueError("lost_followup_requires_gap_before_hard_limit")

    assignments = []
    used_times = set()
    for r in records:
        h = r.history
        # Terminal occupancy alone cannot determine prior index-qualified success.
        if endpoint == Endpoint.SUCCESS and h.initial_state in TERMINAL:
            assignments.append(_unchanged(h, "BLOCKED_TERMINAL_ENTRY_SUCCESS_HISTORY_UNSPECIFIED"))
            continue
        if (endpoint == Endpoint.SUCCESS and h.initial_state == State.POST
                and initial_post_policy == InitialPostPolicy.REJECT):
            assignments.append(_unchanged(h, "BLOCKED_INITIAL_POST_NOT_INCIDENT_EVENT_FREE"))
            continue
        if h.observation_end >= horizon:
            assignments.append(_unchanged(h, "OBSERVED_HISTORY_REACHES_HORIZON_UNCHANGED"))
            continue
        if r.kind == FollowupKind.TERMINAL:
            assignments.append(_unchanged(h, "KNOWN_ABSORBING_HISTORY_UNCHANGED"))
            continue
        if endpoint == Endpoint.SUCCESS and _qualified(h):
            assignments.append(_unchanged(h, "FIRST_SUCCESS_ALREADY_DETERMINED_UNCHANGED"))
            continue
        if horizon > r.hard_limit:
            assignments.append(_unchanged(h, "BLOCKED_HORIZON_BEYOND_ROUND_HARD_LIMIT"))
            continue
        if r.kind != FollowupKind.LOST:
            # Administrative records can reach this branch only at their limit,
            # already caught above; retain an explicit fail-closed guard.
            assignments.append(_unchanged(h, "BLOCKED_NOT_GENUINE_LOST_FOLLOWUP"))
            continue

        destination = None
        if endpoint == Endpoint.SUCCESS:
            if direction == Direction.OPTIMISTIC:
                destination = State.POST
                assumption = "assume_index_qualifying_nonterminal_success_then_operation_to_horizon"
            else:
                assumption = "assume_no_qualifying_success_and_continued_operation_to_horizon"
        elif direction == Direction.ADVERSE:
            destination = State.CLOSURE
            assumption = "assume_closure_after_last_observation"
        else:
            assumption = "assume_continued_operation_without_closure_to_horizon"

        transitions = h.transitions
        scenario_end = horizon
        if destination is not None:
            if h.round_id not in assignment_times:
                raise ValueError("explicit_hypothetical_event_time_required:" + h.round_id)
            t = assignment_times[h.round_id]
            _time(t, "hypothetical_event_time")
            if not h.observation_end < t <= horizon:
                raise ValueError("hypothetical_event_must_be_strictly_after_observation_and_by_horizon")
            used_times.add(h.round_id)
            transitions = h.transitions + (Transition(t, _current(h), destination),)
            if destination in TERMINAL:
                scenario_end = t
        hypothetical = History(h.round_id, h.company_id, h.initial_state,
                               scenario_end, transitions)
        assignments.append(Assignment(h, hypothetical, "HYPOTHETICAL_TAIL_ASSIGNED",
                                      assumption, h.observation_end, scenario_end))
    if set(assignment_times) != used_times:
        raise ValueError("unused_or_ineligible_hypothetical_event_times")
    # Arithmetic validation is deliberately distinct from evidentiary validation.
    validate(tuple(a.hypothetical for a in assignments))
    return Scenario(endpoint, direction, horizon, extraction_limit,
                    initial_post_policy, tuple(assignments),
                    not any(a.status.startswith("BLOCKED_") for a in assignments))
