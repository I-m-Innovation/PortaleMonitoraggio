from __future__ import annotations

from django.utils import timezone

from ..models import FotovoltaicoMetricheTecniche
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


def persist_metrics_to_fotovoltaico_metriche_tecniche(
    impianto,
    metrics: ComputedPlantMetrics,
    *,
    sync_status: str = FotovoltaicoMetricheTecniche.SyncStatus.OK,
    sync_note: str = "",
) -> None:
    record, _ = FotovoltaicoMetricheTecniche.objects.get_or_create(impianto=impianto)
    record.pr_ultimi_12_mesi = metrics.performance_ratio
    record.mancata_produzione = metrics.missed_production_kwh
    record.energia_stimata_anno_corrente_kwh = metrics.expected_energy_kwh
    record.ore_equivalenti_ultimi_12_mesi = metrics.equivalent_hours
    record.stato_operativo = (
        metrics.status or FotovoltaicoMetricheTecniche.StatoOperativo.UNKNOWN
    )
    record.last_sync_at = timezone.now()
    record.sync_status = sync_status
    record.sync_note = sync_note
    record.save(
        update_fields=[
            "pr_ultimi_12_mesi",
            "mancata_produzione",
            "energia_stimata_anno_corrente_kwh",
            "ore_equivalenti_ultimi_12_mesi",
            "stato_operativo",
            "last_sync_at",
            "sync_status",
            "sync_note",
        ]
    )
