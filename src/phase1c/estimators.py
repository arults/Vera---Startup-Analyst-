from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, sqrt
from random import Random
from statistics import NormalDist

from .outcomes import State

@dataclass(frozen=True)
class TimedTransition:
    subject_id: str
    company_id: str
    time: float
    source: State
    destination: State

@dataclass(frozen=True)
class SubjectFollowup:
    subject_id: str
    company_id: str
    censor_time: float

@dataclass(frozen=True)
class OccupancyPoint:
    time: float
    probabilities: dict[str,float]
    risk_by_state: dict[str,int]

@dataclass(frozen=True)
class CompetingRiskObservation:
    subject_id: str
    company_id: str
    time: float
    cause: str | None  # None = right censor

@dataclass(frozen=True)
class CIFPoint:
    time: float
    at_risk: int
    target_events: int
    all_events: int
    event_free_survival: float
    cumulative_incidence: float

TRANSIENT=(State.OPERATING_PRE_SUCCESS,State.OPERATING_POST_SUCCESS)
ALL_STATES=(
    State.OPERATING_PRE_SUCCESS,
    State.OPERATING_POST_SUCCESS,
    State.TERMINAL_SUCCESS_EXIT,
    State.ACQUISITION_VALUE_UNKNOWN,
    State.CLOSURE,
)

def _eye(n):
    return [[1.0 if i==j else 0.0 for j in range(n)] for i in range(n)]

def _matmul(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]

def aalen_johansen_occupancy(transitions: list[TimedTransition], followup: list[SubjectFollowup]) -> list[OccupancyPoint]:
    """Dependency-free Aalen-Johansen state-occupancy engine."""
    ids={f.subject_id for f in followup}
    if len(ids)!=len(followup):
        raise ValueError("duplicate_subject_followup")
    by_subject={s:[] for s in ids}
    for tr in sorted(transitions,key=lambda x:(x.time,x.subject_id)):
        if tr.subject_id not in by_subject:
            raise ValueError("transition_without_followup")
        by_subject[tr.subject_id].append(tr)

    state={s:State.OPERATING_PRE_SUCCESS for s in ids}
    fup={f.subject_id:f for f in followup}
    index={s:i for i,s in enumerate(ALL_STATES)}
    P=_eye(len(ALL_STATES))
    points=[]
    times=sorted({tr.time for tr in transitions})

    for t in times:
        risk={s:0 for s in ALL_STATES}
        for sid,current in state.items():
            if fup[sid].censor_time >= t:
                risk[current]+=1

        counts={}
        at_t=[tr for tr in transitions if tr.time==t]
        for tr in at_t:
            if fup[tr.subject_id].censor_time < t:
                raise ValueError("event_after_censor")
            if state[tr.subject_id] != tr.source:
                raise ValueError("source_state_mismatch")
            counts[(tr.source,tr.destination)]=counts.get((tr.source,tr.destination),0)+1

        step=_eye(len(ALL_STATES))
        for source in TRANSIENT:
            n=risk[source]
            outgoing=[((a,b),c) for (a,b),c in counts.items() if a==source]
            if not outgoing:
                continue
            if n<=0:
                raise ValueError("event_with_empty_risk_set")
            total=sum(c for _,c in outgoing)
            if total>n:
                raise ValueError("events_exceed_risk_set")
            step[index[source]][index[source]]-=total/n
            for (a,b),c in outgoing:
                step[index[a]][index[b]]+=c/n

        P=_matmul(P,step)
        for tr in at_t:
            state[tr.subject_id]=tr.destination

        initial_row=P[index[State.OPERATING_PRE_SUCCESS]]
        probs={ALL_STATES[i].value:initial_row[i] for i in range(len(ALL_STATES))}
        points.append(OccupancyPoint(t,probs,{k.value:v for k,v in risk.items()}))
    return points

def independent_operating_probability(point: OccupancyPoint) -> float:
    return (
        point.probabilities.get(State.OPERATING_PRE_SUCCESS.value,0.0)
        + point.probabilities.get(State.OPERATING_POST_SUCCESS.value,0.0)
    )

def competing_risk_cif(observations: list[CompetingRiskObservation], target_cause: str) -> list[CIFPoint]:
    """
    Aalen-Johansen cumulative incidence for a first-event estimand.
    Other non-null causes are competing events; None is right censoring.
    """
    if not observations:
        return []
    if any(o.time < 0 for o in observations):
        raise ValueError("negative_followup")
    times=sorted({o.time for o in observations if o.cause is not None})
    s=1.0
    cif=0.0
    out=[]
    for t in times:
        n=sum(1 for o in observations if o.time >= t)
        all_events=sum(1 for o in observations if o.time==t and o.cause is not None)
        target=sum(1 for o in observations if o.time==t and o.cause==target_cause)
        if n<=0 or all_events<=0:
            continue
        cif += s * target/n
        s *= 1-all_events/n
        out.append(CIFPoint(t,n,target,all_events,s,cif))
    return out

def cif_at_horizon(observations: list[CompetingRiskObservation], target_cause: str, horizon: float) -> float:
    pts=[p for p in competing_risk_cif(observations,target_cause) if p.time<=horizon]
    return pts[-1].cumulative_incidence if pts else 0.0

def cluster_bootstrap_indices(company_ids: list[str], n_boot: int=1000, seed: int=0) -> list[list[int]]:
    """Return row indices from resampling canonical companies, preserving all rounds of each sampled company."""
    groups={}
    for i,c in enumerate(company_ids):
        groups.setdefault(c,[]).append(i)
    companies=sorted(groups)
    rng=Random(seed)
    reps=[]
    for _ in range(n_boot):
        picked=[rng.choice(companies) for _ in companies]
        idx=[]
        for c in picked:
            idx.extend(groups[c])
        reps.append(idx)
    return reps

def bootstrap_cif_interval(
    observations: list[CompetingRiskObservation],
    target_cause: str,
    horizon: float,
    n_boot: int=1000,
    seed: int=0,
    alpha: float=0.05,
) -> tuple[float,float,float]:
    if not observations:
        raise ValueError("empty_observations")
    point=cif_at_horizon(observations,target_cause,horizon)
    reps=cluster_bootstrap_indices([o.company_id for o in observations],n_boot=n_boot,seed=seed)
    values=[]
    for idx in reps:
        sample=[
            CompetingRiskObservation(
                subject_id=f"boot{j}:{observations[i].subject_id}",
                company_id=f"boot{j}:{observations[i].company_id}",
                time=observations[i].time,
                cause=observations[i].cause,
            )
            for j,i in enumerate(idx)
        ]
        values.append(cif_at_horizon(sample,target_cause,horizon))
    lo,hi=percentile_interval(values,alpha)
    return point,lo,hi

def percentile_interval(values: list[float], alpha: float=0.05) -> tuple[float,float]:
    if not values:
        raise ValueError("empty_bootstrap")
    xs=sorted(values)
    lo_i=max(0,min(len(xs)-1,int((alpha/2)*len(xs))))
    hi_i=max(0,min(len(xs)-1,int((1-alpha/2)*len(xs))-1))
    return xs[lo_i],xs[hi_i]

def km_greenwood_interval(durations: list[float], terminal_event: list[bool], horizon: float, alpha: float=0.05) -> tuple[float,float,float]:
    """Analytic diagnostic interval for independent-operation survival at a landmark."""
    pairs=sorted(zip(durations,terminal_event))
    event_times=sorted({t for t,e in pairs if e and t<=horizon})
    s=1.0; green=0.0
    for t in event_times:
        n=sum(1 for x,e in pairs if x>=t)
        d=sum(1 for x,e in pairs if x==t and e)
        if n<=0: continue
        s*=1-d/n
        if n-d>0:
            green+=d/(n*(n-d))
    if s in (0.0,1.0) or green==0:
        return s,s,s
    z=NormalDist().inv_cdf(1-alpha/2)
    se=sqrt(green)/abs(log(s))
    ll=log(-log(s))
    lo=exp(-exp(ll+z*se))
    hi=exp(-exp(ll-z*se))
    return s,lo,hi

def interval_disagreement(primary: tuple[float,float], diagnostic: tuple[float,float], tolerance: float=0.10) -> bool:
    return abs(primary[0]-diagnostic[0])>tolerance or abs(primary[1]-diagnostic[1])>tolerance
