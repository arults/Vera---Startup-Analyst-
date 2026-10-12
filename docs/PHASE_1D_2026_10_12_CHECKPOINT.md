# Phase 1D bounded checkpoint — 12 October 2026

This records completed work through 15:00 UTC. **Scientific Phase 1D remains incomplete.** There is no new numerical prior, production cohort admission, empirical caller migration or active-plugin update in this checkpoint. The published analyst plugin remains 0.3.13; the latest promoted framework remains v0.5.0.

## Published engineering changes

1. [RQ2 offering-year key integrity](PHASE_1D_POOL_KEY_INTEGRITY.md), commit [011abbb](https://github.com/arults/Vera---Startup-Analyst-/commit/011abbb7135828ef987359ca7ab7074bf26cfe39), rejects invalid requested years and duplicate year cells before reporting decisions. Valid-input behavior is preserved. A later authorized archival replay passed all 58 reporting tests, including the previously unavailable replay; it reproduced the original 24 RQ1 and 60 RQ2 output rows without changing their values or order. The earlier report's one optional skip accurately describes its earlier execution, not the later replay.
2. [Operating uncertainty numerical guards](PHASE_1D_OPERATING_NUMERICAL_GUARDS.md), commit [c8a8e30](https://github.com/arults/Vera---Startup-Analyst-/commit/c8a8e3096da48d279a561052859019e0ce97e59b), adds an independently imported reporting guard. It preserves frozen mathematical estimators and raw samples, withholds machine-sized degenerate intervals, and rejects materially invalid probability domains. Its separate dependency/isolation checks and rational-reference tests do not establish empirical coverage.

For each published commit, all seven triggered GitHub workflow runs reached successful terminal states. Exact parent, changed-file set and remote file bytes were verified. These are engineering results. The additive guard is not automatically used by existing empirical callers.

## Tested adoption path

A separate, unmerged synthetic-only shadow-report proposal compared the original and guarded operating reports with matched explicit histories and configurations. Across 104 cases and 4,701 draws per side, raw mathematical points, sampled identities and analytic gradients were preserved. Three cases exhibited the intended reporting-only differences; 101 retained original fields exactly. Independent review found and fixed a double-read input-hash race before the proposal was sealed.

This proposal has not replaced an empirical caller. Further model review is pending. No permission, statistical adequacy or research admission should be inferred from the successful synthetic comparison.

## Bounded research and date review

Two completed source-review waves covered nine pre-existing round rows across five companies. This is targeted follow-up, not a representative cohort, a population total or nine estimator-ready histories. Exact source lineage, instrument meanings, date precision, missingness and holds were reviewed independently. Neither wave admitted a new exact history or changed the frozen ledger. Company-specific candidate facts and source receipts remain in separate research artifacts rather than this repository checkpoint.

A date-scope audit found no reproduced generic-footer propagation defect in the existing normalized tables. It compared 1,544 saved raw rows and joined all 952 scoped ledger rows to the saved derived date fields. Its later CP7 capture controls do not authenticate the earlier CP2 HTML bytes or semantically clear every campaign. The syntactic parser and source-specific interpretation still require separate review.

The five-platform frozen source policy remains in force. External primary records can inform a separately labelled research lane; their existence does not silently alter the study's eligibility, history, event definitions, clock or cutoff.

## Performance and accounting limits

Six predeclared synthetic workloads completed under a 45-second per-process bound. The largest tested workload, 250 histories/companies with 100 draws, took approximately 3.82 seconds of compute time and 23,808 KiB local child peak RSS. These measurements are not a full-cohort capacity guarantee, a serving-host observation or a performance plateau. No deployment SLO was supplied and no optimization was justified by this test alone.

Research tool counts cover visible worker calls only; shared calls are counted once, and concurrent wall intervals are not additive. Unexposed model usage, billing and host RAM remain unavailable rather than estimated from shell output or an unrelated helper process.

## Remaining gate

Resolve source-specific economic-round identity, funded origin, initial state, index-specific target, typed event history, endpoint observation and cohort assignment. Preserve unknowns, intervals, competing outcomes and all original rows. Source review, research admission, estimator adoption, uncertainty adequacy and scientific promotion remain separate decisions. A bounded search can stop when known public routes are exhausted without establishing global research completion.
