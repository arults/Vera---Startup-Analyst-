# Phase 1B outcome and survival provenance

Date: 2026-10-08

## Outcome collection rule
Each of the 42 frozen funded offerings has exactly one dated outcome/censor row in `data/outcomes.csv`.

Evidence hierarchy, selected by Jev:
1. regulator/court records;
2. reputable independent news;
3. independent customer/partner/retailer/app records;
4. company-controlled evidence only after documented independent-search exhaustion, labelled lower confidence.

Jev chose `independent_first` with probability 1.00 / confidence 1.00. A current undated company site may be used only when it demonstrates current operating functionality and identity continuity; selected probability 0.99 / confidence 0.98. If no later reliable evidence is found after diligent search, censor at the last dated SEC filing; selected probability 1.00 / confidence 1.00.

## Endpoint counts
- 35 active/right-censored
- 4 observed failures
- 2 acquisition/successor censors
- 1 public-listing censor

Observed failures:
- Cortex Automation Inc. — ceased operations / liquidation, 2023-03-31.
- Comsero, Inc. — bankruptcy, 2023-12-22.
- Sircles Media Inc. — winding down, 2026-04-17.
- Curastory Inc. — Chapter 7 bankruptcy, 2026-08-27.

Non-failure terminal endpoints:
- Envel, Inc. — acquired/successor technology transaction, 2023-06-20.
- GroGuru, Inc. — acquired by Goanna Ag, 2025-08-20.
- Boxabl Inc. — public listing censor, 2026-07-20.

Nine obscure firms are intentionally censored at their last retained SEC filing after no later qualifying evidence was found. Four rows use constrained company-controlled fallback evidence after search exhaustion. These are retained in the row-level CSV rather than silently upgraded.

## Primary Kaplan-Meier result
Five-year operating survival:
- primary funding-time estimate: 0.930147 (93.01%)
- Greenwood log-log 95% CI: 0.743966–0.982427 (74.40%–98.24%)
- at risk at 5 years: 12
- cumulative observed failures by 5 years: 2
- cumulative censors by 5 years: 28

## Funding-date sensitivity
Forty of 42 funding-close dates are conservative proxies. Replacing them with their later SEC close-date bounds yields:
- 5-year survival: 0.925666 (92.57%)
- 95% CI: 0.730690–0.981165
- at risk: 8

The five-year conclusion is therefore stable to the preregistered time-zero uncertainty.

## Six-year limitation
Primary six-year at-risk count is 3; late-bound at-risk count is 1. Jev assigns only 0.08 probability to promoting the six-year estimate. It remains a sensitivity output, not a promoted empirical prior.

## Public-listing sensitivity
Continuing BOXABL operating follow-up from its listing date through the analysis cutoff does not change the current five-year estimate.

## Reproducibility
- manifest SHA-256: `62468cea323ed6d2732df90cbe5ced04990db907cf908e4939b4128a302f78c8`
- outcomes SHA-256: `7f87d79c2a24bf748a6751180fed4cc286b678e0621d4fcbe8ec8b38b2afb5fc`
- verifier GitHub Actions run: `37766586864`
- unit tests: 13/13 PASS
- D01–D08, O01–O07, S01–S03: PASS
