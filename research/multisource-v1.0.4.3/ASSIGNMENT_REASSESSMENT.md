# Operator-bound prepublication assignment reassessment

This additive research-only path removes a workflow incompatibility, not an evidence
requirement. The historical v1.0.0 path is unchanged. Native data, frozen method guards,
claim policy bytes, statistical methods and estimator eligibility are unchanged.

An earlier user-authorized assignment can predate publication of source-admission
v1.2.0 without having been a v1.0.0 dataset. Preserve its original receipt. Describe a
later structured plan containing queries, results and route dispositions as a
postcollection normalization. Do not call those detailed fields preregistered. Keep
earlier normalization versions and observed-time limitations; exact old request
envelopes need not be invented or claimed available.

## Separate operator trust boundary

Use report(data, root, as_of, reviewer_registry, assignment_authorization), or the CLI
--assignment-authorization path. This argument is separately supplied by the operator,
like --reviewer-registry. An object embedded in the evidence input has no authority.
The operator must authenticate its origin and substantively review its assertions.
Neither hashes, JSON fields nor registry names authenticate identities or source truth.

The authorization is an immutable operator review receipt, not a credential, new
account permission or statistical-method approval. Never generate genuine approvals
from fixture names, copied signatures or an approval of a different packet.

## Packet fields

research_scope.prepublication_assignment_reassessment contains:

- assignment_kind: user_authorized_prepublication_research
- original_policy: authorized-parent-assignment-YYYY-MM-DD (a valid date)
- plan_was_reconstructed_after_collection: true
- original_assignment_reference and original_assignment_sha256: preserved receipt bytes
- original_plan_reference and original_plan_sha256: exact retrospective normalization
  JSON file whose research_plan equals the input plan. Its filename does not imply
  that it existed before collection.
- reviewed_under and reviewed_policy_hash: the unchanged v1.1.0 claim policy and hash
- amendment_policy and amendment_policy_sha256: published v1.2.0 and its exact hash
- selected_claim_ids, same_selected_claim_scope=true, retrospective_reassessment=true,
  new_policy_prospectively_registered=false, reviewed_by and rationale
- coverage_equivalence objects for claim_scope, source_authority, identity_mapping,
  contradiction_search, timing_provenance and inspection_scope; each needs status
  satisfied_for_selected_scope and a substantive basis from the source verifier
- new_required_searches: [] only when no required search remains

Do not also provide historical_plan_reassessment. Legacy policy IDs cannot enter the
assignment route. Changing a label or receipt never grants authorization.

## External authorization fields

- schema: vera.prepublication-assignment-authorization.v1
- evidence_packet_sha256: sha256(stable(data)); stable is canonical sorted-key compact
  UTF-8 JSON, not the hash of a pretty-printed file
- reassessment_sha256: sha256(stable(the reassessment object))
- original_policy, original_assignment_sha256 and original_plan_sha256: exact matches
- assignment_scope_authenticated: true, only after the operator authenticates the
  actual original assignment scope; this does not authenticate unavailable old queries
- retrospective_normalization_acknowledged: true
- authorized_by: actual integrator with integrator role in the external registry
- authorized_at or receipt-backed authorization_timing, at/after independent reviews
  and acknowledgements and no later than the report as-of day in UTC
- acknowledgements: one entry per actual actor/role/policy tuple. Each has actor,
  role, policy, policy_sha256, and acknowledged_at or receipt-backed
  acknowledgement_timing. Required roles are all selected collectors/researchers,
  accepting claim verifiers, the dedicated source verifier and the integrator.
  Every role must exist in the external registry and acknowledge both exact policies.
- review_receipts: entries with actor, role, reference and sha256 for the actual
  independent source and accepting claim reviewers. Referenced bytes are checked.

The integrator must be distinct from the source review's researcher. Existing
researcher/verifier independence, claim/source hashes, authority, identity, relevant
section inspection, context closure, contradictions, material-route completeness,
cutoff and release gates still run. The helper does not replace any of them.

Declaration windows use the existing receipt-bound timing format. The declaration
window must establish a lower and upper bound; missing, inconsistent, tampered or
overlapping plan/search timing holds. Selected factual and identity-source acquisition
windows must be receipt-bound and end before the independent source and claim reviews.
Earlier reused evidence may predate the assignment. Exact times remain optional when
honest receipt-backed windows exist.

The report records the authorization hash, labels retrospective normalization and
explicitly disclaims historical-query-envelope authentication and estimator admission.
Passing only this adapter is insufficient to release a fact. All ordinary checks must
also pass; no numerical or empirical-method promotion follows.
