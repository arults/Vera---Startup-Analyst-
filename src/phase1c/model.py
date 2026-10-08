from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

PLATFORMS = {"wefunder", "startengine", "crowdcube", "republic_us", "republic_europe"}
YEARS = set(range(2020, 2026))
PRIMARY_FIELDS = {
    "saas_enterprise_software",
    "biotech_therapeutics",
    "healthcare_medtech",
    "fintech_insurtech",
    "consumer_retail",
    "marketplaces_platforms",
    "hardware_robotics_deeptech",
    "climate_energy_industrial",
    "food_beverage_agtech",
    "media_gaming_creator",
    "mobility_logistics_aerospace",
    "realestate_hospitality_proptech",
    "other_diversified",
}
ROUND_STATUSES = {"pending", "funded_completed", "failed", "withdrawn"}
AVAILABILITY = {"PUBLIC_VISIBLE", "AUTH_REQUIRED", "UNAVAILABLE"}

@dataclass(frozen=True)
class RoundRecord:
    round_id: str
    canonical_company_id: str
    platform: str
    offering_year: int
    first_live_date: date
    status: str
    primary_field: str
    instrument_type: str
    legal_name: str
    source_url: str
    source_availability: str = "PUBLIC_VISIBLE"
    completion_date: date | None = None
    comparable_valuation: float | None = None
    valuation_cap: float | None = None
    amount_raised: float | None = None
    cohost_platforms: tuple[str, ...] = field(default_factory=tuple)

    @property
    def layer_a_eligible(self) -> bool:
        return True

    @property
    def layer_b_eligible(self) -> bool:
        return self.status == "funded_completed" and self.completion_date is not None

def validate_round(r: RoundRecord) -> list[str]:
    errors: list[str] = []
    if not r.round_id:
        errors.append("round_id_missing")
    if not r.canonical_company_id:
        errors.append("company_id_missing")
    if r.platform not in PLATFORMS:
        errors.append("platform_invalid")
    if r.offering_year not in YEARS:
        errors.append("offering_year_invalid")
    if r.first_live_date.year != r.offering_year:
        errors.append("offering_year_must_equal_first_live_year")
    if r.status not in ROUND_STATUSES:
        errors.append("status_invalid")
    if r.primary_field not in PRIMARY_FIELDS:
        errors.append("primary_field_invalid")
    if r.source_availability not in AVAILABILITY:
        errors.append("source_availability_invalid")
    if not r.source_url:
        errors.append("source_url_missing")
    if r.status == "funded_completed" and r.completion_date is None:
        errors.append("funded_round_requires_completion_date")
    if r.completion_date and r.completion_date < r.first_live_date:
        errors.append("completion_before_first_live")
    if r.status in {"pending", "failed", "withdrawn"} and r.layer_b_eligible:
        errors.append("nonfunded_round_in_layer_b")
    if any(p not in PLATFORMS for p in r.cohost_platforms):
        errors.append("cohost_platform_invalid")
    return errors

def unique_round_ids(rounds: Iterable[RoundRecord]) -> bool:
    ids=[r.round_id for r in rounds]
    return len(ids)==len(set(ids))
