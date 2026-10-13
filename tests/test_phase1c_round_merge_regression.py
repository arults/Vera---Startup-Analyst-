"""Synthetic tests only. They do not establish empirical round admissions."""
from dataclasses import replace
from datetime import date
from hashlib import sha256
import itertools
import unittest

from src.phase1c.graph import (
    SameRoundEvidence, build_round_graph, next_round_edges, qualifying_followon,
    round_relation, same_economic_round, native_vs_graph_reclassification,
    native_vs_graph_by_platform,
)
from src.phase1c.model import RoundRecord, validate_round


def sample(round_id='a', **changes):
    base = RoundRecord(
        round_id, 'company', 'republic_us', 2023, date(2023, 1, 1),
        'funded_completed', 'consumer_retail', 'Crowd SAFE', 'Example Inc.',
        'https://example.test/offering', completion_date=date(2023, 5, 1),
        valuation_cap=5_000_000,
    )
    return replace(base, **changes)


def attestation(a, b, **changes):
    quote = 'These two records represent the same synthetic offering and its amendment.'
    proof = SameRoundEvidence(
        a.round_id, b.round_id, 'AMENDMENT_CHAIN', 'https://example.test/source',
        sha256(quote.encode()).hexdigest(), quote, 'synthetic-independent-reviewer',
    )
    return replace(proof, **changes)


class RoundMergeRegression(unittest.TestCase):
    def assertUnresolved(self, a, b, **kwargs):
        self.assertEqual(round_relation(a, b, **kwargs).decision, 'UNRESOLVED')
        self.assertFalse(same_economic_round(a, b, **kwargs))
        result = build_round_graph([a, b], **kwargs)
        self.assertEqual(result.edges, ())
        self.assertEqual(len(result.unresolved_pairs), 1)

    def test_different_safe_caps_without_priced_values_do_not_merge_or_split(self):
        self.assertUnresolved(sample(), sample('b', valuation_cap=10_000_000))

    def test_equal_caps_without_priced_values_are_not_same_round_proof(self):
        self.assertUnresolved(sample(), sample('b'))

    def test_both_cap_and_priced_terms_missing_remain_unknown(self):
        self.assertUnresolved(sample(valuation_cap=None), sample('b', valuation_cap=None))

    def test_one_priced_value_missing_remains_unknown(self):
        self.assertUnresolved(sample(comparable_valuation=8_000_000), sample('b'))

    def test_cap_missing_on_one_side_remains_unknown(self):
        self.assertUnresolved(sample(), sample('b', valuation_cap=None))

    def test_conflicting_caps_do_not_hide_behind_equal_priced_values(self):
        self.assertUnresolved(sample(comparable_valuation=8_000_000),
                              sample('b', comparable_valuation=8_000_000, valuation_cap=9_000_000))

    def test_native_id_only_is_not_economic_round_proof(self):
        a, b = sample(), sample('b')
        evidence = attestation(a, b, relation='NATIVE_ID_ONLY')
        self.assertUnresolved(a, b, same_round_evidence=(evidence,))

    def test_evidence_endpoints_must_match(self):
        a, b = sample(), sample('b')
        self.assertUnresolved(a, b, same_round_evidence=(attestation(a, b, right_round_id='other'),))

    def test_evidence_requires_full_review_provenance(self):
        a, b = sample(), sample('b')
        for change in ({'source_url': ''}, {'source_sha256': ''}, {'relation_quote': ''}, {'reviewer_id': ''}):
            with self.subTest(change=change):
                self.assertUnresolved(a, b, same_round_evidence=(attestation(a, b, **change),))

    def test_reviewed_same_offering_preserves_tiered_caps(self):
        a, b = sample(), sample('b', valuation_cap=10_000_000, platform='wefunder')
        evidence = (attestation(a, b, relation='SAME_OFFERING'),)
        self.assertTrue(same_economic_round(a, b, same_round_evidence=evidence))
        result = build_round_graph([a, b], same_round_evidence=evidence)
        self.assertEqual(len(result.edges), 1)
        self.assertEqual(result.edges[0].edge_type, 'COHOST_SAME_ROUND')
        self.assertTrue(result.edges[0].cross_platform)
        self.assertEqual(result.unresolved_pairs, ())

    def test_evidence_direction_does_not_change_match(self):
        a, b = sample(), sample('b', valuation_cap=10_000_000)
        evidence = (attestation(a, b),)
        self.assertTrue(same_economic_round(b, a, same_round_evidence=evidence))

    def test_amendment_chain_survives_nonoverlapping_endpoints(self):
        a = sample(completion_date=date(2023, 2, 15))
        b = sample('b', first_live_date=date(2023, 2, 1), completion_date=date(2023, 3, 15), valuation_cap=8_000_000)
        c = sample('c', first_live_date=date(2023, 3, 1), completion_date=date(2023, 4, 1), valuation_cap=10_000_000)
        result = build_round_graph([a, b, c], same_round_evidence=(attestation(a, b), attestation(b, c)))
        self.assertEqual([e.edge_type for e in result.edges], ['COHOST_SAME_ROUND'] * 2)
        self.assertEqual(result.unresolved_pairs, ())

    def test_different_company_cannot_be_overridden(self):
        a, b = sample(), sample('b', canonical_company_id='another_company')
        self.assertFalse(same_economic_round(a, b, same_round_evidence=(attestation(a, b),)))
        self.assertEqual(build_round_graph([a, b], same_round_evidence=(attestation(a, b),)).edges, ())

    def test_different_instrument_cannot_be_overridden(self):
        a, b = sample(), sample('b', instrument_type='Common equity')
        self.assertUnresolved(a, b, same_round_evidence=(attestation(a, b),))

    def test_nonoverlap_cannot_be_overridden_and_conflicting_proof_is_held(self):
        a = sample(completion_date=date(2023, 2, 1))
        b = sample('b', first_live_date=date(2023, 3, 1))
        self.assertUnresolved(a, b, same_round_evidence=(attestation(a, b),))

    def test_safe_cap_stepup_is_never_priced_success(self):
        a = sample(completion_date=date(2023, 2, 1))
        b = sample('b', first_live_date=date(2023, 3, 1), valuation_cap=15_000_000)
        self.assertFalse(qualifying_followon(a, b))
        result = build_round_graph([a, b])
        self.assertEqual(len(result.edges), 1)
        self.assertEqual(result.edges[0].edge_type, 'NEXT_ROUND')
        self.assertFalse(result.edges[0].qualified_followon_success)

    def test_known_priced_same_round_still_merges(self):
        a = sample(valuation_cap=None, comparable_valuation=10_000_000, instrument_type='Common equity')
        b = replace(a, round_id='b', platform='wefunder', comparable_valuation=10_050_000)
        self.assertTrue(same_economic_round(a, b))
        self.assertEqual(next_round_edges([a, b])[0].edge_type, 'COHOST_SAME_ROUND')

    def test_priced_nonoverlap_followon_and_reporting_unchanged(self):
        a = sample(valuation_cap=None, comparable_valuation=10_000_000, instrument_type='Common equity', completion_date=date(2023, 2, 1))
        b = replace(a, round_id='b', platform='wefunder', first_live_date=date(2023, 3, 1), completion_date=date(2023, 5, 1), comparable_valuation=20_000_000)
        edges = next_round_edges([a, b])
        self.assertTrue(edges[0].qualified_followon_success)
        self.assertEqual(native_vs_graph_reclassification(edges)['cross_platform_reclassified'], 1)
        rows = native_vs_graph_by_platform([a, b], edges, set())
        self.assertEqual(sum(r.cross_platform_reclassified for r in rows), 1)

    def test_nonfunded_endpoints_never_qualify_despite_dates_and_stepup(self):
        a = sample(valuation_cap=None, comparable_valuation=10_000_000,
                   instrument_type='Common equity', completion_date=date(2023, 2, 1))
        b = replace(a, round_id='b', platform='wefunder', first_live_date=date(2023, 3, 1),
                    completion_date=date(2023, 5, 1), comparable_valuation=20_000_000)
        for status in ('pending', 'failed', 'withdrawn'):
            for left, right in ((replace(a, status=status), b), (a, replace(b, status=status))):
                with self.subTest(status=status, endpoint=left.status):
                    self.assertFalse(qualifying_followon(left, right))
                    edges = next_round_edges([left, right])
                    self.assertEqual(len(edges), 1)
                    self.assertFalse(edges[0].qualified_followon_success)
                    self.assertEqual(native_vs_graph_reclassification(edges)['qualified_followons'], 0)
                    self.assertEqual(sum(row.cross_platform_reclassified for row in
                                         native_vs_graph_by_platform([left, right], edges, set())), 0)

    def test_ambiguous_component_does_not_generate_followon(self):
        a = sample(comparable_valuation=10_000_000, completion_date=date(2023, 3, 1))
        b = sample('b', comparable_valuation=20_000_000, valuation_cap=9_000_000)
        c = sample('c', first_live_date=date(2023, 6, 1), completion_date=date(2023, 7, 1), comparable_valuation=40_000_000)
        result = build_round_graph([a, b, c])
        self.assertEqual(result.edges, ())
        self.assertEqual(len(result.unresolved_pairs), 1)

    def test_unambiguous_later_rounds_continue_without_bridging_hold(self):
        a, b = sample(), sample('b', valuation_cap=9_000_000)
        c = sample('c', first_live_date=date(2023, 6, 1), completion_date=date(2023, 7, 1), comparable_valuation=10_000_000, valuation_cap=None)
        d = sample('d', first_live_date=date(2023, 8, 1), completion_date=date(2023, 9, 1), comparable_valuation=20_000_000, valuation_cap=None)
        result = build_round_graph([a, b, c, d])
        self.assertEqual([(e.source_round_id, e.destination_round_id) for e in result.edges], [('c', 'd')])

    def test_pending_same_offering_never_promotes_layer_b(self):
        a, b = sample(status='pending', completion_date=None), sample('b', status='pending', completion_date=None, valuation_cap=9_000_000)
        result = build_round_graph([a, b], same_round_evidence=(attestation(a, b),))
        self.assertFalse(a.layer_b_eligible or b.layer_b_eligible)
        self.assertEqual(validate_round(a), [])
        self.assertEqual(result.edges[0].edge_type, 'COHOST_SAME_ROUND')
        self.assertFalse(result.edges[0].qualified_followon_success)

    def test_priced_tolerance_is_not_transitive_identity(self):
        a = sample(valuation_cap=None, comparable_valuation=100)
        b = sample('b', valuation_cap=None, comparable_valuation=100.9)
        c = sample('c', valuation_cap=None, comparable_valuation=101.8)
        result = build_round_graph([a, b, c])
        self.assertEqual(len(result.edges), 1)
        self.assertEqual(result.edges[0].edge_type, 'COHOST_SAME_ROUND')
        self.assertTrue(any(p.reason == 'inconsistent_round_cluster' for p in result.unresolved_pairs))

    def test_explicit_chain_does_not_override_company_or_instrument_gate(self):
        a, b = sample(), sample('b', valuation_cap=9_000_000)
        for change in ({'canonical_company_id': 'other'}, {'instrument_type': 'Common equity'}):
            c = sample('c', **change)
            result = build_round_graph([a, b, c], same_round_evidence=(attestation(a, b), attestation(b, c)))
            cohosts = [e for e in result.edges if e.edge_type == 'COHOST_SAME_ROUND']
            self.assertEqual(len(cohosts), 1)
            self.assertEqual({cohosts[0].source_round_id, cohosts[0].destination_round_id}, {'a', 'b'})

    def test_input_order_is_deterministic(self):
        a, b, c = sample(), sample('b', valuation_cap=9_000_000), sample('c', valuation_cap=12_000_000)
        proof = (attestation(a, b), attestation(b, c))
        expected = build_round_graph([a, b, c], same_round_evidence=proof)
        for records in itertools.permutations([a, b, c]):
            self.assertEqual(build_round_graph(list(records), same_round_evidence=tuple(reversed(proof))), expected)

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate_round_id'):
            build_round_graph([sample(), sample()])

    def test_missing_company_or_instrument_is_not_match_evidence(self):
        self.assertUnresolved(sample(canonical_company_id=''), sample('b', canonical_company_id=''))
        self.assertUnresolved(sample(instrument_type=''), sample('b', instrument_type=''))

    def test_invalid_numerical_terms_fail_closed(self):
        for value in (float('nan'), float('inf'), -1, 0):
            with self.subTest(value=value):
                self.assertUnresolved(sample(comparable_valuation=value), sample('b', comparable_valuation=value))

    def test_malformed_terms_cannot_be_overridden_by_lineage(self):
        a, b = sample(), sample('b', valuation_cap=float('nan'))
        self.assertUnresolved(a, b, same_round_evidence=(attestation(a, b),))

    def test_invalid_nonoverlapping_terms_do_not_generate_followon(self):
        a = sample(comparable_valuation=-10, completion_date=date(2023, 2, 1))
        b = sample('b', comparable_valuation=-2, first_live_date=date(2023, 3, 1))
        self.assertUnresolved(a, b)

    def test_invalid_values_cannot_bypass_through_different_instrument(self):
        a = sample(valuation_cap=None, comparable_valuation=10_000_000,
                   instrument_type='Common equity', completion_date=date(2023, 2, 1))
        for value in (float('inf'), float('nan'), -1, 0):
            b = sample('b', valuation_cap=None, comparable_valuation=value,
                       instrument_type='Preferred equity', first_live_date=date(2023, 3, 1))
            with self.subTest(value=value):
                self.assertUnresolved(a, b)
                self.assertFalse(qualifying_followon(a, b))

    def test_direct_followon_rejects_each_invalid_endpoint(self):
        a = sample(valuation_cap=None, comparable_valuation=10_000_000,
                   completion_date=date(2023, 2, 1))
        b = sample('b', valuation_cap=None, comparable_valuation=20_000_000,
                   first_live_date=date(2023, 3, 1))
        for value in (float('inf'), float('nan'), -1, 0):
            self.assertFalse(qualifying_followon(replace(a, comparable_valuation=value), b))
            self.assertFalse(qualifying_followon(a, replace(b, comparable_valuation=value)))

    def test_invalid_tolerance_rejected(self):
        for value in (float('nan'), float('inf'), -1):
            with self.assertRaisesRegex(ValueError, 'invalid_valuation_tolerance'):
                same_economic_round(sample(), sample('b'), value)

    def test_empty_and_single_round_graphs(self):
        self.assertEqual(build_round_graph([]).edges, ())
        self.assertEqual(build_round_graph([sample()]).edges, ())


if __name__ == '__main__':
    unittest.main(verbosity=2)
