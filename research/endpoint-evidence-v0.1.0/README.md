# Endpoint evidence requirements v0.1.0

A small, additive requirements planner for three different questions. Select the endpoint before collecting evidence. Optional fields are absent from its work queue; conditional fields first ask whether the fact matters. It neither authenticates evidence nor certifies statistical readiness.

## What changes

The older preparation audit is an inventory for exact first-success histories. It adds six review groups to every row but **does not say every listed field must be filled**. Applying that inventory as a universal checklist over-collects evidence. This package classifies all 38 distinct legacy fields in `legacy-field-map.json` and provides a selectable queue.

| Existing question | Operating survival only | Frozen qualifying-company-success composite | Investor cash MOIC |
|---|---|---|---|
| Round identity/funded origin | Keep for funded-round frame; adequate aggregate evidence can suffice | Keep index-round identity and funded origin | Historical funded position, or exact proposed entry for forecast |
| Initial PRE/POST success | Optional; keep independent-operation entry status | Required index-relative baseline and incident policy | Only if relevant to position, model or selection |
| Valuation/success qualification | Optional for nonterminal success | Actual comparable prices required only for priced-follow-on branch | Company valuation/cap is not cash return; model rights and net cash |
| Full/exact event chronology | Relevant operation transitions only; exact dates remain required by exact-history caller | Relevant first-success/competing history | Relevant contributions/distributions or joint forecast paths |
| Observation endpoint | Affirmative operating follow-up and terminal facts | Success ascertainment; an observed absorbing event can resolve that endpoint | Cash ascertainment for labels; historical calibration and information cutoff for forecasts |
| Cohort assignment | Keep frame, denominator and clustering | Keep frame, denominator and clustering | Keep target population/position policy and unknown outcomes |

Detailed founder biographies, customer quotations, unused tags, total funds raised, every contract, full cap tables and unrelated later events become optional enrichment unless they identify the target/frame, are used in the selected model, or could materially change the decision. Optional does not mean statistically irrelevant forever. Declare relevance before observing outcomes and revisit contradictions/new evidence. Operating metrics may be useful forecast predictors even when unnecessary for an observed survival label.

Literal duplicate review columns are not additional research tasks: one source-bound adjudication can support several facts. Retain its exact claim/input/policy binding. Recheck changed dependencies and contradictions, with independent cohort-level checks for systematic mistakes. A single actual review can cover the four nested investor thresholds when coverage and exact versions are explicit; it cannot be replaced by generic methodology approval.

## Three examples

1. A company has a verified funded close and dated operating evidence, but private individual investor agreements. The survival queue asks for its identity, funded origin, entry/operation/terminal observations and observation assumptions. It does not request payout, cap-table or exit-allocation evidence. Whether the operating-only method can use these data is still a separate question.
2. A company has an independently qualifying IPO. A documented nonapplicable valuation-multiple branch removes that price-comparison question. A doubled SAFE cap does not clear the priced-equity branch. An acquisition with unknown consideration can end independent operation while success and investor return remain unresolved.
3. An investor-return forecast keeps exact proposed terms, calibrated joint cash-return mechanics, and actual company-specific independent/JEV release reviews. It does not demand future payout records. A historical 12x net-cash label instead requires verified contributed capital and complete distributions at H; a full cap table need not be reconstructed if those net cash facts already resolve the ratio.

Company success remains the frozen **typed composite**, not simply company value growth: priced-equity follow-on >=1.5x comparable index valuation, IPO/direct listing, qualifying evidenced acquisition consideration/value, or profitable exit with inferable gross investor MOIC >1x. Investor targets remain unconditional **net realized cash MOIC at H >=10/25/50/100**, with failure and nonliquidity retained. No SAFE cap, paper markup, or survival label can replace them.

## Use

Standard library, Python 3.10+. No network, private ledger read, output-directory mutation or numerical estimation.

    python -B -m unittest discover -s research/endpoint-evidence-v0.1.0 -v
    python -B research/endpoint-evidence-v0.1.0/requirements.py path/to/spec.json

`spec.schema.json` describes the six selection keys; runtime checks reject incoherent combinations. `build_plan(...)` returns REQUIRED, CONDITIONAL and OPTIONAL lists. `work_queue(plan, applicability)` omits optional items and explicitly nonapplicable conditions. An unknown condition asks a relevance question, not a wholesale contract/source search. The queue rejects a modified or stale plan instead of trusting edited requirement lists. TRUE/FALSE applicability declarations need rationale and a review reference; they remain supplied declarations, not authenticated facts. Do not infer a pass from populated columns, a short queue, or an asserted review reference.

Forecast plans use only history available at the prediction cutoff and historical calibration labels; future operating, qualifying-success and payout facts are modeled outcomes, never required observations.

An interval-capable or horizon-status selection does **not** implement that estimator. Interval facts remain intervals; material uncertain order remains unresolved. The existing exact-history caller retains its exact timing rules. A separately validated operating-only method may collapse PRE/POST success for operating occupancy, but this package does not change the frozen multistate engine or assume noninformative censoring.

## Status and gates

Implemented and synthetically tested: requirements selection and queue filtering. Not implemented: empirical ingestion, source adjudication, a new survival/return estimator, active caller/UI integration, or a new calibrated prior. Frozen audit, policy, cohorts, outputs, active plugin 0.3.13 and promoted framework 0.5.0 remain unchanged. Use this package to plan new endpoint-specific work now; adoption into any empirical caller requires an explicit versioned change and endpoint-specific validation.

The current JEV conceptual review used generic requirements and fictional examples only, with no private code, dependency or company/ledger export. It chose a guarded pilot (choice probability 0.99, reported confidence 0.98) and correctly marked all-row retention necessary but not sufficient for identified estimates. Those are reviewer outputs, not investment probabilities or code approval. The previous private-source export hold is unaffected. Exact request/response receipts are retained with the delivery evidence.

## Small pilot and measured acceptance

Use 12 existing source packets, selected prospectively across six patterns (two each): straightforward operating evidence; only nonterminal financing; unknown-value acquisition; stale/lost follow-up; interval/tied timing; repeat-company/index ambiguity. Reuse existing evidence before searching. Keep the same input set for all three queues and retain all 12 dispositions. This is a usability/safety pilot, not a population sample or probability-validation study.

Measure before/after unique requested facts, avoidable source requests and elapsed analyst time; report observed deltas rather than promise speed gains. Independent reviewers check every case.

Accept queue adoption only if: (a) survival requests zero investor-payout/cap-table/exit-allocation facts unless a documented identity/terminal/observation ambiguity makes them necessary; (b) 12/12 rows retained with unchanged source bindings and unresolved facts; (c) zero false upgrades from unknown to success/closure/cash return, zero SAFE-cap-to-priced-value substitutions and zero future-label requirements for forecasts; (d) all timing-incompatible cases among the 12, when present, retain HOLD or a separately supported method; (e) all material reviewer disagreements resolved, and no frozen estimate or denominator changes; (f) an observed reduction in irrelevant requests, with actual review time reported. If there is no useful reduction, simplify the planner before adoption. No numeric-prior promotion follows from passing this pilot.
