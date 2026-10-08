# Phase 1B denominator reconstruction provenance

- Official source family: SEC Crowdfunding Offerings Data Sets and direct EDGAR filings.
- SEC dataset page: https://www.sec.gov/data-research/sec-markets-data/crowdfunding-offerings-data-sets
- Structured enumeration mirror used because the SEC quarterly ZIP is binary and unavailable to the current browser runtime: apsinghAnalytics/CrowdOfferingsStudy, files CrowdFundingCampaignsCleanedData.csv and scrapedCrowdOfferingsData.csv.
- The mirror is used for enumeration/normalization only. Every admitted row retains deterministic direct SEC EDGAR URLs for its initial Form C and final selected Form C-U.
- Universe rule: earliest Form C in calendar 2020, Wefunder Portal LLC, intermediary CIK 0001670254.
- Primary funded rule: at least one C-U with positive successful-close/proceeds evidence; latest C-U selected when multiple updates exist; no C-W withdrawal on admitted rows.
- Reconstructed initial-offering universe: 360.
- Primary funded denominator: 42.
- Excluded offerings: 318.
- Initial offerings with any C-U: 43; positive funded C-U rows admitted: 42.
- T4L INC (020-27165) filed a C-U saying only that it was launching on StartEngine and is excluded as CU_PRESENT_BUT_NO_POSITIVE_PROCEEDS.

The remembered historical denominator of 42 was not used as an input filter. The reconstruction independently returned 42.

## CP2 chronology repair

The first independent verifier run reproduced 42 rows and passed D01-D07 but failed D08 chronology for seven rows because a cleaned "final campaign deadline" could be later than a Form C-U already describing the offering as final/closed.

Jev decision (jev-1.13.0):
- close-time rule: explicit C-U close date when available; otherwise earlier of latest SEC campaign deadline and final/closed C-U filing date. Confidence 1.00; selected-option probability 1.00.
- retain proxy-date sensitivity: yes probability 0.79.
- change denominator membership because of this defect: yes probability 0.19. Membership therefore remains 42; only time-zero metadata was repaired.

The manifest now records `funding_close_is_proxy` and `funding_close_date_late_bound`. Forty rows use a conservative proxy and two rows have an explicit close date in the C-U text. The late-bound field supports the preregistered timing sensitivity analysis in CP3.
