#!/usr/bin/env python3
"""Vera return-panel contract 1.0.0: structural checks, NOT investment validation.

No third-party dependencies. Run: python tools/validate_return_panel.py FILE.json
A valid payload can abstain. A valid numeric payload can still be substantively wrong.
"""
import json
import math
import sys
from datetime import date

VERSION = "1.0.0"
THRESHOLDS = [10, 25, 50, 100]
REVIEW_STATUSES = {"NOT_RUN", "PENDING_AUTHORIZATION", "UNAVAILABLE", "COMPLETED", "FAILED"}
PROVENANCE_FIELDS = (
    "model_version", "input_artifact_version", "computation_artifact", "reference_class", "reference_class_fit",
    "sample_size_and_denominator", "failures_missingness_censoring", "measured_return_basis",
    "company_update_evidence", "adjustment_logic", "scenario_weights_and_paths",
    "dependence_treatment", "uncertainty_method", "calibration_evidence",
)
TERMS_FIELDS = (
    "security_and_entry_price", "entry_date", "horizon", "capital_denominator_and_followons",
    "ownership_conversion_and_dilution", "rights_and_exercise_policy", "waterfall_and_debt",
    "fees_and_carry", "currency_and_fx", "tax_treatment", "cash_observation_policy",
)

def _text(x):
    return isinstance(x, str) and bool(x.strip())

def _in(x, choices):
    return isinstance(x, str) and x in choices

def _prob(x):
    return type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1

def validate(panel):
    errors = []
    def need(ok, message):
        if not ok:
            errors.append(message)
    if not isinstance(panel, dict):
        return ["panel must be an object"]
    need(panel.get("contract_version") == VERSION, "unsupported contract_version")
    need(_in(panel.get("publication_state"), {"DRAFT", "RELEASED"}), "publication_state must be DRAFT or RELEASED")
    need(panel.get("estimand") == "unconditional_net_realized_moic_at_horizon", "wrong estimand")
    need(_text(panel.get("analysis_identity")), "analysis_identity is required")
    try:
        date.fromisoformat(panel.get("data_cutoff", ""))
    except (ValueError, TypeError):
        errors.append("data_cutoff must be YYYY-MM-DD")
    need(_in(panel.get("calibration_status"), {"CALIBRATED", "PARTIALLY_CALIBRATED", "UNCALIBRATED"}), "invalid calibration_status")
    terms = panel.get("terms")
    need(isinstance(terms, dict), "terms must be an object")
    if isinstance(terms, dict):
        for name in TERMS_FIELDS:
            need(_text(terms.get(name)), "terms." + name + " must describe known terms or explicit gap")
    rows = panel.get("thresholds")
    if not isinstance(rows, list) or len(rows) != 4 or not all(isinstance(r, dict) for r in rows):
        return errors + ["thresholds must contain four objects"]
    need([r.get("threshold") for r in rows] == THRESHOLDS, "thresholds must be ordered 10,25,50,100")
    previous = {}
    any_numeric = False
    for row in rows:
        tag = str(row.get("threshold")) + "x: "
        status = row.get("status")
        need("probability" in row and "interval" in row, tag + "explicit probability and interval keys required")
        need(_in(status, {"ESTIMATED", "NOT_ESTIMABLE"}), tag + "invalid status")
        need(_text(row.get("derivation")), tag + "derivation required")
        gaps = row.get("blocking_gaps")
        need(isinstance(gaps, list) and all(_text(g) for g in gaps), tag + "blocking_gaps must be text array")
        if status == "NOT_ESTIMABLE":
            need(row.get("probability") is None and row.get("interval") is None, tag + "abstention must have null probability and interval")
            need(bool(gaps), tag + "abstention requires blocking gaps")
        elif status == "ESTIMATED":
            any_numeric = True
            need(panel.get("calibration_status") != "UNCALIBRATED", tag + "uncalibrated numeric output forbidden")
            need(not gaps, tag + "numeric output cannot have blocking gaps")
            need(isinstance(row.get("source_ids"), list) and bool(row["source_ids"]) and all(_text(s) for s in row["source_ids"]), tag + "source_ids required")
            need(_text(row.get("assumptions")), tag + "assumptions required")
            p, interval = row.get("probability"), row.get("interval")
            need(p is None or _prob(p), tag + "invalid point probability")
            need(isinstance(interval, dict), tag + "uncertainty interval required")
            values = {"probability": p}
            if isinstance(interval, dict):
                lo, hi = interval.get("lower"), interval.get("upper")
                need(_prob(lo) and _prob(hi), tag + "invalid interval bounds")
                if _prob(lo) and _prob(hi):
                    need(lo <= hi, tag + "reversed interval")
                    need(p is None or (_prob(p) and lo <= p <= hi), tag + "point outside interval")
                kind = interval.get("kind")
                need(_in(kind, {"confidence", "credible", "sensitivity", "judgment"}), tag + "invalid interval kind")
                need(_text(interval.get("interpretation")), tag + "interval interpretation required")
                need(_text(interval.get("method")), tag + "interval method required")
                if _in(kind, {"confidence", "credible"}):
                    need(_prob(interval.get("coverage")) and interval.get("coverage") not in (0, 1), tag + "statistical interval requires coverage in (0,1)")
                else:
                    need(interval.get("coverage") is None, tag + "judgment/sensitivity ranges have no statistical coverage")
                values.update(lower=lo, upper=hi)
            for key, value in values.items():
                if _prob(value):
                    need(key not in previous or value <= previous[key], tag + "non-monotone " + key)
                    previous[key] = value
        reviews = row.get("reviews")
        need(isinstance(reviews, dict), tag + "reviews required")
        if isinstance(reviews, dict):
            for who in ("independent_verifier", "jev"):
                review = reviews.get(who)
                need(isinstance(review, dict), tag + who + " review required")
                if not isinstance(review, dict):
                    continue
                need(_in(review.get("status"), REVIEW_STATUSES), tag + who + " invalid review status")
                need(_in(review.get("scope"), {"generic_method", "company_estimate", "none"}), tag + who + " invalid scope")
                need(_text(review.get("feedback")), tag + who + " actual feedback or unavailability reason required")
                if review.get("status") == "COMPLETED":
                    need(review.get("scope") != "none", tag + who + " completed review needs scope")
                    for name in ("reviewer", "timestamp", "input_version", "result", "resolution"):
                        need(_text(review.get(name)), tag + who + " completed review requires " + name)
    if any_numeric:
        need(type(panel.get("basis_complete")) is bool, "numeric panel requires typed basis_complete")
        basis_gaps = panel.get("basis_blocking_gaps")
        need(isinstance(basis_gaps, list) and all(_text(g) for g in basis_gaps), "basis_blocking_gaps must be text array")
        if panel.get("publication_state") == "RELEASED":
            need(panel.get("basis_complete") is True and basis_gaps == [], "released numeric panel requires complete basis without blocking gaps")
            provenance = panel.get("provenance", {})
            if not isinstance(provenance, dict):
                provenance = {}
            for row in rows:
                if row.get("status") != "ESTIMATED":
                    continue
                reviews = row.get("reviews", {})
                if not isinstance(reviews, dict):
                    continue
                for who in ("independent_verifier", "jev"):
                    review = reviews.get(who, {})
                    if not isinstance(review, dict):
                        continue
                    tag = str(row.get("threshold")) + "x: " + who + ": "
                    need(review.get("status") == "COMPLETED" and review.get("scope") == "company_estimate" and review.get("result") == "PASS", tag + "released numeric row requires completed company-estimate PASS")
                    need(_text(review.get("input_version")) and review.get("input_version") == provenance.get("input_artifact_version"), tag + "review input version must match provenance")
                    need(_text(review.get("model_version")) and review.get("model_version") == provenance.get("model_version"), tag + "review model version must match provenance")
                    need(review.get("material_blockers") == [], tag + "released review requires explicit empty material_blockers")
        provenance = panel.get("provenance")
        need(isinstance(provenance, dict), "numeric panel requires provenance")
        if isinstance(provenance, dict):
            for name in PROVENANCE_FIELDS:
                need(_text(provenance.get(name)), "provenance." + name + " required")
    return errors

def main():
    if len(sys.argv) != 2:
        print("Usage: validate_return_panel.py FILE.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as file:
            panel = json.load(file)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    errors = validate(panel)
    print("\n".join(errors) if errors else "Contract checks passed; not empirical or investment validation.")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
