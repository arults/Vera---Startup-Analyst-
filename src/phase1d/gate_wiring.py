"""Wiring helper for multi-source gate into reporting / verifier path.

Call require_multi_source_for_outcome before accepting any outcome label.
"""
from __future__ import annotations
from .multi_source_gate import check_multi_source_gate, MultiSourceGateResult

def require_multi_source_for_outcome(coverage: dict | None, event_type: str) -> MultiSourceGateResult:
    """
    Fail-closed check. Caller must treat non-passed result as blocking promotion.
    """
    return check_multi_source_gate(coverage, event_type)

def is_outcome_promotable(coverage: dict | None, event_type: str, primary_hash_present: bool) -> bool:
    """
    Both multi-source gate and primary content hash are required.
    """
    gate = check_multi_source_gate(coverage, event_type)
    return gate.passed and primary_hash_present
