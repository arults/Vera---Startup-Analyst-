"""Independent exact-rational weighted competing-risks reference for review.

Does not call production first-event extraction, success estimator, derivative,
resampling, or reporting functions. Inputs are explicit prepared histories only.
"""
from fractions import Fraction


def weighted_reference(histories, horizon, weights=None):
    if weights is None:
        weights = [Fraction(1) for _ in histories]
    weights = list(map(Fraction, weights))
    total = sum(weights)
    baseline = sum(w for h,w in zip(histories,weights)
                   if h.initial_state.value == 'operating_post_success') / total
    event_rows = []
    for h,w in zip(histories,weights):
        if h.initial_state.value == 'operating_post_success':
            continue
        assert h.initial_state.value == 'operating_pre_success'
        if h.transitions:
            tr = h.transitions[0]
            event_rows.append((tr.time,
                'success' if tr.destination.value in ('operating_post_success','terminal_success_exit') else 'competing', w))
        else:
            event_rows.append((h.observation_end,'censored',w))
    alive = 1 - baseline
    success = competing = Fraction(0)
    event_times = sorted({t for t,c,w in event_rows if c != 'censored' and t <= horizon})
    for time in event_times:
        denominator = sum(w for t,c,w in event_rows if t >= time)
        success_count = sum(w for t,c,w in event_rows if t == time and c == 'success')
        competing_count = sum(w for t,c,w in event_rows if t == time and c == 'competing')
        success += alive * success_count / denominator
        competing += alive * competing_count / denominator
        alive *= 1 - (success_count + competing_count) / denominator
    return {'baseline_qualified_fraction':baseline, 'incident_success_cif':success,
            'ever_qualified_probability':baseline+success, 'competing_cif':competing,
            'event_free_probability':alive}


def finite_difference(histories, horizon, target, indices, epsilon=Fraction(1,100000)):
    lo = [1-epsilon if i in indices else Fraction(1) for i in range(len(histories))]
    hi = [1+epsilon if i in indices else Fraction(1) for i in range(len(histories))]
    return float((weighted_reference(histories,horizon,hi)[target] -
                  weighted_reference(histories,horizon,lo)[target])/(2*epsilon))
