"""Public synthetic report-entrypoint regressions for selected identity sources.

Synthetic approvals deliberately permit contradictory chronology in negative cases;
the report cutoff must still fail closed. No real reviewer authority is asserted.
"""
import copy
import unittest

import evidence as e
import test_scoped_review as fixtures
import test_source_verifier as source_fixtures


class IdentitySourceCutoffTests(unittest.TestCase):
    AS_OF = e.date('2026-10-10')
    REGISTRY = {
        'synthetic-reviewer': ['source_verifier'],
        'synthetic-claim-reviewer': ['claim_verifier'],
    }
    IDENTITY_ID = 'synthetic-identity-only'

    def fixture(self, field='retrieved_at', value='2026-10-09T12:00:00Z', linked=True):
        helper = fixtures.ScopedTests()
        data = helper.fixture()
        data['sources'][0]['retrieved_at'] = '2026-10-02T12:00:00Z'
        identity = copy.deepcopy(data['sources'][0])
        identity['id'] = self.IDENTITY_ID
        identity[field] = value
        data['sources'].append(identity)
        if linked:
            data['claims'][0]['identity']['evidence_source_ids'] = [identity['id']]
        helper.sign(data)
        return data

    def report(self, data):
        before = copy.deepcopy(data)
        result = e.report(data, source_fixtures.ROOT, self.AS_OF, self.REGISTRY)
        self.assertEqual(data, before, 'Reporting must not rewrite source inputs')
        self.assertEqual(result['native_changes'], 0)
        self.assertIsNone(result['rates'])
        self.assertEqual(result['prior_promotions'], 0)
        self.assertEqual(result['scoped_source_coverage_audit']['blockers'], [])
        return result

    def assert_future_hold(self, field, value, blocker):
        result = self.report(self.fixture(field, value))
        row = result['augmented_observations'][0]
        # These production-state checks fail on the pre-repair implementation.
        self.assertEqual(result['released_selected_claims'], 0)
        self.assertEqual(row['release_status'], 'UNRELEASED_RESEARCH_OBSERVATION')
        self.assertIn(self.IDENTITY_ID + ':' + blocker, result['scope']['blockers'])
        self.assertEqual(row['status'], 'ACCEPTED_ATTRIBUTED_OBSERVATION')
        self.assertEqual(row['reasons'], [])

    def assert_release(self, field, value):
        result = self.report(self.fixture(field, value))
        self.assertEqual(result['released_selected_claims'], 1)
        self.assertEqual(result['scope']['blockers'], [])
        self.assertEqual(result['augmented_observations'][0]['release_status'], 'RELEASED_RESEARCH_FINDING')

    def test_identity_retrieval_next_utc_midnight_holds(self):
        self.assert_future_hold('retrieved_at', '2026-10-11T00:00:00Z', 'FUTURE_IDENTITY_RETRIEVAL')

    def test_identity_retrieval_same_local_day_future_utc_holds(self):
        self.assert_future_hold('retrieved_at', '2026-10-10T23:30:00-02:00', 'FUTURE_IDENTITY_RETRIEVAL')

    def test_identity_publication_future_calendar_day_holds(self):
        self.assert_future_hold('publication_date', '2026-10-11', 'IDENTITY_SOURCE_POSTDATES_AS_OF')

    def test_identity_as_of_future_calendar_day_holds(self):
        self.assert_future_hold('as_of_date', '2026-10-11', 'IDENTITY_SOURCE_POSTDATES_AS_OF')

    def test_identity_retrieval_last_utc_microsecond_releases(self):
        self.assert_release('retrieved_at', '2026-10-10T23:59:59.999999Z')

    def test_identity_retrieval_next_local_day_same_utc_day_releases(self):
        self.assert_release('retrieved_at', '2026-10-11T01:30:00+02:00')

    def test_identity_retrieval_equivalent_utc_instant_releases(self):
        self.assert_release('retrieved_at', '2026-10-10T23:30:00Z')

    def test_identity_source_same_calendar_day_releases(self):
        for field in ('publication_date', 'as_of_date'):
            with self.subTest(field=field):
                self.assert_release(field, '2026-10-10')

    def test_unselected_unlinked_future_source_does_not_block(self):
        data = self.fixture(value='2026-10-11T00:00:00Z', linked=False)
        data['sources'][-1]['publication_date'] = '2026-10-11'
        data['sources'][-1]['as_of_date'] = '2026-10-11'
        fixtures.ScopedTests().sign(data)
        result = self.report(data)
        self.assertEqual(result['released_selected_claims'], 1)
        self.assertEqual(result['scope']['blockers'], [])
        self.assertNotIn(self.IDENTITY_ID, result['scope']['reviewed_factual_origin_groups'])

    def test_unknown_selected_identity_source_holds(self):
        data = self.fixture()
        data['claims'][0]['identity']['evidence_source_ids'] = ['synthetic-missing-source']
        fixtures.ScopedTests().sign(data)
        result = self.report(data)
        self.assertEqual(result['released_selected_claims'], 0)
        self.assertIn('IDENTITY_OR_EVIDENCE_SOURCE_MISSING:synthetic-missing-source', result['scope']['blockers'])

    def test_malformed_identity_references_reject(self):
        for value in ('synthetic-identity-only', [42], None):
            with self.subTest(value=value):
                data = self.fixture()
                data['claims'][0]['identity']['evidence_source_ids'] = value
                fixtures.ScopedTests().sign(data)
                with self.assertRaisesRegex(ValueError, 'identity evidence IDs must be a string list'):
                    self.report(data)

    def test_naive_identity_retrieval_rejects(self):
        with self.assertRaisesRegex(ValueError, 'timestamp requires timezone'):
            self.report(self.fixture(value='2026-10-10T12:00:00'))

    def test_invalid_identity_calendar_date_rejects(self):
        with self.assertRaises(ValueError):
            self.report(self.fixture('publication_date', '2026-13-01'))

    def test_unknown_identity_retrieval_keeps_predicate_projection(self):
        data = self.fixture(value=None)
        data['sources'][-1]['retrieval_missingness'] = 'not_reported'
        fixtures.ScopedTests().sign(data)
        result = self.report(data)
        self.assertEqual(result['released_selected_claims'], 1)
        row = result['augmented_observations'][0]
        self.assertEqual(row['known_by_retrieval'], '2026-10-02T12:00:00+00:00')
        self.assertEqual([x['source_id'] for x in row['freshness']], [data['sources'][0]['id']])
        self.assertIsNone(data['sources'][-1]['retrieved_at'])

    def test_later_identity_source_does_not_become_predicate_corroboration(self):
        unlinked = self.fixture(linked=False)
        linked = copy.deepcopy(unlinked)
        linked['claims'][0]['identity']['evidence_source_ids'] = [self.IDENTITY_ID]
        # Different authority/origin metadata must not alter predicate projection.
        linked['sources'][-1]['source_type'] = 'official_registry'
        linked['sources'][-1]['publisher'] = 'Synthetic identity-only registry'
        fixtures.ScopedTests().sign(linked)
        baseline = self.report(unlinked)
        result = self.report(linked)
        self.assertEqual(result['released_selected_claims'], 1)
        self.assertEqual(result['augmented_observations'], baseline['augmented_observations'])
        row = result['augmented_observations'][0]
        self.assertEqual(row['known_by_retrieval'], '2026-10-02T12:00:00+00:00')
        self.assertEqual(row['publisher_count'], 1)
        self.assertEqual(row['declared_origin_family_count'], 1)
        self.assertEqual(result['scope']['reviewed_origin_group_count'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
