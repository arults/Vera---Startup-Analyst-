from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class CellDecision:
    report: bool
    pool: bool
    low_information: bool
    reasons: tuple[str,...]

def rq1_cell_decision(n: int, informative_events: int) -> CellDecision:
    if n<=0:
        return CellDecision(False,False,True,("empty_cell",))
    low=n<30 or informative_events<5
    reasons=[]
    if n<30: reasons.append("n_lt_30")
    if informative_events<5: reasons.append("events_lt_5")
    return CellDecision(True,False,low,tuple(reasons))

def rq2_field_cell_decision(n: int, informative_events: int, ascertainment_coverage: float) -> CellDecision:
    reasons=[]
    if n<30: reasons.append("n_lt_30")
    if informative_events<5: reasons.append("events_lt_5")
    if ascertainment_coverage<0.80: reasons.append("ascertainment_lt_80pct")
    ok=not reasons
    return CellDecision(ok,not ok,not ok,tuple(reasons))

def maturity_block(year: int) -> str:
    if year in {2020,2021,2022,2023}: return "2020_2023"
    if year in {2024,2025}: return "2024_2025"
    raise ValueError("year_out_of_scope")

def adjacent_pool_order(year: int) -> list[int]:
    block=[2020,2021,2022,2023] if year<=2023 else [2024,2025]
    return sorted(block,key=lambda y:(abs(y-year),y))

def lost_followup_sensitivity(observed_events: int, lost: int, denominator: int) -> dict:
    if denominator<=0 or observed_events<0 or lost<0 or observed_events+lost>denominator:
        raise ValueError("invalid_counts")
    return {
        "optimistic_rate":observed_events/denominator,
        "adverse_rate":(observed_events+lost)/denominator,
        "lost_followup_share":lost/denominator,
    }
