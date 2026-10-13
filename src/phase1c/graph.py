from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
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

@dataclass(frozen=True)
class SameRoundEvidence:
    """A caller-supplied, independently reviewed source attestation for one pair.

    This is NOT an evidence verifier. Callers must establish the source hash,
    platform-hosted quoted relation, issuer identity, and review before constructing it. A native
    campaign ID by itself is not a same-economic-round attestation.
    """
    left_round_id: str
    right_round_id: str
    relation: str  # SAME_OFFERING | AMENDMENT_CHAIN
    source_url: str
    source_sha256: str
    relation_quote: str
    reviewer_id: str

    def supports(self, a: RoundRecord, b: RoundRecord) -> bool:
        return (
            {self.left_round_id, self.right_round_id} == {a.round_id, b.round_id}
            and self.left_round_id != self.right_round_id
            and self.relation in {"SAME_OFFERING", "AMENDMENT_CHAIN"}
            and self.source_url.startswith(("https://", "http://"))
            and len(self.source_sha256) == 64
            and all(c in "0123456789abcdef" for c in self.source_sha256)
            and bool(self.relation_quote.strip())
            and bool(self.reviewer_id.strip())
        )


@dataclass(frozen=True)
class RoundRelation:
    decision: str  # SAME | DISTINCT | UNRESOLVED
    reason: str


@dataclass(frozen=True)
class UnresolvedRoundPair:
    left_round_id: str
    right_round_id: str
    reason: str


@dataclass(frozen=True)
class RoundGraphResult:
    edges: tuple[RoundEdge, ...]
    unresolved_pairs: tuple[UnresolvedRoundPair, ...]


def round_relation(
    a: RoundRecord,
    b: RoundRecord,
    valuation_tolerance: float = 0.01,
    *,
    same_round_evidence: tuple[SameRoundEvidence, ...] = (),
) -> RoundRelation:
    """Classify identity without treating absent terms as evidence of equality.

    Explicit source attestations resolve term variants, but never bypass the
    frozen same-issuer, same-instrument, and overlapping-window requirements.
    DISTINCT is a pair classification, not proof of funded status or an outcome.
    """
    if not isfinite(valuation_tolerance) or valuation_tolerance < 0:
        raise ValueError("invalid_valuation_tolerance")
    if not a.canonical_company_id or not b.canonical_company_id:
        return RoundRelation("UNRESOLVED", "company_identity_missing")
    if a.canonical_company_id != b.canonical_company_id:
        return RoundRelation("DISTINCT", "different_company")
    av, bv = a.comparable_valuation, b.comparable_valuation
    ac, bc = a.valuation_cap, b.valuation_cap
    if any(v is not None and (not isfinite(v) or v <= 0) for v in (av, bv, ac, bc)):
        return RoundRelation("UNRESOLVED", "invalid_valuation_terms")
    if not a.instrument_type or not b.instrument_type:
        return RoundRelation("UNRESOLVED", "instrument_missing")
    supported = any(e.supports(a, b) for e in same_round_evidence)
    if a.instrument_type != b.instrument_type:
        if supported:
            return RoundRelation("UNRESOLVED", "same_round_evidence_instrument_conflict")
        return RoundRelation("DISTINCT", "different_instrument")
    if not _windows_overlap(a, b):
        if supported:
            return RoundRelation("UNRESOLVED", "same_round_evidence_window_conflict")
        return RoundRelation("DISTINCT", "nonoverlapping_windows")
    if supported:
        return RoundRelation("SAME", "reviewed_same_round_source")
    if ac != bc:
        return RoundRelation("UNRESOLVED", "cap_terms_unresolved")
    if av is None or bv is None:
        return RoundRelation("UNRESOLVED", "priced_terms_missing")
    denom = max(abs(av), abs(bv), 1.0)
    if abs(av - bv) / denom <= valuation_tolerance:
        return RoundRelation("SAME", "comparable_priced_terms")
    return RoundRelation("DISTINCT", "different_priced_terms")


def same_economic_round(
    a: RoundRecord,
    b: RoundRecord,
    valuation_tolerance: float = 0.01,
    *,
    same_round_evidence: tuple[SameRoundEvidence, ...] = (),
) -> bool:
    """Compatibility predicate: False includes unresolved, not just distinct."""
    return round_relation(
        a, b, valuation_tolerance, same_round_evidence=same_round_evidence
    ).decision == "SAME"

def qualifying_followon(predecessor: RoundRecord, successor: RoundRecord, stepup: float=1.5) -> bool:
    if predecessor.canonical_company_id != successor.canonical_company_id:
        return False
    if predecessor.round_id == successor.round_id:
        return False
    if not predecessor.layer_b_eligible or not successor.layer_b_eligible:
        return False
    if predecessor.completion_date is None or successor.completion_date is None:
        return False
    if successor.completion_date <= predecessor.completion_date:
        return False
    # Comparable priced metrics only. A valuation cap is deliberately ignored.
    if predecessor.comparable_valuation is None or successor.comparable_valuation is None:
        return False
    if any(not isfinite(v) or v <= 0
           for v in (predecessor.comparable_valuation, successor.comparable_valuation)):
        return False
    return successor.comparable_valuation >= stepup * predecessor.comparable_valuation

def build_round_graph(
    rounds: list[RoundRecord],
    *,
    same_round_evidence: tuple[SameRoundEvidence, ...] = (),
) -> RoundGraphResult:
    """Build only resolved graph edges and retain ambiguous pairs for review.

    Source-backed amendment chains may be transitive. Inferred priced matches
    require complete-link agreement, preventing tolerance drift. Components
    touched by an unresolved pair emit no NEXT_ROUND edges; excluded components
    are not bypassed to manufacture a follow-on. This does not admit Layer B.
    """
    if len({r.round_id for r in rounds}) != len(rounds):
        raise ValueError("duplicate_round_id")
    by_company: dict[str, list[RoundRecord]] = {}
    for r in rounds:
        by_company.setdefault(r.canonical_company_id, []).append(r)
    edges = []
    unresolved = []
    for company in sorted(by_company):
        rs = sorted(by_company[company], key=lambda x: (x.first_live_date, x.round_id))
        groups = {i: {i} for i in range(len(rs))}
        owner = list(range(len(rs)))
        relations = {
            (i, j): round_relation(rs[i], rs[j], same_round_evidence=same_round_evidence)
            for i in range(len(rs)) for j in range(i + 1, len(rs))
        }

        def relation(i: int, j: int) -> RoundRelation:
            return relations[min(i, j), max(i, j)]

        def merge(i: int, j: int) -> None:
            left, right = owner[i], owner[j]
            if left == right:
                return
            # Keep deterministic earliest-origin attribution.
            keep, drop = min(left, right), max(left, right)
            for k in groups[drop]:
                owner[k] = keep
            groups[keep].update(groups.pop(drop))
            edges.append(RoundEdge(rs[i].round_id, rs[j].round_id,
                                   "COHOST_SAME_ROUND", rs[i].platform != rs[j].platform, False))

        # Explicit adjacent amendment relations can preserve a whole chain even
        # when its first and last representations do not directly overlap.
        for (i, j), rel in relations.items():
            if rel.decision == "SAME" and rel.reason == "reviewed_same_round_source":
                merge(i, j)
        for (i, j), rel in relations.items():
            if rel.decision != "SAME" or owner[i] == owner[j]:
                continue
            if all(relation(a, b).decision == "SAME"
                   for a in groups[owner[i]] for b in groups[owner[j]]):
                merge(i, j)

        held_groups = set()
        for (i, j), rel in relations.items():
            if owner[i] == owner[j]:
                continue
            if rel.decision in {"UNRESOLVED", "SAME"}:
                reason = rel.reason if rel.decision == "UNRESOLVED" else "inconsistent_round_cluster"
                unresolved.append(UnresolvedRoundPair(rs[i].round_id, rs[j].round_id, reason))
                held_groups.update((owner[i], owner[j]))
        ordered = sorted(groups)
        for left, right in zip(ordered, ordered[1:]):
            if left in held_groups or right in held_groups:
                continue
            a, b = rs[left], rs[right]
            edges.append(RoundEdge(a.round_id, b.round_id, "NEXT_ROUND",
                                   a.platform != b.platform, qualifying_followon(a, b)))
    return RoundGraphResult(tuple(edges), tuple(unresolved))


def next_round_edges(
    rounds: list[RoundRecord],
    *,
    same_round_evidence: tuple[SameRoundEvidence, ...] = (),
) -> list[RoundEdge]:
    """Compatibility edge list; use build_round_graph for unresolved diagnostics."""
    return list(build_round_graph(rounds, same_round_evidence=same_round_evidence).edges)

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
