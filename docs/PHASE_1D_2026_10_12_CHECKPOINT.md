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

## Successor verification checkpoint — completed through 16:10 UTC

This section is a later record. The earlier counts above remain the completed scope at 15:00. Scientific Phase 1D is still incomplete; the active plugin, promoted framework, empirical ledgers, existing callers and admission policies have not changed.

### Source coverage and temporal controls

Four completed Republic Europe research waves now cover **15 distinct pre-existing round rows across 11 canonical companies**. They are targeted source reviews, not 15 new histories or a cohort denominator. Relevant original filing pages supplied stronger transaction/security context in later waves. Reviews preserved asset-sale versus share-transfer meaning, gross figures versus recipient exceptions, legal versus operating dates, and unknown campaign-investor proceeds. No new native post-index endpoint or estimator admission followed from those external records.

A separate audit reviewed every row in the historical **47-row Republic US latest-report selection**: 25 exact source-observation dates, six period-valued reports and 16 holds, with 45 unique normalized body hashes. All original captures matched their recorded compressed Git blobs, decompressed hashes and visible-body bindings. Two parsers agreed, and 20 source-scope/temporal test methods passed; a coordinator replay passed the same 20 methods and adds no distinct coverage. No unsupported point date was demonstrated in the existing selection. A report's concrete present activity can support a report-day source observation without dating its retrospective milestones to publication. Period totals, forecasts and linked-content titles retain their separate limits. This temporal finding does not verify real-world assertions, independent ownership, terminal history or estimator eligibility.

The Republic US source-review counts are separate from the Republic Europe round/issuer counts. They must not be summed into a cross-platform population or new-admission total. Earlier saved posts belonging to held latest-report cases were identified as a separate research queue; their review is outside this checkpoint's completed temporal-audit scope.

### Active-caller negative finding and recovered verifier prerequisites

A malformed-input evaluation reproduced weaknesses in directly called legacy helpers but did **not** reproduce those inputs reaching the inspected reporting calculations. Follow-up/horizon validation and fixed internal interval configuration protected those paths. The tester and independent reviewer each reran 158 distinct selected test identities on both unchanged trees, without failures or skips. The reviewer added 13 independent tests, including valid forwarding controls and a validation-bypass sensitivity control. The 360 matched valid-output records and 600 rational comparisons are nested cases, not additional test-method counts. No implementation fix was justified. Excluded out-of-frame rows are not validated by these paths; this is not a ledger-validation census or a general helper-API robustness certificate.

The initial review could not run the aggregate Phase 1C verifier because five prerequisites were absent from its sparse local snapshot. A successor check retrieved those files at commit [7201259](https://github.com/arults/Vera---Startup-Analyst-/commit/7201259213660713ab2a22866b4d8c3928abe34d), verified their Git blobs and all 184 Python files against that revision, and passed all **25 framework gates** in a fresh isolated run. The complete remote tree also confirmed the scope-guard's three forbidden full-dataset paths were absent. This resolves that particular local execution gap; it does not rewrite the earlier UNRUN receipt, claim whole-tree identity for the earlier snapshot, or constitute full-repository testing or Phase 1D promotion.

### Synthetic interval availability and coverage

Seven locally predeclared mathematical scenarios ran 200 trials each, with 199 company-bootstrap draws per trial: **1,400 trials and 278,600 draws**. The models had known Bernoulli operating probabilities, equal cluster sizes, independent censoring in one scenario, and a paired perfectly correlated two-round scenario. An independent reviewer reproduced all records byte-for-byte and reconstructed every draw from company counts, checking point estimates, IJ variance, percentile interpolation, availability denominators and Monte Carlo uncertainty. These simple models are not startup-population calibration.

The exercise exposed a diagnostic limitation, not a new estimator coding defect. In the 30-company scenario with synthetic truth 0.90, the analytic normal interval contained truth in 156 of 192 issued intervals; the bootstrap contained it in 191 of 192. The other eight trials withheld intervals. Exact binomial enumeration supports the normal method's finite-sample undercoverage. At synthetic truth 0.99, both methods issued intervals in only 52 of 200 trials; 52/52 conditional coverage is not certainty or full availability. The report retains Monte Carlo uncertainty, withheld counts and the separate joint issuance-and-coverage quantity.

In that 0.90 scenario, there were 35 truth-containment disagreements but zero endpoint-distance flags at the configured 0.05 threshold. An endpoint-disagreement flag therefore cannot certify calibration or nominal coverage. Its absence is not an interval-quality approval. The existing normal interval remains diagnostic only; no interval-method switch is made here.

One evaluator-summary bug was corrected in a preserved successor: the original summary expected the wrong supported-status literal. Raw trial statuses and all calculations were correct and unchanged. The corrected recount uses explicit recognized labels and rejects unknown ones. Original plan, runner, records and result remain preserved beside the corrected summary. Local predeclaration is bounded by the observed tool window, not represented as externally registered or precisely filesystem-timestamped. External model review was not run while the separate export approval was pending.

## Successor source checkpoint — completed through 17:15 UTC

This is a later completed-work record. Earlier sections retain their historical scope and counts. The private repository audience, frozen five-platform rules, promoted framework v0.5.0 and active plugin 0.3.13 remain unchanged. No source-review result below changes a canonical admission, analytical clock, empirical caller or numerical prior.

### Additional source and issuer coverage

Five completed Republic Europe source-review waves now cover **17 distinct pre-existing round rows across 13 canonical companies**. The fifth wave added two rows and two companies to the earlier 15/11 scope. Its independent review completed 100 checks. Legal share-transfer records, acquirer/asset transaction context and conditional consideration were kept separate from campaign-beneficiary proceeds. Brand continuity, a nominal share transfer or estate receipts did not establish investor return. These are targeted research records, not 17 new admissions or a population denominator.

A separate Republic US review read **20 earlier saved posts across four campaign URLs**, plus four held latest-post contexts. It preserved 40 typed source facts and 42 support spans, including point, period, future, historical and mixed date roles. Independent source adequacy passed with caveats; analytical use remained held. Concrete reported activity can strengthen a bounded observation without resolving issuer continuity, economic-round identity, investor instruments or complete terminal history.

Original campaign/document reviews then strengthened four native issuer/offering bridges. One packet authenticated seven native originals and 13 post bindings, with 21 author tests and 22 independent tests, including 254 negative/mutation probes. The other authenticated 15 original archive bindings, including six newly reviewed campaign/timeline/document sources and nine prior posts, with 34 author tests and 28 independent tests, including 36 rejected mutants. Their counts describe different source units and overlap earlier post reviews; they must not be summed as new companies, rounds or independent origins. Offered SAFE caps and blank template agreements were not treated as priced equity valuations or executed investor positions. Historical-security table discrepancies and later-round relations remain explicit holds.

### Native funding notices and temporal scope

The existing 47-campaign latest-report selection supplied a bounded timeline audit: 46 saved native timelines were reviewed structurally, with one exhausted lane excluded. These contained **815 visible cards: 706 issuer-post excerpts, 92 launch/final milestones and 17 platform locked-funds notices across 14 campaign URLs**. All compressed Git blobs, decompressed hashes and historical launch/final date pairs matched their pinned records. There were no date or notice-amount corrections.

Independent review reconstructed every card and checked all 17 complete locked-notice contexts and all 57 financing-keyword-selected excerpt contexts. The 26 author tests and 41 independent tests passed, including 49 rejected negative controls/mutants. The other 649 issuer excerpts received structural checks only in this pass; full linked posts and historical completeness were not verified. The keyword rule was fixed after archive recovery and before manual excerpt reading, not externally preregistered. A separate controlling addendum corrects the original report's stronger wording without rewriting its sealed bytes.

The earliest observed locked notice per affected campaign precedes its final source label by 22–142 days; all 17 individual notice gaps span 15–142 days. These are source-label differences, not investor holding periods or new analytical origins. Notice amounts were not added to final totals, assigned an ISO currency from the dollar symbol alone, or treated as separate economic rounds. A saved locked-funds notice supports its stated funding activity but does not establish the first financing, first investor-security issuance or complete prior history.

### Provenance corrections and bounded stops

Independent checks distinguished historical republic.co document links from republic.com campaign records, rather than asserting literal host equality. Another packet's local metadata mislabeled an older commit reference as a root tree; a separate receipt reconstructed the correct pinned tree and verified all 15 source blobs. The sealed original remains preserved with the correction. Source fidelity and a narrow interpretation can be accepted while broader investor/outcome inferences remain unresolved.

A cancelled original-download operation in a separate live-source lane remains incomplete and uncounted, with exact targets and the cancellation boundary retained in its receipt. No denied/cancelled route was retried. External model review remained pending for the separately blocked source export; local verifier passes are not JEV passes. These are bounded source and verification advances, not a study-wide plateau or Phase 1D completion.
