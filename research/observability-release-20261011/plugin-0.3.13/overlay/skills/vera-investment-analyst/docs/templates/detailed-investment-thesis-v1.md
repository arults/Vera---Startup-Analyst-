# Vera detailed investment thesis template v1.1.0

Use with the existing Vera research and calibration gates; complete every section. Brackets are fields to resolve, never facts or numerical defaults.

## Decision and evidence limits
- Company, canonical identity, security/tranche, source, analysis date and data cutoff: [ ]
- Decision and price/terms that change it: [ ]
- Research depth, coverage classification and sufficiency score: [ ]
- Probability calibration status and actual validation evidence: [ ]
- Highest-value unknown, thesis fragility, blocking gaps: [ ]
- Operational run ID, company-analysis ID, plugin/contract version and UTC start: [ ]

## Mandatory investor-return panel
Estimand: P(net realized investor MOIC >= k at [horizon/date] measured from [entry date]). Unconditional over all paths, including failure and no liquidity. Net realized MOIC means [cash distributions net of explicitly specified fees/carry/FX/taxes treatment] / [initial plus specified follow-on invested capital]. Unrealized marks are excluded. Explain future funding commitments and denominator timing.

| Threshold | Probability/status | Uncertainty and interpretation | How derived and sources | Independent verifier feedback | JEV feedback | Gaps/resolution |
|---|---|---|---|---|---|---|
| 10x | [estimate or NOT ESTIMABLE] | [interval type/coverage or unavailable] | [row-specific path sum / not estimable reason] | [actual status and findings] | [actual status and findings] | [ ] |
| 25x | [estimate or NOT ESTIMABLE] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 50x | [estimate or NOT ESTIMABLE] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 100x | [estimate or NOT ESTIMABLE] | [ ] | [ ] | [ ] | [ ] | [ ] |

Do not put zero in an unknown field. Probabilities and coherent envelope bounds must be non-increasing across thresholds. Mark any point unsupported by the evidence as unavailable. Do not convert votes, survival rates, company valuation gains, test results, or methodology acceptance into return probabilities.

## Terms and investor cash-flow bridge
Entry price/cap and exact instrument; primary/secondary; cap table/conversion; ownership; future rounds, timing, financing failure and dilution; pro-rata rights and whether exercised; debt; liquidation waterfall and preference seniority; participation/caps; transfer/liquidity restrictions; fees/carry; investor currency/FX; taxes; follow-on contributions; horizon. Cite current applicable legal terms. Distinguish sourced facts and explicit assumptions.

## Return-model provenance and uncertainty
Model/version and reproducible input/output artifact; reference-class population/fit; cohort count and denominator; entry vintages; measured return basis/horizon; outcomes, failures, exclusions, missingness and right-censoring; data cutoff; company-specific updates; scenario definitions/weights and dependence; no-liquidity paths; parameter and model uncertainty; interval/range type and method; calibration status and validation evidence. Unfinished Phase 1D work is not a validated return model.

## Exact arithmetic versus assumptions
Show contractual payout arithmetic only when terms suffice. Otherwise show labelled conditional/approximate hurdle math and missing inputs. Separate mechanical arithmetic from estimated likelihoods. A deterministic return hurdle does not estimate the chance of reaching it.

## Required diligence and causal thesis
Preserve the full existing output contract: Research Coverage Matrix and source gaps; causal gates; reference classes; TAM/SAM/SOM/REM; PMF/traction/distribution/unit economics; independently verified team; competition/moat; capital/financing; technical/regulatory/timing; strongest bear case; contradiction ledger; evidence/provenance audit; sensitivity and decision reversal; question ledger/value of information; final recommendation and price/conditions where it changes.

## Independent review and JEV record
For each review: actual reviewer, scope (generic method or company estimate), timestamp, model/input version, result, critiques, resolutions and unresolved blockers. Attach threshold-specific feedback. When not run, awaiting authority, unavailable or failed, say so. JEV is methodological feedback, not empirical investment calibration. A generic method review cannot establish company-specific verification.

## Next evidence required
List decision-critical missing data, where it may be obtained, which probability/decision it affects, and whether it is public, private, inaccessible, or inherently uncertain. When probabilities are not estimable, say what would make estimation defensible without promising that obtaining the data guarantees calibration.

### Accounting and observation cautions
Use the cumulative cash-flow ratio at the stated horizon, not an interim peak ratio. A growing follow-on denominator means probabilities need not increase across horizons. Assign fees once, either to capital paid or net distributions. Unobserved proceeds are missing/censored, not zero. Verified zero distributions at a fully observed horizon do not establish economic failure or worthless remaining holdings.

The MOIC annualization shortcut assumes one initial contribution and one terminal distribution. Multiple cash flows require dated cash-flow IRR/XIRR if a meaningful solution exists.

Publication status: [DRAFT / RELEASED]. Before released numeric conclusions, both actual company-estimate reviews must pass against the matching model/input version with no unresolved material review or estimation-basis blockers. Pending, generic-only, stale or adverse reviews block numerical release.
A final detailed thesis uses the RELEASED gate. If required reviews are unavailable, unauthorized, pending, stale or materially adverse, show all four rows with abstention and precise reasons. Internal draft estimates must not be presented as final probabilities.

## Operational metrics (mandatory for this company/run)
Follow `../../references/run-metrics-contract-v0.1.0.md`. Run ID: [ ]. Observation cutoff: [UTC timestamp and final/pre-response snapshot]. Outcome: [completed/failed/cancelled/blocked]. Instrumentation: [actual collector/hook/manual ledger, version and limits].

| Metric | Value and unit | Basis / coverage | Scope, coverage and provenance |
|---|---|---|---|
| Tokens used | [total tokens, or UNAVAILABLE; input/output and cached-input breakdown when exposed] | [measured/estimated; complete/partial/unavailable] | [included parent/workers/reviews/retries; usage source and missing calls] |
| Total tool invocations | [invocation count, or UNAVAILABLE; distinct-tool count separately] | [measured/estimated; complete/partial/unavailable] | [counting boundary, retries/errors, observed event range and gaps] |
| Wall-clock latency | [seconds, or UNAVAILABLE] | [measured/estimated; complete/partial/unavailable] | [start/cutoff, waits and parallel work; not summed worker durations] |
| Total cost | [amount + currency, or UNAVAILABLE] | [actual billed/estimated; complete/partial/unavailable] | [billing source or rate-card version/date; model/tool charges, allocation, known subtotal and missing charges] |
| Memory used (peak RAM/RSS) | [bytes or MiB, or UNAVAILABLE] | [measured; complete/partial/unavailable] | [process/container scope, sampler/high-water method and interval; never context tokens or stored bytes] |

Keep all five rows even if all values are unavailable. Unknown numeric fields are `null`, not zero. Report partial figures as observed subtotals/limited scope; disclose whether final-response generation is included. Do not label a sum of independent process peaks as concurrent RAM. Optional context-token and persistent-storage measurements belong in separately named rows. Include a private machine-readable ledger/summary reference only if it exists and the audience is authorized. Public examples must be synthetic or expressly authorized; no raw prompts or sensitive run data.

