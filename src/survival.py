import csv, math
from datetime import date

def read_csv(path):
    with open(path,newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def kaplan_meier(manifest_path,outcomes_path):
    cohort={r["offering_key"]:r for r in read_csv(manifest_path)}
    obs=read_csv(outcomes_path)
    samples=[]
    for o in obs:
        start=date.fromisoformat(cohort[o["offering_key"]]["funding_close_date"])
        end=date.fromisoformat(o["observation_date"])
        days=(end-start).days
        event=1 if o["event_type"]=="failure" else 0
        samples.append((days,event,o["offering_key"]))
    times=sorted({t for t,e,k in samples if e})
    s=1.0; green=0.0; curve=[]
    for t in times:
        n=sum(1 for x,e,k in samples if x>=t)
        events=sum(1 for x,e,k in samples if x==t and e)
        cens=sum(1 for x,e,k in samples if x==t and not e)
        if n<=0 or events<=0: continue
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
        curve.append({"days":t,"years":t/365.25,"at_risk":n,"events":events,"censored_at_time":cens,"survival":s,"ci95_lower":lo,"ci95_upper":hi})
    return curve

def verify_curve(curve):
    vals=[r["survival"] for r in curve]
    s01=all(0<=x<=1 for x in vals)
    s02=all(vals[i]<=vals[i-1]+1e-15 for i in range(1,len(vals)))
    s03=all(r["at_risk"]>=r["events"]>=1 for r in curve)
    return [{"id":"S01_PROBABILITY_BOUNDS","passed":s01},{"id":"S02_NON_INCREASING","passed":s02},{"id":"S03_RISK_SET_ARITHMETIC","passed":s03}]
