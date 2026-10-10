# Phase 1D CP10 continuation: verified fields, corrections and open gates

Latest continuation: sections 13-17 correct the admission-rule interpretation, integrate targeted graph/CI repairs and apply two reviewed legacy rounds to a versioned research ledger. Earlier document-only sections retain their original scope. The integration CI runs have since passed for revision ee9c79e (section 18); Phase 1D and global plateau remain unproven.

Date: 2026-10-10 UTC. Source snapshot: `7291d33ff32cdd6b07ae9cfe1f342849a447f536`, committed 2026-10-10 02:39:50 UTC. This is a documentation/source-field checkpoint. It does not promote production data, a numerical prior, a new release or full-study completion.

Status: **PHASE 1D INCOMPLETE; GLOBAL RESEARCH PLATEAU NOT DEMONSTRATED.** Promoted VERSION remains `0.5.0`; source collection versions are `0.6.5-dev.research.1` and `0.6.5-dev.research.2`. Older current-state wording in the progress log and skill history is superseded by this dated checkpoint. Historical source and validation artifacts remain unchanged.

## 1. Current source-count reconciliation

- Republic US current sitemap: 53,854 native URLs; a complete captured published sitemap tree, not a complete historical campaign population.
- 1,242 new single-path URLs classified: 568 native-ID-bound campaigns, 96 non-campaign/unresolved-schema pages, 255 redirects/scope holds and 323 unavailable. The unavailable set includes 318 circuit-unattempted entries. Fourteen known legacy campaigns are absent from the current sitemap.
- 568 distinct candidate native IDs and URLs; 449 launch-verified rows. The nested triage funnel is 363 launch-year-eligible 2020–2025 rows -> 335 matching parent close -> 305 with one unvalidated linked CIK -> 233 marketed SAFE-family securities.
- All 363 launch-year-eligible rows have timeline completion, but 28 lack parent-close matching. Across the broader 449 launch-verified rows, nine lack completion and 39 lack parent close. Do not describe all 449 as fully parent-bound pairs.
- Canonical company IDs, canonical economic-round IDs, economic-identity admission and estimator admission remain zero for this new candidate set. Do not sum these units with the older 125 selected campaign records or with Republic Europe.

The two immutable collection summaries are at `data/phase1d/cp10/collection-1/summary.json` and `data/phase1d/cp10/collection-2-campaigns-large-docs/summary.json`; detailed candidates are at `data/phase1d/cp10/collection-2-campaigns-large-docs/native_campaign_candidates.json`. The independent audit reproduced the derived rows, performed one raw timeline replay and passed 19 row/replay/adversarial checks. It did not replay every raw source or certify a historical denominator.

## 2. Document queue and accepted source-field scope

The old 106-request download backlog is superseded. Collection 1 attempted all 106, obtaining 100 PDFs, one non-PDF/parse hold and five size holds. Collection 2 fully captured all five large PDFs, for 105 captured PDFs and no remaining large-file hold. This continuation identifies the one non-PDF hold as readable StartGlobal DOCX. Preserve the original collection summaries as-of capture; do not rewrite them to imply the later parse was already complete.

Eight documents now have bounded independent source-field reviews: seven PDFs and one DOCX. This is not eight admitted economic rounds or 106 fully adjudicated documents. Chilling, Currently Wine, Ecotone Renewables and Moriondo were captured in CP10 but remained unmaterialized in the first bounded review; a connector materialization issue must not regress their native capture status.

### Wave 1: four original Form C documents

| Campaign | Document-level legal issuer | Reviewed series / SAFE cap | Form C signature | Original target deadline |
|---|---|---|---|---|
| BuyAlerts | Live Stream Technology Services Inc. | Series 2023 / USD 28m | 2023-03-13 | 2023-05-12 |
| Get On Board | Get on Board Holding Corp. | Series 2024 / USD 6m | 2024-04-02 | 2024-07-01 |
| Phantom Phood | Phantom Phood Inc. | Series 2023 / USD 12m | 2023-02-14 | 2023-04-15 |
| Stock Card | Stock Card, Inc. | Series 2022 / USD 10m | 2022-08-29 | 2023-02-24 |

- The cover CIK `0001751525` belongs to intermediary OpenDeal Portal; these covers do not prove issuer CIKs. Legal-name source acceptance is separate from canonical cross-round identity.
- Get On Board explicitly states a 20% discount, yielding a derived 80% financing-price fraction. Other unassigned discounts remain unknown, not zero. The USD 6m cap belongs to the reviewed Series 2024 form, not every historical Get On Board security.
- Actual Crowd SAFE signature pages are 57, 78, 56 and 70 respectively. Nominee/proxy pages are 59, 81, 58 and 72. Both sets are blank. The corrected page-scope labels supersede the initial generic signature labels.
- Stock Card's signing date is distinct from inherited native launch 2022-09-06. This PDF-only review did not revalidate parent HTML launch fields.
- 70 anchors passed two parsers after explicitly recorded whitespace normalization; 20 material PDF pages were independently visually inspected. Raw SHA-256, gzip SHA-256 and Git blob hashes were checked. Parser agreement does not mean byte-identical extracted text.

Corrected accepted-ledger SHA-256: `4beb86494a718e083e2e6a2e463c29f6b5512e570489173f9228484c1f56be1c`. The independent final review binds this corrected ledger. The earlier source-review JEV receipt predates the signature-label correction and is not silently rebound to new bytes.

### Wave 2: three amended filings and a DOCX

- **Layali LLC:** material Form C/A; USD 2.5m summary conversion numerator and literal financing-price multiplier 20%. This is not labeled a 20% discount. Form signature date is blank on physical page 4; Exhibit E is heading-only on page 36. The inherited 2019 launch stays outside the 2020–2025 study despite the April 20, 2020 deadline.
- **Nobody Studios, Inc.:** material amendment signed February 21, 2023, extending the target deadline to April 7, 2023. The template is still Crowd SAFE Series 2022 with a USD 30m cap. Actual SAFE page 68 and nominee page 70 are separate and blank. An amendment is not a new 2023 economic round.
- **Soar Robotics Inc.:** material amendment signed December 19, 2019; summary USD 7m conversion numerator and 80% price multiplier. The March 10, 2020 target deadline is neither an actual close nor a cohort-entry date. Exhibit E, page 32, is heading-only; inherited 2019 launch stays excluded.
- **StartGlobal, Inc.:** readable original Form C DOCX, structurally checked through OOXML numbering. Form signature text is August 13, 2024; target deadline November 11, 2024; summary SAFE cap USD 12.5m pre-money. Paragraph 281 has custody/nominee summary text naming Brassica Trust Company LLC. Full security, custody and nominee agreement bodies are absent; do not infer them from headings or treat historical USD 3m/USD 5m securities as current terms.

Wave 2 independently checked 49 field anchors, 17 PDF pages and static ZIP/OOXML plus python-docx structure. No external links or embedded content were executed. DOCX paragraph locations, not source-page numbers inferred from a derived render, identify fields. Raw, gzip and Git hashes matched. Accepted-ledger SHA-256: `afa993df3fe89a63126babc5655988a9bf77807b8c546a71601d122ef5320887`.

Both independent final JEV reviews accepted only the bounded source-field scope, retained identity/instrument/funding/outcome/population holds and rejected phase-completion implications. Selected choices had probability/confidence 1.00. These are model judgments, not statistical certainty or percentages of work completed.

## 3. Acceptance holds and next evidence needed

1. **Issuer and economic-round identity:** verify identifier roles, legal issuer/coissuer, series and regime; reconcile repeat raises, overlapping windows and cross-platform bridges before canonical assignment.
2. **Claim-specific instrument chain:** bind original filings and known material amendments sufficiently for the claim. Verify exact operative investor terms when material to identity, instrument comparability or investor-specific returns; do not require every private executed contract for all aggregate funded rows. A template's cap is not a priced valuation.
3. **Funded Layer B and time zero:** adjudicate source-bound successful financing producing a security position and its completed close/date. Coherent public aggregate completion evidence can satisfy this gate; a blank template or commitments alone cannot. Individual private receipts are not universally required. Keep launch, signature, deadline and completion separately typed; preserve failed/withdrawn/pending cases.
4. **Operating and terminal outcomes:** require admissible dated evidence for the correct entity. Preserve period-only reports and interval uncertainty. A wind-down announcement is not completed closure or an investor loss fraction; acquisition consideration is not necessarily investor proceeds.
5. **Historical populations:** Wefunder, StartEngine, Crowdcube and Republic US remain incomplete. Republic Europe retains 24 LOW_INFORMATION RQ1 cells and zero reportable RQ2 cells. Current directories and search excerpts do not close historical coverage.
6. **Estimation:** after source/identity/funding/outcome gates, rerun frozen estimators and independent checks. RQ2 requires n >= 30, >= 5 informative events and >= 80% ascertainment. No source count or green CI pass overrides these gates.

## 4. Upgrade and reproducibility record

- Corrected stale document-backlog and phase-completion wording without modifying historical sources.
- Made source-unit labels, date semantics, original/amendment roles, intermediary identity, literal SAFE multipliers and signature-block scope explicit.
- Added a compact source manifest with immutable paths and separate raw/gzip/Git hashes for all eight documents, selected typed fields and page/paragraph anchors. Hash the compressed source, then decompress and hash raw bytes; never interchange these hashes. Original review-ledger/receipt fingerprints are retained separately from this derived manifest.
- Updated the existing `SKILLS.md` and `VERSION_PROGRESS.txt` convention; no duplicate lowercase skill file, new release version, source-data admission, main merge or deployment.
- Actual JEV review of the nonsecret documentation workflow selected `suitable_for_scoped_documentation` (probability 0.99, confidence 0.98), `bounded_documentation_checkpoint_only` (1.00/1.00) and `no_direct_source_review` (1.00/1.00). Usage: 948 input + 161 output tokens. This workflow review does not certify document values. Independent review of the complete diff and expected-head guarded publication remain separate requirements.

The companion manifest is `evidence/phase1d_cp10/continuation_2026_10_10_manifest.json`. It is a documentation provenance artifact, not a production cohort or full replacement for the original accepted ledgers.

## 5. Continuation status

This note records the verified Republic CP10 source-field checkpoint above. Additional platform research must be appended only after its final artifacts and independent review are available; it cannot be presumed from active work. Full Phase 1D remains open.

## 6. StartEngine native-memorandum recovery, 2026-10-10

Recovered the native-linked Voltaic Marine offering memorandum: 45 PDF pages, 41,636,538 bytes, SHA-256 `1fc30125ed6333437efe67f239ce7ab8924addcef40569b14130bfa781b429e8`. This is substantive source recovery within the frozen 1,545-URL directory frame; it adds no new URL or funded-round admission.

- The document distinguishes Delaware issuer Voltaic Marine, Inc. from Oregon parent Voltaic, LLC and their different formation/effective dates. Do not collapse parent, issuer or clocks.
- Advertised base terms are common stock at USD 1 per share, USD 15,000 target, USD 1,235,000 maximum and USD 200 minimum investment; bonus provisions prevent an unqualified executed-price inference.
- An undated embedded campaign screenshot displays USD 18,847.38 and 34 investors. It is not final proceeds or proof of a completed security-producing close. Its countdown is not converted into an exact date.
- May 2, 2023 in the PDF and June 21, 2023 in the captured native page are scheduled deadline observations. Extension/amendment chronology is unresolved; neither is an actual close, and two deadlines do not establish two economic rounds.
- June 21 at 11:59 PM PDT and June 22 at 06:59 AM UTC are the same instant. Normalize timezones before labeling date discrepancies; this equivalence does not resolve the distinct May deadline.
- OCR misread Suite 350 as 550. Independent visual inspection of the original establishes 350; erroneous OCR was excluded. Material OCR fields require visual confirmation against the original.
- A separate H2O.ai indexed title/Reg D SPV observation stays held outside the target scope. An aggregator's suggested filings/amount remain discovery-only because primary documents were not retrieved.

The independent final JEV accepted scoped source fields, held round/completion and retained study gates, with selected probability/confidence 1.00 for each. Receipt usage: 1,827 input + 150 output tokens. Frozen claims hash: `c1e8af9f0e05073c700a0bd016d2f026b81878c61fd19b1fca2b04ec6f7dd505`. Exact launch, actual successful close, final proceeds, canonical economic round, historical census and estimator admission remain unestablished. Model output is not independent proof of these events.

Independent review recomputed the original PDF hash and visually inspected physical pages 1, 2, 3, 9, 31, 32, 36, 42 and 45, then checked saved native campaign and indexed-page records directly. The manifest fingerprints that review separately from its later final JEV decision.

## 7. Wefunder partial round-link review, 2026-10-10

Reviewed three existing baseline candidates: Unitonomy (62840), PDX FC (61198) and RIZOME (57310). The frozen baseline remains **65 events across 57 native profiles**; this review adds no event or profile IDs. The complete prior twelve-event selection was unavailable, so novelty versus prior review remains provisional.

- Native profiles report funded months February 2021, February 2021 and August 2021 respectively. These month-level badges/displays do not establish exact first-live or successful-close dates.
- Unitonomy Details displays issuer name Unitonomy Inc., a SAFE link label, round URL token 36123 and a February 2021 SAFE table row of USD 134,710. The template body was not fetched. A linked SEC issuer-path CIK 1821191 is an unvisited link, not independently validated issuer identity.
- Keep Unitonomy's separate March 2020 SAFE row of USD 237,500 apart from the February 2021 row. The issuer's separate-cap-table OrgVitals narrative is not Unitonomy same-round proceeds, a qualified follow-on or a verified continuity bridge.
- PDX FC displays USD 94,271 while its inherited event amount is USD 94,271.76. Preserve both source values and precision; do not silently equalize them, infer a rounding method or label the difference an established contradiction.
- Unitonomy financial-period labels are inconsistent and cash/runway text is dated April 2022. This page does not establish current operations or survival. PDX FC and RIZOME Details remain unreviewed.

Revised frozen claims SHA-256: `b30ce1538d9101d31badd22eda954d40bc1421af2226aa69b5860fce643acebb`. The provenance covers 95,358 preserved source-text bytes including the inherited baseline, web-rendered profile text and browser accessibility text; this is not raw HTML or network-transfer volume. Independent review recomputed all three hashes, counted the baseline and checked original saved anchors/links. Final JEV accepted attributed source fields with probability 0.98/confidence 0.97; separate unresolved identity and context-only/no-incremental-count choices were 1.00/1.00. Usage: 2,028 input + 165 output tokens. These are model judgments. Final review/receipt details are bound in the manifest. Exact dates, executed terms, legal/economic identity, outcomes, historical coverage and estimation remain held.

## 8. Previously pending factual-review gates closed

Two actual JEV reviews completed for the preserved CabinetM public-source findings and five Republic PDFs. They resolve the former pending review labels at source/context scope; they do not admit funded economic rounds, legal closure timepoints, investor returns, numerical priors or Phase 1D completion.

- **CabinetM:** accepted issuer-attributed dissolution context and relative certificate-receipt timing from the public post at https://wefunder.com/feed/235158. November 2025 is inferred relative to the December 23, 2025 post; November 1–30 is a conservative certificate-receipt interval, not the effective legal dissolution date or completed operating-cessation date. Loss fraction, payout/MOIC, canonical round and estimator admission remain held. All selected source-scope choices had probability/confidence 1.00.
- **Republic:** three Arka filings are one offering amendment chain, alongside one Base8 Form C and one A Boring Life Form C/A. JEV accepted source fields only (1.00/1.00) and selected one Arka chain (probability 0.98/confidence 0.96), not three rounds. Final executed securities, early-investor terms, canonical round, cohort entry and outcomes remain held. The exact reviewed payload contained historical queue counts; those do not override the successor CP10 inventory above. Base8's signed Form C date 2024-09-25 was separately verifier-backed and was not a field in that JEV payload.

The companion manifest contains all five source-document hashes/URLs and actual receipt fingerprints. CabinetM receipt SHA-256: `c0a1ece30f4a104b3d6dce3e3713a57d2af509227e03e57228184b6a2c2b6bd4`; Republic receipt: `09b13d53179d053f5254ecb7bba73d1883ce84b41d7f4f943fb7bc58aa8e6ab1`. The two calls used 2,554 input + 307 output tokens. These are model judgments for specific supplied scopes, not independently measured outcome probabilities.

## 9. Separately delivered supervised implementation

A supervised budgeted-agent implementation was delivered separately, with mandatory JEV gates and shared phase budgets. The verified handoff recorded 83 local package checks, 53 independent package checks and 75 concurrency checks. Recorded final ZIP SHA-256: `d0804a5377b9df68746087eeb51ffeb05d346c0dd5441a7610cab0f4e2893475`.

These are package-specific implementation checks, not full-repository regression or scientific-study passes. They were not rerun for this documentation change. The package is not integrated into this repository or an unattended runtime; this commit adds no implementation code or binaries. Operational tooling delivery does not close the population, identity, funding, outcome, estimation or research-plateau gates.

## 10. Successor review: four prior materialization holds resolved

2026-10-10; independent final review as of 05:26:30 UTC. This entry follows documentation commit `1c2d33e15ecce0dccbce25089f88c8ce150acfd0`. The four Chilling, Currently Wine, Ecotone Renewables and Moriondo Coffee materialization holds described in section 2 are now resolved. The earlier text remains a dated record of that prior review; it is not the current access status for these four documents.

Four exact public-source requests returned HTTP 200 without redirects or retries: 7,186,139 raw PDF bytes, each byte-identical to its original CP10 capture. This is recovery of previously captured evidence, not four new native documents, companies or economic rounds. Original CP10 capture totals remain unchanged. This review recomputed raw PDF hashes; inherited gzip and Git metadata were not newly retrieved or independently rehashed by this wave.

Independent review accepted 80 enumerated source fields: 87/87 text anchors passed both parsers with Unicode whitespace removal only, and 30 material pages were visually inspected. The 372 parsed PDF pages are not 372 semantically reviewed pages. Visual-only fields remain separately labeled.

- **Chilling, Inc.:** original Form C and Series 2022 Crowd SAFE; stated USD 10m cap without independently normalized pre/post-money basis. The form's two signer dates on physical page 31 read August 19, 2022. Garbled extracted date text required visual confirmation; no dual-parser date pass is claimed. Actual SAFE page 71 is blank. First qualifying financing permits issuer discretion.
- **Currently Wine / Proud Pour Inc.:** the campaign brand maps to the document-level legal issuer Proud Pour Inc. The Series 2025 SAFE explicitly uses a USD 8m pre-money cap and 20% discount with conditionally mandatory conversion. Form signed January 21, 2025; target deadline April 21, 2025. Actual SAFE page 56 is blank. The source-level name association does not admit canonical historical identity.
- **Ecotone Renewables PBC:** Series Seed-4 Preferred Stock offered at USD 0.6073 per share, distinct from USD 0.001 par value. Exact offer arithmetic: 82,331 shares = USD 49,999.6163 target; 870,844 shares = USD 528,863.5612 maximum. Generic valuation-cap boilerplate does not reclassify preferred stock as a SAFE. The issuer's stated USD 10m implied valuation is offer wording with basis unestablished on that page; no completed priced round or comparable follow-on is proven. Form signed December 17, 2024; target deadline March 17, 2025; subscription page 79 is blank.
- **Moriondo Coffee / Luxbeverage LLC:** Series 2022 Crowd SAFE with USD 6.4m pre-money cap through the campaign's first USD 500,000 of subscriptions, then USD 8m for USD 500,000.01–1,235,000. One investor can receive both tranches. Keep one campaign's tiered terms distinct from two economic rounds; conversion concerns LLC equity units. Form signed December 21, 2022; target deadline February 19, 2023; actual SAFE page 59 is blank.

All four original forms mark no co-issuer; CIK 0001751525 is still the intermediary's identifier. Campaign IDs and launch dates remain inherited context, not revalidated by this document tranche. Signing, SEC acceptance, first-live, target deadline, actual completion and investor issuance remain different clocks and gates.

Accepted ledger SHA-256: `36449f5a5099e88604f4eb1884066684983db8ff549158c2edd43ce32dc85d0f`. One actual independent final JEV call bound all 80 field values/page references; it selected source-field acceptance, materialization-only accounting, preserved instrument distinctions and research incomplete, each probability/confidence 1.00. Usage: 7,485 input + 191 output tokens. These are model judgments, not additional source evidence or empirical certainty.

No canonical issuer/economic round, completed funding date, outcome, denominator, numerical prior, full-document semantic completion or global plateau is admitted. Parent/amendment lineage, legal identity, actual funding, historical census and dated outcome gates stay open.

## 11. Final bounded source tranche: four further original filings

2026-10-10; independent final review as of 05:36:30 UTC. Four already-captured CP10 originals were materialized from their exact native public URLs: Inlightened, Reental, Revero and Upside. Four GETs returned 7,331,578 PDF bytes, matching the original CP10 hashes and lengths without redirects or retries. This does not increase native capture, company, campaign or economic-round counts.

Independent review accepted 91 enumerated source fields, with 95/95 text anchors passing both parsers and 28 material pages visually inspected. The 520 parsed pages are not a full semantic audit. All four actual investor SAFE signature blocks remain blank.

- Inlightened, Inc.: original Form C signed August 25, 2022; Series 2022 Crowd SAFE with USD 7m conversion cap, basis not adjudicated beyond the source label. First qualifying financing permits issuer discretion. November 4, 2022 is the source target deadline; actual SAFE page 68 is blank.
- Reental Holding Company: original Form C signed March 21, 2024; Series 2024 Crowd SAFE, USD 42m conversion cap with basis unassigned, 20% discount and issuer-discretion conversion. The cover describes 120 days after launch while body wording uses the end of a fourth-month period after commencement. Preserve both formulations; do not manufacture an exact calendar deadline or derive launch from signing. A known later amendment is unreviewed, so these original terms are not claimed as latest operative terms. Actual SAFE page 70 is blank.
- Revero Inc: original Form C signed September 23, 2025; Series 2025 SAFE with explicit USD 50m post-money conversion cap and conditional issuance under its formula. December 22, 2025 is a target deadline; actual SAFE page 72 is blank. This post-money cap is not interchangeable with a pre-money cap or a priced-equity valuation. Its qualifying financing definition requires at least USD 1m cash; older forms' explicit instrument-conversion exclusion wording is not imported.
- Upside / Vision Sports Ventures, PBC: original Form C signed August 20, 2024; Series 2024CF SAFE with explicit USD 45m pre-money cap and 20% discount. Actual SAFE page 78 is blank. Its Equity Financing definition has no stated dollar minimum; do not import a USD 1m threshold from other forms. The instrument's conditional liquidity cash-out formula references the greater of 3x purchase amount or conversion amount, subject to qualifications and priority; this is not a realized 3x return. The source separately describes a Vision Sports Ventures, Inc.-to-PBC conversion and names Daily Number and Hubstar as collateral/security-agreement parties. The SAFE references a March 24, 2023 security agreement, while the attached amended agreement has a blank effective date. These source statements do not establish collateral perfection/enforceability, registry-verified canonical continuity, co-issuers, completed outcomes or investor proceeds.

All four original covers mark no co-issuer and identify the intermediary CIK, not a verified issuer CIK. Parent campaign/timeline and amendment-chain binding, issuer identity, actual execution/issuance, completed financing and exact date, outcomes, historical census and estimation gates remain open.

Accepted ledger SHA-256: aa4175e1d4e1ebe2f432ca7b0559f928dd89e90e7ca03580564b9f3adcb101f4. One actual independent final JEV accepted the enumerated source fields, preserved all instrument/identity/date distinctions and selected a closed bounded source review with research incomplete, each probability/confidence 1.00. Usage: 8,081 input + 168 output tokens. These are structured model judgments, not empirical certainty or investment-return probabilities.

## 12. Combined checkpoint and resource stopping boundary

The two successor tranches cover eight distinct original documents: 171 enumerated fields, 182 passing text anchors and 58 independently visually inspected pages. They used eight exact public GETs and 14,517,717 raw PDF bytes. Four previously documented materialization holds are resolved; the other four already-captured originals gain field reviews. Original CP10 capture totals remain unchanged. These review counts are neither new cohort entries nor full-document semantic completion.

This closes the final bounded source-review batch under the current scope and resource allocation. Further source acquisition requires a new scope/budget decision. The observed stopping boundary is operational; it does not establish scientific completeness or global exhaustion of research alternatives. Phase 1D remains incomplete, no numerical prior is promoted, and all unmet population, identity, funding, outcome and estimator gates remain explicit. Earlier accepted artifacts and the predecessor documentation commit remain preserved.

Observable budget checkpoint, 2026-10-10 05:37:53 UTC: 23 of 24 JEV invocation slots are consumed, including one cancelled invocation with unknown cost. One slot remains; another standard source-plan plus independent-final-review cycle needs two calls and would reach 25, exceeding the current cap. Continue only after an explicit same-phase budget decision; do not automatically reset the phase or its allowance. Native tokens, active time, historical usage and total download/cost data are not fully observed, so this checkpoint certifies neither global spending nor 500 MB compliance.

## 13. Frozen-protocol correction and stagewise admission

2026-10-10. Independent readers audited the original Phase 1C/1D rules at revision `994175e232687dcb0d1ddcd11a6917e72b02ff74`, including `docs/PHASE_1C_SPEC.md`, `src/phase1c/identity.py` and `src/phase1c/model.py`. The continuation's general wording had become too restrictive when read as universally requiring private executed investor contracts, individual receipts, issuer CIK or a complete agreement audit before any funded-row admission. That universal interpretation is corrected; the frozen study gates are not weakened.

Company identity may use exact strong identifiers or at least two independent medium identifiers, such as legal-name/domain agreement, with 100% second review of medium/manual matches. Name similarity alone is insufficient; conflicting strong identifiers cannot be bypassed. Layer B requires a successfully completed financing that produced an investment/security position and a successful close date. Source-bound public aggregate completion evidence can establish that predicate without every investor's private executed contract. Positive commitments or a blank offering template alone still do not establish completion.

Economic-round identity still requires issuer, comparable instrument/terms and overlapping-window reconciliation. Known material amendment, cohost, series or tranche conflicts remain claim-specific holds. Exact final investor terms are required when material to the particular valuation, identity, comparability or investor-return claim. A current historical-population gap or missing post-close follow-up does not erase an otherwise supported individual identity/funding observation; it does continue to block the corresponding population/outcome/estimator claim.

Earlier PDF-only reviews remain correct in saying they did not establish execution or completion from those PDFs. Later parent/timeline/identity review adds evidence; it does not rewrite their source limits. Section 3's broad next-gate wording is clarified accordingly, and original receipts/field ledgers remain unchanged.

The CP10 collector initializes identity/admission flags to false and never performs downstream adjudication. Its 568 unadjudicated rows are not 568 scientific rejections. The separate derived funnel is 363 launch-year candidates -> 335 matching parent close -> 318 finalized -> 305 also with positive parent amount. The earlier 305 single-unvalidated-CIK subset uses a different predicate. Do not equate memberships merely because counts match, require finalized as a newly invented universal rule, or mass-admit the entire date-verified set.

Independent tests reproduced 13 frozen-rule behaviors, including the medium-ID review path and separation of model predicates from source proof. These are synthetic implementation checks, not empirical outcome evidence. Actual final audit JEV selected stagewise correction, reviewed lineage/terms and bounded admissions only, each probability/confidence 1.00; model judgment does not replace independent source review.

## 14. Two accepted recommendations, before downstream application

The immutable admission matrix and final acceptance overlay support two bounded observed Republic round recommendations from the preserved legacy campaign frame. Neither URL belongs to the 568-new-candidate subframe. The matrix itself made zero production admissions; downstream adapter application and estimator eligibility are separate statuses.

| Selected campaign | Verified launch / offering year | Platform-reported completed close | Native dated raised milestone | Original offered instrument |
|---|---|---|---|---|
| Phantom Phood Inc. | 2023-02-14 / 2023 | 2023-04-16 | USD 39,645.69 | Crowd SAFE Series 2023; USD 12m offered cap |
| Stock Card, Inc. | 2022-09-06 / 2022 | 2022-12-16 | USD 41,580 | Crowd SAFE Series 2022; USD 10m offered cap |

Legal name, domain and headquarters match native parent and Form C; page 8 reciprocally identifies each campaign. Mandatory independent identity review, separate raw timeline replay, source hashes and known-frame collision checks passed. The parent explicitly reports successful funding/closure, and positive aggregate funding exceeds each original USD 25,000 minimum. These are source-attributed financing observations, not audited net cash or individual contract execution. The union collision check covers the 125 legacy plus 568 new Republic candidate records, not an exhaustive five-platform graph.

Phantom's hero USD 39,645, footer USD 39,646 and timeline USD 39,645.69 remain separate displays; no rounding mechanism is invented. Its possible concurrent outside offering is conditional, not proven to have occurred. Its prior 2022 USD 197,000 SAFE financing at a USD 5m cap is not merged into Series 2023. Stock Card's earlier USD 25,000/37,000 SAFEs and their different conversion terms remain distinct from the offered Series 2022 instrument, even where nominal caps match.

All caps retain original-offered-term scope; comparable priced valuation remains null. Empty cohost lists mean none positively identified in this bounded review, not proof of absence. Outcomes, censor dates, investor returns, unobserved amendments/cohosts, full historical coverage and numerical estimation remain unadmitted.

Matrix SHA-256: `0bbadd0f5d85d039eb6a7b2288ef9a1681d118428ec843ec0fed6a793311eebc`. Final acceptance overlay SHA-256: `e8b60c16cd2b3f5e69aa2a410c151287c5b65a7a804167c40c15e59b310a1e23`. The matrix has 87 local checks and 24 independent source checks, with 10 PDF pages independently viewed. Final JEV selected both bounded observed rounds at probability/confidence 1.00; its 0.02 judgment for numerical rates or phase completion is not an empirical probability or work-completion percentage.

## 15. Implementation and CI observations requiring separate disposition

The audit reproduced a graph hazard: overlapping same-company/same-instrument records with both priced valuations null can merge while ignoring cap/term differences. Null is unknown, not evidence of comparable terms. A cap difference can also represent valid within-offering tranches, so unconditional splitting is not the solution. The required disposition is source-reviewed same/distinct/unresolved relationships, preserving issuer/window constraints and blocking false follow-on events. The audit report is not a code-fix certificate; apply the separately verified implementation status below when available.

At the inspected branch revision, GitHub Actions Phase 1B run 38028415416 failed its 205-test discovery with three import errors: bs4 in one test module and requests in two. Its full verifier was skipped. Phase 1C run 38028415402 and Phase 1D run 38028415420 succeeded. The observed failing job used PR #3 merge commit `5ec58d3c5dccfe95a52caa9851f097b36034a6a7`. These are historical run observations, not a pass for later changes. Dependencies must be repaired without skipping tests; local validation and subsequent remote CI must be reported separately.

The previous resource stopping note remains an explicitly dated checkpoint. Work resumed under renewed continuation direction and the same phase history. A bounded source review, accepted two-row recommendation, engineering fix or green historical workflow still cannot establish Phase 1D completion or global plateau.

## 16. Reviewed graph repair and CI dependency alignment

The integrated graph repair adds SAME/DISTINCT/UNRESOLVED relations and a source-attested same-offering/amendment path. Missing priced terms, invalid numeric values and unresolved cap differences cannot silently become proven matching rounds. Complete-link matching prevents tolerance chaining; unresolved components do not emit or get bypassed by fabricated NEXT_ROUND edges. A qualifying priced follow-on now requires both endpoints to satisfy funded-completed Layer B and have finite positive comparable priced values. SAFE caps never substitute for priced valuations.

The new `build_round_graph` result retains unresolved pairs. The compatibility `next_round_edges` wrapper still returns edges only, and `same_economic_round == False` includes unresolved pairs. Downstream consumers must use the richer result to expose those diagnostics; that migration remains open. `SameRoundEvidence` is a caller-supplied attestation: source bytes, quoted native relation, issuer identity and independent review must be verified before construction. A syntactically valid attestation or a campaign ID alone is not proof. No production source attestations or existing empirical estimates are silently generated or recomputed.

Exact graph SHA-256: `58b151aadce73bba3f916965bb8d86ea05fdb576fa3fa2f2d053ee8b2ec9c810`; reviewed graph/test diff: `2f45d274e952979afc347156848155f77ea45c0e2912cd936b3ecc6bba92fa4c`. Verification passed 34 added regressions, an independent rerun of those tests, 18 separate independent checks including 500 null-priced pairs and 24 input permutations, 16 original identity/model/graph tests, and two original reporting methods. The full reporting module and repository suite were not run in the focused local checkout. Final JEV accepted integration testing and targeted-verification-only scope, each probability/confidence 1.00; this does not certify a full scientific study.

The Phase 1B workflow now installs the same requests, beautifulsoup4 and curl_cffi dependencies already used by the passing Phase 1D workflow, before unchanged test discovery and verification commands. The workflow diff `055c83a3cf665c91c9e88e8c3ca814a0b32e6314668b9d6b04bd403c75c128e6` passed five static checks and exact local patch application. This fixes the identified dependency omission in configuration; successful dependency installation, full tests and CI on the integrated revision still require an actual run. Tests are not skipped or weakened.

## 17. Applied versioned research ledger and remaining acceptance gates

The exact-row adapter is now included at `data/phase1d/cp10/canonical-admission-v1/`. Its component release `v0.3.0` applies the two accepted legacy Republic recommendations to an immutable canonical research ledger: two companies, two observed economic rounds and two research Layer B rows. This component version does not change promoted Vera VERSION `0.5.0`. The matrix recommendation, adapter application and cohort-estimator admission remain separately recorded.

The applied ledger is `data/phase1d/cp10/canonical-admission-v1/releases/v0.3.0/canonical-research-ledger.json`, SHA-256 `026d411e62b5b37424a1bd2a9ec3e0c3fc88031c0d6f691b59c34aeb22fa7d28`. The adapter SHA-256 is `8bbc74533ade26aa4a41dc58884eb8dda8f0aa9b7e26c2bfd74024b84f280d73`. Canonical `valuation_cap` and `comparable_valuation` remain null for both rows. Their USD 12m/10m original offered caps live only in separately named, source-anchored offered-term metadata. Outcomes remain unadjudicated; production admissions and estimation-eligible rows both remain zero. No rate, prior, synthetic observation or hypothetical cohost/amendment bridge is added.

The portable package authenticates exact reviewed inputs and existing repository-relative source captures; it is deliberately not a generic semantic adjudicator for arbitrary campaigns. Twenty-eight path-only input normalizations preserve original matrix/decision hashes as lineage and have their own independent byte-bound attestation. Original receipts are not silently rebound to changed bytes. Source captures are reused without modification or duplicate PDF publication. Atomic release creation rejects different existing content; deterministic replay is identical.

The package passed 45 focused tests, 34 independent checks, repository-layout/default-discovery replay and 302 finite schema-parity diagnostic cases. A one-line integral-number parity correction received its own independent successor addendum and actual final JEV request bound to the new code hash. That final JEV accepted the exact successor at probability 0.99/confidence 0.98; these are model review judgments, not scientific completion percentages. The frozen schema checker uses the standard library and supports only the pinned schema's keywords; the separate reference-parity diagnostic is not a new runtime dependency.

Reproduce from a full checkout with `python data/phase1d/cp10/canonical-admission-v1/scripts/admission_adapter.py --source-root .` and the normal repository unittest command. The complete portable file manifest and final acceptance/independent/JEV receipts are bundled under that directory. Full repository regression and the relevant scientific verifiers on the exact integrated revision remain pending actual remote CI; local targeted passes must not be represented as that result.

Current disposition: reviewed bounded research integration with rates suppressed; exact integrated CI pending. This is progress toward a PASS_WITH_SUPPRESSION checkpoint, not an unqualified Phase 1D completion or global plateau. Missing outcomes can legitimately remain censored/unknown and sparse cells suppressed under the frozen rules; completion never requires zero missingness. It does require defensible declared-scope coverage and properly applied evidence/reporting gates. Feasible review of existing source evidence, historical frame recovery, dated outcome/follow-up ascertainment and downstream graph-diagnostic integration remain material work. A later scoped execution stop must satisfy the original genuine-research-iteration and independent stopping tests; engineering tests, access failure or a relabeled unresolved queue are insufficient.

## 18. Exact integration CI completed

Observed 2026-10-10 06:27:40 UTC. The integration commit `ee9c79eccfc5a2c9106138f6c6988f1d18db2133` has four completed successful GitHub Actions runs:

- [Phase 1B verifier (pull_request)](https://github.com/arults/Vera---Startup-Analyst-/actions/runs/38030746958), run `38030746958`: completed / success.
- [Phase 1D verifier (pull_request)](https://github.com/arults/Vera---Startup-Analyst-/actions/runs/38030747008), run `38030747008`: completed / success.
- [Phase 1C verifier (pull_request)](https://github.com/arults/Vera---Startup-Analyst-/actions/runs/38030746994), run `38030746994`: completed / success.
- [Phase 1D verifier (push)](https://github.com/arults/Vera---Startup-Analyst-/actions/runs/38030743225), run `38030743225`: completed / success.

The push-triggered Phase 1D run checks the published branch revision; the pull-request runs are associated with the same source head through GitHub's PR workflow context. This closes the previously pending integrated CI observation for that revision, including the formerly failing Phase 1B dependency path. It does not retroactively turn focused local tests into a full-checkout test run, nor certify a later documentation commit before its own checks run.

Sections 16-17 retain the limits and pending status recorded at integration time. The two-row ledger, original accepted source bytes and code are unchanged by this follow-up. There are still two applied research companies/rounds, zero production admissions and zero estimator-eligible rows. Successful engineering CI is not scientific study completion, global plateau, full historical coverage or evidence of new outcomes.

## 19. Remaining fourteen-document source review; final JEV and application pending

The fourteen remaining campaigns in the selected sixteen-document set now have independently supported local dispositions. This completes this bounded source-review pass, not every CP10 document's semantic review or the larger research scope. The split is nine ordinary observed-round proposals, one observed-financing proposal with an estimator-clock hold, two canonical-round holds retaining positive source evidence, and two 2019 first-live exclusions. None of these fourteen has been applied to the existing two-row admission release.

The source-final JEV gate remains unrun because specific authorization to transmit this tranche's methodology/findings for that external review is pending. Independent support is not represented as final JEV acceptance. A separately reviewed, versioned adapter extension is also required before any additional research-ledger admission; the current immutable two-row release is unchanged.

| Campaign | Native first live | Native final campaign completion | Dated campaign amount (USD) | Independently supported local disposition |
|---|---|---|---|---|
| [Get on Board](https://republic.com/get-on-board) | 2024-04-02 | 2024-07-02 | 64100 | Observed-round proposal |
| [Inlightened](https://republic.com/inlightened) | 2022-08-26 | 2022-11-05 | 162629.13 | Observed-round proposal |
| [Chilling](https://republic.com/chilling) | 2022-08-19 | 2023-03-01 | 289450.61 | Observed-round proposal |
| [Revero](https://republic.com/revero) | 2025-09-23 | 2025-12-23 | 1262624.85 | Observed-round proposal |
| [Nobody Studios](https://republic.com/nobodystudios) | 2022-12-26 | 2023-04-08 | 771105 | Observed financing; estimator clock held |
| [StartGlobal](https://republic.com/startglobal) | 2024-08-13 | 2024-11-12 | 115776 | Observed-round proposal |
| [BuyAlerts](https://republic.com/buy-alerts) | 2023-03-13 | 2023-07-12 | 1470818.40 | Canonical round held; positive source facts retained |
| [Currently Wine](https://republic.com/currently-wine) | 2025-01-21 | 2025-04-22 | 478706 | Observed-round proposal |
| [Ecotone Renewables](https://republic.com/ecotone-renewables) | 2024-12-17 | 2025-02-16 | 208391 | Observed-round proposal |
| [Moriondo Coffee](https://republic.com/moriondo-coffee) | 2022-12-21 | 2023-02-20 | 58700 | Observed-round proposal |
| [Upside](https://republic.com/upside-app) | 2024-08-20 | 2025-03-02 | 122815.83 | Canonical round held; positive source facts retained |
| [Reental](https://republic.com/reental) | 2024-03-22 | 2024-09-18 | 202725 | Observed-round proposal |
| [Layali](https://republic.com/layali) | 2019-09-28 | 2020-04-21 | 77172 | Exclude: 2019 first-live year |
| [Soar Robotics](https://republic.com/soar-robotics) | 2019-09-05 | 2020-03-11 | 1070000 | Exclude: 2019 first-live year |

The dated amounts above are native campaign aggregates, not audited net cash or current combined fundraising totals. Twenty-eight existing captured parent/timeline objects were recovered with Git-blob, gzip and raw-byte verification: 652,844 compressed bytes and 3,575,526 decompressed bytes. Fourteen already materialized documents (13 PDFs and one DOCX) were reused. No additional original document download or capture-count increase is implied.

Primary review passed 150 source/schema checks. Independent review passed 308 original-integrity/date checks, 152 matrix/schema/scope checks and 267 original-document anchor checks, including rereading all close-to-security clauses. These are distinct review units, not additional companies, outcomes or pooled sample sizes. The exact primary ledger is bound by SHA-256 `ce72599e524af405bf8683a71be351471d272541c3b70e16009f476312b10e23`; the companion manifest records the final independent artifact bindings and selected source hashes. Its embedded row summary is a documentation projection, not an edited replacement for the frozen ledger.

### Findings and remaining case-specific gates

- Header scope matters. Currently Wine displays USD 1,408,706 in a combined header, while its dated milestone/footer is USD 478,706. Upside displays USD 742,815 in the header versus milestone USD 122,815.83 and footer USD 122,816. Both native tooltips explicitly describe public plus private funding at the same terms over a source-stated twelve-month period; the lookback anchor was not independently established. Keep these amounts separate. Do not infer exact private cash by subtracting rounded displays, or apply this interpretation to the earlier 305-row funnels without checking each source.
- Currently Wine's USD 930,000 prior SAFE dated 2024-02-16 makes arithmetic reconciliation plausible, but does not prove dollar-level tracing. Upside explicitly mentions outside investors, so outside financing is not merely hypothetical; its actual dates/economic-round grouping and amendment 13466 remain unreviewed. Its positive native campaign financing survives the canonical-round hold.
- BuyAlerts has explicit dated successful-close evidence alongside a `preparing_to_finalize` attribute and evolved maximum-offering amounts. Amendments 3878/3879 require case-specific reconciliation. Do not turn the DOM state into a universal finalized-only gate or infer invalid fundraising.
- Nobody Studios' document records a 2023-01-31 first security closing of USD 137,536 within the same offering that ended on 2023-04-08. Preserve both dates without inventing a second round. The estimator's first-versus-final close clock remains held.
- Reental's observed campaign funding can remain a proposal while amendment 10583 and final operative terms remain unresolved. Ecotone's Series Seed-4 preferred shares and Moriondo's two offered cap tranches keep their original instrument scopes. StartGlobal's DOCX close-to-security clause supplies bounded aggregate-funding context without claiming every investor's private contract is known.
- Layali and Soar retain their native 2019 launches even though final completion is in 2020. Soar's earlier cash draw reserved securities without issuing them; cash movement alone is not a new security-producing round.

Identity review uses legal-name/domain evidence with mandatory independent second review. Headquarters discrepancies are not counted as matches; different reciprocal document slugs are not called exact URL matches. The bounded Republic collision frame contains 693 records: 682 with searchable identity fields and 11 with null fields. Selected names/linked-CIK aliases match only their own URLs among those searchable records. This is neither clearance of the null records nor an exhaustive five-platform graph; linked CIKs remain unvalidated as strong issuer identifiers.

Status after this documentation update: two earlier research rows applied; fourteen independently supported local proposals/holds/exclusions pending final JEV and any adapter extension; zero production or estimator admissions. Outcomes, historical coverage, final operative terms where material, global plateau and full Phase 1D completion remain open. Finishing the selected source-review queue does not establish broad research exhaustion.

Durable resume checkpoint: [`data/phase1d/cp10/tranche14-source-review`](../data/phase1d/cp10/tranche14-source-review/README.md). It includes the portable matrix, independent review, project report, all native repository source references, scoped amendment inventory and an independently verified normalization/hash manifest. Original scientific values and original artifact hashes are preserved. Local path metadata and private retry details were normalized explicitly; the historical reviews are not silently rebound to changed bytes. No new native capture or ledger admission is introduced.
