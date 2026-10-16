# Vera Research Source Rules — Quality, Depth, and Breadth

Date: 2026-10-17
Status: OPERATIONAL RULE — applies to all live company analysis and Phase 1D evidence collection

## Principle
Vera's probabilistic model is only as good as the evidence that feeds it. Every material claim must be supported by high-quality, provenance-tagged sources drawn from a deliberately wide variety of channels. Missing a signal from any major channel is a research failure, not a "not found."

## Required source categories (must be searched for every material company or cohort)
1. **Primary platform & regulatory**
   - Platform campaign/round pages, issuer updates, portfolio pages (Wefunder, StartEngine, Crowdcube, Republic US, Republic Europe).
   - SEC EDGAR (Form C, C-U, C-AR, 8-K, etc.) for US Reg CF.
   - Equivalent UK/EU filings where applicable.

2. **Independent news & journalism**
   - Major outlets (TechCrunch, Bloomberg, Reuters, Financial Times, WSJ, etc.).
   - Sector-specific and local business press.
   - Company press releases only as starting points; never sole evidence.

3. **Discussion forums & community**
   - Reddit (r/startups, r/investing, r/SecurityAnalysis, company-specific, equity-crowdfunding subs).
   - Hacker News, Indie Hackers, specialized Discords/Slacks when publicly indexed.
   - Investor comment threads on the platforms themselves.

4. **Video & long-form**
   - YouTube (founder interviews, pitch videos, product demos, analyst breakdowns).
   - Podcast transcripts when available.
   - Conference talks.

5. **Multi-engine search discipline**
   - Google, Bing, and DuckDuckGo must all be queried for key claims (company name + outcome terms, founder names, product + controversy, etc.).
   - Results from each engine are discovery only; the underlying page or document is the evidence.
   - Record which engines returned unique hits.

6. **Additional corroborative**
   - LinkedIn (team, headcount signals), Crunchbase/PitchBook (public portions), company websites, GitHub (for tech claims), government grant databases, court filings.

## Evidence rules (unchanged non-negotiables still apply)
- Every source carries: URL or accession, retrieval date, availability state, content hash where feasible, and evidence class (primary / independent_secondary / company_controlled / community / video).
- Search-engine snippets are never evidence.
- Company-controlled sources are allowed only after documented independent-search exhaustion and are labelled lower confidence.
- Silence, stale page, or "no recent news" never equals survival or closure.
- Conflicting credible sources become explicit contradiction ledger entries; never silently resolved.
- Forum and YouTube claims require the same verification standard as any other secondary source before they can move probabilities.

## Research workflow to embed in Vera
1. Coverage matrix: mark each source category as searched / not-found / inaccessible / not-material.
2. Multi-engine pass for every high-value unknown (Value-of-Information prioritized).
3. Extract candidate claims with provenance.
4. Jev (or equivalent structured judgment) evaluates support / contradiction / silence for material claims when needed.
5. Only Verifier-passing, provenance-bound evidence may update reference classes or company-level posteriors.

## Phase 1D application
When extracting outcomes for the Wefunder pilot and later multi-platform cohorts, the same multi-source sweep applies to every company that reaches Layer B. Platform-hosted + SEC remains the primary evidence for funding and official status; forums, news, and YouTube supply corroboration, contradiction, or early signals that must still be verified before they affect survival/success/closure labels.

## Promotion discipline
No rate, prior, or company probability may be promoted if a material source category was skipped without an explicit "searched-not-found" or "inaccessible" flag.
