"""Synthetic authorizations exercise gates; they never approve actual findings."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import test_scoped_review as fixtures
import evidence as e
import scoped_review as sc
import assignment_reassessment as ar


class AssignmentReassessmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.helper = fixtures.ScopedTests()
        self.data = self.helper.fixture()
        for source in self.data['sources']:
            source['retrieved_at'] = '2026-10-02T00:00:00Z'
            path = self.root / source['capture']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((fixtures.fixtures.ROOT / source['capture']).read_bytes())
        receipt = {'window': ['2026-10-01T00:00:00Z', '2026-10-01T01:00:00Z'],
                   'text': 'Synthetic prior assignment, explicitly reconstructed later.'}
        self.write('assignment.json', receipt)
        plan = self.data['research_plan']
        plan['policy'] = 'authorized-parent-assignment-2026-10-01'
        plan['declared_at'] = None
        plan['declared_timing'] = self.window('assignment.json', '/window', receipt['window'])
        self.write('plan.json', {'research_plan': plan, 'reconstructed': True})
        self.h = {
            'original_policy': plan['policy'], 'reviewed_under': e.POLICY,
            'assignment_kind': 'user_authorized_prepublication_research',
            'plan_was_reconstructed_after_collection': True,
            'reviewed_policy_hash': e.sha((fixtures.fixtures.ROOT / 'POLICY.md').read_bytes()),
            'amendment_policy': ar.AMENDMENT_POLICY, 'amendment_policy_sha256': ar.AMENDMENT_SHA256,
            'original_plan_reference': 'plan.json', 'original_plan_sha256': self.hash('plan.json'),
            'original_assignment_reference': 'assignment.json',
            'original_assignment_sha256': self.hash('assignment.json'),
            'selected_claim_ids': self.data['research_scope']['selected_claim_ids'],
            'same_selected_claim_scope': True, 'retrospective_reassessment': True,
            'new_policy_prospectively_registered': False, 'reviewed_by': 'synthetic-reviewer',
            'rationale': 'Synthetic scope-faithful retrospective reassessment only.',
            'coverage_equivalence': {k: {'status': 'satisfied_for_selected_scope',
                                        'basis': 'Synthetic independent check only.'} for k in ar.REQUIREMENTS},
            'new_required_searches': []}
        self.data['research_scope']['prepublication_assignment_reassessment'] = self.h
        self.registry = {'synthetic-reviewer': ['source_verifier'],
                         'synthetic-claim-reviewer': ['claim_verifier'],
                         'demo_importer': ['researcher'], 'synthetic-integrator': ['integrator']}
        self.write('reviews.json', {'text': 'Synthetic independently reviewed test receipt.'})
        self.sign()

    def write(self, name, obj):
        (self.root / name).write_bytes(e.stable(obj))

    def hash(self, name):
        return e.sha((self.root / name).read_bytes())

    def window(self, name, pointer, value):
        return {'kind': 'observed_window', 'lower': value[0], 'upper': value[1],
                'evidence_reference': name, 'evidence_sha256': self.hash(name), 'evidence_pointer': pointer}

    def sign(self):
        self.helper.sign(self.data)
        self.authorization = {
            'schema': 'vera.prepublication-assignment-authorization.v1',
            'evidence_packet_sha256': e.sha(e.stable(self.data)),
            'reassessment_sha256': e.sha(e.stable(self.h)),
            'original_policy': self.h['original_policy'],
            'original_plan_sha256': self.h['original_plan_sha256'],
            'original_assignment_sha256': self.h['original_assignment_sha256'],
            'assignment_scope_authenticated': True, 'retrospective_normalization_acknowledged': True,
            'authorized_by': 'synthetic-integrator', 'authorized_at': '2026-10-04T00:00:00Z',
            'acknowledgements': [
                {'actor': actor, 'role': role, 'policy': policy, 'policy_sha256': digest,
                 'acknowledged_at': '2026-10-03T00:00:00Z'}
                for actor, roles in self.registry.items() for role in roles
                for policy, digest in [(e.POLICY, self.h['reviewed_policy_hash']),
                                       (ar.AMENDMENT_POLICY, ar.AMENDMENT_SHA256)]],
            'review_receipts': [{'actor': actor, 'role': role, 'reference': 'reviews.json',
                                 'sha256': self.hash('reviews.json')}
                                for actor, roles in self.registry.items() for role in roles
                                if role in {'source_verifier', 'claim_verifier'}]}

    def report(self, authorization=True):
        return e.report(self.data, self.root, e.date('2026-10-10'), self.registry,
                        self.authorization if authorization else None)

    def assertHeld(self):
        self.assertEqual(self.report()['released_selected_claims'], 0)

    def test_authorized_window_reassessment_releases_and_preserves_input(self):
        before = e.stable(self.data)
        report = self.report()
        self.assertEqual(report['released_selected_claims'], 1, report)
        self.assertEqual(report['scope']['blockers'], [])
        self.assertEqual(before, e.stable(self.data))
        self.assertIsNone(self.data['research_plan']['declared_at'])
        self.assertIn('prepublication assignment', report['amended_policy_design'])

    def test_missing_authority_or_embedded_self_authorization_does_not_release(self):
        self.data['assignment_authorization'] = self.authorization
        self.assertEqual(self.report(False)['released_selected_claims'], 0)

    def test_each_binding_and_authentication_assertion_is_required(self):
        for key in ('evidence_packet_sha256', 'reassessment_sha256', 'original_policy',
                    'original_plan_sha256', 'original_assignment_sha256', 'assignment_scope_authenticated',
                    'retrospective_normalization_acknowledged', 'authorized_by', 'schema'):
            with self.subTest(key=key):
                old = self.authorization.pop(key)
                self.assertHeld()
                self.authorization[key] = old

    def test_assignment_plan_and_review_receipt_tampering_blocks(self):
        for name in ('assignment.json', 'plan.json', 'reviews.json'):
            with self.subTest(name=name):
                original = (self.root / name).read_bytes()
                (self.root / name).write_bytes(original + b' ')
                self.assertHeld()
                (self.root / name).write_bytes(original)

    def test_changed_original_plan_does_not_become_equivalent_by_resigning(self):
        self.data['research_plan']['entities'][0]['aliases'].append('Unplanned alias')
        self.sign()
        self.assertHeld()

    def test_stale_source_review_or_claim_review_still_blocks(self):
        self.data['source_review']['scope_sha256'] = '0' * 64
        self.authorization['evidence_packet_sha256'] = e.sha(e.stable(self.data))
        self.assertHeld()

    def test_legacy_policy_cannot_be_relabelled_as_assignment_even_with_new_authorization(self):
        self.h['original_policy'] = self.data['research_plan']['policy'] = 'vera.multisource.claim-policy.v1.0.0'
        self.write('plan.json', {'research_plan': self.data['research_plan']})
        self.h['original_plan_sha256'] = self.hash('plan.json')
        self.sign()
        self.assertHeld()

    def test_arbitrary_original_policy_cannot_reuse_authorization(self):
        self.h['original_policy'] = self.data['research_plan']['policy'] = 'invented-policy'
        self.assertHeld()

    def test_wrong_final_amendment_and_claim_policy_hashes_block(self):
        for key in ('amendment_policy_sha256', 'reviewed_policy_hash'):
            old = self.h[key]
            self.h[key] = '0' * 64
            self.sign()
            self.assertHeld()
            self.h[key] = old

    def test_each_actual_role_requires_both_policy_acknowledgements(self):
        for index in range(len(self.authorization['acknowledgements'])):
            ack = self.authorization['acknowledgements'].pop(index)
            self.assertHeld()
            self.authorization['acknowledgements'].insert(index, ack)

    def test_unregistered_integrator_or_reviewer_cannot_authorize(self):
        for actor in self.registry:
            roles = self.registry[actor]
            self.registry[actor] = []
            self.assertHeld()
            self.registry[actor] = roles

    def test_overlap_and_tampered_declaration_window_block(self):
        self.data['research_plan']['declared_timing']['upper'] = '2026-10-02T01:00:00Z'
        self.sign()
        self.assertHeld()

    def test_true_overlapping_receipt_window_cannot_pass(self):
        self.write('assignment.json', {'window': ['2026-10-01T00:00:00Z', '2026-10-02T01:00:00Z']})
        self.data['research_plan']['declared_timing'] = self.window('assignment.json', '/window',
                                        ['2026-10-01T00:00:00Z', '2026-10-02T01:00:00Z'])
        self.write('plan.json', {'research_plan': self.data['research_plan']})
        self.h['original_plan_sha256'] = self.hash('plan.json')
        self.h['original_assignment_sha256'] = self.hash('assignment.json')
        self.sign()
        self.assertHeld()

    def test_unbound_or_future_source_capture_window_blocks(self):
        self.data['sources'][0]['retrieval_timing'] = {'kind': 'observed_window',
                       'lower': '2026-10-02T00:00:00Z', 'upper': '2026-10-02T01:00:00Z'}
        self.sign()
        self.assertHeld()

    def test_receipt_bound_source_window_succeeds_without_invented_exact_time(self):
        self.write('capture.json', {'window': ['2026-10-02T00:00:00Z', '2026-10-02T01:00:00Z']})
        source = self.data['sources'][0]
        source['retrieved_at'] = None
        source['retrieval_timing'] = self.window('capture.json', '/window',
                                      ['2026-10-02T00:00:00Z', '2026-10-02T01:00:00Z'])
        self.sign()
        self.assertEqual(self.report()['released_selected_claims'], 1)
        self.assertIsNone(self.data['sources'][0]['retrieved_at'])

    def test_capture_after_claim_review_or_source_review_blocks(self):
        self.data['sources'][0]['retrieved_at'] = '2026-10-03T01:00:00Z'
        self.sign()
        self.assertHeld()

    def test_authorization_cutoff_is_utc_day(self):
        self.authorization['authorized_at'] = '2026-10-11T00:30:00+01:00'
        self.assertEqual(self.report()['released_selected_claims'], 1)
        self.authorization['authorized_at'] = '2026-10-10T23:30:00-01:00'
        self.assertHeld()

    def test_unperformed_material_route_is_not_bypassed(self):
        self.data['research_plan']['routes'][0]['status'] = 'unperformed'
        self.write('plan.json', {'research_plan': self.data['research_plan']})
        self.h['original_plan_sha256'] = self.hash('plan.json')
        self.sign()
        self.assertHeld()

    def test_missing_equivalence_and_remaining_searches_block(self):
        for key in ar.REQUIREMENTS:
            old = self.h['coverage_equivalence'].pop(key)
            self.sign()
            self.assertHeld()
            self.h['coverage_equivalence'][key] = old
        self.h['new_required_searches'] = ['Material gap']
        self.sign()
        self.assertHeld()

    def test_backdated_or_future_operator_authorization_blocks(self):
        for value in ('2026-10-02T00:00:00Z', '2026-10-11T00:00:00Z'):
            self.authorization['authorized_at'] = value
            self.assertHeld()

    def test_dual_exception_paths_or_prospective_policy_claim_block(self):
        self.data['research_scope']['historical_plan_reassessment'] = {}
        self.sign()
        self.assertHeld()
        del self.data['research_scope']['historical_plan_reassessment']
        self.h['new_policy_prospectively_registered'] = True
        self.sign()
        self.assertHeld()

    def test_malformed_authorization_fails_closed(self):
        for value in (None, [], 'untrusted', {'schema': 'wrong'}):
            self.authorization = value
            self.assertHeld()
