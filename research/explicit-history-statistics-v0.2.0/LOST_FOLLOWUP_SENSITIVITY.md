# Lost-to-platform event-assignment sensitivity candidate

**Additive, source-neutral, synthetic-verified implementation. No empirical rates,
canonical edits, third-party disclosures, or promotion.**

This module implements one bounded original-spec component: constructing explicit
optimistic/adverse missing-event scenarios for genuine lost platform follow-up.
It does not replace the primary platform-observed history. It is distinct from
moving an interval-dated event to its start, midpoint, or end.

The frozen specification calls these sensitivity “bounds.” This candidate does
not establish sharp, statistical, or identification bounds. It creates declared
endpoint-local hypothetical histories, not a guaranteed envelope around a true
probability or an AJ estimate. Favorable/adverse labels describe the assumed
missing individual outcome, not a proved monotonic ordering of a later estimator.

## Run

Python 3.10+, standard library only. From this directory:

    python -m unittest -v

From its parent:

    python -m unittest discover -s frozen-lost-followup-sensitivity-candidate-v1 -p 'test_*.py' -v

The 23 producer tests cover all six endpoint/direction combinations, 400 seeded
synthetic prefix-preservation/cap checks, observed success followed by assumed
closure, known terminal paths and future known events, terminal-at-entry success
ambiguity, explicit timing boundaries, mixed complete/blocked records, malformed
classification, duplicate rounds, and finite-time validation. Tests establish
stated transformation behavior, not empirical validity or inferential coverage.

## Prepared input contract

`PreparedFollowup` contains a validated exact `History`, one explicit
`FollowupKind`, and a hard limit on the same analysis time scale. Inputs must be
source-qualified/prepared elsewhere. This code does not classify a silent page,
a missing website, or an absent update as closure or loss of follow-up.

- `LOST`: the final known state is independently operating, the prepared last
  observation is strictly before the hard limit, and source preparation has
  explicitly classified the remaining gap as lost-to-platform follow-up.
- `ADMINISTRATIVE`: the final state is operating and the observed endpoint equals
  its prepared hard administrative limit. This is never reclassified as loss.
- `TERMINAL`: the history ends in an absorbing terminal state, including a terminal
  initial state where explicitly supplied. Calling this history lost is rejected.

Each history retains its economic-round and company identifiers, mandatory initial
state, observed endpoint, and all transitions. All supplied rounds are returned.
No common-calendar mapping is inferred from round-relative times. The global
`extraction_limit` is a supplied ceiling on this synthetic analysis scale; each
round also supplies its own hard limit. A real adapter must derive those limits
from the actual extraction date and each approved origin. Supplying a permissive
number does not authenticate future observations or authorize a mature horizon.

`horizon > extraction_limit` always rejects, even if every input is terminal.
An unresolved operating record whose individual hard limit is before the horizon
is retained unchanged with a blocked status. Already determined first-success or
known absorbing histories remain unchanged, without extending their observation
endpoints. This mathematical endpoint determination does not make the requested
horizon observationally supported.

## Exact endpoint-specific assumptions

Only an eligible lost operating tail ending before the requested horizon is
assigned. The following are separate hypothetical packets, not one jointly
realized company future:

- Independent operating occupancy, optimistic: assume continued independent
  operation to the horizon with no new state transition.
- Independent operating occupancy, adverse: assume closure at an explicitly
  supplied time after the last observed endpoint and no later than the horizon.
- First qualifying success, optimistic: when still PRE, assume a qualifying
  nonterminal PRE→POST event at an explicitly supplied time, then continued
  operation to the horizon. A terminal success exit is not silently substituted.
- First qualifying success, adverse: when still PRE, assume no qualifying success
  and continued operation through the horizon. This is one explicit adverse
  success scenario; it does not additionally assume closure.
- Closure, optimistic: assume continued operation without closure to the horizon.
- Closure, adverse: assume closure at an explicitly supplied time after the last
  observed endpoint and no later than the horizon.

For a closure assignment the hypothetical prepared endpoint stops at that
terminal event. For an assumed operating tail it extends to the horizon. Neither
extension is a new affirmative observation. Endpoint `confirmed_closure_cif`
identifies the primary endpoint being stress-tested; assigned closure is explicitly
hypothetical and is never labeled confirmed platform evidence.

An observed first qualifying success, including one followed by observed closure,
is never erased. Already-qualified first-success records remain unchanged, even
if later operation is lost. An initial POST record requires explicit
`InitialPostPolicy`: `BASELINE_QUALIFIED` declares prior index qualification;
`REJECT` blocks it for incident-only interpretation. Baseline qualification is not
labeled incident success. Terminal initial occupancy alone cannot identify earlier
success, so these records are retained and blocked for the first-success packet.
No round is silently dropped to solve that ambiguity.

## Timing and support safeguards

`assignment_times` is mandatory, including an empty mapping when no event is
assigned. It must name exactly the rows requiring a hypothetical event. Extra
keys, missing keys, times at/before the last observed endpoint, and times after the
horizon reject. There is no hidden epsilon, midpoint, or inferred event date.
A nonterminal success occurring on the last observed day is preserved; a new
hypothetical event must occur strictly later.

A packet contains both each immutable `original` and its separately constructed
`hypothetical` history, row-level reasons, the assumed tail interval, and a
conspicuous hypothetical/non-bound interpretation. `complete` means only that no
row is blocked from the requested transformation. A mixed packet may contain
eligible transformed rows and unchanged blocked rows, but `complete=false` means
it must not be presented as a completed sensitivity or evaluated as a selected
subset. No scalar estimator is provided here.

Crucially, downstream AJ code may see the hypothetical extensions as numerical
risk support. That cannot be advertised as observed support. Preserve the
original-history diagnostics and hypothetical provenance separately. The frozen
no-extrapolation rule still applies to empirical reporting; a scenario assumption
does not defeat a primary/scenario support gate. This module neither adopts nor
changes a reporting, bootstrap-replicate, confidence-interval, or source policy.

## Remaining integration work

Actual use requires reviewed source mapping for genuine loss, hard limits,
initial-state/index-success semantics, origins, and histories; a declared timing
assumption; explicit hypothetical versus observed reporting; and review of any
subsequent estimator/support policy. This packet does not compute rates, intervals,
ascertainment coverage, sharp bounds, or a new scientific target.

Multiple rounds from one company are preserved, but their separate relative-time
assignments need not describe one possible common-calendar company history. A
calendar/source adapter must reconcile that before any company-coherent empirical
sensitivity is claimed. The transformations alone do not close the original
frozen sensitivity obligation end to end or complete Phase 1D.

## Packaging and provenance

The supplied `aj_explicit_history.py` and `first_success.py` are exact source-neutral
dependency snapshots from the statistical candidate. They are included to make this
folder executable on its own, not forked implementations. A consolidated public
bundle may include one hash-matching copy of each. `SOURCE_BINDINGS.json` binds
requirements and dependency snapshots; `MANIFEST.json` binds all deliverable files.
No research records, company facts, source credentials, external calls, actual
missing observations, or empirical calculations were used.
