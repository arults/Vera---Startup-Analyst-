"""Synthetic review oracle: exact-rational weighted full transition matrices.

No estimator, derivative, bootstrap, or reporting routines are imported. Only
prepared input attributes are read; all state labels are declared here.
"""
from fractions import Fraction


STATES = ('operating_pre_success', 'operating_post_success',
          'terminal_success_exit', 'acquisition_value_unknown', 'closure')


def weighted_occupancy(histories, horizon, weights=None):
    weights = [Fraction(w) for w in (weights if weights is not None else [1] * len(histories))]
    total = sum(weights)
    initial = [sum(w for h, w in zip(histories, weights) if h.initial_state.value == state) / total
               for state in STATES]
    matrix = [[Fraction(i == j) for j in range(5)] for i in range(5)]
    times = sorted({tr.time for h in histories for tr in h.transitions if tr.time <= horizon})
    for time in times:
        risks = dict.fromkeys(STATES, Fraction(0))
        counts = {}
        for history, weight in zip(histories, weights):
            prior = [tr for tr in history.transitions if tr.time < time]
            state = prior[-1].destination.value if prior else history.initial_state.value
            if history.observation_end >= time:
                risks[state] += weight
            for transition in history.transitions:
                if transition.time == time:
                    pair = transition.source.value, transition.destination.value
                    counts[pair] = counts.get(pair, Fraction(0)) + weight
        step = [[Fraction(i == j) for j in range(5)] for i in range(5)]
        for (source, destination), count in counts.items():
            i, j = STATES.index(source), STATES.index(destination)
            hazard = count / risks[source]
            step[i][i] -= hazard
            step[i][j] += hazard
        matrix = [[sum(matrix[i][k] * step[k][j] for k in range(5))
                   for j in range(5)] for i in range(5)]
    probabilities = {STATES[j]: sum(initial[i] * matrix[i][j] for i in range(5))
                     for j in range(5)}
    return probabilities, probabilities[STATES[0]] + probabilities[STATES[1]]
