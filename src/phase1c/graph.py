from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from .model import RoundRecord

@dataclass(frozen=True)
class RoundEdge:
    source_round_id: str
    destination_round_id: str
    edge_type: str  # NEXT_ROUND | COHOST_SAME_ROUND
    cross_platform: bool
    qualified_followon_success: bool = False

def _windows_overlap(a: RoundRecord, b: RoundRecord) -> bool:
    a_end=a.completion_date or a.first_live_date
    b_end=b.completion_date or b.first_live_date
    return max(a.first_live_date,b.first_live_date) <= min(a_end,b_end)

def same_economic_round(a: RoundRecord, b: RoundRecord, valuation_tolerance: float=0.01) -> bool:
    if a.canonical_company_id != b.canonical_company_id:
        return False
    if a.instrument_type != b.instrument_type:
        return False
    if not _windows_overlap(a,b):
        return False
    av,bv=a.comparable_valuation,b.comparable_valuation
    if av is None and bv is None:
        return True
    if av is None or bv is None:
        return False
    denom=max(abs(av),abs(bv),1.0)
    return abs(av-bv)/denom <= valuation_tolerance

def qualifying_followon(predecessor: RoundRecord, successor: RoundRecord, stepup: float=1.5) -> bool:
    if predecessor.canonical_company_id != successor.canonical_company_id:
        return False
    if predecessor.round_id == successor.round_id:
        return False
    if predecessor.completion_date is None or successor.completion_date is None:
        return False
    if successor.completion_date <= predecessor.completion_date:
        return False
    # Comparable priced metrics only. A valuation cap is deliberately ignored.
    if predecessor.comparable_valuation is None or successor.comparable_valuation is None:
        return False
    return successor.comparable_valuation >= stepup * predecessor.comparable_valuation

def next_round_edges(rounds: list[RoundRecord]) -> list[RoundEdge]:
    by_company: dict[str,list[RoundRecord]]={}
    for r in rounds:
        by_company.setdefault(r.canonical_company_id,[]).append(r)
    edges=[]
    for company, rs in by_company.items():
        rs=sorted(rs,key=lambda x:(x.first_live_date,x.round_id))
        canonical=[]
        for r in rs:
            if canonical and same_economic_round(canonical[-1],r):
                edges.append(RoundEdge(canonical[-1].round_id,r.round_id,"COHOST_SAME_ROUND",canonical[-1].platform!=r.platform,False))
            else:
                canonical.append(r)
        for a,b in zip(canonical,canonical[1:]):
            edges.append(RoundEdge(a.round_id,b.round_id,"NEXT_ROUND",a.platform!=b.platform,qualifying_followon(a,b)))
    return edges

def native_vs_graph_reclassification(edges: list[RoundEdge]) -> dict:
    q=[e for e in edges if e.edge_type=="NEXT_ROUND" and e.qualified_followon_success]
    cross=[e for e in q if e.cross_platform]
    return {
        "qualified_followons":len(q),
        "cross_platform_reclassified":len(cross),
        "cross_platform_share":len(cross)/len(q) if q else 0.0,
    }


@dataclass(frozen=True)
class PlatformBiasRow:
    platform: str
    denominator_rounds: int
    native_successes: int
    graph_successes: int
    cross_platform_reclassified: int
    native_rate: float
    graph_rate: float
    absolute_delta: float

def native_vs_graph_by_platform(
    rounds: list[RoundRecord],
    edges: list[RoundEdge],
    native_success_round_ids: set[str],
) -> list[PlatformBiasRow]:
    eligible=[r for r in rounds if r.layer_b_eligible]
    by_id={r.round_id:r for r in eligible}
    graph_success=set(native_success_round_ids)
    for e in edges:
        if e.edge_type=="NEXT_ROUND" and e.cross_platform and e.qualified_followon_success and e.source_round_id in by_id:
            graph_success.add(e.source_round_id)
    out=[]
    for platform in sorted({r.platform for r in eligible}):
        ids={r.round_id for r in eligible if r.platform==platform}
        n=len(ids)
        native=len(ids & native_success_round_ids)
        graph_n=len(ids & graph_success)
        reclass=graph_n-native
        nr=native/n if n else 0.0
        gr=graph_n/n if n else 0.0
        out.append(PlatformBiasRow(platform,n,native,graph_n,reclass,nr,gr,gr-nr))
    return out
