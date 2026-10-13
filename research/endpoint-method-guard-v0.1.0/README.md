# Endpoint method guard v0.1.0

A planning-only compatibility layer for one concrete frozen route: historical,
funded-round independent operating-state occupancy from
`explicit-history-statistics-v0.2.0`, under the bound `PHASE_1C_SPEC.md` policy.
No existing planner, empirical caller, history, estimator, policy or plugin is changed.

## Why this is necessary

The endpoint planner correctly makes nonterminal success optional for a separately
validated operating-only method. The frozen multistate implementation is not that
method. It uses separate PRE and POST risk sets, so summing their output probabilities
does not make their input histories dispensable.

In a fictional example, A qualifies at time 0.5 and is observed through 3, B is
censored at 1, and C closes at 2; all start PRE. At horizon 2.5 the frozen operating
occupancy is 1/3. Erasing A's success transition changes it to 1/2. Both runs have
numerical risk support. A second example shows that collapse can hide unsupported
POST mass. Neither example estimates a real-world probability.

## Contract

`bind_method` verifies exact planner, engine and policy bytes, then validates the
unmodified endpoint plan. The known method adds six review obligations: native
source policy; index-relative initial state; relevant success/terminal history;
exact timing/order; common entry/round weighting; and observation/identification.
Unknown methods and incompatible frames/purposes return explicit HOLDs.

Investor payout records, full cap tables and unrelated contracts remain absent
from the default survival queue. Initial PRE/POST and a relevant priced-success
predicate are method requirements, not cash-return requirements. A documented
platform-final-completion clock can use sufficient aggregate native close evidence;
this layer does not impose first legal close or every investor's contract.

The result is `BOUND_FOR_REVIEW_NOT_EVIDENCE_READY`, never admission. A review
reference string or hash cannot prove a claim. No empirical history is constructed,
estimator called or numeric release authorized. Endpoint and method requirements
must both be satisfied under independently reviewed source and observation rules.

## Reproduce

From the repository root, run:

    python -B -m unittest discover -s research/endpoint-method-guard-v0.1.0 -v
    python -B research/endpoint-method-guard-v0.1.0/run_fictional_pilot.py

The neighboring published planner, frozen engine and `docs/PHASE_1C_SPEC.md` must
match the fixed bindings. The finite fictional pilot executes the unchanged engine
on six valid mathematical examples and records three expected rejections. It never
accepts empirical records. The collapsed examples are explicitly other-model
counterexamples, not an adapter or implementation proposal.

## Adoption decision

This guard can be reviewed as an additive non-admitting research aid. It does not
make the endpoint-only checklist compatible with the frozen empirical caller,
validate an operating-only estimator, or demonstrate comparative research savings.
Real dated operating assertions still need issuer/entry, history and observation
review. A documentary day tie is not automatically a scientific transition tie;
an access restriction is not a verified historical loss-to-follow-up mechanism.

Any production adoption, source admission or new method requires its own exact
review. The frozen method and its existing holds remain controlling for this guard's
declared native-only route. For new external research facts, use the prospective
[v1.2.0 source amendment](../../docs/EXTERNAL_SOURCE_ADMISSION_v1.2.0.md) and its
independent claim/source reviews instead. Do not route those facts through this
guard as native-compatible or change its policy/engine pins to bypass review.
The guard implementation and frozen specification bytes remain unchanged.
