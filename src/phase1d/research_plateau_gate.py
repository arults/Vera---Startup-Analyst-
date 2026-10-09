"""Fail-closed Phase 1D research stop gate. Replay stability is not research plateau.

A PASS concerns only the declared research scope, never numeric-prior promotion.
Three snapshots and two distinct, completed, evidenced feedback/action iterations
are required. All evidence is checked against actual bytes, not remembered counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

SCOPE = "phase1d_public_platform_research"
DIMENSIONS = {
    "denominator_grade_platform_share", "republic_europe_cohort_year_coverage",
    "rate_eligible_strong_identity_share", "usable_positive_followup_coverage",
    "closure_audit_target_coverage", "scientific_gate_pass_share",
    "rq1_reportable_share", "rq2_reportable_share", "promoted_rate_share",
}
LABELS = {
    "candidate_version", "closure_audit_effect", "closure_events_total",
    "platform_statuses", "promotion_status", "rates_promoted",
    "rq1_low_information_cells", "rq2_reportable_cells", "verifier_promotion_gate",
}
SOURCES = {
    "cp1_coverage.json", "cp2_republic_europe_normalized_manifest.json",
    "cp3_republic_europe_identity_review_applied_manifest.json",
    "cp3_republic_europe_outcome_ledger_v4_manifest.json",
    "cp3_republic_europe_zero_valuation_closure_adjudication_manifest.json",
    "cp4_republic_europe_candidate_v3_manifest.json",
}
ACTIONS = {"new_source_search", "source_reconciliation",
           "parser_repair_reexecution", "targeted_outcome_review"}


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _number(value: Any) -> bool:
    try:
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value) and 0 <= value <= 1)
    except OverflowError:
        return False


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone required")
    return result


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_state(state: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["state_not_object"]
    for field in ("dimensions", "labels", "source_hashes"):
        if not isinstance(state.get(field), dict) or not state[field]:
            errors.append(f"empty_or_invalid_{field}")
    dims = state.get("dimensions", {})
    if isinstance(dims, dict):
        if set(dims) != DIMENSIONS:
            errors.append("dimension_schema_mismatch")
        if any(not _number(v) for v in dims.values()):
            errors.append("nonfinite_or_out_of_range_dimension")
    labels = state.get("labels", {})
    if isinstance(labels, dict) and set(labels) != LABELS:
        errors.append("label_schema_mismatch")
    hashes = state.get("source_hashes", {})
    if isinstance(hashes, dict) and set(hashes) != SOURCES:
        errors.append("source_manifest_schema_mismatch")
    if isinstance(hashes, dict) and any(
        not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v)
        for v in hashes.values()
    ):
        errors.append("invalid_source_digest")
    verifier = state.get("verifier", {})
    if not isinstance(verifier, dict):
        errors.append("invalid_verifier")
    elif (type(verifier.get("total")) is not int or verifier["total"] <= 0
          or type(verifier.get("passed")) is not int
          or verifier["passed"] != verifier["total"]
          or verifier.get("promotion_gate") != "PASS"):
        errors.append("scientific_verifier_not_passing")
    return errors


def compare_states(previous: Any, current: Any, threshold: float = 0.05) -> dict:
    """Compare quality without authorizing a research stop from state alone."""
    errors = validate_state(previous) + validate_state(current)
    if not _number(threshold):
        errors.append("invalid_threshold")
    deltas: dict[str, float] = {}
    improved: list[str] = []
    regressed: list[str] = []
    labels_changed = hashes_changed = True
    if not errors:
        deltas = {k: current["dimensions"][k] - previous["dimensions"][k]
                  for k in sorted(DIMENSIONS)}
        improved = [k for k, v in deltas.items() if v > threshold + 1e-12]
        regressed = [k for k, v in deltas.items() if v < -1e-12]
        labels_changed = previous["labels"] != current["labels"]
        hashes_changed = previous["source_hashes"] != current["source_hashes"]
    stable = not (errors or improved or regressed or labels_changed or hashes_changed)
    return {
        "state_stable": stable,
        "research_plateau": False,
        "errors": sorted(set(errors)),
        "dimension_changes": deltas,
        "improvements_over_threshold": improved,
        "regressions": regressed,
        "material_labels_changed": labels_changed,
        "source_hashes_changed": hashes_changed,
        "threshold": threshold,
    }


def _evidence(root: Path, item: Any) -> bytes:
    if not isinstance(item, dict) or not _text(item.get("path")):
        raise ValueError("invalid_evidence_reference")
    path = (root / item["path"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("evidence_path_outside_root")
    raw = path.read_bytes()
    if not raw or hashlib.sha256(raw).hexdigest() != item.get("sha256"):
        raise ValueError("evidence_missing_or_hash_mismatch")
    return raw


def assess(snapshots: list[dict], receipts: list[dict], root: Path) -> dict:
    """Receipts must be completed real work, not replays or blocked retries.

    Each receipt references distinct feedback, execution and verification artifacts.
    The verification JSON must bind its PASS to the exact input/output states.
    Human/source adjudication and Jev approval remain separate requirements.
    """
    reasons: list[str] = []
    comparisons: list[dict] = []
    if len(snapshots) != 3:
        return {"research_plateau": False, "status": "INVALID_WINDOW",
                "reasons": ["three_snapshots_required"], "empirical_promotion": False}
    states = [s.get("state") if isinstance(s, dict) else None for s in snapshots]
    for index, state in enumerate(states):
        reasons += [f"snapshot_{index}:{e}" for e in validate_state(state)]
    if not reasons:
        comparisons = [compare_states(states[i], states[i + 1]) for i in range(2)]
        if not all(c["state_stable"] for c in comparisons):
            reasons.append("unstable_or_regressed_research_state")
        # Verify actual source manifest bytes, not hash-shaped assertions.
        for state in states:
            for name, digest in state["source_hashes"].items():
                try:
                    _evidence(root, {"path": "data/phase1d/" + name, "sha256": digest})
                except (ValueError, OSError, TypeError):
                    reasons.append("source_manifest_unverified:" + str(name))
    try:
        times = [_time(s.get("captured_at")) for s in snapshots]
        if not times[0] < times[1] < times[2]:
            reasons.append("snapshot_times_not_strictly_ordered")
        ids = [s.get("round_id") for s in snapshots]
        if not all(_text(v) for v in ids) or len(set(ids)) != 3:
            reasons.append("snapshot_ids_not_distinct")
    except (ValueError, TypeError, AttributeError):
        reasons.append("invalid_snapshot_metadata")
        times = []
    if len(receipts) != 2:
        reasons.append("two_substantive_iteration_receipts_required")
    elif not reasons:
        ids: list[str] = []
        alternatives: list[str] = []
        execution_digests: list[str] = []
        for i, receipt in enumerate(receipts):
            try:
                if not isinstance(receipt, dict):
                    raise ValueError("receipt_not_object")
                if (receipt.get("scope") != SCOPE
                        or receipt.get("status") != "COMPLETED"
                        or receipt.get("action_kind") not in ACTIONS):
                    raise ValueError("not_completed_substantive_research")
                for field in ("iteration_id", "alternative_id", "feedback", "action"):
                    if not _text(receipt.get(field)):
                        raise ValueError("missing_" + field)
                if receipt.get("remaining_material_actions") != []:
                    raise ValueError("unresolved_material_actions")
                before, after = canonical_hash(states[i]), canonical_hash(states[i + 1])
                if (receipt.get("input_state_sha256") != before
                        or receipt.get("output_state_sha256") != after):
                    raise ValueError("receipt_state_binding_mismatch")
                if not (times[i] <= _time(receipt.get("started_at"))
                        < _time(receipt.get("completed_at")) <= times[i + 1]):
                    raise ValueError("iteration_outside_snapshot_window")
                artifacts = receipt.get("evidence")
                if not isinstance(artifacts, dict) or set(artifacts) != {
                    "feedback", "execution", "verification"
                }:
                    raise ValueError("three_evidence_kinds_required")
                if len({v.get("path") for v in artifacts.values()}) != 3:
                    raise ValueError("evidence_roles_not_distinct")
                for artifact in artifacts.values():
                    raw = _evidence(root, artifact)
                    try:
                        metadata = json.loads(raw)
                    except (ValueError, UnicodeError):
                        metadata = None
                    if isinstance(metadata, dict) and (
                        metadata.get("synthetic") is True
                        or metadata.get("evidence_origin") in {"synthetic", "fixture", "replay"}
                    ):
                        raise ValueError("synthetic_or_replay_evidence_forbidden")
                execution = json.loads(_evidence(root, artifacts["execution"]))
                expected_execution = {
                    "status": "COMPLETED", "scope": SCOPE,
                    "iteration_id": receipt["iteration_id"],
                    "alternative_id": receipt["alternative_id"],
                    "action_kind": receipt["action_kind"],
                    "input_state_sha256": before, "output_state_sha256": after,
                }
                if not isinstance(execution, dict) or any(
                    execution.get(k) != v for k, v in expected_execution.items()
                ):
                    raise ValueError("execution_not_bound_to_iteration")
                execution_digests.append(artifacts["execution"]["sha256"])
                verification = json.loads(_evidence(root, artifacts["verification"]))
                if not isinstance(verification, dict) or any(
                    verification.get(k) != v for k, v in {
                        "status": "PASS", "scope": SCOPE,
                        "iteration_id": receipt["iteration_id"],
                        "input_state_sha256": before, "output_state_sha256": after,
                    }.items()
                ):
                    raise ValueError("verification_not_bound_to_iteration")
                ids.append(receipt["iteration_id"])
                alternatives.append(receipt["alternative_id"])
            except (ValueError, OSError, TypeError, AttributeError) as exc:
                reasons.append(f"iteration_{i + 1}:" + str(exc))
        if (len(set(ids)) != 2 or len(set(alternatives)) != 2
                or len(set(execution_digests)) != 2):
            reasons.append("iterations_or_alternatives_not_distinct")
    return {
        "schema_version": "1.0.0", "scope": SCOPE,
        "research_plateau": not reasons,
        "status": "SCOPED_PLATEAU_CANDIDATE" if not reasons else "PLATEAU_NOT_DEMONSTRATED",
        "replay_stable": bool(comparisons) and all(c["state_stable"] for c in comparisons),
        "reasons": sorted(set(reasons)), "comparisons": comparisons,
        "empirical_promotion": False,
        "interpretation": "Structural/evidence gate only; Verifier/Jev adjudication still required.",
    }


def write_immutable(path: Path, value: Any) -> None:
    """Publish a complete, fsynced JSON file atomically without overwriting one."""
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)  # Fails if the destination already exists.
    finally:
        os.unlink(temp)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshots", nargs=3, type=Path, required=True)
    parser.add_argument("--receipts", nargs=2, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-research-plateau", action="store_true")
    args = parser.parse_args()
    snapshots = [json.loads(p.read_text()) for p in args.snapshots]
    receipts = [json.loads(p.read_text()) for p in (args.receipts or [])]
    report = assess(snapshots, receipts, args.root)
    write_immutable(args.output, report)
    print(json.dumps(report, sort_keys=True))
    if args.require_research_plateau and not report["research_plateau"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
