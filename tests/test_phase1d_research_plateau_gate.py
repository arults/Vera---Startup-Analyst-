"""Synthetic adversarial conformance tests; not empirical startup observations."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.phase1d.research_plateau_gate import (
    DIMENSIONS, LABELS, SOURCES, SCOPE, assess, canonical_hash, compare_states, write_immutable,
)


def state():
    return {"dimensions": {k: 0.5 for k in DIMENSIONS},
            "labels": {k: "stable" for k in LABELS},
            "source_hashes": {k: hashlib.sha256(b"{}\n").hexdigest() for k in SOURCES},
            "verifier": {"total": 43, "passed": 43, "promotion_gate": "PASS"}}


class ResearchPlateauGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data/phase1d").mkdir(parents=True)
        for name in SOURCES:
            (self.root / "data/phase1d" / name).write_text("{}\n")
        self.snaps = [{"state": state(), "round_id": f"r{i}",
                       "captured_at": f"2026-10-09T0{i}:00:00+00:00"} for i in range(3)]
        self.receipts = []
        for i in range(2):
            receipt = {"iteration_id": f"it{i}", "alternative_id": f"alt{i}",
                       "scope": SCOPE, "status": "COMPLETED", "action_kind": "targeted_outcome_review",
                       "feedback": "Synthetic feedback fixture", "action": "Synthetic action fixture",
                       "remaining_material_actions": [],
                       "input_state_sha256": canonical_hash(state()),
                       "output_state_sha256": canonical_hash(state()),
                       "started_at": f"2026-10-09T0{i}:10:00+00:00",
                       "completed_at": f"2026-10-09T0{i}:20:00+00:00", "evidence": {}}
            for kind in ("feedback", "execution", "verification"):
                path = self.root / f"{i}-{kind}.json"
                value = {"kind": kind, "status": "COMPLETED" if kind == "execution" else "PASS", "scope": SCOPE,
                         "alternative_id": f"alt{i}", "action_kind": "targeted_outcome_review",
                         "iteration_id": f"it{i}", "input_state_sha256": canonical_hash(state()),
                         "output_state_sha256": canonical_hash(state())}
                raw = json.dumps(value, sort_keys=True).encode()
                path.write_bytes(raw)
                receipt["evidence"][kind] = {"path": path.name, "sha256": hashlib.sha256(raw).hexdigest()}
            self.receipts.append(receipt)

    def audit(self):
        return assess(self.snaps, self.receipts, self.root)

    def test_valid_shaped_mock_contract_is_candidate_not_promotion(self):
        r = self.audit()
        self.assertTrue(r["research_plateau"], r)
        self.assertFalse(r["empirical_promotion"])
        self.assertEqual(r["status"], "SCOPED_PLATEAU_CANDIDATE")

    def test_identical_replays_alone_do_not_prove_research_plateau(self):
        r = assess(self.snaps, [], self.root)
        self.assertTrue(r["replay_stable"])
        self.assertFalse(r["research_plateau"])

    def test_state_comparison_never_authorizes_research_stop(self):
        r = compare_states(state(), state())
        self.assertTrue(r["state_stable"])
        self.assertFalse(r["research_plateau"])

    def test_regression_fails(self):
        self.snaps[1]["state"]["dimensions"]["rq1_reportable_share"] = 0.4
        self.assertFalse(self.audit()["research_plateau"])

    def test_large_improvement_requires_more_iterations(self):
        s = state(); s["dimensions"]["rq1_reportable_share"] = 0.56
        self.assertFalse(compare_states(state(), s)["state_stable"])

    def test_exact_threshold_is_not_large_improvement(self):
        s = state(); s["dimensions"]["rq1_reportable_share"] = 0.55
        self.assertTrue(compare_states(state(), s)["state_stable"])

    def test_nonfinite_bounds_booleans_rejected(self):
        for value in [float("nan"), float("inf"), -0.01, 1.01, True, "0.5"]:
            with self.subTest(value=value):
                s = state(); s["dimensions"]["rq1_reportable_share"] = value
                self.assertFalse(compare_states(s, s)["state_stable"])

    def test_empty_missing_or_changed_dimension_schema_rejected(self):
        for value in [{}, {"unexpected": 0.5}]:
            s = state(); s["dimensions"] = value
            self.assertFalse(compare_states(s, s)["state_stable"])

    def test_failed_or_zero_verifier_rejected(self):
        for passed, total in [(42, 43), (0, 0), (True, 1)]:
            s = state(); s["verifier"].update(passed=passed, total=total)
            self.assertFalse(compare_states(s, s)["state_stable"])

    def test_changed_labels_and_hashes_rejected(self):
        for field, value in [("labels", {"rates_promoted": True}),
                             ("source_hashes", {"fixture.json": "a" * 64})]:
            s = state(); s[field] = value
            self.assertFalse(compare_states(state(), s)["state_stable"])

    def test_source_bytes_tampered_rejected(self):
        (self.root / "data/phase1d/cp1_coverage.json").write_text("changed")
        self.assertFalse(self.audit()["research_plateau"])

    def test_receipt_hash_tampered_rejected(self):
        self.receipts[0]["evidence"]["execution"]["sha256"] = "a" * 64
        self.assertFalse(self.audit()["research_plateau"])

    def test_duplicate_alternative_rejected(self):
        self.receipts[1]["alternative_id"] = self.receipts[0]["alternative_id"]
        self.assertFalse(self.audit()["research_plateau"])

    def test_blocked_retry_not_substantive_completed_iteration(self):
        self.receipts[0]["status"] = "ACCESS_BLOCKED"
        self.assertFalse(self.audit()["research_plateau"])

    def test_replay_action_rejected(self):
        self.receipts[0]["action_kind"] = "unchanged_replay"
        self.assertFalse(self.audit()["research_plateau"])

    def test_open_material_actions_rejected(self):
        self.receipts[0]["remaining_material_actions"] = ["untried viable source"]
        self.assertFalse(self.audit()["research_plateau"])

    def test_time_order_and_window_rejected(self):
        self.receipts[0]["completed_at"] = "2026-10-09T04:00:00Z"
        self.assertFalse(self.audit()["research_plateau"])

    def test_duplicate_snapshot_id_rejected(self):
        self.snaps[1]["round_id"] = self.snaps[0]["round_id"]
        self.assertFalse(self.audit()["research_plateau"])

    def test_missing_state_binding_rejected(self):
        self.receipts[0]["input_state_sha256"] = "b" * 64
        self.assertFalse(self.audit()["research_plateau"])

    def test_path_escape_rejected(self):
        self.receipts[0]["evidence"]["feedback"]["path"] = "../outside"
        self.assertFalse(self.audit()["research_plateau"])

    def alter_artifact(self, kind, changes):
        artifact = self.receipts[0]["evidence"][kind]
        path = self.root / artifact["path"]
        value = json.loads(path.read_text()); value.update(changes)
        raw = json.dumps(value, sort_keys=True).encode(); path.write_bytes(raw)
        artifact["sha256"] = hashlib.sha256(raw).hexdigest()

    def test_explicit_synthetic_evidence_rejected(self):
        self.alter_artifact("execution", {"synthetic": True})
        self.assertFalse(self.audit()["research_plateau"])

    def test_execution_artifact_wrong_iteration_rejected(self):
        self.alter_artifact("execution", {"iteration_id": "other"})
        self.assertFalse(self.audit()["research_plateau"])

    def test_execution_failed_despite_claimed_completion_rejected(self):
        self.alter_artifact("execution", {"status": "ACCESS_BLOCKED"})
        self.assertFalse(self.audit()["research_plateau"])

    def test_verification_wrong_state_rejected(self):
        self.alter_artifact("verification", {"output_state_sha256": "f" * 64})
        self.assertFalse(self.audit()["research_plateau"])

    def test_relabelled_same_execution_rejected(self):
        self.receipts[1]["evidence"]["execution"] = copy.deepcopy(self.receipts[0]["evidence"]["execution"])
        self.assertFalse(self.audit()["research_plateau"])

    def test_naive_timestamp_rejected(self):
        self.snaps[0]["captured_at"] = "2026-10-09T00:00:00"
        self.assertFalse(self.audit()["research_plateau"])

    def test_huge_integer_rejected_without_crashing(self):
        s = state(); s["dimensions"]["rq1_reportable_share"] = 10 ** 1000
        self.assertFalse(compare_states(s, s)["state_stable"])

    def test_missing_snapshot_window_rejected(self):
        self.assertFalse(assess(self.snaps[:2], self.receipts, self.root)["research_plateau"])

    def test_invalid_threshold_rejected(self):
        for threshold in [True, float("nan"), -1, 2]:
            self.assertFalse(compare_states(state(), state(), threshold)["state_stable"])

    def test_missing_feedback_rejected(self):
        self.receipts[0]["feedback"] = "  "
        self.assertFalse(self.audit()["research_plateau"])

    def test_omitted_label_in_both_snapshots_rejected(self):
        for snap in self.snaps:
            del snap["state"]["labels"]["platform_statuses"]
        self.assertFalse(self.audit()["research_plateau"])

    def test_omitted_source_in_both_snapshots_rejected(self):
        for snap in self.snaps:
            del snap["state"]["source_hashes"]["cp1_coverage.json"]
        self.assertFalse(self.audit()["research_plateau"])

    def test_no_source_manifest_can_be_replaced_by_unrelated_file(self):
        for snap in self.snaps:
            snap["state"]["source_hashes"]["unrelated.json"] = snap["state"]["source_hashes"].pop("cp1_coverage.json")
        self.assertFalse(self.audit()["research_plateau"])

    def test_immutable_write_refuses_overwrite(self):
        path = self.root / "checkpoint.json"
        write_immutable(path, {"version": 1})
        with self.assertRaises(FileExistsError):
            write_immutable(path, {"version": 2})
        self.assertEqual(json.loads(path.read_text()), {"version": 1})
        self.assertEqual(list(self.root.glob(".pending-*")), [])

    def test_invalid_json_never_publishes_partial_checkpoint(self):
        path = self.root / "checkpoint.json"
        with self.assertRaises(ValueError):
            write_immutable(path, {"value": float("nan")})
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
