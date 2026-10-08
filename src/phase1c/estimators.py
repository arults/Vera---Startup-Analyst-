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
    """
    A small dependency-free Aalen-Johansen state-occupancy engine.
    All subjects begin in OPERATING_PRE_SUCCESS at t=0.
    """
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
        # update observed states after using pre-event risk sets
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
