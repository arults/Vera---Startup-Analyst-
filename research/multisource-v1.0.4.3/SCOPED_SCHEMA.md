# Scope extension contract, implementation 1.0.2 / policy 1.1.0

The exchange envelope remains `vera.multisource.evidence.v1`; `policy` selects the amended semantics. JSON Schema checks structure; Python validates hashes, authority, chronology and cross-record semantics. Neither authenticates arbitrary self-supplied reviewer names. The caller supplies a trusted operator reviewer registry.

## Scope and contextual evidence
`research_scope.selected_claim_ids` identifies proposed released findings. The full parent ledger is retained. `context_links` names from/to, relation, reviewed_by, rationale, plus contradiction status/resolution. Claim dependencies and contradictions, inbound contradiction links, shared-entity/shared-source relevance, and affected counterevidence routes determine closure. `route_dispositions` may explain context or materiality, but cannot demote `research_plan.verifier_required_route_ids`. A context claim need not itself be release-eligible. Unresolved contradictions still block dependent selected claims.

`source_review` adds scope_sha256, claim_ids, context_claim_ids, timing_checked and inspection_scope_checked. The scope digest binds the full source/claim/plan snapshot and all scope decisions. No approval is migrated automatically. Origin assessments record factual_origin_id and scoped authority; SEC hosting alone does not make an issuer assertion independent.

## Time provenance
Exact searched_at/retrieved_at are allowed only when known. A search_timing object uses kind observed_window, lower, upper and either evidence_reference/evidence_sha256/evidence_pointer selecting the exact two-element window, or lower_evidence and upper_evidence each naming reference/sha256/pointer. Actual receipt bytes must match. Completed_by has no established lower bound and cannot prove post-declaration execution. Both exact and interval representations, if present, must agree. Bounds must be aware timestamps and are compared as UTC instants. Required chronology uses latest earlier bound versus earliest later bound; overlapping intervals do not establish order. Known-by acquisition is not earliest public availability. Never fill historical gaps using the current clock.

## Inspection
source.inspection has scope full_document or relevant_sections, document_reference, original_sha256, sections with exact locator and context, exclusions, limitations, adequate_claim_ids, qualifiers_checked, cross_references_checked and unresolved_material_sections. Its review binds inspection_sha256, reviewer and reviewed_at. Section adequacy requires genuine independent inspection of relevant qualifiers and cross-references, including material identity evidence identified by claim.identity.evidence_source_ids. Unread material appendices hold. No full-read claim is inferred from a short excerpt.

## Historical plan reassessment
research_scope.historical_plan_reassessment preserves original_policy, original_policy_hash, reviewed_under, reviewed_policy_hash, parent_dataset_reference, parent_dataset_sha256, original_plan_document_reference/hash, original_plan_sha256, selected_claim_ids and same_selected_claim_scope. It requires retrospective_reassessment=true, new_policy_prospectively_registered=false, reviewed_by and rationale. coverage_equivalence must explain claim_scope, source_authority, identity_mapping, contradiction_search, timing_provenance and inspection_scope. Any new_required_searches blocks equivalence. Review binds the full parent bytes, not just its plan. The original declaration time and policy are unchanged.

## Prepublication assignment reassessment
Use the separate operator-bound contract in [ASSIGNMENT_REASSESSMENT.md](ASSIGNMENT_REASSESSMENT.md) when the original provenance is an authorized assignment, not the legacy v1.0.0 dataset. Detailed postcollection normalizations are never labeled preregistered.
