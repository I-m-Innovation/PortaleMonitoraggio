from __future__ import annotations

from .dtos import ComputedPlantMetrics


def persist_metrics_to_impianto(impianto, metrics: ComputedPlantMetrics) -> None:
    """
    Adapter verso il model attuale `Impianto`.

    Nota: i nomi dei campi restano quelli legacy del progetto corrente.
    """
    impianto.ore_equivalenti_giornaliere = metrics.daily_equivalent_hours
    impianto.ore_equivalenti_annue = metrics.equivalent_hours
    impianto.ore_equivalenti_totali = metrics.total_equivalent_hours
    impianto.stato_operativo = metrics.status
    impianto.energia_annua_kwh = metrics.energy_kwh
    impianto.ha_meteo_station = metrics.has_weather_station
    impianto.irraggiamento_annuo_kwh_m2 = metrics.irradiation_kwh_m2
    impianto.performance_ratio_annuo = metrics.performance_ratio
    impianto.save(
        update_fields=[
            "ore_equivalenti_giornaliere",
            "ore_equivalenti_annue",
            "ore_equivalenti_totali",
            "stato_operativo",
            "energia_annua_kwh",
            "ha_meteo_station",
            "irraggiamento_annuo_kwh_m2",
            "performance_ratio_annuo",
        ]
    )
