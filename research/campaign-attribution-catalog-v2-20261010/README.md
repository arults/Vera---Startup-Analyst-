# Campaign source-attribution catalog

Prepared on October 10, 2026 at 19:06:28 UTC. This separate research deliverable contains 105 attributed statements from ten Republic US campaign pages. It preserves what the captured page displayed or what an interested issuer said. It does not establish independent financial, legal or business truth, provide investment advice, or form an investment-performance dataset.

## Files and reading order

- `catalog.json`: compact canonical statement catalog, with common limitations stated once.
- `sources.json`: ten selected parent-page sources, public URLs, native offering IDs, exact raw-capture hashes, capture windows and page-specific context.
- `catalog.csv`: an optional derived, human-readable view retained for local review. It is excluded from this release’s three-file publication allowlist and may be distributed separately only if specifically included later. Its 105 statements duplicate the JSON, not another dataset to append.

Join JSON statements to sources using `source_id`. Public statement IDs are unique within their campaign namespaces because upstream short claim labels can collide between different campaigns. Neither a native offering ID nor a statement ID is a verified legal-entity or economic-round identifier. The two FCF team pages stay separate, while their shared league narrative does not become independent corroboration.

The count is 105 statements, not 105 independent facts or events. Business narratives, display fields and conditional plans may overlap. Six separate linked-template observations are outside this catalog.

## What each statement contains

Each statement retains its predicate, scoped subject, short attributed summary, structured value, original precision/comparator information, time meaning, material qualifications, and DOM source locators. `value_metadata` preserves additional typed components where the original structured value alone is insufficient. Read every component and the source context together; a headline number alone may mislead.

`value` can be a scalar, object or array. Tiered amounts and multi-part metrics are intentionally not flattened. `null` means unknown or not established; it never means zero, false or an uneventful history. A numeric display is not automatically an exact operative amount. Units and precision may be recorded in component names, value metadata or qualifications. Dollar-display wording remains distinct from independently determined currency where necessary.

`time_scope` separates asserted activity dates, relative periods, projections and underlying publication/as-of uncertainty. A founding label is not incorporation; a product launch is not the securities campaign launch. An undated issuer statement does not establish operation or a financial balance as of capture.

Each source records the selected parent capture's start and finish in UTC. Those are retrieval windows, not event dates, publication dates, approval dates or earliest public availability. All ten windows are recorded; underlying page publication/as-of dates remain unknown. Source hashes identify captured bytes, not their truth. No archived raw bodies are distributed. Hashes without those original bodies do not provide public reproduction. A current URL may change or become inaccessible, so this public catalog alone does not reproduce the historical capture.

The status on every row is `SOURCE_ATTRIBUTION_ONLY_NOT_CANONICAL_OR_ESTIMATION_INPUT`. The catalog does not release new companies, financing rounds, outcomes, returns, rates, model priors or cohort entries. Finless Foods' associated offering is outside the 2020–2025 cohort window. Other entries' cohort eligibility is not determined here.

## Important distinctions retained

- A SAFE conversion cap is not an observed priced-equity valuation. FCF's displayed implied valuation at conversion price is a different concept again.
- Easy Expense's two cap tiers are one displayed offering schedule, not evidence of separate financing rounds or appreciation.
- Projections, intentions, commitments and possible conversion interests do not establish completed acts or received cash.
- Strict greater-than thresholds, plus signs, approximate metrics, rounded displays and unknown endpoints remain explicit.
- Brand, predecessor, product, league, issuer and user-level measures retain separate subjects. Fitbux user assets and debts are not issuer assets or assets under management.
- Ephemeris' reservation/considering-hosting and cancelled-page language does not establish historical launch, transaction refunds or company failure.
- Finless' regulatory expectation is an issuer forecast, not FDA approval or a safety finding.
- Fleeting's different usage and revenue displays are preserved without selecting an assumed latest number or reconciling accounting definitions.

The source representation is static claim-relevant HTML. Linked operative documents, external registries, press destinations, images and video are not evidence for these catalog rows. Separate document work is not incorporated by implication. No executed security rights, legal continuity or independent financial audit is certified.

The three-file publication allowlist is catalog.json, sources.json and README.md. Preparation does not assert that publication or an independent review has occurred. The JSON catalog and source table together are the smaller, complete representation. The CSV is an optional equivalent convenience view. Keep this README with either representation. None of these files claims public publication, deployment, or new independent source validation.
