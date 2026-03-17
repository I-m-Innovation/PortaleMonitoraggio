from __future__ import annotations

from .dtos import ComputedPlantMetrics, ProviderPlantSnapshot
from .windows import MetricsWindow


class DefaultMetricsCalculator:
    """Shared calculator for providers that can expose energy + irradiation + power."""

    def compute(self, snapshot: ProviderPlantSnapshot, window: MetricsWindow) -> ComputedPlantMetrics:
        equivalent_hours = None
        if snapshot.window_energy_kwh is not None and snapshot.peak_power_kw:
            equivalent_hours = snapshot.window_energy_kwh / snapshot.peak_power_kw

        performance_ratio = None
        if (
            snapshot.window_energy_kwh is not None
            and snapshot.window_irradiation_kwh_m2 is not None
            and snapshot.peak_power_kw
            and snapshot.window_irradiation_kwh_m2 > 0
        ):
            performance_ratio = snapshot.window_energy_kwh / (
                snapshot.peak_power_kw * snapshot.window_irradiation_kwh_m2
            )

        return ComputedPlantMetrics(
            source_name=snapshot.source_name,
            plant_name=snapshot.plant_name,
            window_start=window.start_date,
            window_end=window.end_date,
            status=snapshot.status,
            energy_kwh=snapshot.window_energy_kwh,
            equivalent_hours=round(equivalent_hours, 4) if equivalent_hours is not None else None,
            daily_equivalent_hours=snapshot.daily_equivalent_hours,
            total_equivalent_hours=snapshot.total_equivalent_hours,
            irradiation_kwh_m2=snapshot.window_irradiation_kwh_m2,
            performance_ratio=round(performance_ratio, 4) if performance_ratio is not None else None,
            has_weather_station=snapshot.has_weather_station,
            inverters_count=snapshot.inverters_count,
            inverters_ok=snapshot.inverters_ok,
            coverage=snapshot.coverage,
            missing_inverters=list(snapshot.missing_inverters),
        )
