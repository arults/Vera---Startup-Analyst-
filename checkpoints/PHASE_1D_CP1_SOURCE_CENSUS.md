# Phase 1D — Checkpoint 1: Source Census & Immutable Discovery

Date: 2026-10-08
Status: **PASS_WITH_SUPPRESSION**

## Frozen coverage state
- Republic Europe: **PASS_NATIVE_ENUMERABLE** — 2,896 sitemap URLs, 2,073 candidate slugs. Proceed to validation/normalization.
- StartEngine: **CENSUS_INCOMPLETE** — official directory states 1,539 offerings, but complete campaign URL/year enumeration was not recovered; 112 structured-search URLs retained for future improvement.
- Republic US: **CENSUS_INCOMPLETE** — 108 structured-search URLs + public page access, but no defensible exhaustive platform-year denominator.
- Wefunder: **CENSUS_INCOMPLETE** — partial browser/search discovery only (23 native candidates; 46 structured-search URLs).
- Crowdcube: **CENSUS_INCOMPLETE** — native access blocked by Cloudflare; 20 structured-search URLs retained.

## Jev gate
- incomplete census => suppress invalid cells: probability 1.00 / confidence 1.00
- completeness gate => enumerable platform surface or convergent independent discovery + on-platform validation: probability 1.00 / confidence 1.00
- canonical platform-page extracts are valid platform evidence; search snippets alone are not: probability 1.00 / confidence 1.00
- CP1 state => PASS_WITH_SUPPRESSION: probability 1.00 / confidence 1.00

## Execution consequence
Phase 1D continues with Republic Europe. Other platforms remain visible in coverage/discovery artifacts but **their outcome rates are prohibited** until their denominator coverage improves.

Raw checkpoint artifacts:
- data/phase1d/cp1_discovery_candidates.csv
- data/phase1d/cp1_discovery_report.json
- data/phase1d/cp1_manifest.json
- data/phase1d/cp1_tavily_candidates_us.csv
- data/phase1d/cp1_tavily_candidates_eu_web.csv
- data/phase1d/cp1_search_* (failed Bing fallback retained as iteration evidence)
