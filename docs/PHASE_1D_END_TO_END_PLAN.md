# Phase 1D End-to-End Autonomous Execution Plan

Date: 2026-10-17
Status: ACTIVE — research → update → build → log → test → verify → fix loop

## Goal
Build enough verified, multi-source, multi-platform cohort data (Wefunder, StartEngine, Crowdcube, Republic US, Republic Europe) across sectors so that Vera can produce stronger, exchangeability-checked empirical reference classes for operating survival, typed success, and confirmed closure.

Target: at least one platform-year or platform-field cell that passes RQ gates and can be submitted for Jev promotion, plus systematic coverage of the other platforms.

## Loop (repeat until stop condition)
1. **Research** — multi-source sweep (platform + SEC/UK filings + news + forums + YouTube + Google/Bing/DuckDuckGo) for a batch of companies.
2. **Update** — write RoundRecords, source captures, outcome events, identity reviews, and research coverage matrices into data/ and evidence/.
3. **Build** — extend extractors, schemas, and estimators as needed; keep Phase 1C contracts.
4. **Log** — append to docs/ITERATION_LOG.md and docs/PHASE_1D_RESEARCH_LOG.md; record rejected approaches.
5. **Test** — unit tests + Phase 1C regression + new Phase 1D gates.
6. **Verify** — run deterministic verifier; produce evidence/verifier/*.json.
7. **Fix** — address failures; reopen matcher or design only on concrete contract failure >2% identity error or censoring failure.
8. **Jev** — structured Choice/Noul/Score on freeze and promotion decisions.

Stop when: pilot + at least one additional platform have frozen Layer B cohorts with multi-source coverage, estimators run, and at least one cell is Jev-promotable, or when diminishing returns on public data are reached.

## Platforms and initial sources
- **Wefunder**: Phase 1B 42-row 2020 SEC-backed cohort already in data/cohort_manifest.csv. Expand 2021–2022 via EDGAR + platform pages.
- **StartEngine**: SEC Form C/C-U (CIK searches), Crowdfund Insider volume reports, platform explore pages. 2020 volume ~$147M.
- **Crowdcube**: Platform blog/shareholder updates, news (Phlo, Citymapper, Curve, etc.), Companies House where applicable. UK/EU focus.
- **Republic US**: republic.com portfolio/documents, SEC filings, public raise lists (Gumroad, Customer.io, etc.).
- **Republic Europe** (formerly Seedrs): europe.republic.com, Dealroom, news of acquisitions (Republic acquired Seedrs Dec 2021).

## Sector coverage
Use the 12 Phase 1C primary fields. Prioritize cells that can reach n≥30 / ≥5 events / ≥80% ascertainment, or document why they cannot.

## Non-negotiables (binding)
- Multi-source rules in docs/RESEARCH_SOURCE_RULES.md.
- No silence = survival/closure.
- No promotion without Verifier PASS + Jev.
- 2024–2025 right-censored.
- Company-round unit.
- Preserve all rejections in ITERATION_LOG.md.

## Immediate next batches
1. Materialize and live-hash the Wefunder 2020 cohort.
2. Seed StartEngine 2020–2021 known raises from public reports.
3. Seed Crowdcube and Republic examples from news and portfolio pages.
4. Run multi-source sweeps on a 10-company pilot subset.
5. Produce first estimator outputs and verifier evidence.
