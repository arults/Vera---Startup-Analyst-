import json
from pathlib import Path
import tempfile
import unittest
from requirements import build_plan, resolve_applicability, work_queue, load_spec


def ids(plan, category):
    return {item['id'] for item in plan[category]}


def conditional(plan, key):
    return next(item for item in plan['conditional'] if item['id'] == key)


class RequirementTests(unittest.TestCase):
    def test_survival_omits_investor_and_success_tasks(self):
        tasks = {item['id'] for item in work_queue(build_plan('operating_survival'))}
        self.assertTrue({'identity_unit', 'funded_round_origin', 'operating_endpoint_evidence'} <= tasks)
        self.assertFalse(tasks & {'nonterminal_success_qualification', 'investor_payout_and_contract_detail', 'comparable_priced_valuations', 'exit_consideration_or_gross_moic', 'entry_terms_return_mapping'})

    def test_survival_private_contract_detail_is_optional(self):
        self.assertIn('investor_payout_and_contract_detail', ids(build_plan('operating_survival'), 'optional'))

    def test_survival_success_classification_is_optional(self):
        self.assertIn('nonterminal_success_qualification', ids(build_plan('operating_survival'), 'optional'))

    def test_composite_entry_and_competition_stay_required(self):
        self.assertTrue({'index_relative_entry_success', 'typed_composite_success', 'relevant_success_competition'} <= ids(build_plan('qualifying_company_success'), 'required'))

    def test_valuation_is_conditional_not_universally_required(self):
        plan = build_plan('qualifying_company_success')
        self.assertIn('comparable_priced_valuations', ids(plan, 'conditional'))
        self.assertNotIn('comparable_priced_valuations', ids(plan, 'required'))

    def test_unknown_branch_keeps_question(self):
        task = next(t for t in work_queue(build_plan('qualifying_company_success')) if t['id'] == 'comparable_priced_valuations')
        self.assertEqual(task['action'], 'DECIDE_RELEVANCE_FIRST')

    def test_applicable_branch_collects_fact(self):
        task = next(t for t in work_queue(build_plan('qualifying_company_success'), {'comparable_priced_valuations': {'status': 'TRUE', 'rationale': 'Priced follow-on branch', 'review_ref': 'claim-policy-v1'}}) if t['id'] == 'comparable_priced_valuations')
        self.assertEqual(task['action'], 'ESTABLISH_APPLICABLE_FACT')

    def test_nonapplicable_valuation_removed_from_queue(self):
        tasks = work_queue(build_plan('qualifying_company_success'), {'comparable_priced_valuations': {'status': 'FALSE', 'rationale': 'Independently qualifying IPO; no valuation-multiple branch involved', 'review_ref': 'claim-policy-v1'}})
        self.assertNotIn('comparable_priced_valuations', {t['id'] for t in tasks})

    def test_unsubstantiated_false_rejected(self):
        with self.assertRaises(ValueError):
            resolve_applicability(conditional(build_plan('qualifying_company_success'), 'comparable_priced_valuations'), {'status': 'FALSE'})

    def test_boolean_not_predicate(self):
        item = conditional(build_plan('qualifying_company_success'), 'comparable_priced_valuations')
        for value in [True, False, '', None, 0]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_applicability(item, {'status': value})

    def test_absent_and_unknown_unresolved(self):
        item = conditional(build_plan('qualifying_company_success'), 'comparable_priced_valuations')
        self.assertEqual(resolve_applicability(item), 'UNRESOLVED')
        self.assertEqual(resolve_applicability(item, {'status': 'UNKNOWN'}), 'UNRESOLVED')

    def test_observed_returns_need_cash_not_full_cap_table(self):
        plan = build_plan('investor_moic')
        self.assertIn('observed_net_cash', ids(plan, 'required'))
        self.assertIn('cash_reconstruction_mechanics', ids(plan, 'conditional'))
        self.assertIn('full_cap_table_when_cash_complete', ids(plan, 'optional'))

    def test_forecast_does_not_require_future_payouts(self):
        plan = build_plan('investor_moic', purpose='forecast', frame='proposed_position', method='forecast_model', platform_year=False)
        self.assertIn('future_realized_payouts', ids(plan, 'optional'))
        self.assertNotIn('observed_net_cash', ids(plan, 'required'))
        self.assertTrue({'entry_terms_return_mapping', 'calibration_uncertainty', 'numeric_release_reviews'} <= ids(plan, 'required'))

    def test_all_four_return_thresholds_present(self):
        self.assertEqual(build_plan('investor_moic')['investor_thresholds'], [10, 25, 50, 100])

    def test_company_origin_does_not_inherit_round_requirement(self):
        plan = build_plan('operating_survival', frame='company_origin', platform_year=False)
        self.assertNotIn('funded_round_origin', ids(plan, 'required'))
        self.assertIn('declared_entry_origin', ids(plan, 'required'))

    def test_frozen_round_success_not_company_origin(self):
        with self.assertRaises(ValueError):
            build_plan('qualifying_company_success', frame='company_origin')

    def test_investor_return_not_company_origin(self):
        with self.assertRaises(ValueError):
            build_plan('investor_moic', frame='company_origin')

    def test_exact_dates_required_for_existing_exact_method(self):
        self.assertIn('exact_relevant_chronology', ids(build_plan('operating_survival'), 'required'))

    def test_interval_method_does_not_invent_exactness(self):
        plan = build_plan('operating_survival', method='interval_supported')
        self.assertNotIn('exact_relevant_chronology', ids(plan, 'required'))
        self.assertIn('interval_order_resolution', ids(plan, 'conditional'))
        self.assertEqual(plan['estimator_compatibility'], 'NOT_VERIFIED')

    def test_platform_year_optional_only_when_not_requested(self):
        self.assertIn('platform_offering_year', ids(build_plan('operating_survival'), 'required'))
        self.assertNotIn('platform_offering_year', ids(build_plan('operating_survival', platform_year=False), 'required'))

    def test_field_materiality_is_selectable(self):
        self.assertIn('field_assignment', ids(build_plan('operating_survival', field_breakdown=True), 'required'))
        self.assertIn('unused_field_tags', ids(build_plan('operating_survival'), 'optional'))

    def test_no_readiness_or_release_claim(self):
        for endpoint in ['operating_survival', 'qualifying_company_success', 'investor_moic']:
            plan = build_plan(endpoint)
            self.assertEqual(plan['evidence_eligibility'], 'NOT_ADJUDICATED')
            self.assertEqual(plan['numeric_release'], 'NOT_AUTHORIZED_BY_PLAN')
            self.assertFalse(plan['canonical_changes'])

    def test_every_conditional_preserves_unknown(self):
        for endpoint in ['operating_survival', 'qualifying_company_success', 'investor_moic']:
            for item in build_plan(endpoint)['conditional']:
                self.assertEqual(item['unknown_applicability'], 'UNRESOLVED_NOT_OPTIONAL')

    def test_no_duplicate_requirement_ids(self):
        for endpoint in ['operating_survival', 'qualifying_company_success', 'investor_moic']:
            plan = build_plan(endpoint)
            keys = [item['id'] for group in ['required', 'conditional', 'optional'] for item in plan[group]]
            self.assertEqual(len(keys), len(set(keys)))

    def test_invalid_spec_and_type_rejected(self):
        for kwargs in [{'endpoint': 'safe_cap_return'}, {'endpoint': 'operating_survival', 'platform_year': 1}, {'endpoint': 'investor_moic', 'purpose': 'forecast'}, {'endpoint': 'operating_survival', 'frame': 'proposed_position'}, {'endpoint': 'investor_moic', 'frame': 'proposed_position', 'purpose': 'forecast', 'method': 'forecast_model'}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build_plan(**kwargs)

    def test_unknown_condition_id_rejected(self):
        with self.assertRaises(ValueError):
            work_queue(build_plan('operating_survival'), {'typo': {'status': 'FALSE'}})

    def test_no_side_effect_and_deterministic(self):
        first = build_plan('operating_survival')
        text = json.dumps(first, sort_keys=True)
        work_queue(first)
        self.assertEqual(json.dumps(first, sort_keys=True), text)
        self.assertEqual(first, build_plan('operating_survival'))

    def test_loader_exact_keys_and_duplicate_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'spec.json'
            path.write_text('{"endpoint":"operating_survival", "endpoint":"investor_moic"}')
            with self.assertRaises(ValueError):
                load_spec(path)
            path.write_text(json.dumps(build_plan('operating_survival')['spec']))
            self.assertEqual(load_spec(path), build_plan('operating_survival'))

class ArtifactConsistencyTests(unittest.TestCase):
    def test_examples_replay_exactly(self):
        for example in json.loads((Path(__file__).parent/'examples.json').read_text()):
            plan=build_plan(**example['spec'])
            queue=work_queue(plan,example['applicability'])
            self.assertEqual([q['id'] for q in queue],example['queue_ids'])
            self.assertFalse(set(example['omitted_ids']) & {q['id'] for q in queue})
            self.assertEqual(plan['evidence_eligibility'],'NOT_ADJUDICATED')

    def test_legacy_map_has_38_unique_fields_and_explicit_domains(self):
        mapping=json.loads((Path(__file__).parent/'legacy-field-map.json').read_text())
        self.assertEqual(len(mapping['fields']),38)
        self.assertEqual(len({f['field'] for f in mapping['fields']}),38)
        for field in mapping['fields']:
            self.assertTrue(field['legacy_groups'])
            for endpoint in ['operating_survival','qualifying_company_success','historical_cash_moic','forecast_cash_moic']:
                self.assertIn(field[endpoint],mapping['classes'])

    def test_schema_enums_match_runtime(self):
        from requirements import ENDPOINTS,PURPOSES,FRAMES,METHODS
        schema=json.loads((Path(__file__).parent/'spec.schema.json').read_text())
        for name,values in [('endpoint',ENDPOINTS),('purpose',PURPOSES),('frame',FRAMES),('method',METHODS)]:
            self.assertEqual(tuple(schema['properties'][name]['enum']),values)
        self.assertFalse(schema['additionalProperties'])


if __name__ == '__main__':
    unittest.main()
