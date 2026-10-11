# Vera Phase 1C — Multi-Platform Calibration Framework

Version target: 0.5.0
Status: DESIGN FROZEN / IMPLEMENTATION STARTED
Date: 2026-10-08

## Scope
Phase 1C builds the executable framework for later multi-platform calibration. It does **not** collect the full 2020–2025 dataset and does **not** publish final outcome rates.

In-scope platforms:
- Wefunder
- StartEngine
- Crowdcube
- Republic US
- Republic Europe

Offering cohorts: 2020–2025. The 2024–2025 cohorts are right-censored by construction.

## Research questions
RQ1 — platform × offering-year operating survival, typed success and confirmed closure with censoring-aware estimators and uncertainty.
RQ2 — same outcomes within platform by field; report platform × field × year only when cell gates pass, otherwise pool adjacent years and disclose pooling.
RQ3 — each economic company-round is one row with platform, offering year, primary field and controlled tags. One company may have multiple rows.
RQ4 — cross-platform round graph, especially Wefunder→Republic US/StartEngine and Crowdcube→Republic Europe; quantify native-only vs graph-aware bias.

## Cohort architecture
Layer A — accessible-deal census: all publicly launched accessible deals, including funded, failed, withdrawn and pending. Used for coverage/selection analysis.
Layer B — funded/completed investor-outcome cohort: successfully completed rounds that produced an investment/security position. Used for RQ1/RQ2 outcome estimation.

Offering year = year first live/public on platform.
Outcome time zero = successful completion/close date in Layer B.
Pending rounds remain in a pending ledger until completion and never silently shift cohort year.

## Unit of analysis
Primary unit = economic company-round. A company can appear in multiple rounds.
Same issuer + comparable instrument/terms + overlapping raise window => one economic round.
If the same economic round is co-hosted, keep one round and a round-platform bridge; origin/first-live platform is the primary platform attribution and co-host sensitivity is retained.

## Identity resolution
Auto-match only on:
1. exact strong identifiers; or
2. at least two independent medium identifiers.

Medium identifiers include normalized legal/brand name, company domain, founders/executives, headquarters, compatible product description and explicit prior-round references.
Name similarity alone cannot auto-match.

QA:
- 100% second review of medium/manual matches;
- stratified 10% second-review sample of auto-matches;
- reopen matcher if sampled false-match or false-split rate >2%.

## Primary field taxonomy
1. SaaS & Enterprise Software
2. Biotech & Therapeutics
3. Healthcare & MedTech
4. Fintech & Insurtech
5. Consumer & Retail
6. Marketplaces & Platforms
7. Hardware, Robotics & Deep Tech
8. Climate, Energy & Industrial
9. Food, Beverage & AgTech
10. Media, Gaming & Creator
11. Mobility, Logistics & Aerospace
12. Real Estate, Hospitality & PropTech
Fallback: Other / Diversified

Exactly one primary field per round. Tie-break: lead commercial/clinical product → dominant disclosed revenue/usage driver → Other/Diversified.

## Controlled tags
Versioned multi-label groups:
- business model
- customer type
- technology
- company stage
- geography
- regulatory intensity
- instrument / investment structure

Raw platform-native tags are preserved separately.

## Outcome rules
### Survival
Independent operating-state occupancy. Nonterminal success events can move a company from operating_pre_success to operating_post_success.

### Success
Primary success time = first qualifying event; later typed events stay in history.
Qualifying events:
- priced equity follow-on with comparable valuation >=1.5× the index round;
- IPO/direct listing;
- acquisition only when platform-hosted evidence establishes shareholder consideration or transaction value;
- profitable exit where gross investor MOIC >1.0× is inferable from platform-hosted evidence.

SAFE/convertible caps are not treated as actual priced valuations.
Same-platform secondary trading alone is not success.

### Closure
Requires explicit dated platform-hosted evidence of shutdown, bankruptcy, liquidation, dissolution or ceased operations.
Stale/inaccessible page, no recent news or investor comments never establish closure.

### Acquisition with unknown value
Confirmed acquisition without sufficient consideration evidence is a terminal independent-operation event with success value UNKNOWN, not automatic success.

## State model
- operating_pre_success
- operating_post_success
- terminal_success_exit
- acquisition_value_unknown
- closure
- right_censored

## Censoring / follow-up
Right-censor at last dated platform-hosted evidence affirmatively supporting ongoing operation, capped at extraction date.
Results are labelled **platform-observed**, not universal true outcomes.
Report lost-to-platform-follow-up and ascertainment coverage.
Primary estimate is accompanied by optimistic/adverse event-assignment sensitivity bounds for lost follow-up.

## Estimators
Use right-censored competing-risk/multistate analysis (Aalen–Johansen/state-transition framework).
- success: cumulative incidence of first qualifying success;
- closure: cumulative incidence of confirmed closure;
- survival: occupancy probability of independent operating states.

Primary uncertainty = company-clustered bootstrap.
Diagnostic uncertainty = estimator-specific analytic interval.
Material disagreement is flagged.

Reporting landmarks = 12, 24, 36, 60 months only when estimable, plus each cell's maximum supported follow-up. Never extrapolate.

## RQ1 reporting
Every platform × offering-year Layer-B cell with n>0 remains visible.
Flag LOW_INFORMATION if n<30 or fewer than 5 informative events.

Report:
- n funded/completed rounds
- unique companies
- at-risk count
- event counts
- censor count
- lost-follow-up rate
- ascertainment coverage
- survival / success CIF / closure CIF
- primary and diagnostic intervals
- maximum supported horizon

## RQ2 field cell gate
Individual platform × field × year cell requires:
- n >= 30
- >=5 informative events
- ascertainment coverage >=80%

If not, expand into adjacent years. Do not silently cross the 2023/2024 maturity boundary; if crossing is required, mark it explicitly. Suppress irreducibly sparse cells.

## Cross-round graph
Node = company_round.
Edges:
- NEXT_ROUND
- COHOST_SAME_ROUND

A qualifying cross-platform follow-on:
1. counts as success for the predecessor round;
2. creates a new destination round row with a new outcome clock.

Compute native-only and graph-aware estimates and report delta + number/percentage reclassified + origin→destination matrix.

## Public source hierarchy
Evidence is restricted to public/access-controlled pages on the five platforms:
1. campaign/round page;
2. platform-hosted documents and issuer/admin updates;
3. platform portfolio/funded/secondary pages.

Search engines are discovery-only; snippets are never evidence.
No assumed paid database.

Availability status must be explicit:
- PUBLIC_VISIBLE
- AUTH_REQUIRED
- UNAVAILABLE

Missing campaigns remain with missingness flags when core identity/year is otherwise established from the same platform; no outcome is imputed.

## Required bias register
- survivorship/page persistence
- platform outcome-reporting lag
- informative censoring / lost follow-up
- 2024–2025 maturity
- US vs UK/EU disclosure differences
- repeat issuers
- campaign-vs-company count ambiguity
- cross-platform follow-on leakage
- co-hosted campaigns
- identity false match / false split
- instrument comparability
- success visibility / quiet-failure under-ascertainment
- taxonomy drift
- platform-selection drift by year

## Non-goals
Phase 1C does not compute the final platform/field rates, claim causal platform effects, estimate final IRR/MOIC distributions, use inaccessible paid databases, or provide mature 5-year outcomes for 2024–2025.
