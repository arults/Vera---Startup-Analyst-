# Phase 1D — Checkpoint 2: Republic Europe Cohort & Round Graph Freeze

Date: 2026-10-09
Status: **PASS / FROZEN for Republic Europe**

## Frozen funded-round universe
- Normalized funded rounds with platform-funded date in 2020–2025: **952**
- Unique companies: **792**
- Unique round IDs: **952**
- Strong company-ID rows (platform company number): **946 / 952 (99.37%)**
- Weak name-fallback rows: **6 / 952**
- Cohort-year-usable rows: **796**
- Cohort-year-unresolved rows: **156**
- All 796 rate-eligible rows have strong company IDs.

## Offering-year rule
Exact first-live date is not exposed on Republic Europe pages.

Jev-approved execution rule:
- store exact first-live date as null;
- retain platform approval date and funded date as interval bounds;
- assign offering year only when approval and funded dates lie in the same calendar year;
- cross-year or missing-approval rows remain YEAR_UNRESOLVED and are suppressed from platform-year rates.

Date audit:
- approval coverage: **910 / 952 (95.59%)**
- median approval→funding lag: **50 days**
- p10/p90: **28 / 85 days**
- negative lags: **0**
- same-year approval/funding: **796**
- cross-year: **114**
- missing approval: **42**

Usable cohort rows by offering year:
- 2020: **184**
- 2021: **191**
- 2022: **181**
- 2023: **142**
- 2024: **47**
- 2025: **51**

## Repeat-round graph
- Companies with multiple rounds: **121**
- Repeat-company round rows: **281**
- Chronological NEXT_ROUND edge candidates: **160**
- Same-economic-round review candidates meeting audit threshold: **0**

No rows are collapsed.

## Jev CP2 freeze
- state = pass_frozen: probability **0.99**, confidence **0.98**
- keep all rounds distinct: probability **0.89**, confidence **0.83**
- freeze sequence graph candidates: probability **1.00**, confidence **1.00**
- design reopen is not required for the bounded-year representation.

## Scope
This freezes Republic Europe only. Wefunder, StartEngine, Republic US and Crowdcube remain CENSUS_INCOMPLETE under CP1 and their rates remain suppressed.
