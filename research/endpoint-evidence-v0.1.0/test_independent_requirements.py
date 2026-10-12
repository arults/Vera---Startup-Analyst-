"""Independent adversarial controls for the planning-only contract.

These verify requirement routing and non-adjudication; no real observations,
company forecasts, source authentication, estimator or investment result.
"""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest

from requirements import build_plan, resolve_applicability, work_queue, load_spec


def keys(plan, group):
    return {item['id'] for item in plan[group]}


def admitted_plans():
    for endpoint, purpose, frame, method, platform_year, field_breakdown in product(
        ('operating_survival', 'qualifying_company_success', 'investor_moic'),
        ('historical_endpoint', 'forecast'),
        ('funded_rounds', 'company_origin', 'proposed_position'),
        ('exact_history', 'interval_supported', 'horizon_status', 'forecast_model'),
        (False, True), (False, True),
    ):
        try:
            yield build_plan(endpoint, purpose=purpose, frame=frame, method=method,
                             platform_year=platform_year, field_breakdown=field_breakdown)
        except ValueError:
            continue


class IndependentRequirementsTests(unittest.TestCase):
    def test_all_admitted_specs_preserve_shared_obligations(self):
        common = {'identity_unit', 'target_clock', 'frame_dispositions',
                  'provenance_observation', 'method_compatibility'}
        plans = list(admitted_plans())
        self.assertGreater(len(plans), 20)
        for plan in plans:
            with self.subTest(spec=plan['spec']):
                self.assertTrue(common <= keys(plan, 'required'))

    def test_all_admitted_specs_have_disjoint_unique_requirement_ids(self):
        for plan in admitted_plans():
            with self.subTest(spec=plan['spec']):
                ids = [item['id'] for group in ('required', 'conditional', 'optional')
                       for item in plan[group]]
                self.assertEqual(len(ids), len(set(ids)))

    def test_all_admitted_specs_default_unknowns_to_relevance_tasks(self):
        for plan in admitted_plans():
            tasks = {task['id']: task for task in work_queue(plan)}
            for item in plan['conditional']:
                with self.subTest(spec=plan['spec'], requirement=item['id']):
                    self.assertEqual(tasks[item['id']]['action'], 'DECIDE_RELEVANCE_FIRST')
                    self.assertEqual(item['unknown_applicability'], 'UNRESOLVED_NOT_OPTIONAL')

    def test_all_admitted_specs_omit_optional_collection(self):
        for plan in admitted_plans():
            tasks = {task['id'] for task in work_queue(plan)}
            self.assertFalse(keys(plan, 'optional') & tasks)
            self.assertTrue(keys(plan, 'required') <= tasks)

    def test_false_declarations_never_create_authentication_or_release(self):
        for plan in admitted_plans():
            declarations = {item['id']: {'status': 'FALSE',
                'rationale': 'Fictional declaration, not authenticated source evidence',
                'review_ref': 'fictional-policy-v1'} for item in plan['conditional']}
            work_queue(plan, declarations)
            self.assertEqual(plan['evidence_eligibility'], 'NOT_ADJUDICATED')
            self.assertEqual(plan['estimator_compatibility'], 'NOT_VERIFIED')
            self.assertEqual(plan['numeric_release'], 'NOT_AUTHORIZED_BY_PLAN')
            self.assertIs(plan['canonical_changes'], False)

    def test_false_resolution_explicitly_says_declared(self):
        item = build_plan('qualifying_company_success')['conditional'][0]
        status = resolve_applicability(item, {'status': 'FALSE', 'rationale': 'Synthetic IPO branch',
                                              'review_ref': 'fictional-policy-v1'})
        self.assertEqual(status, 'NOT_APPLICABLE_DECLARED')

    def test_truthy_and_falsey_values_are_not_predicate_statuses(self):
        item = build_plan('qualifying_company_success')['conditional'][0]
        for status in (1, 0, [], {}, 'false', 'true', 'FALSE ', ' TRUE', 'NONE'):
            with self.subTest(status=status), self.assertRaises(ValueError):
                resolve_applicability(item, {'status': status, 'rationale': 'synthetic', 'review_ref': 'v1'})

    def test_resolved_statuses_reject_blank_rationale_or_review(self):
        item = build_plan('qualifying_company_success')['conditional'][0]
        for status, field, value in product(('TRUE', 'FALSE'), ('rationale', 'review_ref'), ('', '  ', None, 7)):
            declaration = {'status': status, 'rationale': 'Synthetic branch', 'review_ref': 'v1'}
            declaration[field] = value
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                resolve_applicability(item, declaration)

    def test_unknown_remains_unknown_even_with_review_looking_fields(self):
        item = build_plan('qualifying_company_success')['conditional'][0]
        declaration = {'status': 'UNKNOWN', 'rationale': 'Reviewed but unresolved', 'review_ref': 'v1'}
        self.assertEqual(resolve_applicability(item, declaration), 'UNRESOLVED')

    def test_queue_never_mutates_input_plan_or_declarations(self):
        plan = build_plan('qualifying_company_success')
        declarations = {plan['conditional'][0]['id']: {'status': 'TRUE',
                           'rationale': 'Synthetic valuation branch', 'review_ref': 'v1'}}
        original = deepcopy((plan, declarations))
        first = work_queue(plan, declarations)
        self.assertEqual((plan, declarations), original)
        self.assertEqual(first, work_queue(plan, declarations))

    def test_new_plans_do_not_share_mutable_requirement_lists(self):
        first = build_plan('operating_survival')
        original = deepcopy(first)
        first['required'].clear()
        first['spec']['endpoint'] = 'investor_moic'
        self.assertEqual(build_plan('operating_survival'), original)

    def test_return_forecast_excludes_observed_future_cash_and_keeps_release_gates(self):
        plan = build_plan('investor_moic', purpose='forecast', method='forecast_model',
                          frame='proposed_position', platform_year=False)
        tasks = {task['id'] for task in work_queue(plan)}
        self.assertNotIn('observed_net_cash', tasks)
        self.assertNotIn('future_realized_payouts', tasks)
        self.assertTrue({'net_cash_target', 'entry_terms_return_mapping',
                         'calibration_uncertainty', 'numeric_release_reviews'} <= tasks)
        self.assertEqual(plan['investor_thresholds'], [10, 25, 50, 100])

    def test_interval_selection_cannot_prove_estimator_exists(self):
        for method in ('interval_supported', 'horizon_status'):
            plan = build_plan('qualifying_company_success', method=method)
            self.assertEqual(plan['estimator_compatibility'], 'NOT_VERIFIED')
            self.assertIn('method_compatibility', keys(plan, 'required'))
            self.assertNotIn('exact_relevant_chronology', keys(plan, 'required'))
            item = next(item for item in plan['conditional'] if item['id'] == 'interval_order_resolution')
            self.assertEqual(resolve_applicability(item), 'UNRESOLVED')

    def test_round_frame_never_loses_funding_or_origin_requirement(self):
        for plan in admitted_plans():
            if plan['spec']['frame'] == 'funded_rounds':
                self.assertIn('funded_round_origin', keys(plan, 'required'))

    def test_survival_and_success_do_not_claim_investor_thresholds(self):
        for endpoint in ('operating_survival', 'qualifying_company_success'):
            self.assertEqual(build_plan(endpoint)['investor_thresholds'], [])

    def test_json_loader_rejects_extras_missing_keys_and_nonfinite_values(self):
        valid = build_plan('operating_survival')['spec']
        invalid = [dict(valid, surprise=True), {k: v for k, v in valid.items() if k != 'method'},
                   dict(valid, platform_year=None), dict(valid, platform_year=1)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'spec.json'
            for payload in invalid:
                path.write_text(json.dumps(payload))
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    load_spec(path)
            for token in ('NaN', 'Infinity', '-Infinity'):
                path.write_text(json.dumps(valid).replace('true', token))
                with self.subTest(token=token), self.assertRaises(ValueError):
                    load_spec(path)

    def test_json_loader_rejects_nested_duplicate_keys_before_plan_building(self):
        valid = json.dumps(build_plan('operating_survival')['spec'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'spec.json'
            path.write_text(valid[:-1] + ', "extra": {"x": 1, "x": 2}}')
            with self.assertRaisesRegex(ValueError, 'duplicate_key:x'):
                load_spec(path)

    def test_forecast_operating_plan_does_not_require_future_endpoint_observations(self):
        plan = build_plan('operating_survival', purpose='forecast', method='forecast_model')
        self.assertNotIn('operating_endpoint_evidence', keys(plan, 'required'),
            'Historical endpoint observations must be replaced by explicitly prediction-time known history for forecasts.')

    def test_forecast_success_plan_does_not_require_future_first_event(self):
        plan = build_plan('qualifying_company_success', purpose='forecast', method='forecast_model')
        self.assertNotIn('relevant_success_competition', keys(plan, 'required'),
            'The future first qualifying/competing event is an outcome, not a mandatory forecast input.')


    def test_modified_or_stale_plans_cannot_suppress_work(self):
        mutations = [
            lambda p: p['required'].clear(),
            lambda p: p['conditional'].clear(),
            lambda p: p.update(policy_version='stale-v0'),
            lambda p: p.update(evidence_eligibility='READY'),
            lambda p: p.update(numeric_release='APPROVED'),
            lambda p: p['required'][0].update(meaning='Optional'),
            lambda p: p['spec'].update(method='horizon_status'),
            lambda p: p.update(investor_thresholds=[]),
        ]
        for mutate in mutations:
            plan = build_plan('investor_moic')
            mutate(plan)
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                work_queue(plan)

    def test_invalid_plan_containers_rejected(self):
        for plan in (None, [], {}, {'spec': []}, {'spec': {'unexpected': True}}):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                work_queue(plan)

    def test_nonreturn_forecasts_explicitly_bind_input_history_to_cutoff(self):
        expected_ids = {'operating_survival': 'operating_history_at_prediction',
                        'qualifying_company_success': 'success_history_at_prediction'}
        for endpoint, key in expected_ids.items():
            plan = build_plan(endpoint, purpose='forecast', method='forecast_model')
            item = next(item for item in plan['required'] if item['id'] == key)
            self.assertIn('prediction cutoff', item['meaning'])
            self.assertIn('Future', item['meaning'])
            self.assertIn('not required', item['meaning'])
        plan = build_plan('qualifying_company_success', purpose='forecast', method='forecast_model')
        for key in ('comparable_priced_valuations', 'exit_consideration_or_gross_moic'):
            item = next(item for item in plan['conditional'] if item['id'] == key)
            self.assertIn('forecast', item['meaning'].lower())
            self.assertIn('future', item['meaning'].lower())
            self.assertIn('observed', item['required_if'].lower())

    def test_legacy_map_covers_all_38_distinct_inventory_fields(self):
        mapping = json.loads((Path(__file__).parent / 'legacy-field-map.json').read_text())
        expected = set('administrative_extraction_limit canonical_company_id censor_date closure_date cohort_membership_review completion_date endpoint_specific_observation_review entry_eligibility_review event_precision_review evidence_trace followup_months funded_position_evidence index_qualification_review initial_post_policy initial_state_evidence last_positive_date offering_year offering_year_status origin_convention_review platform prepared_history_disposition reviewed_economic_round_identity reviewed_exact_transition_sequence reviewed_initial_state round_id same_subject_tie_resolution selected_success_endpoint source_availability_review success_date success_evidence_sha256 success_evidence_url success_type success_valuation_multiple terminal_event_evidence_url terminal_event_interval_end terminal_event_interval_start terminal_event_midpoint_for_primary terminal_event_type'.split())
        fields = [row['field'] for row in mapping['fields']]
        self.assertEqual(set(fields), expected)
        self.assertEqual(len(fields), 38)
        self.assertEqual(len(fields), len(set(fields)))
        groups = {g for row in mapping['fields'] for g in row['legacy_groups']}
        self.assertEqual(groups, {'round_identity_and_funded_origin', 'initial_state',
                                 'index_success_and_target', 'typed_event_chronology',
                                 'endpoint_observation', 'cohort_assignment'})
        for row in mapping['fields']:
            for column in ('operating_survival', 'qualifying_company_success',
                           'historical_cash_moic', 'forecast_cash_moic'):
                self.assertIn(row[column], mapping['classes'])

    def test_legacy_map_preserves_proposed_entry_and_midpoint_boundaries(self):
        mapping = json.loads((Path(__file__).parent / 'legacy-field-map.json').read_text())
        by_field = {row['field']: row for row in mapping['fields']}
        self.assertIn('proposed investor position', mapping['scope'])
        for key in ('completion_date', 'funded_position_evidence', 'round_id'):
            self.assertEqual(by_field[key]['forecast_cash_moic'], 'OPTIONAL')
        row = by_field['terminal_event_midpoint_for_primary']
        for column in ('operating_survival', 'qualifying_company_success',
                       'historical_cash_moic', 'forecast_cash_moic'):
            self.assertEqual(row[column], 'OPTIONAL')
        self.assertIn('never an automatic primary transition', row['note'])

if __name__ == '__main__':
    unittest.main()
