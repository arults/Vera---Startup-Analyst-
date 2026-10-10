# Evidence-review lessons and regression links

Local publication candidate. The 13 required skills remain in [SKILL.md](SKILL.md). These lessons do not claim improved model accuracy.

## 1. Material research cannot be downgraded to obtain release

A verifier-required unrestricted search and identity document had been treated as optional context. Preserve their materiality; difficulty representing times is not a scope exception.

Evidence status: Observed draft scope correction. Regression: [test_historical_plan.py::test_required_route_cannot_be_demoted](tests/test_historical_plan.py).

## 2. Unknown times stay unknown

Use only genuine receipt-bound execution windows. Later offline inspection is never a retrieval timestamp. Overlapping windows do not establish order.

Evidence status: Observed representational limit and regression. Regression: [test_time_windows.py::test_split_receipt_window_is_bound; test_plan_overlap_unknown; test_completedby_cannot_establish_start](tests/test_time_windows.py).

## 3. Review must bind the entire parent dataset

Binding only the prior plan allowed changed parent claims or sources to escape stale-review checks. Bind exact parent bytes and original/current policy hashes.

Evidence status: Observed defect, reproduced and fixed. Regression: [test_historical_plan.py::test_parent_bytes_changed_without_plan_change_holds; test_policy_hashes_required](tests/test_historical_plan.py).

## 4. Contradictions must work in either direction

A cancellation record can contradict a selected completion claim without contradicting itself. Preserve inbound, outbound and transitive context.

Evidence status: Observed defect, reproduced and fixed. Regression: [test_scoped_review.py::test_reverse_contradiction_cannot_evade_closure; test_link_only_contradiction_blocks_without_self_conflict](tests/test_scoped_review.py).

## 5. Malformed nested metadata must fail safely

Lists, strings and nulls in inspection or timing fields caused uncontrolled exceptions. Validate shape and return explicit hold or validation error.

Evidence status: Observed defects, reproduced and fixed. Regression: [test_scoped_review.py::test_malformed_inspection_reported_hold; test_time_windows.py::test_malformed_window_types_hold_without_crash](tests/test_scoped_review.py).

## 6. Different hosts do not imply independent facts

An issuer website and issuer assertion hosted by a regulator can have the same factual origin. Count claim-specific origin groups separately from route types.

Evidence status: Preventive challenge confirmed by tests. Regression: [test_scoped_review.py::test_regulatory_and_issuer_origin_not_doublecounted](tests/test_scoped_review.py).

## 7. Business identification does not establish every issuer link

A buyer identifies the acquired business, but canonical offering continuity requires separately bound identity evidence. Do not infer legal control or holder payout.

Evidence status: Observed actual-input gap corrected. Regression: [test_evidence.py::test_identity_pending_holds; test_name_only_holds; test_empty_strong_id_cannot_bypass_identity](tests/test_evidence.py).

## 8. Short excerpts do not establish full-document inspection

Use accurately scoped original sections, exact locators and qualifiers under the amended policy. Material unread appendices remain a hold.

Evidence status: Observed provenance overstatement corrected. Regression: [test_scoped_review.py::test_section_mode_does_not_fake_fullread; test_unread_material_appendix_blocks](tests/test_scoped_review.py).

## 9. Retrospective reassessment is not preregistration

Preserve the original policy and declaration. Require fresh selected-scope equivalence and hold unmet new requirements.

Evidence status: Observed historical-plan migration risk corrected. Regression: [test_historical_plan.py::test_retrospective_positive_preserves_old_policy; test_cannot_claim_new_policy_preregistered; test_missing_new_requirement_holds](tests/test_historical_plan.py).

## 10. Freeze after documentation changes

Documentation edits after a manifest freeze invalidate package verification. Rebuild the final manifest, then test exact bytes.

Evidence status: Observed manifest mismatch corrected. Regression: [verify_package.py](verify_package.py) and [test_native_pins_unchanged](tests/test_evidence.py).

## 11. Forecast and recorded completion are distinct predicates

Fleeting’s preview forecasts July 10, 2020, while preserved parent/milestone displays record July 11 completion. Preserve both; no invented timezone conversion, settlement instant or extension.

Evidence status: Observed archive ambiguity, no automatic adjudication. Check status: Proposed archive-specific regression; not yet executable.

## 12. Offering IDs do not prove distinct economic rounds

Ember has overlapping native offering records. Keep offering identities separate until counterpart originals and security definitions establish economic-round relationships. Do not sum fundraising displays.

Evidence status: Observed archive ambiguity, no automatic adjudication. Check status: Proposed economic-round identity regression; not yet executable.

## 13. Denied request and canceled status poll are different actions

A tunnel-denied source request remains an attempted source-read row. Canceling a status poll does not create another source request. Reconcile request receipts and control-plane actions separately.

Evidence status: Observed accounting reconciliation correction. Check status: Receipt reconciliation check; no dedicated executable regression yet.

## Version binding

The original thirteen lessons’ executed regression references refer to implementation 1.0.2, frozen manifest SHA256 3aca306ce2473754fab84c3b118a70bb0e089a71559a8cf2639de30e30e375d7. The three archive/accounting lessons are separately documented review findings; their proposed dedicated regressions have not been executed. Original research archives and private review records are omitted.

## Precision-withdrawal successor

Implementation1.0.3introduced explicit independently reviewed precision withdrawal. Exact original DOM ownership, unchanged event/claim semantics, genuine separate reviewer roles and stale-review hashes are mandatory. See [contract](PRECISION_WITHDRAWAL.md), [validator](precision_withdrawal.py) and [tests](tests/test_precision_withdrawal.py). The original13lesson test references remain available; new130test result does not create actual research approval.

## Shared report-version provenance

A duplicate scoped report-version literal escaped126tests. Implementation1.0.3.1corrects only that metadata path. Both scoped and unscoped reports must use the engine constant; [version tests](tests/test_report_version.py) also check manifest/lineage declarations. Recompute reports from unchanged inputs and compare every other field; never hand-edit historical output labels. See [output provenance](OUTPUT_PROVENANCE.md).
