"""Add a concrete frozen-method contract to a historical survival work queue.

Planning only: no evidence authentication, history construction or estimator call.
The endpoint planner and frozen engine bytes are required and verified unchanged.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import types

VERSION = "endpoint-method-guard-v0.1.0"
FROZEN_METHOD = {
    "id": "equal-round-explicit-multistate-operating-occupancy",
    "version": "explicit-history-statistics-v0.2.0",
    "engine_git_blob": "a71beeaed288f89d0886f4d3fd4dd30c0089cbc4",
    "target_policy_git_blob": "fb62fb062274cf51b8090f91990c3181dc99bdb2",
}
PLANNER_SHA256 = "38277bea32c6f7acad55a7ae7c7f31afc0fbc0cd5096c51ecf7ef62bb42aee79"

# These are mandatory properties of this specific frozen implementation, not
# universal scientific requirements for every operating-survival estimator.
FROZEN_OBLIGATIONS = (
    ("frozen_platform_observed_source_policy",
     "Bind every material endpoint fact to the frozen PHASE_1C_SPEC platform-observed source "
     "rules and its exact reviewed source/claim. External evidence can be retained as context "
     "but does not become native-source admission through this planning guard. Retain "
     "conflicts and mandatory source-review companions; hashes establish bytes, not truth."),
    ("frozen_index_relative_state",
     "Explicit reviewed initial PRE, POST or typed terminal state for each index round. "
     "Blank success is not PRE, independent operation alone is not a PRE/POST classification, "
     "and a later round cannot reset prior terminal history."),
    ("frozen_success_and_terminal_history",
     "Source-bound relevant nonterminal PRE-to-POST success and typed terminal chronology, "
     "including index-relative qualification where the state/transition depends on it. "
     "Do not drop qualifying events merely because the reported endpoint sums PRE and POST."),
    ("frozen_exact_time_and_order",
     "Adjudicated exact times under one declared origin/time conversion. Distinct transitions "
     "within one subject must have strictly increasing times. Unknown order and interval dates "
     "remain on HOLD; do not break ties by invented epsilon, date midpoint or month endpoint. "
     "The engine uses events before censors at the same time and the same pre-event risk vector "
     "for cross-subject tied events."),
    ("frozen_common_entry_and_weights",
     "Common analysis time zero, equal economic-round contribution and company dependence "
     "clusters. No automatic left truncation, company reweighting or origin replacement; "
     "multiple rounds remain separate but clustered."),
    ("frozen_observation_and_identification",
     "Prepared endpoint-specific observation through each stated endpoint and review of "
     "censoring/ascertainment assumptions at PRE/POST state level. Point operating evidence "
     "does not prove complete intervening history. Missingness, lost follow-up, unsearched "
     "material and administrative cutoff remain distinct. A no-gap numerical status is not "
     "evidence of empirical identification."),
)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _dependencies(research_root=None):
    root = Path(research_root) if research_root is not None else Path(__file__).resolve().parent.parent
    planner_path = root / "endpoint-evidence-v0.1.0" / "requirements.py"
    engine_path = root / FROZEN_METHOD["version"] / "aj_explicit_history.py"
    policy_path = root.parent / "docs" / "PHASE_1C_SPEC.md"
    planner_bytes, engine_bytes, policy_bytes = (planner_path.read_bytes(), engine_path.read_bytes(),
                                               policy_path.read_bytes())
    if _sha256(planner_bytes) != PLANNER_SHA256:
        raise ValueError("planner_dependency_hash_mismatch")
    if _git_blob(engine_bytes) != FROZEN_METHOD["engine_git_blob"]:
        raise ValueError("frozen_engine_dependency_hash_mismatch")
    if _git_blob(policy_bytes) != FROZEN_METHOD["target_policy_git_blob"]:
        raise ValueError("frozen_target_policy_dependency_hash_mismatch")
    # Execute only the exact verified planner bytes, never a second read or an
    # import located through ambient PYTHONPATH. The engine is not executed here.
    module = types.ModuleType("_bound_endpoint_planner")
    module.__file__ = str(planner_path)
    exec(compile(planner_bytes, str(planner_path), "exec"), module.__dict__)
    return module, {"planner_sha256": _sha256(planner_bytes),
                    "engine_git_blob": _git_blob(engine_bytes),
                    "target_policy_git_blob": _git_blob(policy_bytes)}


def bind_method(plan, *, method, applicability=None, research_root=None):
    """Return a method-bound queue or an explicit incompatibility HOLD.

    A known method contract only specifies work to establish. No supplied
    declaration, nonempty field, hash or short queue is an evidence pass.
    """
    planner, bindings = _dependencies(research_root)
    endpoint_queue = planner.work_queue(plan, applicability)
    compatible_spec = (plan["spec"]["endpoint"] == "operating_survival"
                       and plan["spec"]["purpose"] == "historical_endpoint"
                       and plan["spec"]["method"] == "exact_history"
                       and plan["spec"]["frame"] == "funded_rounds")
    recognized = isinstance(method, dict) and method == FROZEN_METHOD
    if not recognized:
        status = "HOLD_UNRECOGNIZED_OR_UNVALIDATED_METHOD"
    elif not compatible_spec:
        status = "HOLD_SPEC_OUTSIDE_THIS_METHOD_CONTRACT"
    else:
        status = "BOUND_FOR_REVIEW_NOT_EVIDENCE_READY"
    obligations = [{"id": key, "action": "ESTABLISH_FROZEN_METHOD_REQUIREMENT", "question": meaning}
                   for key, meaning in FROZEN_OBLIGATIONS] if status.startswith("BOUND_") else []
    return {"guard_version": VERSION, "spec": deepcopy(plan["spec"]),
            "method_requested": deepcopy(method), "method_contract_status": status,
            "dependency_bindings": bindings,
            "endpoint_queue": deepcopy(endpoint_queue), "method_obligations": obligations,
            "work_queue": deepcopy(endpoint_queue) + obligations,
            "evidence_eligibility": "NOT_ADJUDICATED",
            "empirical_histories_constructed": 0,
            "numerical_estimates_computed": 0,
            "numeric_release": "NOT_AUTHORIZED_BY_METHOD_BINDING",
            "canonical_changes": False}
