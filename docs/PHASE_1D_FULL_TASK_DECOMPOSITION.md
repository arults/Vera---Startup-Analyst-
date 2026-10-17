# Phase 1D Full Task Decomposition

Date: 2026-10-17
Status: ACTIVE EXECUTION PLAN
Goal: Complete multi-platform, multi-source, verified cohort data sufficient for stronger empirical reference classes (baseline model) while keeping the Vera (Jev + Verifier) promotion layer strict.

## Master loop (repeat until stop)
1. Select company or platform-year batch.
2. Extract Layer B RoundRecords + source captures (primary first).
3. Multi-source sweep (platform/regulatory + news + forums + YouTube + Google/Bing/DuckDuckGo).
4. Verify every material claim (hash, cross-source, contradiction ledger).
5. Build outcome events and identity links.
6. Run estimators (AJ/CIF, company-cluster bootstrap).
7. Log hypotheses, evidence, mistakes.
8. Verifier gates (including multi-source gate).
9. Jev promotion decision.
10. Fix or expand; never silently promote.

## Decomposed tasks by workstream

### A. Scope and governance (done / ongoing)
- A1. Freeze CP1 platform-year cells and non-negotiables.
- A2. Maintain RESEARCH_SOURCE_RULES.md and SKILLS.md.
- A3. Keep ITERATION_LOG and RESEARCH_LOG append-only with hypothesis/evidence/result/mistake.

### B. Data extraction
- B1. Wefunder 2020: run pilot_extractor + live hashes on cohort_manifest.csv (42 rows).
- B2. StartEngine: parse Form C/C-U for CIK 0001665160, 2020–2022.
- B3. Crowdcube: platform campaign pages + news for named raises (Phlo, Curve, Citymapper, etc.).
- B4. Republic US: portfolio/raise pages (Gumroad, Customer.io, etc.).
- B5. Republic Europe / Seedrs: campaign archives and year-in-review lists.
- B6. Identity resolution across platforms (strong ID or ≥2 medium).

### C. Company-level verification (example pattern — apply to every Layer B company)
For each company answer and source:
- C1. Still operational? (platform page, Companies House, news, website).
- C2. Years since last crowdfunding round.
- C3. Total funding raised (platform + later VC).
- C4. Current revenue (if disclosed).
- C5. Investor return context for each round (secondary, valuation step-up, or unknown).
- C6. Typed outcome event (operating evidence, qualified follow-on, IPO, closure, or none).
- C7. Multi-source coverage matrix complete.
- C8. Contradiction ledger if sources conflict.

### D. Outcomes and statistics
- D1. Apply state machine and censoring rules.
- D2. Run AJ/CIF + bootstrap on eligible cells.
- D3. RQ gates (n≥30, ≥5 events, ≥80% ascertainment).
- D4. Produce reporting artifacts with limits and non-comparability notes.

### E. Verification and promotion
- E1. Deterministic verifier (Phase 1C gates + multi_source_gate).
- E2. Jev Choice/Noul/Score on freeze and promotion.
- E3. Update registry only after PASS.
- E4. Version notes and bias register.

### F. Stop condition
- At least one platform-year or platform-field cell passes RQ gates, Verifier, and Jev, with full multi-source provenance.
- Systematic coverage started on all five platforms.
- Baseline model strengthened with verified company-level anchors (Phlo-style profiles).

## Immediate next decomposed tasks
1. Complete Phlo verified profile (C1–C8) and store as template.
2. Hash primary pages for Curastory, BOXABL, Phlo.
3. Wire multi_source_gate into verifier path.
4. Expand StartEngine skeleton to real Form C parse plan.
5. Repeat company verification pattern on 5 more companies.
