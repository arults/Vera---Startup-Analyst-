import csv, math
from datetime import date

def read_csv(path):
    with open(path,newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def kaplan_meier(manifest_path,outcomes_path,start_field="funding_close_date",listing_continue_to=None):
    cohort={r["offering_key"]:r for r in read_csv(manifest_path)}
    obs=read_csv(outcomes_path)
    samples=[]
    for o in obs:
        start=date.fromisoformat(cohort[o["offering_key"]][start_field])
        end=date.fromisoformat(o["observation_date"])
        if listing_continue_to and o["event_type"]=="listing_censor":
            end=date.fromisoformat(listing_continue_to)
        days=(end-start).days
        if days < 0:
            raise ValueError(f"negative follow-up: {o['offering_key']}")
        event=1 if o["event_type"]=="failure" else 0
        samples.append((days,event,o["offering_key"],o["event_type"]))
    times=sorted({t for t,e,k,et in samples if e})
    s=1.0; green=0.0; curve=[]
    for t in times:
        n=sum(1 for x,e,k,et in samples if x>=t)
        events=sum(1 for x,e,k,et in samples if x==t and e)
        if n<=0 or events<=0: continue
        s_prev=s
        s*=1-events/n
        if n-events>0: green += events/(n*(n-events))
        if 0<s<1 and green>0:
            z=1.959963984540054
            se_loglog=math.sqrt(green)/abs(math.log(s))
            ll=math.log(-math.log(s))
            lo=math.exp(-math.exp(ll+z*se_loglog))
            hi=math.exp(-math.exp(ll-z*se_loglog))
        elif s==1: lo=hi=1.0
        else: lo=hi=0.0
        curve.append({
            "days":t,"years":t/365.25,"at_risk":n,"events":events,
            "survival_before":s_prev,"survival":s,
            "ci95_lower":lo,"ci95_upper":hi
        })
    return curve

def yearly_summary(manifest_path,outcomes_path,start_field="funding_close_date",listing_continue_to=None,years=range(1,7)):
    cohort={r["offering_key"]:r for r in read_csv(manifest_path)}
    obs=read_csv(outcomes_path)
    samples=[]
    for o in obs:
        start=date.fromisoformat(cohort[o["offering_key"]][start_field])
        end=date.fromisoformat(listing_continue_to) if listing_continue_to and o["event_type"]=="listing_censor" else date.fromisoformat(o["observation_date"])
        samples.append(((end-start).days,1 if o["event_type"]=="failure" else 0))
    curve=kaplan_meier(manifest_path,outcomes_path,start_field,listing_continue_to)
    result=[]
    for y in years:
        horizon=round(y*365.25)
        past=[r for r in curve if r["days"]<=horizon]
        if past:
            p=past[-1]
            surv,lo,hi=p["survival"],p["ci95_lower"],p["ci95_upper"]
        else:
            surv=lo=hi=1.0
        result.append({
            "year":y,
            "at_risk":sum(1 for t,e in samples if t>=horizon),
            "failures_cumulative":sum(1 for t,e in samples if e and t<=horizon),
            "censored_cumulative":sum(1 for t,e in samples if not e and t<=horizon),
            "survival":surv,"ci95_lower":lo,"ci95_upper":hi,
        })
    return result

def verify_curve(curve):
    vals=[r["survival"] for r in curve]
    s01=all(0<=x<=1 and 0<=r["ci95_lower"]<=r["ci95_upper"]<=1 for x,r in zip(vals,curve))
    s02=all(vals[i]<=vals[i-1]+1e-15 for i in range(1,len(vals)))
    expected=1.0; s03=True; last_n=None
    for r in curve:
        n=r["at_risk"]; e=r["events"]
        if n<=0 or e<=0 or e>n or (last_n is not None and n>last_n):
            s03=False; break
        expected*=1-e/n
        if abs(expected-r["survival"])>1e-12:
            s03=False; break
        last_n=n
    return [
        {"id":"S01_PROBABILITY_BOUNDS","passed":s01},
        {"id":"S02_NON_INCREASING","passed":s02},
        {"id":"S03_RISK_SET_ARITHMETIC","passed":s03},
    ]
