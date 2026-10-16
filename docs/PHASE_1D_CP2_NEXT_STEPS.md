# Phase 1D CP2 — Next Concrete Steps (executed)

Date: 2026-10-17

## Done in this commit
1. **Extractor fleshed out**: `src/phase1d/pilot_extractor.py` now reads `data/cohort_manifest.csv` (the verified Phase 1B 42-row 2020 funded cohort) and emits:
   - `data/phase1d_wefunder_pilot_rounds.json` (RoundRecord-shaped)
   - `data/phase1d_wefunder_pilot_captures.json` (source-capture stubs with structural hashes)
2. **Identity-review schema**: `schema/phase1d_identity_review.schema.json` + template queue.
3. **Outcome-event schema**: `schema/phase1d_outcome_event.schema.json` (extends Phase 1C with evidence_class, source_category, and search_engines_used to enforce multi-source rules).
4. **Exact Jev payloads**: `evidence/jev/PHASE_1D_CP2_FREEZE_PAYLOADS.json` with Choice and Noul questions for cohort freeze, multi-source mandate, and identity threshold.

## Still required before freeze
- Run the extractor (`python -m src.phase1d.pilot_extractor`).
- Replace stub hashes with live SEC page fetches.
- Perform multi-source sweeps (news, Reddit, YouTube, Google/Bing/DuckDuckGo) per `docs/RESEARCH_SOURCE_RULES.md` for each company.
- Populate identity review queue and outcome events.
- Submit Verifier + Jev on the resulting artifacts.

## Non-negotiables
No rates promoted. Stubs are not evidence. Multi-source rules are now binding.
