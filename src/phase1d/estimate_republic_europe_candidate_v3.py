#!/usr/bin/env python3
"""Compute non-promoted, censoring-aware Republic Europe candidate estimates from ledger v4."""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import os
import tempfile
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


def validate_followup_input(row: dict) -> float | None:
    """Reject malformed supplied values; None retains absent numeric follow-up."""
    start = row.get("completion_date")
    end = row.get("censor_date")
    for field, value in (("completion_date", start), ("censor_date", end)):
        if value is not None and not isinstance(value, str):
            raise ValueError(f"invalid date type:{field}")
    start_date = date.fromisoformat(start) if start else None
    end_date = date.fromisoformat(end) if end else None
    if start_date is not None and end_date is not None and end_date < start_date:
        raise ValueError("censor_date precedes completion_date")
    raw = row.get("followup_months", "")
    if raw in (None, ""):
        return None
    if isinstance(raw, bool):
        raise ValueError("invalid follow-up")
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid follow-up") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError("follow-up must be finite and nonnegative")
    return value


def followup_time(row: dict) -> float:
    value = validate_followup_input(row)
    if value is not None:
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
        validate_followup_input(row)
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


def _bootstrap_not_run(status: str, seed: int | None = None) -> dict:
    return {
        "requested_replicates": BOOTSTRAPS, "completed_replicates": 0,
        "seed": seed, "execution_status": status,
        "interval_status": "WITHHELD_BOOTSTRAP_NOT_RUN", "primary_interval": None,
        "supported_draw_count": None, "unsupported_draw_count": None,
        "defined_draw_count": None, "undefined_draw_count": None,
        "not_run_draw_count": BOOTSTRAPS, "degenerate_draw_count": None,
        "degenerate_distribution": None, "draws": [],
    }


def _caller_bootstrap_report(rows: list[dict], endpoint: str, horizon: float, seed: int) -> dict:
    """Retain every company draw; support is checked on the endpoint's own history.

    This is a conservative reporting disposition, not a coverage guarantee. The
    operating endpoint remains the caller's existing collapsed-terminal KM.
    """
    if isinstance(BOOTSTRAPS, bool) or not isinstance(BOOTSTRAPS, int) or BOOTSTRAPS < 0:
        raise ValueError("nonnegative_integer_replicate_count_required")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("integer_seed_required")
    if endpoint not in ("success", "closure", "survival"):
        raise ValueError("unsupported_bootstrap_endpoint")
    if isinstance(horizon, bool) or not isinstance(horizon, (int, float)) or not math.isfinite(horizon) or horizon < 0:
        raise ValueError("finite_nonnegative_horizon_required")
    if endpoint == "survival":
        observations = [CompetingRiskObservation(
            r["round_id"], r["canonical_company_id"],
            (months(r.get("completion_date", ""), terminal_date(r)) or 0.0)
            if terminal_date(r) else followup_time(r),
            "terminal" if terminal_date(r) else None,
        ) for r in rows]
        point = km_survival(rows, horizon)
    else:
        observations = [first_event_observation(r, endpoint) for r in rows]
        point = cif_at_horizon(observations, endpoint, horizon)
    parent_supported = landmark_supported(observations, horizon)
    metadata = {
        "endpoint": endpoint, "horizon": horizon, "point": point,
        "full_sample_support_status": "SUPPORTED" if parent_supported else "UNSUPPORTED_HORIZON",
        "company_count": len({r["canonical_company_id"] for r in rows}),
        "round_count": len(rows), "confidence_level": .95,
        "percentile_convention": "legacy_discrete_indices_floor(B*alpha/2)_and_floor(B*(1-alpha/2))-1_clamped",
    }
    if BOOTSTRAPS == 0 or metadata["company_count"] < 2:
        status = "NOT_RUN_ZERO_REPLICATES_REQUESTED" if BOOTSTRAPS == 0 else "NOT_RUN_INSUFFICIENT_COMPANY_CLUSTERS"
        return dict(metadata, **_bootstrap_not_run(status, seed))
    draws = []
    for index, indices in enumerate(grouped_bootstrap_indices(rows, BOOTSTRAPS, seed)):
        sample_obs = [observations[i] for i in indices]
        support_status = "SUPPORTED" if landmark_supported(sample_obs, horizon) else "UNSUPPORTED_HORIZON"
        try:
            value = (km_survival([rows[i] for i in indices], horizon) if endpoint == "survival"
                     else cif_at_horizon(sample_obs, endpoint, horizon))
            if not math.isfinite(value):
                raise ValueError("nonfinite_bootstrap_statistic")
            reason = None
        except (ValueError, ArithmeticError) as error:
            value = None
            reason = f"{type(error).__name__}:{error}"
        draws.append({
            "index": index, "source_row_indices": indices,
            "source_round_ids": [rows[i]["round_id"] for i in indices],
            "source_company_ids_by_row": [rows[i]["canonical_company_id"] for i in indices],
            "mathematical_value": value, "numerical_support_status": support_status,
            "statistic_status": "DEFINED" if value is not None else "UNDEFINED_BOOTSTRAP_STATISTIC",
            "failure_reason": reason,
        })
    unsupported = sum(d["numerical_support_status"] == "UNSUPPORTED_HORIZON" for d in draws)
    undefined = sum(d["mathematical_value"] is None for d in draws)
    values = [d["mathematical_value"] for d in draws if d["mathematical_value"] is not None]
    degenerate = (min(values) == max(values)) if not undefined else None
    interval = None
    if not parent_supported:
        interval_status = "WITHHELD_FULL_SAMPLE_STATE_RISK_GAP"
    elif undefined:
        interval_status = "WITHHELD_UNDEFINED_BOOTSTRAP_DRAWS"
    elif unsupported:
        interval_status = "WITHHELD_UNSUPPORTED_BOOTSTRAP_DRAWS"
    elif BOOTSTRAPS < 2:
        interval_status = "WITHHELD_FEWER_THAN_TWO_REPLICATES"
    elif degenerate:
        interval_status = "WITHHELD_DEGENERATE_BOOTSTRAP_DISTRIBUTION"
    else:
        interval = percentile_interval(values)
        interval_status = "PERCENTILE_BOOTSTRAP_INTERVAL_NO_NOMINAL_COVERAGE_GUARANTEE"
    return dict(metadata, requested_replicates=BOOTSTRAPS, completed_replicates=len(draws),
        seed=seed, execution_status="RUN_ALL_REQUESTED_DRAWS_RETAINED",
        interval_status=interval_status, primary_interval=interval,
        supported_draw_count=len(draws) - unsupported, unsupported_draw_count=unsupported,
        defined_draw_count=len(draws) - undefined, undefined_draw_count=undefined,
        not_run_draw_count=BOOTSTRAPS - len(draws),
        degenerate_draw_count=len(draws) if degenerate else (None if undefined else 0),
        degenerate_distribution=degenerate, draws=draws)


def bootstrap_cif(rows: list[dict], estimand: str, horizon: float, seed: int, *, return_report: bool = False):
    report = _caller_bootstrap_report(rows, estimand, horizon, seed)
    if return_report:
        return report
    lo, hi = report["primary_interval"] or (None, None)
    return report["point"], lo, hi


def bootstrap_survival(rows: list[dict], horizon: float, seed: int, *, return_report: bool = False):
    report = _caller_bootstrap_report(rows, "survival", horizon, seed)
    if return_report:
        return report
    lo, hi = report["primary_interval"] or (None, None)
    return report["point"], lo, hi


def _rq1_bootstrap_fields(reports: dict[str, dict], report_prefix: str) -> dict:
    """Compact diagnostics only; the full draw records belong in the audit sidecar."""
    fields = {}
    for endpoint, report in reports.items():
        for field in ("execution_status", "interval_status", "requested_replicates",
                      "completed_replicates", "seed", "supported_draw_count",
                      "unsupported_draw_count", "defined_draw_count", "undefined_draw_count",
                      "not_run_draw_count", "degenerate_draw_count", "degenerate_distribution"):
            fields[f"{endpoint}_bootstrap_{field}"] = report[field]
        fields[f"{endpoint}_bootstrap_report_id"] = f"{report_prefix}/{endpoint}"
    return fields


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"bootstrap_audit_artifact_conflict:{path.name}")
        return
    # Publish a complete file atomically without replacing a concurrent writer.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(payload)
        temporary_path = Path(temporary.name)
    try:
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError(f"bootstrap_audit_artifact_conflict:{path.name}")
    finally:
        temporary_path.unlink()


def write_bootstrap_audit(output_dir: Path, reports: dict[str, dict], source_hashes: dict[str, str]) -> dict:
    """Write portable, deterministic, content-addressed full-draw evidence.

    These files contain source identifiers, inherit the ledger's access controls,
    and must not be published simply because the implementation is public.
    Serialization is validated before writing; existing artifacts are immutable.
    """
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as compressed:
        for report_id, report in sorted(reports.items()):
            if not report_id or report_id.startswith("/") or ".." in report_id.split("/"):
                raise ValueError("relative_bootstrap_report_id_required")
            record = {"report_id": report_id, "report": report}
            compressed.write((json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8"))
    draw_bytes = buffer.getvalue()
    draw_hash = hashlib.sha256(draw_bytes).hexdigest()
    draw_path = output_dir / f"cp4_republic_europe_candidate_v3_bootstrap_draws.{draw_hash}.jsonl.gz"
    manifest = {
        "schema_version": "caller-bootstrap-audit-v1",
        "reporting_policy": "retain_all_requested_draws_and_withhold_affected_intervals",
        "empirical_failure_claim": False,
        "source_sha256": source_hashes,
        "artifact": {"relative_path": draw_path.name, "sha256": draw_hash,
                     "format": "gzip_jsonl_one_report_per_line"},
        "reports": {report_id: {"line_1based": i + 1,
                     "requested_replicates": report["requested_replicates"],
                     "completed_replicates": report["completed_replicates"],
                     "interval_status": report["interval_status"]}
                    for i, (report_id, report) in enumerate(sorted(reports.items()))},
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest_path = output_dir / f"cp4_republic_europe_candidate_v3_bootstrap_manifest.{manifest_hash}.json"
    # Check both existing artifacts before publishing either one.
    for path, payload in ((draw_path, draw_bytes), (manifest_path, manifest_bytes)):
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"bootstrap_audit_artifact_conflict:{path.name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_immutable(draw_path, draw_bytes)
    _write_immutable(manifest_path, manifest_bytes)
    return {"bootstrap_audit_manifest": manifest_path.name,
            "bootstrap_audit_manifest_sha256": manifest_hash,
            "bootstrap_audit_artifact": draw_path.name,
            "bootstrap_audit_artifact_sha256": draw_hash}


def supported(observation: CompetingRiskObservation, horizon: float) -> bool:
    return observation.time >= horizon or (observation.cause is not None and observation.time <= horizon)


def landmark_supported(observations: list[CompetingRiskObservation], horizon: float) -> bool:
    """Held proposal: require risk support or complete modeled first-event absorption.

    An early event supports that individual's status, but does not by itself
    support the unresolved remainder at an arbitrarily later landmark.
    """
    if not observations:
        return False
    if any(o.time >= horizon for o in observations):
        return True
    points = [p for p in competing_risk_cif(observations, "__support_only__") if p.time <= horizon]
    return bool(points and points[-1].event_free_survival == 0.0)


def supported_survival_scenario(rows: list[dict], horizon: float, mode: str) -> tuple[float | None, str]:
    """Gate an endpoint sensitivity on its own declared risk history.

    The primary midpoint endpoint is not an administrative cap on the start/end
    scenario. Complete modeled absorption remains supported at later horizons.
    """
    if mode not in ("start", "end"):
        raise ValueError("unsupported survival scenario mode")
    observations = []
    for row in rows:
        validate_followup_input(row)
        endpoint = terminal_date(row, mode)
        duration = months(row.get("completion_date", ""), endpoint) if endpoint else followup_time(row)
        observations.append(CompetingRiskObservation(
            row["round_id"], row["canonical_company_id"],
            duration if duration is not None else 0.0,
            "terminal" if endpoint else None,
        ))
    if not landmark_supported(observations, horizon):
        return None, "UNSUPPORTED_HORIZON"
    return km_survival(rows, horizon, mode), "SUPPORTED"


def event_count(observations: list[CompetingRiskObservation], cause: str, horizon: float) -> int:
    return sum(1 for o in observations if o.cause == cause and o.time <= horizon)


def zero_event_upper(n: int) -> float | None:
    return 1.0 - 0.05 ** (1.0 / n) if n > 0 else None


def zero_event_survival_lower(n: int) -> float | None:
    return 0.05 ** (1.0 / n) if n > 0 else None


def is_ascertained(row: dict) -> bool:
    value = validate_followup_input(row)
    return bool(
        (value is not None and value > 0)
        or row.get("success_date")
        or row.get("closure_date")
        or terminal_date(row)
    )


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.12g}"


def rq1_rows(ledger: list[dict], *, bootstrap_audit: dict[str, dict] | None = None) -> list[dict]:
    if isinstance(BOOTSTRAPS, bool) or not isinstance(BOOTSTRAPS, int) or BOOTSTRAPS < 0:
        raise ValueError("nonnegative_integer_replicate_count_required")
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
            survival_supported = sum(bool(followup_time(r) >= horizon or (terminal_date(r) and (months(r["completion_date"], terminal_date(r)) or 0) <= horizon)) for r in cell)
            n_supported = min(success_supported, closure_supported, survival_supported)
            survival_obs = [
                CompetingRiskObservation(
                    r["round_id"], r["canonical_company_id"],
                    (months(r["completion_date"], terminal_date(r)) or 0.0)
                    if terminal_date(r) else followup_time(r),
                    "terminal" if terminal_date(r) else None,
                )
                for r in cell
            ]
            estimable = n > 0 and all(
                landmark_supported(observations, horizon)
                for observations in (success_obs, closure_obs, survival_obs)
            )
            success_events = event_count(success_obs, "success", horizon)
            closure_events = event_count(closure_obs, "closure", horizon)
            terminal_other = event_count(closure_obs, "terminal_other", horizon)
            bootstrap_reports = {endpoint: dict(
                _bootstrap_not_run(
                    "NOT_RUN_ZERO_OBSERVED_EVENTS" if estimable else "NOT_RUN_PRIMARY_UNESTIMABLE",
                    year * 1000 + int(horizon) + offset),
                endpoint=endpoint, horizon=horizon, company_count=companies, round_count=n,
                full_sample_support_status="SUPPORTED" if landmark_supported(observations, horizon) else "UNSUPPORTED_HORIZON",
            ) for endpoint, offset, observations in (
                ("success", 11, success_obs), ("closure", 23, closure_obs), ("survival", 37, survival_obs))}
            if estimable:
                success_point = cif_at_horizon(success_obs, "success", horizon)
                closure_point = cif_at_horizon(closure_obs, "closure", horizon)
                survival_point = km_survival(cell, horizon)
                if success_events:
                    bootstrap_reports["success"] = bootstrap_cif(cell, "success", horizon, year * 1000 + int(horizon) + 11, return_report=True)
                    success_lo, success_hi = bootstrap_reports["success"]["primary_interval"] or (None, None)
                else:
                    success_lo = success_hi = None
                if closure_events:
                    bootstrap_reports["closure"] = bootstrap_cif(cell, "closure", horizon, year * 1000 + int(horizon) + 23, return_report=True)
                    closure_lo, closure_hi = bootstrap_reports["closure"]["primary_interval"] or (None, None)
                else:
                    closure_lo = closure_hi = None
                if closure_events + terminal_other:
                    bootstrap_reports["survival"] = bootstrap_survival(cell, horizon, year * 1000 + int(horizon) + 37, return_report=True)
                    survival_lo, survival_hi = bootstrap_reports["survival"]["primary_interval"] or (None, None)
                else:
                    survival_lo = survival_hi = None
                terminal_start, terminal_start_status = supported_survival_scenario(cell, horizon, "start")
                terminal_end, terminal_end_status = supported_survival_scenario(cell, horizon, "end")
            else:
                success_point = closure_point = survival_point = None
                success_lo = success_hi = closure_lo = closure_hi = survival_lo = survival_hi = None
                terminal_start = terminal_end = None
                terminal_start_status = terminal_end_status = "NOT_EVALUATED_PRIMARY_UNESTIMABLE"
            low_information = (
                n < 30
                or success_events < 5
                or closure_events < 5
                or ascertainment < 0.80
                or n_supported < 30
            )
            report_prefix = f"republic_europe/{year}/{int(horizon)}"
            if bootstrap_audit is not None:
                for endpoint, report in bootstrap_reports.items():
                    bootstrap_audit[f"{report_prefix}/{endpoint}"] = report
            output.append({
                **_rq1_bootstrap_fields(bootstrap_reports, report_prefix),
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
                "operating_survival_terminal_start_status": terminal_start_status,
                "operating_survival_terminal_end_status": terminal_end_status,
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
    bootstrap_audit = {}
    rq1 = rq1_rows(ledger, bootstrap_audit=bootstrap_audit)
    audit_binding = write_bootstrap_audit(DATA, bootstrap_audit, {
        LEDGER.name: sha(LEDGER),
        "src/phase1d/estimate_republic_europe_candidate_v3.py": sha(Path(__file__)),
        "src/phase1c/estimators.py": sha(ROOT / "src/phase1c/estimators.py"),
        "src/phase1c/outcomes.py": sha(ROOT / "src/phase1c/outcomes.py"),
        "src/phase1c/reporting.py": sha(ROOT / "src/phase1c/reporting.py"),
    })
    for row in rq1:
        row.update(audit_binding)
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
        "bootstrap_audit": audit_binding,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
