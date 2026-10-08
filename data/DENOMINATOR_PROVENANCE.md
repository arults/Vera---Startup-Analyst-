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
