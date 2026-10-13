"""Execute finite FICTIONAL boundary examples against unchanged frozen bytes.

This module does not accept empirical records, read a ledger or authenticate facts.
The deliberately collapsed histories are counterexamples, never candidate outputs.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys
import types
from time import perf_counter

from method_guard import _dependencies, _git_blob, FROZEN_METHOD, bind_method


def run():
    started = perf_counter()
    planner, bindings = _dependencies()
    path = Path(__file__).resolve().parent.parent / FROZEN_METHOD["version"] / "aj_explicit_history.py"
    name = "_fictional_pilot_bound_engine"
    engine_bytes = path.read_bytes()
    if _git_blob(engine_bytes) != FROZEN_METHOD["engine_git_blob"]:
        raise ValueError("frozen_engine_dependency_hash_mismatch")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    try:
        exec(compile(engine_bytes, str(path), "exec"), module.__dict__)
        S, H, T = module.State, module.History, module.Transition
        scenarios = {
            "F01_clean_operating_full_followup": (
                (H("fictional-A", "fictional-A", S.PRE, 3), H("fictional-B", "fictional-B", S.PRE, 3)), 2),
            "F02_state_specific_censoring": (
                (H("fictional-A", "fictional-A", S.PRE, 3, (T(.5, S.PRE, S.POST),)),
                 H("fictional-B", "fictional-B", S.PRE, 1),
                 H("fictional-C", "fictional-C", S.PRE, 2, (T(2, S.PRE, S.CLOSURE),))), 2.5),
            "F03_cross_subject_event_censor_tie": (
                (H("fictional-A", "fictional-A", S.PRE, 1, (T(1, S.PRE, S.CLOSURE),)),
                 H("fictional-B", "fictional-B", S.PRE, 1)), 1),
            "F04_unsupported_tail_after_tied_censor": (
                (H("fictional-A", "fictional-A", S.PRE, 1, (T(1, S.PRE, S.CLOSURE),)),
                 H("fictional-B", "fictional-B", S.PRE, 1)), 1.1),
            "F05_initial_terminal_mass": (
                (H("fictional-A", "fictional-A", S.ACQUISITION_UNKNOWN, 0),
                 H("fictional-B", "fictional-B", S.POST, 3)), 2),
            "F06_unsupported_post_mass": (
                (H("fictional-A", "fictional-A", S.POST, 1),
                 H("fictional-B", "fictional-B", S.PRE, 3)), 2),
        }
        outputs = []
        for key, (histories, horizon) in scenarios.items():
            result = asdict(module.at_horizon(histories, horizon))
            output = {"case_id": key, "dataset_kind": "FICTIONAL_MATHEMATICAL_FIXTURE",
                      "source_evidence": None, "histories": [asdict(h) for h in histories],
                      "horizon": horizon, "unchanged_engine_result": result}
            if key in ("F02_state_specific_censoring", "F06_unsupported_post_mass"):
                collapsed = tuple(H(h.round_id, h.company_id,
                    S.PRE if h.initial_state in module.OPERATING else h.initial_state,
                    h.observation_end,
                    tuple(T(t.time, S.PRE, t.destination) for t in h.transitions
                          if t.destination in module.TERMINAL)) for h in histories)
                output["forbidden_collapse_counterexample"] = {
                    "label": "ILLUSTRATIVE_OTHER_MODEL_NOT_AN_ADAPTER",
                    "result": asdict(module.at_horizon(collapsed, horizon))}
            outputs.append(output)
        rejected = []
        for key, histories in (
            ("F07_same_subject_tie", (H("fictional-A", "fictional-A", S.PRE, 2,
               (T(1, S.PRE, S.POST), T(1, S.POST, S.CLOSURE))),)),
            ("F08_interval_transition", (H("fictional-A", "fictional-A", S.PRE, 3,
               (T((1, 2), S.PRE, S.CLOSURE),)),)),
            ("F09_unknown_initial_success_state", (H("fictional-A", "fictional-A", "operating", 3),)),
        ):
            try:
                module.validate(histories)
            except ValueError as error:
                rejected.append({"case_id": key, "dataset_kind": "FICTIONAL_MATHEMATICAL_FIXTURE",
                                 "status": "REJECTED_BY_UNCHANGED_ENGINE", "reason": str(error)})
            else:
                raise AssertionError("expected_frozen_rejection:" + key)
        plan = planner.build_plan("operating_survival")
        bound = bind_method(plan, method=FROZEN_METHOD)
        return {"pilot_version": "fictional-method-boundaries-v0.1.0", "dependency_bindings": bindings,
                "scope": "Only fictional finite mathematical examples; no scientific or source admission",
                "accepted_mathematical_examples": outputs, "rejected_mathematical_examples": rejected,
                "method_bound_plan": bound, "empirical_histories": 0,
                "source_requests_issued": 0, "elapsed_seconds": perf_counter() - started,
                "production_adoption": "HOLD", "numeric_prior_promotion": False}
    finally:
        del sys.modules[name]


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True, allow_nan=False))
