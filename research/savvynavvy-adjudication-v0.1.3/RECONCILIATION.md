# Savvy Navvy six-round source reconciliation — candidate v0.1.3

Status: additive diagnostic candidate; independent review pending. No canonical source row, date, success label, censor field or eligibility was changed. No estimator or JEV call ran.

## Finding

The paired source observations differ under the disclosed candidate mappings. Five earlier in-scope campaigns are provisionally linked to KIIS previous-campaign rows by issuer, year and sequence; the table contains no campaign IDs. Exact same-economic-round correspondence and date/amount semantics remain unresolved. The 2024 KIIS repeats all five 2019–2023 historical table entries exactly. This repeat is the same issuer/platform lineage, not independent verification.

| Round | Promotion approved as of | KIIS “Completion date” | Campaign “Funded” | KIIS amount GBP | Campaign amount GBP | Difference GBP |
|---|---|---|---|---:|---:|---:|
| 2020 /1 | 2020-02-03 | 2020-02-06 | 2020-03-04 | 615,821.09 | 616,462 | 640.91 |
| 2021 /2 | 2021-03-22 | 2021-03-24 | 2021-04-20 | 865,212.45 | 866,042 | 829.55 |
| 2022 /3 | 2022-01-21 | 2022-01-24 | 2022-02-24 | 1,349,024.24 | 1,382,090 | 33,065.76 |
| 2023 /4 | 2023-01-30 | 2023-01-30 | 2023-03-06 | 1,342,737.70 | 1,347,589 | 4,851.30 |
| 2024 /5 | 2024-04-29 | 2024-04-30 | 2024-06-05 | 1,216,945.40 | 1,232,893 | 15,947.60 |
| 2025 /6 | 2025-11-10 | Not a previous campaign in own pre-offer KIIS | 2025-12-09 | Not supplied for own completed raise | 692,633 | Not applicable |

The historical KIIS dates are close to financial-promotion approval (0–3 days later) and 27–36 days before “Funded”. A metadata or milestone explanation is plausible but unverified. The packet does not rename them launch dates, select one clock, classify either source as erroneous, or explain amount differences as fees/refunds without evidence.

## Verified material and provenance

- [2025 native KIIS](https://assets.seedrs.com/uploads/kiis/pdf/file/2180/pyz1lazitz1hbi7zfiu30etlt52ksfx/savvy-navvy6-en20251110-1-xxbsx.pdf), page 3. Original bytes downloaded and table visually inspected. SHA256 d85134e13977c926bf4ff6d508bb02e7a986022ab1f2434b6dfb0eca84bec3f2. Page 2 identifies GB company 10919572; page 5 describes this offering's A Ordinary shares. The prior-campaign table labels its rows Primary, Equity.
- [2024 native KIIS](https://assets.seedrs.com/uploads/kiis/pdf/file/911/sg9nlcmorswi8b6t026buoso5x73356/savvy-navvy5-en20240426-1-iwm82n.pdf), page 3. Downloaded and visually inspected; hash in manifest. This earlier document has 2019–2023 entries only.
- Original archived [round 1](https://europe.republic.com/savvy-navvy1), [round 2](https://europe.republic.com/savvy-navvy2), [round 3](https://europe.republic.com/savvy-navvy3), [round 4](https://europe.republic.com/savvy-navvy4), [round 5](https://europe.republic.com/savvy-navvy5), [round 6](https://europe.republic.com/savvy-navvy6) HTML/text bodies are tied to the frozen repository commit and captured October 9, 2026. All six compressed HTML hashes, raw HTML hashes, and raw extracted text hashes match source receipts. Native DOM supplies exact fully diluted pre-money values, strong company IDs, unique campaign IDs, Funded dates, amounts and approval dates. The live KIIS URLs appear in archived native /5 and /6 HTML.
- [Secondary-market business listing](https://europe.republic.com/businesses/savvy-navvy): a new read captured between 13:18:46 and 13:19:03 UTC on October 11, 2026. It defines eligibility as secondary-market trading eligibility, warns of update lag and incomplete/outdated information. Its generic “shares were acquired” carry-fee text is not a company acquisition. This confirms interpretation of the listing, not a new operating endpoint or reconstruction of the October 9 listing body.
- Scientific rules: docs/PHASE_1C_SPEC.md at commit 88cce2695804cb6c7754fb8ce6db4ba3122d2bc9, Git blob fb62fb062274cf51b8090f91990c3181dc99bdb2. Formal gate names come from research/preparation-audit-v0.1.0/preparation_audit.py.

## Index-specific guardrails

All 15 later/index exact valuation ratios were recomputed. Preserve /1→/2 = 1.447000708535 and /3→/5 = 1.472337601993 as below-threshold controls. The existing three success-labelled rows point to /3 for /1 and /2, and /6 for /3. All six frozen row bodies remain intact in the candidate. These comparisons are company pre-money valuation arithmetic, not share-price ratios, investor MOIC, new admissions or a full comparability review.

The 2019 prior round stays as out-of-cohort entry context. No initial PRE/POST is inferred from blank success labels, financing alone, a prior success against another index, or narrative product-market fit. Native financial-promotion approvals and same-year Funded labels preserve bounded-year candidates; neither establishes the exact first-public-live day. No selected six-company-round sample is presented as a representative cohort.

## Preparation-gate assessment

1. Round identity and funded origin: strong issuer ID plus unique campaign IDs supports a six-round identity candidate. For /1–/5, Funded campaign labels plus provisionally linked later KIIS previous Primary Equity rows strengthen a completed-financing candidate. Economic-round correspondence and origin semantics require review. /6's Funded/Equity observations remain accepted source facts; its pre-offer KIIS is not retrospective completion evidence, and lack of a later KIIS is not a new universal evidence requirement. Adequate public native aggregate evidence may resolve this; a private investor contract is not universally required.
2. Initial state: explicitly review independent operation and prior index-specific events at each entry, including 2019 context. No automatic reset or PRE/POST assignment.
3. Index success and target: approve comparable priced-equity semantics, index-specific threshold and incident versus baseline-plus-incident target. Current generic Equity labels and matching valuation basis support review but do not replace it.
4. Typed event chronology: keep typed observations apart and adjudicate exact first qualifying event dates. No transitions were emitted and no interval was invented from two dates with unresolved meanings.
5. Endpoint observation: do not promote secondary-market eligibility, old campaign availability, later financing or retrieval timestamps into affirmative operation. Preserve old endpoints as source input while choosing valid endpoint-specific follow-up.
6. Cohort assignment: PASS_BOUNDED_COHORT_ONLY. Same-year approval/Funded bounds support all six original offering years; exact first-live day is not required. This scoped finding is independent of the other held history gates. Representativeness is solely an aggregate-reporting limitation. Global eligibility remains undetermined; history remains unconstructed.

## Next useful evidence

Seek a public native campaign-closing update, platform field-definition document or issuer/platform correction explaining “Completion date”, “Funded” and amount scope. Do not contact anyone without authorization. Then independently adjudicate entry, target, chronology and endpoint on this exact candidate version before event/history admission or downstream model use. JEV remains held pending credit approval; private research was not transmitted to external models.

## Operational metrics

Run: vera-savvynavvy-adjudication-20261011. See candidate/operational-metrics.json for scope and provenance. Recorded cutoff is 13:19:13 UTC, before candidate assembly and independent review; this is deliberately partial, not a final whole-company total.

| Metric | Value | Status and coverage |
|---|---|---|
| Tokens used | Unknown | Unavailable; no run-level telemetry exposed |
| Total tool invocations | Unknown | Whole parent/worker/reviewer total unavailable. Worker source-read subtotal: 23 through cutoff, includes failed calls, excludes other tool classes and later work |
| Wall-clock latency | 216 seconds | Partial observed interval from task receipt 13:15:37 to cutoff 13:19:13 UTC |
| Total cost | Unknown | Unavailable; no paid JEV call made |
| Memory used, peak RSS | Unknown bytes | No attributable per-run process measurement exposed |

## Revision and bounded next-source search

This successor preserves the v0.1.0 frozen packet (manifest SHA256 5e5254e98ea8d169be5ea83c960e3648f760029867a7e4eccbe886b1744be5f4). Independent semantic review identified the need to distinguish supported cohort-year bounds from held exact-history disposition. No frozen source observation changed. Parent byte/row checks and reviewer semantic review are separate.

Nine targeted queries and a direct native guide read were attempted between 13:22:13 and 13:23:09 UTC. Search snippets are discovery only. The first query used a malformed site.help.seedrs.com operator and is retained as a low-quality attempt, not evidence of absence. Subsequent explicit domain-filtered and exact-name queries found no Savvy Navvy-specific public closing update or documented mapping of these two date fields in the returned results. This is a bounded negative search, not an irreducible or exhaustive evidence gap.

The [native process guide](https://europe.republic.com/investors-site/guides/what-to-expect-as-a-startup-seedrs-investor/) separates closing a campaign to investment from subsequent due diligence, legal work, funds transfer and beneficial share certificates. It does not define the disputed campaign Funded display or KIIS previous-campaign Completion date, and cannot identify a corrected company-round clock. Downloaded original HTML SHA256 27c3e06088ecc043c0db7fe912caab26d911db832a7096ef0c3f6094ae2a0178. This is generic platform-process evidence, not company completion evidence. No external contact was made.

## Publication-safe source handling

New raw HTML captures and re-downloaded archived HTML contain CSRF metadata and/or telemetry scripts. They remain local/private and are excluded from this packet. Script-free, attribute-free text derivatives retain claim evidence, with original hashes, derivative hashes, source URLs, existing repository archive references and category counts in source-receipts.json. Original archive references remain provenance references, not new redistribution. No values from token-bearing fields occur in receipts. PDF sources are retained as published native documents. Review the exact v0.1.3 bytes independently before publishing this held evidence packet.

Status vocabulary: PASS_BOUNDED_COHORT_ONLY applies only to the year/membership predicate; HOLD on other gates and HELD_OTHER_PREPARATION_GATES globally prevent inferred history admission. None is an eligibility classifier.

## Typed DOM evidence retained

The publication-safe typed DOM extract preserves allowlisted nonsecret campaign IDs, exact fully diluted pre-money valuations and approval dates with source selectors, original HTML hashes and existing archive paths. Text-only derivatives necessarily omit HTML structure, scripts and attributes; they do not reproduce original raw-HTML parsing. Reviewers can compare the typed facts against the already-authorized frozen archives. No token-bearing attributes are copied.
