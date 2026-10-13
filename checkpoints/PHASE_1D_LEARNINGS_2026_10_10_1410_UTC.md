# Vera evidence-review lessons — 2026-10-10 14:10 UTC

These 13 case-derived lessons are a learning log, separate from the 13 standing sourcing skills in SKILLS.md. They record corrections and prevention checks, not a claim of improved model accuracy.

Implementation 1.0.2 is a local candidate; its code package has not been published. Package integrity and 114 local tests passed, with an independent 114-test rerun. In an isolated copy, 113 tests passed and one native-archive-unavailable test was explicitly skipped. Actual real-pilot acceptance remains pending. Final private implementation JEV review is blocked pending specific disclosure authorization. Three archive/accounting lessons below have proposed or manual checks, not newly executed automated regressions. Phase 1D and global research plateau remain incomplete; estimates and production promotion remain disabled.

## 1. Material research cannot be downgraded to obtain release

A verifier-required unrestricted search and identity document had been treated as optional context. Preserve their materiality; difficulty representing times is not a scope exception.

Evidence status: Observed draft scope correction. Regression: test_historical_plan.py::test_required_route_cannot_be_demoted.

## 2. Unknown times stay unknown

Use only genuine receipt-bound execution windows. Later offline inspection is never a retrieval timestamp. Overlapping windows do not establish order.

Evidence status: Observed representational limit and regression. Regression: test_time_windows.py::test_split_receipt_window_is_bound; test_plan_overlap_unknown; test_completedby_cannot_establish_start.

## 3. Review must bind the entire parent dataset

Binding only the prior plan allowed changed parent claims or sources to escape stale-review checks. Bind exact parent bytes and original/current policy hashes.

Evidence status: Observed defect, reproduced and fixed. Regression: test_historical_plan.py::test_parent_bytes_changed_without_plan_change_holds; test_policy_hashes_required.

## 4. Contradictions must work in either direction

A cancellation record can contradict a selected completion claim without contradicting itself. Preserve inbound, outbound and transitive context.

Evidence status: Observed defect, reproduced and fixed. Regression: test_scoped_review.py::test_reverse_contradiction_cannot_evade_closure; test_link_only_contradiction_blocks_without_self_conflict.

## 5. Malformed nested metadata must fail safely

Lists, strings and nulls in inspection or timing fields caused uncontrolled exceptions. Validate shape and return explicit hold or validation error.

Evidence status: Observed defects, reproduced and fixed. Regression: test_scoped_review.py::test_malformed_inspection_reported_hold; test_time_windows.py::test_malformed_window_types_hold_without_crash.

## 6. Different hosts do not imply independent facts

An issuer website and issuer assertion hosted by a regulator can have the same factual origin. Count claim-specific origin groups separately from route types.

Evidence status: Preventive challenge confirmed by tests. Regression: test_scoped_review.py::test_regulatory_and_issuer_origin_not_doublecounted.

## 7. Business identification does not establish every issuer link

A buyer identifies the acquired business, but canonical offering continuity requires separately bound identity evidence. Do not infer legal control or holder payout.

Evidence status: Observed actual-input gap corrected. Regression: test_evidence.py::test_identity_pending_holds; test_name_only_holds; test_empty_strong_id_cannot_bypass_identity.

## 8. Short excerpts do not establish full-document inspection

Use accurately scoped original sections, exact locators and qualifiers under the amended policy. Material unread appendices remain a hold.

Evidence status: Observed provenance overstatement corrected. Regression: test_scoped_review.py::test_section_mode_does_not_fake_fullread; test_unread_material_appendix_blocks.

## 9. Retrospective reassessment is not preregistration

Preserve the original policy and declaration. Require fresh selected-scope equivalence and hold unmet new requirements.

Evidence status: Observed historical-plan migration risk corrected. Regression: test_historical_plan.py::test_retrospective_positive_preserves_old_policy; test_cannot_claim_new_policy_preregistered; test_missing_new_requirement_holds.

## 10. Freeze after documentation changes

Documentation edits after a manifest freeze invalidate package verification. Rebuild the final manifest, then test exact bytes.

Evidence status: Observed manifest mismatch corrected. Regression: verify_package.py; test_evidence.py::test_native_pins_unchanged.

## 11. Forecast and recorded completion are distinct predicates

Fleeting’s preview forecasts July 10, 2020, while preserved parent/milestone displays record July 11 completion. Preserve both; no invented timezone conversion, settlement instant or extension.

Evidence status: Observed archive ambiguity, no automatic adjudication. Regression: Proposed archive-specific regression; not yet executable.

## 12. Offering IDs do not prove distinct economic rounds

Ember has overlapping native offering records. Keep offering identities separate until counterpart originals and security definitions establish economic-round relationships. Do not sum fundraising displays.

Evidence status: Observed archive ambiguity, no automatic adjudication. Regression: Proposed economic-round identity regression; not yet executable.

## 13. Denied request and canceled status poll are different actions

A tunnel-denied source request remains an attempted source-read row. Canceling a status poll does not create another source request. Reconcile request receipts and control-plane actions separately.

Evidence status: Observed accounting reconciliation correction. Regression: Receipt reconciliation check; no dedicated executable regression yet.

## Exact version and limitations

Package manifest SHA256 3aca306ce2473754fab84c3b118a70bb0e089a71559a8cf2639de30e30e375d7. Policy SHA256 1aadf72d14ab9481c034f7b73b97de66964bb3ca8d21c5f19bab22814c9b818d. The original public-safe lesson text is bound by SHA256 75c7a099d3b2c0babc660be122fcc6e04e7fac37d1cb6b72085bc6cf265be689. The implementation and its referenced test files are local artifacts, not links to published code. The test references above identify the checks; publishing this log does not publish or rerun those checks. Three archive/accounting lessons have proposed or manual checks, not newly executed automated tests. No model-accuracy improvement or complete research coverage is claimed.

Validation scope: local package integrity, all three native pins, JSON Schema validation and skill validation passed. Exact local validation summary SHA256 782f9f362c68415b3ac15e71e5a65d948815414ad2ce4ddfa4f4b5810821c7e7. No actual research-batch release, remote CI result, investor outcome or complete cohort coverage is asserted by this documentation.
