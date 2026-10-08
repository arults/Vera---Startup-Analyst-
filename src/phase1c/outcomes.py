from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

class State(str, Enum):
    OPERATING_PRE_SUCCESS="operating_pre_success"
    OPERATING_POST_SUCCESS="operating_post_success"
    TERMINAL_SUCCESS_EXIT="terminal_success_exit"
    ACQUISITION_VALUE_UNKNOWN="acquisition_value_unknown"
    CLOSURE="closure"

class EventType(str, Enum):
    QUALIFIED_FOLLOWON="qualified_followon"
    IPO_DIRECT_LISTING="ipo_direct_listing"
    ACQUISITION="acquisition"
    PROFITABLE_EXIT="profitable_exit"
    CLOSURE="closure"
    OPERATING_EVIDENCE="operating_evidence"

TERMINAL={State.TERMINAL_SUCCESS_EXIT,State.ACQUISITION_VALUE_UNKNOWN,State.CLOSURE}

@dataclass(frozen=True)
class OutcomeEvent:
    round_id: str
    event_date: date
    event_type: EventType
    evidence_url: str
    platform_hosted: bool
    comparable_pre_valuation: float | None = None
    comparable_post_valuation: float | None = None
    shareholder_consideration_known: bool = False
    gross_moic: float | None = None
    explicit_closure: bool = False

def is_qualified_success(e: OutcomeEvent) -> bool:
    if not e.platform_hosted:
        return False
    if e.event_type == EventType.QUALIFIED_FOLLOWON:
        return (
            e.comparable_pre_valuation is not None
            and e.comparable_post_valuation is not None
            and e.comparable_pre_valuation > 0
            and e.comparable_post_valuation >= 1.5 * e.comparable_pre_valuation
        )
    if e.event_type == EventType.IPO_DIRECT_LISTING:
        return True
    if e.event_type == EventType.ACQUISITION:
        return e.shareholder_consideration_known
    if e.event_type == EventType.PROFITABLE_EXIT:
        return e.gross_moic is not None and e.gross_moic > 1.0
    return False

def is_confirmed_closure(e: OutcomeEvent) -> bool:
    return (
        e.event_type == EventType.CLOSURE
        and e.platform_hosted
        and e.explicit_closure
        and bool(e.evidence_url)
    )

def next_state(current: State, e: OutcomeEvent) -> State:
    if current in TERMINAL:
        raise ValueError("transition_after_terminal_state")
    if is_confirmed_closure(e):
        return State.CLOSURE
    if e.event_type == EventType.ACQUISITION:
        return State.TERMINAL_SUCCESS_EXIT if is_qualified_success(e) else State.ACQUISITION_VALUE_UNKNOWN
    if e.event_type == EventType.PROFITABLE_EXIT and is_qualified_success(e):
        return State.TERMINAL_SUCCESS_EXIT
    if e.event_type in {EventType.QUALIFIED_FOLLOWON,EventType.IPO_DIRECT_LISTING} and is_qualified_success(e):
        return State.OPERATING_POST_SUCCESS
    if e.event_type == EventType.OPERATING_EVIDENCE:
        return current
    return current

def censor_date(last_positive_platform_evidence: date | None, extraction_date: date, completion_date: date) -> date:
    if last_positive_platform_evidence is None:
        return completion_date
    if last_positive_platform_evidence < completion_date:
        return completion_date
    return min(last_positive_platform_evidence,extraction_date)

def first_success(events: list[OutcomeEvent]) -> OutcomeEvent | None:
    for e in sorted(events,key=lambda x:x.event_date):
        if is_qualified_success(e):
            return e
        if is_confirmed_closure(e) or e.event_type == EventType.ACQUISITION:
            return None
    return None
