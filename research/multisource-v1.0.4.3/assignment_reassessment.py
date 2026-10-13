"""Operator-bound reassessment of a preserved prepublication research assignment.

This checks bindings, not identities or receipt truth. The caller must independently
authenticate the operator authorization, just as it must the reviewer registry.
"""
import json
import re
import datetime as dt
from pathlib import Path
from evidence import POLICY, sha, stable, safe_path
from timing import bounds

AMENDMENT_POLICY = 'vera.source-admission.v1.2.0'
AMENDMENT_SHA256 = 'ad27a76dbc1e2d45d8a3ba14d9567856a6a16a74feebfe529fb4cf6d4efd25a4'
REQUIREMENTS = {'claim_scope', 'source_authority', 'identity_mapping',
                'contradiction_search', 'timing_provenance', 'inspection_scope'}


def checked_bytes(root, record, reference_key, hash_key):
    raw = safe_path(root, record[reference_key]).read_bytes()
    if sha(raw) != record[hash_key]:
        raise ValueError('reassessment receipt hash mismatch')
    return raw


def validate_assignment(data, root, as_of, registry, authorization):
    """Fail closed unless a separately supplied operator approves these exact bytes."""
    try:
        h = data['research_scope']['prepublication_assignment_reassessment']
        review = data.get('source_review') or {}
        if not isinstance(h, dict) or not isinstance(authorization, dict):
            return False
        if 'historical_plan_reassessment' in data['research_scope']:
            return False
        a = authorization
        integrator = a.get('authorized_by')
        if (a.get('schema') != 'vera.prepublication-assignment-authorization.v1'
                or 'integrator' not in registry.get(integrator, [])
                or a.get('evidence_packet_sha256') != sha(stable(data))
                or a.get('reassessment_sha256') != sha(stable(h))):
            return False
        original_policy = h.get('original_policy')
        if not isinstance(original_policy, str) or not re.fullmatch(r'authorized-parent-assignment-\d{4}-\d{2}-\d{2}', original_policy):
            return False
        dt.date.fromisoformat(original_policy.removeprefix('authorized-parent-assignment-'))
        if (h.get('assignment_kind') != 'user_authorized_prepublication_research'
                or h.get('plan_was_reconstructed_after_collection') is not True
                or h['original_policy'] != data['research_plan'].get('policy')
                or a.get('original_policy') != h['original_policy']
                or a.get('assignment_scope_authenticated') is not True
                or a.get('retrospective_normalization_acknowledged') is not True):
            return False
        policy_hash = sha(Path(__file__).with_name('POLICY.md').read_bytes())
        if (h.get('reviewed_under') != POLICY
                or h.get('reviewed_policy_hash') != policy_hash
                or h.get('amendment_policy') != AMENDMENT_POLICY
                or h.get('amendment_policy_sha256') != AMENDMENT_SHA256):
            return False
        selected = set(data['research_scope']['selected_claim_ids'])
        if (h.get('same_selected_claim_scope') is not True
                or set(h.get('selected_claim_ids', [])) != selected
                or h.get('retrospective_reassessment') is not True
                or h.get('new_policy_prospectively_registered') is not False
                or not h.get('rationale')
                or h.get('reviewed_by') != review.get('reviewer')
                or 'source_verifier' not in registry.get(h.get('reviewed_by'), [])):
            return False
        equivalence = h.get('coverage_equivalence')
        if (not isinstance(equivalence, dict) or not REQUIREMENTS <= set(equivalence)
                or any(not isinstance(equivalence[k], dict)
                       or equivalence[k].get('status') != 'satisfied_for_selected_scope'
                       or not equivalence[k].get('basis') for k in REQUIREMENTS)
                or h.get('new_required_searches') != []):
            return False
        original = json.loads(checked_bytes(root, h, 'original_plan_reference', 'original_plan_sha256'))
        checked_bytes(root, h, 'original_assignment_reference', 'original_assignment_sha256')
        if (original['research_plan'] != data['research_plan']
                or a.get('original_plan_sha256') != h['original_plan_sha256']
                or a.get('original_assignment_sha256') != h['original_assignment_sha256']):
            return False
        # Declaration, execution and source reviews still pass the ordinary timing gates.
        # Here also bind the operator's final act after the genuine approvals/acknowledgements.
        authorized, authorization_end, _ = bounds(a, 'authorized_at', 'authorization_timing', root)
        if authorized is None or authorization_end.astimezone(dt.timezone.utc).date() > as_of:
            return False
        if not review.get('researcher') or review['researcher'] == integrator:
            return False
        roles = {(review['researcher'], 'researcher'),
                 (review.get('reviewer'), 'source_verifier'), (integrator, 'integrator')}
        roles |= {(c['collector'], 'researcher') for c in data['claims'] if c['id'] in selected}
        for c in data['claims']:
            if c['id'] not in selected:
                continue
            accepted = [r for r in c['reviews'] if r['decision'] == 'accept'
                        and 'claim_verifier' in registry.get(r['reviewer'], [])]
            if not accepted:
                return False
            for r in accepted:
                roles.add((r['reviewer'], 'claim_verifier'))
                _, end, _ = bounds(r, 'reviewed_at', 'review_timing', root)
                if end > authorized:
                    return False
        review_start, review_end, _ = bounds(review, 'reviewed_at', 'review_timing', root)
        if review_start is None or review_end > authorized:
            return False
        from scoped_review import claim_sources
        used = {sid for c in data['claims'] if c['id'] in selected for sid in claim_sources(c)}
        for source in data['sources']:
            if source['id'] in used:
                _, acquired, _ = bounds(source, 'retrieved_at', 'retrieval_timing', root)
                if acquired > review_start:
                    return False
                for claim in data['claims']:
                    if claim['id'] in selected and source['id'] in claim_sources(claim):
                        for claim_review in claim['reviews']:
                            if claim_review['decision'] == 'accept':
                                start, _, _ = bounds(claim_review, 'reviewed_at', 'review_timing', root)
                                if start is None or acquired > start:
                                    return False
        for actor, role in roles:
            if not actor or role not in registry.get(actor, []):
                return False
            for policy, policy_sha in ((POLICY, policy_hash), (AMENDMENT_POLICY, AMENDMENT_SHA256)):
                matches = [x for x in a.get('acknowledgements', [])
                           if x.get('actor') == actor and x.get('role') == role
                           and x.get('policy') == policy and x.get('policy_sha256') == policy_sha]
                if len(matches) != 1:
                    return False
                _, end, _ = bounds(matches[0], 'acknowledged_at', 'acknowledgement_timing', root)
                if end > authorized:
                    return False
            if role in {'source_verifier', 'claim_verifier'}:
                receipts = [x for x in a.get('review_receipts', [])
                            if x.get('actor') == actor and x.get('role') == role]
                if not receipts:
                    return False
                for receipt in receipts:
                    checked_bytes(root, receipt, 'reference', 'sha256')
        return True
    except (AttributeError, KeyError, TypeError, ValueError, OSError, IndexError):
        return False
