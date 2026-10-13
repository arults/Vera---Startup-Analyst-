"""Review-owned fixture generation; no implementation dependency beyond input types."""
import random
from aj_explicit_history import State as S, History as H, Transition as T

def random_histories(seed, count=100):
    rng=random.Random(seed)
    terminals=[S.SUCCESS_EXIT,S.ACQUISITION_UNKNOWN,S.CLOSURE]
    for case in range(count):
        n=rng.randint(1,18)
        cluster_count=rng.randint(1,n)
        rows=[]
        for i in range(n):
            initial=rng.choice([S.PRE,S.PRE,S.PRE,S.POST])
            end=rng.randint(0,8)
            transitions=[]
            if rng.random()<.75:
                time=rng.randint(0,end)
                destination=rng.choice(terminals+([S.POST] if initial==S.PRE else []))
                transitions.append(T(time,initial,destination))
                if destination==S.POST and time<end and rng.random()<.6:
                    transitions.append(T(rng.randint(time+1,end),S.POST,rng.choice(terminals)))
            rows.append(H(f'round:{case}:{i}',f'company:{rng.randrange(cluster_count)}',initial,end,tuple(transitions)))
        yield rows

def mixed_fixture():
    return [
       H('baseline','A',S.POST,9,(T(1,S.POST,S.CLOSURE),)),
       H('success_closed','A',S.PRE,9,(T(1,S.PRE,S.POST),T(2,S.POST,S.CLOSURE))),
       H('early_censor','A',S.PRE,1),
       H('success_exit','B',S.PRE,9,(T(3,S.PRE,S.SUCCESS_EXIT),)),
       H('competing','C',S.PRE,9,(T(3,S.PRE,S.ACQUISITION_UNKNOWN),)),
       H('late_censor','D',S.PRE,9)]
