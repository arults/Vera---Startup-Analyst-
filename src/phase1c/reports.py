from __future__ import annotations

from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Interval:
    lower: float
    upper: float

@dataclass(frozen=True)
class Estimate:
    value: float | None
    primary_interval: Interval | None
    diagnostic_interval: Interval | None
    interval_disagreement: bool = False

@dataclass(frozen=True)
class ResultCell:
    platform: str
    years: tuple[int,...]
    field: str | None
    n_rounds: int
    n_companies: int
    at_risk: int
    informative_events: int
    censored: int
    lost_followup: int
    ascertainment_coverage: float
    maximum_supported_months: float
    horizon_months: float
    survival: Estimate
    success_cif: Estimate
    closure_cif: Estimate
    low_information: bool
    pooled: bool
    platform_observed: bool = True

def validate_result_cell(c: ResultCell) -> list[str]:
    errors=[]
    if not c.years:
        errors.append("years_missing")
    if c.n_rounds<0 or c.n_companies<0 or c.at_risk<0 or c.informative_events<0 or c.censored<0 or c.lost_followup<0:
        errors.append("negative_count")
    if c.n_companies>c.n_rounds:
        errors.append("companies_exceed_rounds")
    if not 0<=c.ascertainment_coverage<=1:
        errors.append("ascertainment_out_of_bounds")
    if c.horizon_months>c.maximum_supported_months:
        errors.append("horizon_exceeds_supported_followup")
    if not c.platform_observed:
        errors.append("estimand_must_be_platform_observed")
    for name,est in [("survival",c.survival),("success_cif",c.success_cif),("closure_cif",c.closure_cif)]:
        if est.value is not None and not 0<=est.value<=1:
            errors.append(f"{name}_out_of_bounds")
        for iv in (est.primary_interval,est.diagnostic_interval):
            if iv and not (0<=iv.lower<=iv.upper<=1):
                errors.append(f"{name}_interval_invalid")
    return errors

def result_cell_dict(c: ResultCell) -> dict:
    d=asdict(c)
    d["estimand_label"]="platform_observed"
    return d
