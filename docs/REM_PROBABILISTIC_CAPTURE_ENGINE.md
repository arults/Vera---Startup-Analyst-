# REM v3 — Probabilistic Execution-Constrained Market Capture

Date: 2026-10-08  
Status: **PROMOTE_METHOD** — methodology adopted as a Vera candidate/extension; company-level numeric REM outputs remain calibration-gated.

## Why this upgrade exists
A static fourth layer after TAM/SAM/SOM is redundant because standard SOM already means the share of SAM a company can realistically obtain over a defined horizon given channels, resources and win rate. Vera therefore does **not** use REM as "SOM minus another discount."

REM is redefined as Vera's own probabilistic, execution-constrained **revenue-capture distribution**.

## Market-layer semantics
- **TAM** — theoretical category ceiling.
- **SAM** — serviceable market bound given product, geography, regulation and business-model scope.
- **SOM** — conventional sourced/management obtainable-market estimate; retain for context/comparison only.
- **REM** — Vera's independently modeled posterior distribution over realizable annual net revenue at explicit time horizons.

REM is company-specific, evidence-weighted and operational. Every REM simulation must remain within the corresponding dynamic SAM when measured in consistent units. REM need not equal or sit below a management-provided SOM estimate because SOM is an external estimate, not a binding Vera input.

## Core REM engine
Model each materially different segment/geography/use case separately.

For each segment and time period:
1. define eligible/serviceable population;
2. estimate channel/access reach;
3. constrain opportunity creation by GTM/sales capacity;
4. model conversion using evidence-backed distributions;
5. constrain activation by onboarding/production/service capacity;
6. retain prior customer cohorts using evidence-backed retention/churn;
7. apply realized net pricing/ACV, usage/frequency and collections;
8. aggregate segments after de-duplication.

Financing, technical and regulatory gates belong in Vera's causal scenario graph. REM must be tagged **CONDITIONAL** on those states so the same gate is not multiplied twice downstream.

Use explicit dependency/correlation groups for shared shocks; do not assume uncertain parameters are independent.

## Sector adapters
### SaaS / B2B
Accounts -> reachable pipeline -> sales-cycle conversion -> activated accounts/seats -> retention/expansion -> realized net ARR.

### Consumer
Reachable users -> acquisition/conversion -> purchase frequency -> retention -> realized net ARPU.

### Marketplace
Two-sided supply + demand -> matched transactions -> GMV -> take rate. Output is constrained by the scarcer side.

### Hardware / deep tech / defense
Funded orders/backlog -> qualification/certification -> production capacity/yield -> deliveries -> realized ASP + service revenue.

### Biotech / therapeutics
Pre-commercial licensing/milestones are modeled separately. Post-approval capture uses eligible/diagnosed patients -> access/reimbursement -> adoption -> treatment capacity -> net realized price, **conditional** on the clinical/regulatory state so approval risk is not double-counted.

### Digital health
Reachable/contracted employers, health systems or covered lives -> implementation -> activation/utilization -> realized PMPM/visit/license economics.

## Required outputs
Where calibrated:
- REM@12m / REM@36m / REM@60m as **P10 / P50 / P90 annual net revenue**;
- customer/patient/unit counts;
- capture share of dynamic SAM;
- probability each operating bottleneck is binding;
- top sensitivity / Value-of-Information drivers;
- evidence-strength and calibration status.

Where critical inputs are not defensibly anchored: output **UNCALIBRATED** ranges or deterministic breakpoints, never manufactured precision.

## Verifier gates
- **R01** semantics, units and horizon explicit.
- **R02** segment populations reconcile; no duplicate customers/units.
- **R03** every REM simulation <= corresponding SAM.
- **R04** source/provenance/evidence state for every material parameter.
- **R05** capacity conservation across sales/onboarding/production/service.
- **R06** causal conditioning tag prevents double-counting technical/regulatory/financing gates.
- **R07** correlation/dependency groups declared.
- **R08** scenario weights reconcile when scenarios are used.
- **R09** sector adapter declared and justified.
- **R10** realized net pricing used rather than unsupported list price.
- **R11** time horizon and market-growth assumptions explicit.
- **R12** unsupported critical parameter => UNCALIBRATED.
- **R13** forecast snapshot stored for later backtesting/calibration.
- **R14** highest-value unknown / VoI reported.
- **R15** REM feeds the revenue path only; unit economics, financing, valuation and investor returns remain separate downstream layers.

## Calibration and learning
Each uncertain parameter should carry source, as-of date, evidence class, reference-class applicability, distribution/range, and dependency group.

REM forecasts should later be compared with realized revenue using interval coverage and proper continuous-forecast scoring. Calibration should be tracked by sector/stage and model version.

## Verifier -> Jev reflection loop
Initial REM concept: `reachable customers × penetration × ARPU × retention`.

Independent verification found:
- substantial semantic overlap with SOM;
- lack of sector exchangeability;
- double-counting risk;
- missing dependence/correlation treatment;
- insufficient rules for unsupported inputs;
- no deterministic integrity gates;
- no calibration/backtesting path.

Those findings were fed back into Jev and incorporated into REM v3.

Final Jev decision (jev-1.13.0):
- **PROMOTE_METHOD: 1.00**
- conceptual quality: 98% probability of **5/5 major upgrade**
- emit precise numeric REM without calibration: **0.04 yes**
- keep name "REM — Realistically Extractable Market": **0.85 yes**
- ready to share with Vera: **0.86 yes**

## Integration rule
REM is a decision-engine input, not an exit valuation and not a replacement for empirical reference classes. It should feed:
`market capture -> revenue path -> unit economics -> financing/dilution -> exit distribution -> investor return`.

No numeric REM may be promoted as calibrated without Vera's ordinary evidence, exchangeability, verifier and calibration gates.
