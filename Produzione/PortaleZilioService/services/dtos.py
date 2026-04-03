from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ProviderPlantSnapshot:
    source_name: str
    plant_key: str
    plant_name: str
    window_start: date
    window_end: date
    peak_power_kw: float | None
    status: str | None = None
    daily_equivalent_hours: float | None = None
    total_equivalent_hours: float | None = None
    window_energy_kwh: float | None = None
    window_irradiation_kwh_m2: float | None = None
    contractual_pr: float | None = None
    has_weather_station: bool | None = None
    inverters_count: int | None = None
    inverters_ok: int | None = None
    coverage: float | None = None
    missing_inverters: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComputedPlantMetrics:
    source_name: str
    plant_name: str
    window_start: date
    window_end: date
    status: str | None = None
    energy_kwh: float | None = None
    equivalent_hours: float | None = None
    daily_equivalent_hours: float | None = None
    total_equivalent_hours: float | None = None
    irradiation_kwh_m2: float | None = None
    performance_ratio: float | None = None
    missed_production_kwh: float | None = None
    has_weather_station: bool | None = None
    inverters_count: int | None = None
    inverters_ok: int | None = None
    coverage: float | None = None
    missing_inverters: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncOutcome:
    updated: int
    skipped: int
    missing: list[str]
    window_start: date
    window_end: date
