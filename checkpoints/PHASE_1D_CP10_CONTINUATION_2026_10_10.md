# Phase 1D CP10 continuation: verified fields, corrections and open gates

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
2. **Operative instrument chain:** bind original filings, amendments, latest terms and actual investor instruments. Obtain missing full agreement bodies where needed. A template's cap is not a priced valuation.
3. **Funded Layer B and time zero:** bind actual successful financing, investor issuance/receipt and completed close. Keep launch, signature, deadline and completion separately typed; preserve failed/withdrawn/pending cases.
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
