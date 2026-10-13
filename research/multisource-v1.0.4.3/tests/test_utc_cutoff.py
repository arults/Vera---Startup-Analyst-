"""Synthetic public-entrypoint UTC cutoff regressions; no real review authority."""
import copy
import unittest

import evidence as e
import scoped_review as sc
import test_scoped_review as fixtures
import test_source_verifier as source_fixtures


class UTCCutoffTests(unittest.TestCase):
    AS_OF = e.date('2026-10-10')
    REGISTRY = {
        'synthetic-reviewer': ['source_verifier'],
        'synthetic-claim-reviewer': ['claim_verifier'],
    }

    def fixture(self, field, instant):
        helper = fixtures.ScopedTests()
        data = helper.fixture()
        if field == 'claim_review':
            data['claims'][0]['reviews'][0]['reviewed_at'] = instant
        elif field == 'source_retrieval':
            data['sources'][0]['retrieved_at'] = instant
            # Fresh synthetic bindings prevent stale-review holds hiding the bug.
            helper.sign(data)
        else:
            raise AssertionError('Unexpected fixture field')
        data['source_review']['scope_sha256'] = sc.scope_digest(data)
        return data

    def report(self, data):
        before = copy.deepcopy(data)
        result = e.report(data, source_fixtures.ROOT, self.AS_OF, self.REGISTRY)
        self.assertEqual(data, before, 'Reporting must not rewrite temporal inputs')
        self.assertEqual(result['scope']['blockers'], [])
        self.assertEqual(result['scoped_source_coverage_audit']['blockers'], [])
        self.assertEqual(result['native_changes'], 0)
        self.assertIsNone(result['rates'])
        self.assertEqual(result['prior_promotions'], 0)
        return result

    def assert_case(self, field, instant, expected_release):
        result = self.report(self.fixture(field, instant))
        row = result['augmented_observations'][0]
        self.assertEqual(result['released_selected_claims'], expected_release)
        blocker = ('CLAIM_REVIEW_POSTDATES_AS_OF' if field == 'claim_review'
                   else 'FUTURE_RETRIEVAL')
        self.assertEqual(blocker in row['reasons'], not expected_release)
        if field == 'source_retrieval':
            self.assertEqual(row['freshness'][0]['retrieval_age_days'],
                             0 if expected_release else -1)

    def test_review_future_negative_offset(self):
        self.assert_case('claim_review', '2026-10-10T23:30:00-02:00', 0)

    def test_review_same_future_instant_utc(self):
        self.assert_case('claim_review', '2026-10-11T01:30:00Z', 0)

    def test_review_past_positive_offset(self):
        self.assert_case('claim_review', '2026-10-11T01:30:00+02:00', 1)

    def test_review_same_past_instant_utc(self):
        self.assert_case('claim_review', '2026-10-10T23:30:00Z', 1)

    def test_review_last_microsecond_of_utc_day(self):
        self.assert_case('claim_review', '2026-10-10T23:59:59.999999Z', 1)

    def test_review_next_utc_midnight(self):
        self.assert_case('claim_review', '2026-10-11T00:00:00Z', 0)

    def test_retrieval_future_negative_offset(self):
        self.assert_case('source_retrieval', '2026-10-10T23:30:00-02:00', 0)

    def test_retrieval_same_future_instant_utc(self):
        self.assert_case('source_retrieval', '2026-10-11T01:30:00Z', 0)

    def test_retrieval_past_positive_offset(self):
        self.assert_case('source_retrieval', '2026-10-11T01:30:00+02:00', 1)

    def test_retrieval_same_past_instant_utc(self):
        self.assert_case('source_retrieval', '2026-10-10T23:30:00Z', 1)

    def test_retrieval_last_microsecond_of_utc_day(self):
        self.assert_case('source_retrieval', '2026-10-10T23:59:59.999999Z', 1)

    def test_retrieval_next_utc_midnight(self):
        self.assert_case('source_retrieval', '2026-10-11T00:00:00Z', 0)

    def test_naive_review_rejected(self):
        with self.assertRaisesRegex(ValueError, 'timestamp requires timezone'):
            self.report(self.fixture('claim_review', '2026-10-10T12:00:00'))

    def test_naive_retrieval_rejected(self):
        with self.assertRaisesRegex(ValueError, 'timestamp requires timezone'):
            self.report(self.fixture('source_retrieval', '2026-10-10T12:00:00'))

    def test_source_calendar_labels_preserved(self):
        data = self.fixture('source_retrieval', '2026-10-11T01:30:00+02:00')
        claim = data['claims'][0]
        claim['time'] = {'kind': 'point', 'on': '2026-10-10',
                         'basis': 'Synthetic source-local event day',
                         'source_local_day': '2026-10-10 in source local calendar'}
        data['sources'][0]['publication_date'] = '2026-10-10'
        data['sources'][0]['as_of_date'] = '2026-10-10'
        fixtures.ScopedTests().sign(data)
        result = self.report(data)
        row = result['augmented_observations'][0]
        self.assertEqual(result['released_selected_claims'], 1)
        self.assertEqual(row['time'], claim['time'])
        self.assertEqual(row['freshness'][0]['publication_age_days'], 0)
        self.assertEqual(row['freshness'][0]['source_as_of_age_days'], 0)

    def test_source_future_calendar_labels_still_hold(self):
        for field in ('event', 'publication_date', 'as_of_date'):
            with self.subTest(field=field):
                data = self.fixture('source_retrieval', '2026-10-10T23:30:00Z')
                if field == 'event':
                    data['claims'][0]['time'] = {
                        'kind': 'point', 'on': '2026-10-11',
                        'basis': 'Synthetic source-local event day',
                        'source_local_day': '2026-10-11 in UTC+14 local calendar',
                    }
                else:
                    data['sources'][0][field] = '2026-10-11'
                fixtures.ScopedTests().sign(data)
                result = self.report(data)
                self.assertEqual(result['released_selected_claims'], 0)
                self.assertIn('EVENT_POSTDATES_AS_OF' if field == 'event'
                              else 'SOURCE_POSTDATES_AS_OF',
                              result['augmented_observations'][0]['reasons'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
