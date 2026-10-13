# Reviewed precision withdrawal, implementation 1.0.3

Policy 1.1.0 and frozen 1.0.2 remain unchanged. This implementation successor supports one narrow historical reassessment correction. It cannot change an event day, bound, predicate, identity, assertion or evidence relationship.

`research_scope.precision_withdrawal` binds claim_id, source_id, previous_dataset_reference/sha256 (the superseded reviewed predecessor), original_parent_sha256, previous_source_snapshot_sha256, corrected_source_snapshot_sha256, corrected_material_sha256, original_document_reference, ownership_audit_reference/sha256, time_diff and reviews.

The validator independently computes the full time diff, including key presence. It allows only existing nonempty date_timezone to null, absent report_time to null, and absent date_precision_note to the exact NOTE constant in precision_withdrawal.py. Every other time key and nested value must be equal. Every core claim field must equal the superseded reviewed predecessor; predicate supported type is unchanged. Review rationale/signatures may be refreshed independently.

The original historical parent and superseded reviewed predecessor are separately bound. Corrected material digest excludes source_review, correction object and claim reviews to avoid circular signing. The final scope digest still binds correction reviews and the entire ledger. Hashes establish changed bytes, not reviewer authenticity.

The DOM audit binds original source bytes, the issuer-owned displayed day, the exact issuer date selector and separate comment title ancestry. The validator independently parses those original bytes; retained issuer day must match exactly. Source original hash must match its predecessor and the named source must directly support the corrected claim. A changed document cannot be substituted as a metadata withdrawal.

Two distinct operator-authorized reviewers must approve the exact correction digest, with roles claim_verifier and source_verifier. Neither may be the collector/researcher. Their reviews follow the audit and precede the final source review. Existing semantic, inspected-source, coverage and authority gates remain mandatory. No previous approval migrates.

Actual-input workflow: prepare pending derivative with fixed note and correction bindings; clear affected reviews; obtain fresh semantic review; finalize material/correction digest; obtain genuine separate correction attestations; then sign final source scope. The source verifier must repeat any review invalidated by material changes. All predecessors remain immutable and superseded status is explicit.

Known source retrieval instants or window upper bounds must precede the ownership audit. If retrieval time is unknown, source_time_basis must explicitly be hash_bound_inspection_existed_by_audit_not_exact_retrieval; this is a causal inspection bound, never an inferred exact acquisition time. The rejected comment title must contain the withdrawn zone token. All other claims and their contextual relationships must remain unchanged apart from refreshed review metadata.
