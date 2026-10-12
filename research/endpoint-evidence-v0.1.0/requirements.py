"""Endpoint-specific requirements planner. No evidence or probability adjudication."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

VERSION = "endpoint-evidence-v0.1.0"
ENDPOINTS = ("operating_survival", "qualifying_company_success", "investor_moic")
PURPOSES = ("historical_endpoint", "forecast")
FRAMES = ("funded_rounds", "company_origin", "proposed_position")
METHODS = ("exact_history", "interval_supported", "horizon_status", "forecast_model")
THRESHOLDS = (10, 25, 50, 100)


def build_plan(endpoint, *, purpose="historical_endpoint", frame="funded_rounds",
               method="exact_history", platform_year=True, field_breakdown=False):
    """Return obligations, not eligibility. No data are read and no facts are inferred.

    Conditional means required if applicable, with unknown applicability unresolved.
    Choosing a method is an assertion, not validation that an adapter exists.
    """
    for value, allowed, name in ((endpoint, ENDPOINTS, "endpoint"),
                                 (purpose, PURPOSES, "purpose"),
                                 (frame, FRAMES, "frame"), (method, METHODS, "method")):
        if value not in allowed:
            raise ValueError(f"unsupported_{name}:{value}")
    if type(platform_year) is not bool or type(field_breakdown) is not bool:
        raise ValueError("reporting_flags_must_be_boolean")
    if (purpose == "forecast") != (method == "forecast_model"):
        raise ValueError("forecast_purpose_requires_forecast_method_and_vice_versa")
    if frame == "proposed_position" and (purpose != "forecast" or endpoint != "investor_moic"):
        raise ValueError("proposed_position_is_for_investor_forecast")
    if endpoint == "qualifying_company_success" and frame != "funded_rounds":
        raise ValueError("frozen_composite_success_is_index_round_specific")
    if endpoint == "investor_moic" and frame == "company_origin":
        raise ValueError("investor_return_requires_a_position_not_company_origin")
    if frame == "proposed_position" and platform_year:
        raise ValueError("proposed_position_cannot_claim_historical_offering_year")

    required, conditional, optional = [], [], []
    def add(bucket, key, meaning, trigger=None):
        item = {"id": key, "meaning": meaning}
        if trigger:
            item["required_if"] = trigger
            item["unknown_applicability"] = "UNRESOLVED_NOT_OPTIONAL"
        bucket.append(item)

    add(required, "identity_unit", "Resolved analytical subject and unit, distinct company/position/round identifiers, duplicate/cohost and dependence treatment.")
    add(required, "target_clock", "Versioned endpoint predicate, declared origin, horizon and evidence-information cutoff; relevant date precision retained.")
    add(required, "frame_dispositions", "Declared target population and inclusion rule; every input row retained with membership/unknown/exclusion disposition, never complete-case disappearance.")
    add(required, "provenance_observation", "Source-bound material facts and contradictions, endpoint-specific observation coverage and administrative limits; missing, censored, inaccessible and unsearched remain distinct.")
    add(required, "method_compatibility", "Separately establish that the selected estimator supports available precision, order, entry and observation assumptions. This planner does not establish compatibility.")
    if frame == "funded_rounds":
        add(required, "funded_round_origin", "Economic-round identity, position-producing funded/completed fact and chosen origin convention. Sufficient authoritative aggregate evidence may establish it; individual contracts are not universal.")
    else:
        add(required, "declared_entry_origin", "Evidence or explicitly proposed terms supporting this separate company/position origin; do not replace the frozen funded-round clock.")
    if platform_year:
        add(required, "platform_offering_year", "Platform and first-live/public offering year for this requested breakdown; completion year is not a substitute.")
    if field_breakdown:
        add(required, "field_assignment", "Versioned field definition and assignment for the requested field-specific target.")
    else:
        add(optional, "unused_field_tags", "Unused detailed taxonomy and tags; conditional if later used as a predictor, stratum, confounder or transportability criterion.")

    if endpoint == "operating_survival":
        add(required, "independent_operation_entry", "Independent operating/terminal status at entry and any delayed-entry treatment; prior termination cannot be reset away.")
        if purpose == "historical_endpoint":
            add(required, "operating_endpoint_evidence", "Affirmative operation and relevant independent-operation terminal observations, with sufficient time/order for the chosen horizon/method.")
        else:
            add(required, "operating_history_at_prediction", "Known entry/operating/terminal history available by the prediction cutoff plus ascertainment of historical calibration labels. Future operation and terminal outcomes are not required prediction inputs.")
        add(optional, "nonterminal_success_qualification", "Prior/nonterminal equity success classification and valuation are not needed by an independently validated operating-only method unless material to observation/entry/terminal interpretation.")
        add(optional, "investor_payout_and_contract_detail", "Individual payout records, full cap table and detailed holder terms do not universally identify independent company operation.")
    elif endpoint == "qualifying_company_success":
        add(required, "index_relative_entry_success", "Index-relative success status at entry and incident versus baseline-inclusive target. Empty success fields do not establish PRE.")
        add(required, "typed_composite_success", "Preserve the frozen composite: qualifying priced equity, IPO/listing, evidenced acquisition consideration/value, or profitable exit; do not rename it simple valuation growth.")
        if purpose == "historical_endpoint":
            add(required, "relevant_success_competition", "First relevant qualifying event and earlier competing terminals, with adequate endpoint ascertainment/order; no observed event is not proof of no event.")
        else:
            add(required, "success_history_at_prediction", "Known index-relative success and competing-terminal history available by the prediction cutoff, plus ascertainment of historical calibration labels. Future qualifying/competing events are outcomes, not required inputs.")
        add(conditional, "comparable_priced_valuations", "Actual priced-equity index and follow-on comparability and >=1.5x threshold for observed qualification. SAFE/convertible caps and total raised are not actual priced valuations. In forecasts this concerns known history/calibration labels only; future financing values are modeled outcomes.", "An observed qualifying branch uses a valuation multiple, or its unresolved classification could depend on it. In forecasts, only historical information available by prediction cutoff is eligible.")
        add(conditional, "exit_consideration_or_gross_moic", "Shareholder consideration/transaction-value evidence for observed acquisition; gross investor MOIC >1x evidence for observed profitable-exit branch, as applicable. Future consideration/profit is a forecast outcome, not required realized evidence.", "An observed acquisition/profitable-exit classification relies on these predicates. For forecasts this applies only to known history/calibration labels, not future events.")
        add(optional, "investor_10x_payouts", "No requirement for 10x/25x/50x/100x cash returns to establish this different composite endpoint.")
    else:
        add(required, "net_cash_target", "Unconditional net realized cash MOIC at horizon with thresholds 10/25/50/100, security/position, capital and follow-on policy, fee/FX/tax conventions; no unrealized marks or historical maximum crossing.")
        if purpose == "historical_endpoint":
            add(required, "observed_net_cash", "Verified horizon-relevant invested-capital denominator and complete net distributions, or explicit unknown/censored label. Complete cumulative net totals can suffice without every underlying contract.")
            add(conditional, "cash_reconstruction_mechanics", "Terms, conversion, dilution, waterfall, costs and holder continuity needed to reconstruct unresolved investor cash facts; no company-value substitution.", "Direct complete net cash evidence is absent/inadequate or mechanics change cash attribution/denominator.")
            add(optional, "full_cap_table_when_cash_complete", "A full cap table and every contract are unnecessary when complete verified net cash and capital directly establish the ratio; known conflicts remain material.")
        else:
            add(required, "entry_terms_return_mapping", "Exact proposed security/price or cap, capital policy and defensible joint financing, dilution, rights/waterfall, costs and liquidity-to-net-cash mapping; irrelevant mechanics may be explicitly not applicable.")
            add(required, "calibration_uncertainty", "Defensible target-matched probability anchors, observation/selection analysis, company updates, joint/dependent paths, failure/no-liquidity/unresolved mass and uncertainty. No renormalizing away adverse paths.")
            add(required, "numeric_release_reviews", "Keep actual company-specific independent and JEV PASS reviews on exact model/input versions with no material blockers. Generic methodology review is not release evidence.")
            add(optional, "future_realized_payouts", "Future realized payouts are outcomes to predict, not required observed inputs. Missing material forecast mechanics/anchors still require abstention.")

    if purpose == "forecast" and endpoint != "investor_moic":
        add(required, "calibration_uncertainty", "Target-matched calibration, prediction-time information cutoff, transportability and observation/selection uncertainty; a requirements plan creates no numerical prior.")
    if method == "exact_history":
        add(required, "exact_relevant_chronology", "Adjudicated exact dates/order required by the exact-history method. Interval facts remain preserved with HOLD where unsupported, not midpoint-converted.")
    elif method in ("interval_supported", "horizon_status"):
        add(conditional, "interval_order_resolution", "Resolve or explicitly model/bound material interval/order uncertainty; retain source precision and HOLD where unsupported. A separately validated suitable adapter is required and is absent from this package; no exact-date imputation.", "Admissible dates/orders cross the horizon or change classification, risk-set entry, or the selected estimator result.")
    add(conditional, "decision_material_enrichment", "Relevant team/customer/financial/technology/market/contract/graph evidence, collected in priority order with contradictions retained.", "A variable identifies the target/frame/dependence, is used by the chosen model or can plausibly reverse a decision; relevance is declared before outcomes and revisited on new evidence.")
    add(conditional, "systematic_missingness_review", "Endpoint-specific ascertainment, informative-censoring/selection analysis and sensitivity or abstention. All-row retention alone cannot identify an unbiased point estimate.", "Publishing estimates or comparisons, or missingness could change endpoint/selection interpretation.")
    add(optional, "redundant_followup_months", "A duplicate numeric follow-up is derivable from an authoritative selected time basis. If supplied inconsistently, retain and resolve the contradiction rather than choosing silently.")
    add(optional, "unused_background", "Unneeded founder narratives, customer quotations, total raised, full later event history and unused tags; none may replace facts a selected predicate requires.")
    return {
        "policy_version": VERSION,
        "spec": {"endpoint": endpoint, "purpose": purpose, "frame": frame, "method": method,
                 "platform_year": platform_year, "field_breakdown": field_breakdown},
        "required": required, "conditional": conditional, "optional": optional,
        "investor_thresholds": list(THRESHOLDS) if endpoint == "investor_moic" else [],
        "evidence_eligibility": "NOT_ADJUDICATED", "estimator_compatibility": "NOT_VERIFIED",
        "numeric_release": "NOT_AUTHORIZED_BY_PLAN", "canonical_changes": False,
    }


def resolve_applicability(item, declaration=None):
    """Conservative task routing only; declarations are not evidence authentication.

    Absence/UNKNOWN remains unresolved. FALSE needs an explicit rationale and
    version-bound review reference, never a truthiness cast or empty default.
    """
    if "required_if" not in item:
        raise ValueError("not_a_conditional_requirement")
    if declaration is None:
        return "UNRESOLVED"
    if not isinstance(declaration, dict):
        raise ValueError("invalid_applicability_declaration")
    status = declaration.get("status")
    if status not in ("TRUE", "FALSE", "UNKNOWN"):
        raise ValueError("invalid_applicability_status")
    if status == "UNKNOWN":
        return "UNRESOLVED"
    if not all(isinstance(declaration.get(k), str) and declaration[k].strip()
               for k in ("rationale", "review_ref")):
        raise ValueError("resolved_applicability_needs_rationale_and_review_ref")
    return "REQUIRED" if status == "TRUE" else "NOT_APPLICABLE_DECLARED"


def load_spec(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate_key:{key}")
            out[key] = value
        return out
    spec = json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    if not isinstance(spec, dict) or set(spec) != {"endpoint", "purpose", "frame", "method", "platform_year", "field_breakdown"}:
        raise ValueError("spec_requires_exact_declared_keys")
    return build_plan(**deepcopy(spec))


def work_queue(plan, applicability=None):
    """Optional enrichment never enters the queue; UNKNOWN asks relevance first.

    Callers must not treat this queue as a set of failed scientific gates.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("spec"), dict):
        raise ValueError("invalid_plan")
    try:
        expected = build_plan(**plan["spec"])
    except (TypeError, ValueError) as error:
        raise ValueError("invalid_plan_spec") from error
    if plan != expected:
        raise ValueError("plan_must_match_current_version_and_spec")
    applicability = {} if applicability is None else applicability
    if not isinstance(applicability, dict):
        raise ValueError("applicability_must_be_object")
    ids = {item["id"] for item in plan["conditional"]}
    if set(applicability) - ids:
        raise ValueError("unknown_conditional_requirement")
    result = [{"id": item["id"], "action": "ESTABLISH_REQUIRED_FACT",
               "question": item["meaning"]} for item in plan["required"]]
    for item in plan["conditional"]:
        status = resolve_applicability(item, applicability.get(item["id"]))
        if status == "REQUIRED":
            result.append({"id": item["id"], "action": "ESTABLISH_APPLICABLE_FACT", "question": item["meaning"]})
        elif status == "UNRESOLVED":
            result.append({"id": item["id"], "action": "DECIDE_RELEVANCE_FIRST", "question": item["required_if"]})
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    args = parser.parse_args()
    print(json.dumps(load_spec(args.spec), indent=2, sort_keys=True, allow_nan=False))
