"""Fail-closed verifier gate: outcome labels require multi-source coverage matrix.

Extends Phase 1C reporting discipline. No promotion if matrix missing or incomplete.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class MultiSourceGateResult:
    passed: bool
    reasons: tuple[str, ...]

def check_multi_source_gate(coverage: dict | None, event_type: str) -> MultiSourceGateResult:
    """
    Required categories must be searched or explicitly searched_not_found / inaccessible
    before any outcome label (closure, success, etc.) can be accepted.
    """
    if coverage is None:
        return MultiSourceGateResult(False, ("missing_coverage_matrix",))
    required = ["platform_regulatory", "independent_news", "discussion_forums", "youtube_longform"]
    reasons = []
    for cat in required:
        status = coverage.get(cat, {}).get("status", "not_started")
        if status in {"not_started", ""}:
            reasons.append(f"{cat}_not_searched")
    engines = coverage.get("multi_engine", {})
    for eng in ["google", "bing", "duckduckgo"]:
        if engines.get(eng, {}).get("status") in {None, "not_started", ""}:
            reasons.append(f"{eng}_not_searched")
    # For terminal labels, platform_regulatory must be searched
    if event_type in {"closure", "ipo_direct_listing", "qualified_followon"} and coverage.get("platform_regulatory", {}).get("status") != "searched":
        reasons.append("platform_regulatory_required_for_terminal")
    return MultiSourceGateResult(len(reasons) == 0, tuple(reasons))

def assert_gate_or_raise(coverage: dict | None, event_type: str) -> None:
    result = check_multi_source_gate(coverage, event_type)
    if not result.passed:
        raise ValueError(f"multi_source_gate_failed: {result.reasons}")
