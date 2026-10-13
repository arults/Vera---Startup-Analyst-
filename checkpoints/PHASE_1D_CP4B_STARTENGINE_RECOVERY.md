# Phase 1D — Checkpoint 4B: StartEngine Native Recovery

Date: 2026-10-09  
Status: **EXECUTING / NO RATE PROMOTION**

## Why this checkpoint exists

Phase 1D Round 1 left StartEngine `CENSUS_INCOMPLETE`: the platform advertises an official directory total of 1,539 offerings, while the earlier structured-search subset contained only 112 URLs. Search subsets cannot support platform-year outcome rates.

After Wefunder remained a partial recent archive and the Republic US bounded recovery was blocked by HTTP 403 responses, Jev selected a native StartEngine recovery as the next highest-value improvement:

- `probe_startengine_native`: probability **0.81**, confidence **0.75**
- Phase 1D plateau already reached: **NO**, probability **0.97**

## Recovery contract

The execution worker:

1. visits only public StartEngine directory pages;
2. captures public official-domain JSON/network responses and DOM listings;
3. canonicalizes only `/offering/{slug}` campaign URLs;
4. rejects external, credentialed, non-HTTPS and sensitive-query resources;
5. stores content-addressed compressed source snapshots;
6. writes immutable numbered resume checkpoints;
7. records official total hints separately from observed candidate counts;
8. never promotes rates from partial coverage;
9. marks even an apparently exhausted directory only `POTENTIAL_COMPLETE_REVIEW` until independent denominator/year validation passes.

## Verification and durability

- Full repository regression tests run before collection.
- StartEngine-specific adversarial tests cover canonicalization, recursive candidate extraction, total hints, sensitive-resource rejection, snapshot integrity, checkpoint preservation and fail-closed promotion.
- The recovery directory, logs, code hashes, runtime and manifest are uploaded as a separate workflow artifact and persisted to the `phase-1d` branch.

## Promotion boundary

This checkpoint may improve source coverage, but it cannot by itself promote StartEngine platform/year rates. A later Jev + Verifier gate must establish historical 2020–2025 denominator completeness, cohort dates and funded-round eligibility.
