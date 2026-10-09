#!/usr/bin/env python3
"""Compute non-promoted, censoring-aware Republic Europe candidate estimates from ledger v4."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from src.phase1c.estimators import CompetingRiskObservation, cif_at_horizon, competing_risk_cif, percentile_interval
from src.phase1c.reporting import CellStats, pool_adjacent_years

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/phase1d"
LEDGER = DATA / "cp3_republic_europe_outcome_ledger_v4.csv"
PRIOR = DATA / "cp4_republic_europe_rq1_candidate_v2.csv"
RQ1 = DATA / "cp4_republic_europe_rq1_candidate_v3.csv"
RQ2 = DATA / "cp4_republic_europe_rq2_gate_v3.csv"
SUMMARY = DATA / "cp4_republic_europe_candidate_v3_summary.json"
MANIFEST = DATA / "cp4_republic_europe_candidate_v3_manifest.json"

HORIZONS = (12.0, 24.0, 36.0, 60.0)
DAYS_PER_MONTH = 30.4375
BOOTSTRAPS = 1000


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def months(start: str, end: str) -> float | None:
    if not start or not end:
        return None
    delta = (date.fromisoformat(end) - date.fromisoformat(start)).days / DAYS_PER_MONTH
    if delta < -1e-12:
        raise ValueError(f"negative event time {start} -> {end}")
    return max(0.0, delta)


def terminal_date(row: dict, mode: str = "mid") -> str:
    if row.get("closure_date"):
        return row["closure_date"]
    if mode == "start":
        return row.get("terminal_event_interval_start", "") or row.get("terminal_event_midpoint_for_primary", "")
    if mode == "end":
        return row.get("terminal_event_interval_end", "") or row.get("terminal_event_midpoint_for_primary", "")
    return row.get("terminal_event_midpoint_for_primary", "") or row.get("terminal_event_interval_end", "") or row.get("terminal_event_interval_start", "")


def followup_time(row: dict) -> float:
    raw = row.get("followup_months", "")
    if raw not in (None, ""):
        value = float(raw)
        if value < 0:
            raise ValueError("negative follow-up")
        return value
    value = months(row.get("completion_date", ""), row.get("censor_date", ""))
    return value if value is not None else 0.0


def first_event_observation(row: dict, estimand: str) -> CompetingRiskObservation:
    start = row.get("completion_date", "")
    censor = followup_time(row)
    events: list[tuple[float, int, str]] = []
    if estimand == "success" and row.get("success_date"):
        value = months(start, row["success_date"])
        if value is not None:
            events.append((value, 2, "success"))
    if estimand == "closure" and row.get("closure_date"):
        value = months(start, row["closure_date"])
        if value is not None:
            events.append((value, 0, "closure"))
    terminal = terminal_date(row)
    if terminal:
        value = months(start, terminal)
        if value is not None:
            cause = "closure" if row.get("closure_date") else "terminal_other"
            events.append((value, 0 if cause == "closure" else 1, cause))
    if events:
        event_time, _, cause = min(events, key=lambda x: (x[0], x[1]))
        if event_time <= censor + 1e-6:
            return CompetingRiskObservation(row["round_id"], row["canonical_company_id"], event_time, cause)
    return CompetingRiskObservation(row["round_id"], row["canonical_company_id"], censor, None)


def km_survival(rows: list[dict], horizon: float, mode: str = "mid") -> float:
    pairs = []
    for row in rows:
        tdate = terminal_date(row, mode)
        if tdate:
            time = months(row.get("completion_date", ""), tdate)
            pairs.append((time if time is not None else 0.0, True))
        else:
            pairs.append((followup_time(row), False))
    event_times = sorted({t for t, event in pairs if event and t <= horizon})
    survival = 1.0
    for t in event_times:
        at_risk = sum(1 for time, _ in pairs if time >= t)
        events = sum(1 for time, event in pairs if event and abs(time - t) < 1e-9)
        if at_risk <= 0 or events > at_risk:
            raise ValueError("invalid KM risk set")
        survival *= 1.0 - events / at_risk
    return survival


def grouped_bootstrap_indices(rows: list[dict], n: int, seed: int) -> list[list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[row["canonical_company_id"]].append(i)
    companies = sorted(groups)
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        indices = []
        for company in (rng.choice(companies) for _ in companies):
            indices.extend(groups[company])
        samples.append(indices)
    return samples


def bootstrap_cif(rows: list[dict], estimand: str, horizon: float, seed: int) -> tuple[float, float, float]:
    observations = [first_event_observation(r, estimand) for r in rows]
    point = cif_at_horizon(observations, estimand, horizon)
    values = []
    for indices in grouped_bootstrap_indices(rows, BOOTSTRAPS, seed):
        sample = [observations[i] for i in indices]
        values.append(cif_at_horizon(sample, estimand, horizon))
    lo, hi = percentile_interval(values)
    return point, lo, hi


def bootstrap_survival(rows: list[dict], horizon: float, seed: int) -> tuple[float, float, float]:
    point = km_survival(rows, horizon)
    values = []
    for indices in grouped_bootstrap_indices(rows, BOOTSTRAPS, seed):
        sample = [rows[i] for i in indices]
        values.append(km_survival(sample, horizon))
    lo, hi = percentile_interval(values)
    return point, lo, hi


def supported(observation: CompetingRiskObservation, horizon: float) -> bool:
    return observation.time >= horizon or (observation.cause is not None and observation.time <= horizon)


def event_count(observations: list[CompetingRiskObservation], cause: str, horizon: float) -> int:
    return sum(1 for o in observations if o.cause == cause and o.time <= horizon)


def zero_event_upper(n: int) -> float | None:
    return 1.0 - 0.05 ** (1.0 / n) if n > 0 else None


def zero_event_survival_lower(n: int) -> float | None:
    return 0.05 ** (1.0 / n) if n > 0 else None


def is_ascertained(row: dict) -> bool:
    return bool(
        float(row.get("followup_months") or 0) > 0
        or row.get("success_date")
        or row.get("closure_date")
        or terminal_date(row)
    )


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.12g}"


def rq1_rows(ledger: list[dict]) -> list[dict]:
    output = []
    for year in range(2020, 2026):
        cell = [r for r in ledger if r.get("offering_year_status") == "BOUNDED_YEAR" and r.get("offering_year") == str(year)]
        n = len(cell)
        companies = len({r["canonical_company_id"] for r in cell})
        ascertained = sum(is_ascertained(r) for r in cell)
        ascertainment = ascertained / n if n else 0.0
        success_obs = [first_event_observation(r, "success") for r in cell]
        closure_obs = [first_event_observation(r, "closure") for r in cell]
        for horizon in HORIZONS:
            success_supported = sum(supported(o, horizon) for o in success_obs)
            closure_supported = sum(supported(o, horizon) for o in closure_obs)
            survival_supported = sum(followup_time(r) >= horizon or (terminal_date(r) and (months(r["completion_date"], terminal_date(r)) or 0) <= horizon) for r in cell)
            n_supported = min(success_supported, closure_supported, survival_supported)
            estimable = n > 0 and n_supported > 0
            success_events = event_count(success_obs, "success", horizon)
            closure_events = event_count(closure_obs, "closure", horizon)
            terminal_other = event_count(closure_obs, "terminal_other", horizon)
            if estimable:
                success_point = cif_at_horizon(success_obs, "success", horizon)
                closure_point = cif_at_horizon(closure_obs, "closure", horizon)
                survival_point = km_survival(cell, horizon)
                if success_events:
                    _, success_lo, success_hi = bootstrap_cif(cell, "success", horizon, year * 1000 + int(horizon) + 11)
                else:
                    success_lo = success_hi = None
                if closure_events:
                    _, closure_lo, closure_hi = bootstrap_cif(cell, "closure", horizon, year * 1000 + int(horizon) + 23)
                else:
                    closure_lo = closure_hi = None
                if closure_events + terminal_other:
                    _, survival_lo, survival_hi = bootstrap_survival(cell, horizon, year * 1000 + int(horizon) + 37)
                else:
                    survival_lo = survival_hi = None
                terminal_start = km_survival(cell, horizon, "start")
                terminal_end = km_survival(cell, horizon, "end")
            else:
                success_point = closure_point = survival_point = None
                success_lo = success_hi = closure_lo = closure_hi = survival_lo = survival_hi = None
                terminal_start = terminal_end = None
            low_information = (
                n < 30
                or success_events < 5
                or closure_events < 5
                or ascertainment < 0.80
                or n_supported < 30
            )
            output.append({
                "platform": "republic_europe",
                "offering_year": year,
                "horizon_months": int(horizon),
                "n_rounds": n,
                "n_companies": companies,
                "n_supported_to_horizon": n_supported,
                "support_share": fmt(n_supported / n if n else 0.0),
                "ascertainment_coverage": fmt(ascertainment),
                "success_events_observed": success_events,
                "success_cif": fmt(success_point),
                "success_ci_lower": fmt(success_lo),
                "success_ci_upper": fmt(success_hi),
                "success_support_upper_95": fmt(zero_event_upper(n_supported) if success_events == 0 else None),
                "closure_events_observed": closure_events,
                "closure_cif": fmt(closure_point),
                "closure_ci_lower": fmt(closure_lo),
                "closure_ci_upper": fmt(closure_hi),
                "closure_support_upper_95": fmt(zero_event_upper(n_supported) if closure_events == 0 else None),
                "terminal_nonclosure_events_observed": terminal_other,
                "operating_survival": fmt(survival_point),
                "survival_ci_lower": fmt(survival_lo),
                "survival_ci_upper": fmt(survival_hi),
                "survival_support_lower_95": fmt(zero_event_survival_lower(n_supported) if closure_events + terminal_other == 0 else None),
                "operating_survival_terminal_start": fmt(terminal_start),
                "operating_survival_terminal_end": fmt(terminal_end),
                "low_information": str(low_information).lower(),
                "estimable": str(estimable).lower(),
                "estimand_label": "platform_observed",
                "promotion_status": "CANDIDATE_ONLY",
            })
    return output


def rq2_rows(ledger: list[dict]) -> list[dict]:
    fields = sorted({r.get("primary_field", "") for r in ledger if r.get("primary_field")})
    output = []
    for field in fields:
        cell_stats = []
        for year in range(2020, 2026):
            rows = [r for r in ledger if r.get("offering_year_status") == "BOUNDED_YEAR" and r.get("offering_year") == str(year) and r.get("primary_field") == field]
            typed_events = sum(bool(r.get("success_date") or r.get("closure_date") or terminal_date(r)) for r in rows)
            cell_stats.append(CellStats(year, len(rows), typed_events, sum(is_ascertained(r) for r in rows)))
        for target_year in range(2020, 2026):
            result = pool_adjacent_years(target_year, cell_stats)
            output.append({
                "platform": "republic_europe",
                "primary_field": field,
                "target_year": target_year,
                "pooled_years": "|".join(str(y) for y in result.years),
                "n_rounds": result.n,
                "informative_events": result.informative_events,
                "ascertained": result.ascertained,
                "ascertainment_coverage": fmt(result.ascertainment_coverage),
                "report": str(result.report).lower(),
                "suppressed": str(result.suppressed).lower(),
                "crossed_maturity_boundary": str(result.crossed_maturity_boundary).lower(),
                "reasons": "|".join(result.reasons),
            })
    return output


def compare_prior(current: list[dict]) -> dict:
    if not PRIOR.exists():
        return {"prior_present": False}
    prior = read_csv(PRIOR)
    old = {(r["offering_year"], r["horizon_months"]): r for r in prior}
    metrics = ("success_cif", "closure_cif", "operating_survival")
    deltas = []
    for row in current:
        before = old.get((str(row["offering_year"]), str(row["horizon_months"])))
        if not before:
            continue
        for metric in metrics:
            if row.get(metric) not in (None, "") and before.get(metric) not in (None, ""):
                deltas.append({"year": row["offering_year"], "horizon": row["horizon_months"], "metric": metric, "before": float(before[metric]), "after": float(row[metric]), "absolute_delta": abs(float(row[metric]) - float(before[metric]))})
    largest = max(deltas, key=lambda x: x["absolute_delta"], default=None)
    return {
        "prior_present": True,
        "comparable_metric_count": len(deltas),
        "max_absolute_point_estimate_delta": largest["absolute_delta"] if largest else None,
        "largest_delta_cell": largest,
    }


def main() -> None:
    ledger = read_csv(LEDGER)
    if len(ledger) != 952:
        raise ValueError("unexpected ledger row count")
    rq1 = rq1_rows(ledger)
    rq2 = rq2_rows(ledger)
    rq1_fields = list(rq1[0].keys()) if rq1 else []
    rq2_fields = list(rq2[0].keys()) if rq2 else []
    write_csv(RQ1, rq1, rq1_fields)
    write_csv(RQ2, rq2, rq2_fields)
    comparison = compare_prior(rq1)
    summary = {
        "version": "candidate_v3",
        "source_ledger": LEDGER.name,
        "source_rows": len(ledger),
        "rq1_cells": len(rq1),
        "rq1_estimable_cells": sum(r["estimable"] == "true" for r in rq1),
        "rq1_low_information_cells": sum(r["low_information"] == "true" for r in rq1),
        "rq2_cells": len(rq2),
        "rq2_reportable_cells": sum(r["report"] == "true" for r in rq2),
        "rq2_suppressed_cells": sum(r["suppressed"] == "true" for r in rq2),
        "closure_events_total": sum(bool(r.get("closure_date")) for r in ledger),
        "terminal_nonclosure_events_total": sum(bool(terminal_date(r)) and not r.get("closure_date") for r in ledger),
        "success_events_total": sum(bool(r.get("success_date")) for r in ledger),
        "comparison_to_candidate_v2": comparison,
        "promotion_status": "CANDIDATE_ONLY",
        "rates_promoted": False,
        "limitations": [
            "Only Republic Europe has a denominator-grade native census.",
            "All estimable RQ1 cells remain low-information because closure ascertainment is zero and/or ascertainment/support gates fail.",
            "RQ2 field estimates remain suppressed unless n/event/ascertainment gates pass.",
            "2024-2025 remain right-censored; unsupported horizons are not estimated.",
        ],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": {LEDGER.name: sha(LEDGER), PRIOR.name: sha(PRIOR) if PRIOR.exists() else None},
        "output_files": {RQ1.name: sha(RQ1), RQ2.name: sha(RQ2), SUMMARY.name: sha(SUMMARY)},
        "summary": summary,
        "bootstrap_replicates": BOOTSTRAPS,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
