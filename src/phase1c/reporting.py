from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real

def _validate_count(value: int, name: str) -> None:
    """Counts accept integer-valued real numbers, but not booleans or strings."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"invalid_count:{name}")
    if isinstance(value, Integral):
        valid = value >= 0
    else:
        valid = math.isfinite(value) and value >= 0 and value == math.floor(value)
    if not valid:
        raise ValueError(f"invalid_count:{name}")

def _validate_year(year: int) -> None:
    """Require an unambiguous offering-year key inside the frozen study scope."""
    if isinstance(year, bool) or not isinstance(year, Integral):
        raise ValueError("invalid_year")
    if not 2020 <= year <= 2025:
        raise ValueError("year_out_of_scope")


def _validate_coverage(value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not 0 <= value <= 1:
        raise ValueError("invalid_ascertainment_coverage")


@dataclass(frozen=True)
class CellDecision:
    report: bool
    pool: bool
    low_information: bool
    reasons: tuple[str,...]

@dataclass(frozen=True)
class CellStats:
    year: int
    n: int
    informative_events: int
    ascertained: int

    def __post_init__(self) -> None:
        _validate_year(self.year)
        _validate_count(self.n, "n")
        _validate_count(self.informative_events, "informative_events")
        _validate_count(self.ascertained, "ascertained")
        if self.ascertained > self.n:
            raise ValueError("ascertained_exceeds_n")

    @property
    def ascertainment_coverage(self) -> float:
        return self.ascertained/self.n if self.n else 0.0

@dataclass(frozen=True)
class PoolResult:
    years: tuple[int,...]
    n: int
    informative_events: int
    ascertained: int
    ascertainment_coverage: float
    report: bool
    suppressed: bool
    crossed_maturity_boundary: bool
    reasons: tuple[str,...]

def rq1_cell_decision(n: int, informative_events: int) -> CellDecision:
    _validate_count(n, "n")
    _validate_count(informative_events, "informative_events")
    if n<=0:
        return CellDecision(False,False,True,("empty_cell",))
    low=n<30 or informative_events<5
    reasons=[]
    if n<30: reasons.append("n_lt_30")
    if informative_events<5: reasons.append("events_lt_5")
    return CellDecision(True,False,low,tuple(reasons))

def rq2_field_cell_decision(n: int, informative_events: int, ascertainment_coverage: float) -> CellDecision:
    _validate_count(n, "n")
    _validate_count(informative_events, "informative_events")
    _validate_coverage(ascertainment_coverage)
    reasons=[]
    if n<30: reasons.append("n_lt_30")
    if informative_events<5: reasons.append("events_lt_5")
    if ascertainment_coverage<0.80: reasons.append("ascertainment_lt_80pct")
    ok=not reasons
    return CellDecision(ok,not ok,not ok,tuple(reasons))

def maturity_block(year: int) -> str:
    _validate_year(year)
    if year in {2020,2021,2022,2023}: return "2020_2023"
    if year in {2024,2025}: return "2024_2025"
    raise ValueError("year_out_of_scope")

def adjacent_pool_order(year: int) -> list[int]:
    block=[2020,2021,2022,2023] if maturity_block(year)=="2020_2023" else [2024,2025]
    return sorted(block,key=lambda y:(abs(y-year),y))

def pool_adjacent_years(target_year: int, cells: list[CellStats]) -> PoolResult:
    """
    Expand within the target maturity block until RQ2 gates pass.
    This function never silently crosses the 2023/2024 boundary.
    """
    # Validate the complete supplied cell list before any early reporting return.
    # A repeated year is not an instruction to drop, sum or choose one cell.
    _validate_year(target_year)
    by_year={}
    for cell in cells:
        _validate_year(cell.year)
        if cell.year in by_year:
            raise ValueError("duplicate_year_cell")
        by_year[cell.year]=cell
    selected=[]
    last_reasons=()
    for year in adjacent_pool_order(target_year):
        if year not in by_year:
            continue
        selected.append(by_year[year])
        n=sum(x.n for x in selected)
        events=sum(x.informative_events for x in selected)
        ascertained=sum(x.ascertained for x in selected)
        cov=ascertained/n if n else 0.0
        d=rq2_field_cell_decision(n,events,cov)
        last_reasons=d.reasons
        if d.report:
            return PoolResult(tuple(sorted(x.year for x in selected)),n,events,ascertained,cov,True,False,False,())
    n=sum(x.n for x in selected)
    events=sum(x.informative_events for x in selected)
    ascertained=sum(x.ascertained for x in selected)
    cov=ascertained/n if n else 0.0
    return PoolResult(tuple(sorted(x.year for x in selected)),n,events,ascertained,cov,False,True,False,last_reasons or ("insufficient_within_maturity_block",))

def lost_followup_sensitivity(observed_events: int, lost: int, denominator: int) -> dict:
    _validate_count(observed_events, "observed_events")
    _validate_count(lost, "lost")
    _validate_count(denominator, "denominator")
    if denominator<=0 or observed_events<0 or lost<0 or observed_events+lost>denominator:
        raise ValueError("invalid_counts")
    return {
        "optimistic_rate":observed_events/denominator,
        "adverse_rate":(observed_events+lost)/denominator,
        "lost_followup_share":lost/denominator,
    }
