"""Phase 1D reporting extension.

Wraps Phase 1C cell decisions with multi-source and primary-hash requirements.
No cell is reportable until both gates pass.
"""
from __future__ import annotations
from dataclasses import dataclass
from .gate_wiring import is_outcome_promotable
from src.phase1c.reporting import CellDecision, rq2_field_cell_decision

@dataclass(frozen=True)
class Phase1DCellDecision:
    base: CellDecision
    multi_source_ok: bool
    primary_hash_ok: bool
    reportable: bool
    reasons: tuple[str, ...]

def phase1d_cell_decision(
    n: int,
    informative_events: int,
    ascertainment_coverage: float,
    coverage_matrix: dict | None,
    event_type: str,
    primary_hash_present: bool,
) -> Phase1DCellDecision:
    base = rq2_field_cell_decision(n, informative_events, ascertainment_coverage)
    multi_ok = is_outcome_promotable(coverage_matrix, event_type, primary_hash_present)
    reasons = list(base.reasons)
    if not multi_ok:
        reasons.append("multi_source_or_hash_blocked")
    reportable = base.report and multi_ok
    return Phase1DCellDecision(
        base=base,
        multi_source_ok=multi_ok,
        primary_hash_ok=primary_hash_present,
        reportable=reportable,
        reasons=tuple(reasons),
    )
