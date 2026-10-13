from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

from method_guard import (bind_method, _dependencies, FROZEN_METHOD,
                          FROZEN_OBLIGATIONS)


class MethodGuardTest(unittest.TestCase):
    def setUp(self):
        self.planner, _ = _dependencies()
        self.plan = self.planner.build_plan("operating_survival")

    def bind(self, plan=None, method=None, **kwargs):
        return bind_method(self.plan if plan is None else plan,
                           method=FROZEN_METHOD if method is None else method, **kwargs)

    def test_valid_plan_is_not_evidence_ready(self):
        r = self.bind()
        self.assertEqual(r["method_contract_status"], "BOUND_FOR_REVIEW_NOT_EVIDENCE_READY")
        self.assertEqual(r["evidence_eligibility"], "NOT_ADJUDICATED")
        self.assertEqual(r["empirical_histories_constructed"], 0)
        self.assertEqual(r["numerical_estimates_computed"], 0)
        self.assertFalse(r["canonical_changes"])

    def test_frozen_success_state_is_restored(self):
        ids = {x["id"] for x in self.bind()["method_obligations"]}
        self.assertEqual(ids, {x[0] for x in FROZEN_OBLIGATIONS})
        self.assertIn("frozen_index_relative_state", ids)
        self.assertIn("frozen_success_and_terminal_history", ids)

    def test_payout_contracts_do_not_return(self):
        ids = {x["id"] for x in self.bind()["work_queue"]}
        self.assertNotIn("investor_payout_and_contract_detail", ids)
        self.assertNotIn("observed_net_cash", ids)
        self.assertNotIn("cash_reconstruction_mechanics", ids)

    def test_method_id_is_not_generic_exact_history(self):
        for method in ({"id": "exact_history"}, "exact_history", {}, [], False,
                       {**FROZEN_METHOD, "version": "future"},
                       {**FROZEN_METHOD, "engine_git_blob": "0" * 40},
                       {**FROZEN_METHOD, "extra": "ignored"}):
            with self.subTest(method=method):
                r = self.bind(method=method)
                self.assertTrue(r["method_contract_status"].startswith("HOLD_"))
                self.assertEqual(r["method_obligations"], [])
                self.assertEqual(r["empirical_histories_constructed"], 0)

    def test_other_valid_specs_hold(self):
        specs = [dict(endpoint="qualifying_company_success"),
                 dict(endpoint="investor_moic"),
                 dict(endpoint="operating_survival", frame="company_origin"),
                 dict(endpoint="operating_survival", method="horizon_status"),
                 dict(endpoint="operating_survival", method="interval_supported"),
                 dict(endpoint="operating_survival", purpose="forecast", method="forecast_model")]
        for spec in specs:
            with self.subTest(spec=spec):
                self.assertEqual(self.bind(plan=self.planner.build_plan(**spec))["method_contract_status"],
                                 "HOLD_SPEC_OUTSIDE_THIS_METHOD_CONTRACT")

    def test_reporting_flags_do_not_remove_method_gates(self):
        for platform in (False, True):
            for fields in (False, True):
                r = self.bind(plan=self.planner.build_plan("operating_survival",
                              platform_year=platform, field_breakdown=fields))
                self.assertEqual(len(r["method_obligations"]), len(FROZEN_OBLIGATIONS))

    def test_optional_declaration_cannot_disable_frozen_obligation(self):
        with self.assertRaisesRegex(ValueError, "unknown_conditional_requirement"):
            self.bind(applicability={"frozen_index_relative_state": {"status": "FALSE",
                      "rationale": "It is optional", "review_ref": "fictional"}})

    def test_known_condition_is_supported_without_removing_method_gates(self):
        decl = {"decision_material_enrichment": {"status": "FALSE",
                "rationale": "Fictional fixture has no other material predictors", "review_ref": "fictional"}}
        r = self.bind(applicability=decl)
        self.assertNotIn("decision_material_enrichment", {x["id"] for x in r["work_queue"]})
        self.assertEqual(len(r["method_obligations"]), len(FROZEN_OBLIGATIONS))

    def test_modified_plan_rejected(self):
        plan = deepcopy(self.plan)
        plan["required"] = []
        with self.assertRaisesRegex(ValueError, "plan_must_match_current_version_and_spec"):
            self.bind(plan=plan)

    def test_input_and_returned_values_do_not_alias(self):
        before = deepcopy(self.plan)
        method = deepcopy(FROZEN_METHOD)
        r = self.bind(method=method)
        r["spec"]["endpoint"] = "tampered"
        r["method_requested"]["id"] = "tampered"
        r["endpoint_queue"][0]["id"] = "tampered"
        self.assertEqual(self.plan, before)
        self.assertEqual(method, FROZEN_METHOD)
        self.assertNotEqual(r["work_queue"][0]["id"], "tampered")

    def test_dependency_tampering_fails_before_planner_exec(self):
        root = Path(__file__).resolve().parent.parent
        for subdir, filename, expected in (
            ("endpoint-evidence-v0.1.0", "requirements.py", "planner_dependency_hash_mismatch"),
            ("explicit-history-statistics-v0.2.0", "aj_explicit_history.py", "frozen_engine_dependency_hash_mismatch")):
            with self.subTest(file=filename), tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "research"
                dest.mkdir()
                (dest.parent / "docs").mkdir()
                shutil.copyfile(root.parent / "docs" / "PHASE_1C_SPEC.md", dest.parent / "docs" / "PHASE_1C_SPEC.md")
                for folder, name in (("endpoint-evidence-v0.1.0", "requirements.py"),
                                     ("explicit-history-statistics-v0.2.0", "aj_explicit_history.py")):
                    (dest / folder).mkdir()
                    shutil.copyfile(root / folder / name, dest / folder / name)
                path = dest / subdir / filename
                path.write_bytes(path.read_bytes() + b"\nraise RuntimeError('untrusted')\n")
                with self.assertRaisesRegex(ValueError, expected):
                    self.bind(research_root=dest)


if __name__ == "__main__":
    unittest.main()
