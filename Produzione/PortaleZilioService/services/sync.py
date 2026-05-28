from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from math import isclose

from django.db import transaction
from django.db.models import Count, Prefetch, Q

from MonitoraggioImpianti.models import Impianto

from ..models import (
    FotovoltaicoMetricheTecniche,
    ImpiantoAnagrafica,
    ImpiantoDispositivo,
    ImpiantoSorgenteDati,
)
from .calculators import DefaultMetricsCalculator
from .dtos import ProviderPlantSnapshot
from .dtos import SyncOutcome
from .persistence import (
    persist_metrics_to_fotovoltaico_metriche_tecniche,
    persist_metrics_to_impianto,
)
from .registry import ProviderRegistry
from .windows import MetricsWindow, rolling_12_months_until_yesterday

logger = logging.getLogger(__name__)


class MetricsSyncService:
    ISC_SOURCE_NAME = "iSolarCloud"
    SAJ_SOURCE_NAME = "Saj - Elekeeper"

    def __init__(self, registry: ProviderRegistry | None = None, calculator=None) -> None:
        self.registry = registry or ProviderRegistry()
        self.calculator = calculator or DefaultMetricsCalculator()

    def sync_queryset(self, queryset, window: MetricsWindow | None = None) -> SyncOutcome:
        active_window = window or rolling_12_months_until_yesterday()
        skipped = 0
        missing: list[str] = []

        # Phase 1 – network I/O outside any transaction so SQLite is never
        # locked while waiting for HTTP responses.
        impianti_list = list(queryset)
        results: list[tuple] = []
        for impianto in impianti_list:
            provider = self.registry.get_provider(getattr(impianto, "lettura_dati", None))
            try:
                snapshot = provider.fetch_snapshot(impianto, active_window)
                metrics = self.calculator.compute(snapshot, active_window)
                results.append((impianto, metrics))
            except NotImplementedError:
                skipped += 1
                missing.append(impianto.nome_impianto)

        # Phase 2 – write to DB in a single short atomic block.
        updated = 0
        with transaction.atomic():
            for impianto, metrics in results:
                persist_metrics_to_impianto(impianto, metrics)
                updated += 1

        return SyncOutcome(
            updated=updated,
            skipped=skipped,
            missing=missing,
            window_start=active_window.start_date,
            window_end=active_window.end_date,
        )

    def sync_api_isc_impianti(self, window: MetricsWindow | None = None) -> SyncOutcome:
        queryset = Impianto.objects.filter(lettura_dati="API_ISC")
        return self.sync_queryset(queryset, window=window)

    def sync_portale_fotovoltaico_isc_metrics(self, window: MetricsWindow | None = None) -> SyncOutcome:
        return self._sync_portale_source_metrics(
            source_name=self.ISC_SOURCE_NAME,
            queryset=self._get_portale_isc_queryset(),
            window=window,
        )

    def sync_portale_fotovoltaico_saj_metrics(self, window: MetricsWindow | None = None) -> SyncOutcome:
        return self._sync_portale_source_metrics(
            source_name=self.SAJ_SOURCE_NAME,
            queryset=self._get_portale_saj_queryset(),
            window=window,
        )

    def sync_portale_fotovoltaico_saj_annual_produced_energy(
        self,
        today: date | None = None,
    ) -> SyncOutcome:
        current_day = today or date.today()
        end_date = current_day - timedelta(days=1)
        start_of_year = date(end_date.year, 1, 1)
        queryset = self._get_portale_saj_queryset(
            include_historical_devices=True
        ).filter(fotovoltaico_metadata__is_ppu=True)
        provider = self.registry.get_provider(self.SAJ_SOURCE_NAME)
        skipped = 0
        missing: list[str] = []
        updated = 0

        for impianto in queryset:
            sorgenti = self._get_portale_sources(impianto, self.SAJ_SOURCE_NAME)
            if not sorgenti:
                skipped += 1
                missing.append(impianto.nome_impianto)
                continue

            metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)
            start_date, base_energy_kwh = self._annual_energy_resume_state(metriche, end_date)

            if start_date > end_date:
                logger.warning(
                    "[ppu-energy-sync] impianto=%s already_updated_through=%s energy_kwh=%s",
                    impianto.nome_impianto,
                    end_date,
                    base_energy_kwh,
                )
                continue

            logger.warning(
                "[ppu-energy-sync] impianto=%s calculating range=%s..%s base_energy_kwh=%s",
                impianto.nome_impianto,
                start_date,
                end_date,
                base_energy_kwh,
            )
            try:
                added_energy_kwh = provider.fetch_portale_energy_kwh_for_range(
                    impianto,
                    sorgenti[0],
                    start_date,
                    end_date,
                )
            except NotImplementedError as error:
                logger.warning(
                    "[ppu-energy-sync] impianto=%s skipped=%s",
                    impianto.nome_impianto,
                    error,
                )
                skipped += 1
                missing.append(impianto.nome_impianto)
                continue

            total_energy_kwh = base_energy_kwh + Decimal(str(added_energy_kwh))
            logger.warning(
                "[ppu-energy-sync] impianto=%s calculated added_energy_kwh=%s total_energy_kwh=%s updated_through=%s",
                impianto.nome_impianto,
                added_energy_kwh,
                total_energy_kwh,
                end_date,
            )
            with transaction.atomic():
                metriche, _ = FotovoltaicoMetricheTecniche.objects.get_or_create(impianto=impianto)
                metriche.energia_prodotta_anno_corrente_kwh = total_energy_kwh
                metriche.energia_prodotta_anno_corrente_aggiornata_al = end_date
                metriche.save(
                    update_fields=[
                        "energia_prodotta_anno_corrente_kwh",
                        "energia_prodotta_anno_corrente_aggiornata_al",
                    ]
                )
            updated += 1
            logger.warning(
                "[ppu-energy-sync] impianto=%s saved total_energy_kwh=%s updated_through=%s",
                impianto.nome_impianto,
                total_energy_kwh,
                end_date,
            )

        return SyncOutcome(
            updated=updated,
            skipped=skipped,
            missing=missing,
            window_start=start_of_year,
            window_end=end_date,
        )

    @staticmethod
    def _annual_energy_resume_state(metriche, end_date: date) -> tuple[date, Decimal]:
        start_of_year = date(end_date.year, 1, 1)
        updated_through = getattr(metriche, "energia_prodotta_anno_corrente_aggiornata_al", None)
        stored_energy = getattr(metriche, "energia_prodotta_anno_corrente_kwh", None)
        if updated_through and updated_through.year == end_date.year:
            return updated_through + timedelta(days=1), Decimal(str(stored_energy or 0))
        return start_of_year, Decimal("0")

    def sync_portale_fotovoltaico_saj_annual_exported_energy(
        self,
        today: date | None = None,
    ) -> SyncOutcome:
        """Sincronizza energia_immessa_anno_corrente_kwh per gli impianti SAJ PPU.

        Usa il delta del contatore cumulativo totalSellEnergy tra 2 snapshot
        (inizio e fine range), quindi richiede solo 2 chiamate HTTP per
        dispositivo indipendentemente dalla lunghezza del range.

        Il campo aggiornata_al evita di rifare la chiamata se i dati sono già
        aggiornati a ieri. A inizio anno il contatore riparte da zero automaticamente.
        """
        current_day = today or date.today()
        end_date = current_day - timedelta(days=1)
        start_of_year = date(end_date.year, 1, 1)
        queryset = self._get_portale_saj_queryset(
            include_historical_devices=True
        ).filter(fotovoltaico_metadata__is_ppu=True)
        provider = self.registry.get_provider(self.SAJ_SOURCE_NAME)
        skipped = 0
        missing: list[str] = []
        updated = 0

        for impianto in queryset:
            sorgenti = self._get_portale_sources(impianto, self.SAJ_SOURCE_NAME)
            if not sorgenti:
                skipped += 1
                missing.append(impianto.nome_impianto)
                continue

            metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)
            updated_through = getattr(metriche, "energia_immessa_anno_corrente_aggiornata_al", None)

            if updated_through and updated_through >= end_date and updated_through.year == end_date.year:
                logger.warning(
                    "[ppu-exported-sync] impianto=%s already_updated_through=%s",
                    impianto.nome_impianto,
                    updated_through,
                )
                continue

            logger.warning(
                "[ppu-exported-sync] impianto=%s calculating range=%s..%s",
                impianto.nome_impianto,
                start_of_year,
                end_date,
            )
            try:
                exported_kwh = provider.fetch_portale_exported_kwh_for_range(
                    impianto,
                    sorgenti[0],
                    start_of_year,
                    end_date,
                )
            except NotImplementedError as error:
                logger.warning(
                    "[ppu-exported-sync] impianto=%s skipped=%s",
                    impianto.nome_impianto,
                    error,
                )
                skipped += 1
                missing.append(impianto.nome_impianto)
                continue

            total_exported_kwh = Decimal(str(exported_kwh))
            logger.warning(
                "[ppu-exported-sync] impianto=%s exported_kwh=%s updated_through=%s",
                impianto.nome_impianto,
                total_exported_kwh,
                end_date,
            )
            with transaction.atomic():
                metriche, _ = FotovoltaicoMetricheTecniche.objects.get_or_create(impianto=impianto)
                metriche.energia_immessa_anno_corrente_kwh = total_exported_kwh
                metriche.energia_immessa_anno_corrente_aggiornata_al = end_date
                metriche.save(
                    update_fields=[
                        "energia_immessa_anno_corrente_kwh",
                        "energia_immessa_anno_corrente_aggiornata_al",
                    ]
                )
            updated += 1

        return SyncOutcome(
            updated=updated,
            skipped=skipped,
            missing=missing,
            window_start=start_of_year,
            window_end=end_date,
        )

    def _sync_portale_source_metrics(
        self,
        *,
        source_name: str,
        queryset,
        window: MetricsWindow | None = None,
    ) -> SyncOutcome:
        active_window = window or rolling_12_months_until_yesterday()
        skipped = 0
        missing: list[str] = []
        results: list[tuple] = []

        impianti = list(queryset)
        logger.warning(
            "[portale-sync] source=%s window=%s..%s impianti=%s",
            source_name,
            active_window.start_date,
            active_window.end_date,
            len(impianti),
        )

        for impianto in impianti:
            sorgenti = self._get_portale_sources(impianto, source_name)
            logger.warning(
                "[portale-sync] impianto=%s id=%s source=%s sorgenti_attive=%s tags=%s codice_impianto=%r",
                impianto.nome_impianto,
                impianto.pk,
                source_name,
                len(sorgenti),
                [getattr(s, "identificativo_esterno", None) for s in sorgenti],
                getattr(impianto, "codice_impianto", None),
            )
            if not sorgenti:
                skipped += 1
                missing.append(impianto.nome_impianto)
                continue

            provider = self.registry.get_provider(source_name)
            try:
                if source_name == self.ISC_SOURCE_NAME:
                    snapshot = self._build_isc_portale_snapshot(
                        impianto,
                        sorgenti,
                        provider,
                        active_window,
                    )
                else:
                    snapshot = provider.fetch_portale_snapshot(impianto, sorgenti[0], active_window)
                metrics = self.calculator.compute(snapshot, active_window)
                logger.warning(
                    "[portale-sync] impianto=%s snapshot energy=%r irradiation=%r peak_power=%r status=%r inv_count=%r inv_ok=%r pr=%r missed=%r eq=%r",
                    impianto.nome_impianto,
                    snapshot.window_energy_kwh,
                    snapshot.window_irradiation_kwh_m2,
                    snapshot.peak_power_kw,
                    snapshot.status,
                    snapshot.inverters_count,
                    snapshot.inverters_ok,
                    metrics.performance_ratio,
                    metrics.missed_production_kwh,
                    metrics.equivalent_hours,
                )
                results.append((impianto, metrics, self._build_portale_sync_note(snapshot, source_name)))
            except NotImplementedError as error:
                logger.warning(
                    "[portale-sync] impianto=%s source=%s skipped_not_implemented=%s",
                    impianto.nome_impianto,
                    source_name,
                    error,
                )
                skipped += 1
                missing.append(impianto.nome_impianto)

        updated = 0
        with transaction.atomic():
            for impianto, metrics, sync_note in results:
                persist_metrics_to_fotovoltaico_metriche_tecniche(
                    impianto,
                    metrics,
                    sync_status=self._get_portale_sync_status(metrics),
                    sync_note=sync_note,
                )
                updated += 1

        return SyncOutcome(
            updated=updated,
            skipped=skipped,
            missing=missing,
            window_start=active_window.start_date,
            window_end=active_window.end_date,
        )

    def _get_portale_isc_queryset(self):
        inverter_filter = Q(
            dispositivi__tipo_dispositivo=ImpiantoDispositivo.TipoDispositivo.INVERTER,
            dispositivi__attivo=True,
        )
        source_filter = Q(
            sorgenti_dati__tipo_sorgente=ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
            sorgenti_dati__nome_sorgente=self.ISC_SOURCE_NAME,
            sorgenti_dati__attiva=True,
        )
        return (
            ImpiantoAnagrafica.objects.filter(
                tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
                potenza_installata_kw__isnull=False,
                potenza_installata_kw__gt=0,
            )
            .select_related("fotovoltaico_metadata")
            .annotate(
                isc_source_count=Count("sorgenti_dati", filter=source_filter, distinct=True),
                inverter_count=Count("dispositivi", filter=inverter_filter, distinct=True),
            )
            .filter(isc_source_count__gt=0, inverter_count__gt=0)
            .prefetch_related(
                Prefetch(
                    "sorgenti_dati",
                    queryset=ImpiantoSorgenteDati.objects.filter(
                        tipo_sorgente=ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
                        nome_sorgente=self.ISC_SOURCE_NAME,
                        attiva=True,
                    ).order_by("id"),
                ),
                Prefetch(
                    "dispositivi",
                    queryset=ImpiantoDispositivo.objects.filter(
                        tipo_dispositivo=ImpiantoDispositivo.TipoDispositivo.INVERTER,
                        attivo=True,
                    ).order_by("id"),
                ),
            )
            .order_by("nome_impianto")
        )

    def _get_portale_saj_queryset(self, include_historical_devices: bool = False):
        energetic_device_filter = Q(
            dispositivi__tipo_dispositivo__in=[
                ImpiantoDispositivo.TipoDispositivo.INVERTER,
                ImpiantoDispositivo.TipoDispositivo.STORAGE_INVERTER,
            ],
        )
        local_device_filter = Q(
            tipo_dispositivo__in=[
                ImpiantoDispositivo.TipoDispositivo.INVERTER,
                ImpiantoDispositivo.TipoDispositivo.STORAGE_INVERTER,
            ],
        )
        if include_historical_devices:
            energetic_device_filter &= (
                Q(dispositivi__attivo=True)
                | Q(dispositivi__data_inizio_monitoraggio__isnull=False)
                | Q(dispositivi__data_fine_monitoraggio__isnull=False)
            )
            local_device_filter &= (
                Q(attivo=True)
                | Q(data_inizio_monitoraggio__isnull=False)
                | Q(data_fine_monitoraggio__isnull=False)
            )
        else:
            energetic_device_filter &= Q(dispositivi__attivo=True)
            local_device_filter &= Q(attivo=True)
        source_filter = Q(
            sorgenti_dati__tipo_sorgente=ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
            sorgenti_dati__nome_sorgente=self.SAJ_SOURCE_NAME,
            sorgenti_dati__attiva=True,
        )
        return (
            ImpiantoAnagrafica.objects.filter(
                tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
                potenza_installata_kw__isnull=False,
                potenza_installata_kw__gt=0,
            )
            .exclude(codice_impianto__isnull=True)
            .exclude(codice_impianto="")
            .select_related("fotovoltaico_metadata", "fotovoltaico_metriche_tecniche")
            .annotate(
                saj_source_count=Count("sorgenti_dati", filter=source_filter, distinct=True),
                energetic_device_count=Count("dispositivi", filter=energetic_device_filter, distinct=True),
            )
            .filter(saj_source_count__gt=0, energetic_device_count__gt=0)
            .prefetch_related(
                Prefetch(
                    "sorgenti_dati",
                    queryset=ImpiantoSorgenteDati.objects.filter(
                        tipo_sorgente=ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
                        nome_sorgente=self.SAJ_SOURCE_NAME,
                        attiva=True,
                    ).order_by("id"),
                ),
                Prefetch(
                    "dispositivi",
                    queryset=ImpiantoDispositivo.objects.filter(local_device_filter).order_by("id"),
                ),
            )
            .order_by("nome_impianto")
        )

    @staticmethod
    def _get_portale_sources(impianto, source_name: str):
        return [
            sorgente
            for sorgente in impianto.sorgenti_dati.all()
            if sorgente.nome_sorgente == source_name and sorgente.attiva
        ]

    def _build_isc_portale_snapshot(self, impianto, sorgenti, provider, active_window):
        logger.warning(
            "[isc-aggregate] impianto=%s sorgenti=%s",
            impianto.nome_impianto,
            [
                {
                    "id": sorgente.id,
                    "identificativo_esterno": getattr(sorgente, "identificativo_esterno", None),
                    "nome_riferimento_esterno": getattr(sorgente, "nome_riferimento_esterno", None),
                }
                for sorgente in sorgenti
            ],
        )
        snapshots = [
            provider.fetch_portale_snapshot(impianto, sorgente, active_window)
            for sorgente in sorgenti
        ]
        for index, snapshot in enumerate(snapshots, start=1):
            logger.warning(
                "[isc-aggregate] impianto=%s snapshot_index=%s plant=%s source_identifier=%r energy=%r irradiation=%r peak_power=%r status=%r inv_count=%r inv_ok=%r",
                impianto.nome_impianto,
                index,
                snapshot.plant_name,
                snapshot.raw_payload.get("source_identifier"),
                snapshot.window_energy_kwh,
                snapshot.window_irradiation_kwh_m2,
                snapshot.peak_power_kw,
                snapshot.status,
                snapshot.inverters_count,
                snapshot.inverters_ok,
            )
        if len(snapshots) == 1:
            logger.warning("[isc-aggregate] impianto=%s single_snapshot_no_merge", impianto.nome_impianto)
            return snapshots[0]
        return self._aggregate_isc_snapshots(impianto, snapshots)

    @staticmethod
    def _aggregate_isc_snapshots(impianto, snapshots) -> ProviderPlantSnapshot:
        first_snapshot = snapshots[0]

        total_peak_power = sum(
            snapshot.peak_power_kw
            for snapshot in snapshots
            if snapshot.peak_power_kw is not None
        )
        peak_power_kw = total_peak_power or None

        window_energy_kwh = sum(
            snapshot.window_energy_kwh
            for snapshot in snapshots
            if snapshot.window_energy_kwh is not None
        )

        inverters_count = sum(
            snapshot.inverters_count
            for snapshot in snapshots
            if snapshot.inverters_count is not None
        )
        inverters_ok = sum(
            snapshot.inverters_ok
            for snapshot in snapshots
            if snapshot.inverters_ok is not None
        )
        coverage = None
        if inverters_count:
            coverage = round(inverters_ok / inverters_count, 4)

        available_irradiation = [
            (snapshot.window_irradiation_kwh_m2, snapshot.peak_power_kw)
            for snapshot in snapshots
            if snapshot.window_irradiation_kwh_m2 is not None
        ]
        irradiation_kwh_m2 = None
        if available_irradiation:
            weighted_power = sum(
                power
                for _, power in available_irradiation
                if power is not None and not isclose(power, 0.0)
            )
            if weighted_power:
                irradiation_kwh_m2 = sum(
                    irradiation * power
                    for irradiation, power in available_irradiation
                    if power is not None and not isclose(power, 0.0)
                ) / weighted_power
            else:
                irradiation_kwh_m2 = available_irradiation[0][0]

        statuses = {snapshot.status for snapshot in snapshots if snapshot.status}
        if statuses == {"online"}:
            status = "online"
        elif statuses == {"offline"}:
            status = "offline"
        elif statuses:
            status = "warning"
        else:
            status = None

        missing_inverters: list[str] = []
        for snapshot in snapshots:
            for inverter in snapshot.missing_inverters:
                if inverter not in missing_inverters:
                    missing_inverters.append(inverter)

        raw_payload = {
            "aggregated_source_identifiers": [
                snapshot.raw_payload.get("source_identifier")
                for snapshot in snapshots
            ],
            "aggregated_plants": [
                snapshot.raw_payload.get("api_plant", {}).get("ps_name")
                for snapshot in snapshots
            ],
        }

        logger.warning(
            "[isc-aggregate] impianto=%s merged energy=%r irradiation=%r peak_power=%r status=%r inv_count=%r inv_ok=%r coverage=%r plants=%s",
            impianto.nome_impianto,
            window_energy_kwh,
            irradiation_kwh_m2,
            peak_power_kw,
            status,
            inverters_count,
            inverters_ok,
            coverage,
            raw_payload["aggregated_plants"],
        )

        return ProviderPlantSnapshot(
            source_name=first_snapshot.source_name,
            plant_key=str(impianto.pk),
            plant_name=impianto.nome_impianto,
            window_start=first_snapshot.window_start,
            window_end=first_snapshot.window_end,
            peak_power_kw=peak_power_kw,
            status=status,
            daily_equivalent_hours=None,
            total_equivalent_hours=None,
            window_energy_kwh=window_energy_kwh,
            window_irradiation_kwh_m2=irradiation_kwh_m2,
            contractual_pr=first_snapshot.contractual_pr,
            has_weather_station=irradiation_kwh_m2 is not None,
            inverters_count=inverters_count or None,
            inverters_ok=inverters_ok or None,
            coverage=coverage,
            missing_inverters=missing_inverters,
            raw_payload=raw_payload,
        )

    @staticmethod
    def _get_portale_sync_status(metrics) -> str:
        if metrics.performance_ratio is None:
            return FotovoltaicoMetricheTecniche.SyncStatus.PARTIAL
        return FotovoltaicoMetricheTecniche.SyncStatus.OK

    @staticmethod
    def _build_portale_sync_note(snapshot, source_name: str) -> str:
        notes: list[str] = []
        if not snapshot.has_weather_station:
            if source_name == MetricsSyncService.ISC_SOURCE_NAME:
                notes.append("Weather station ISC non trovata: PR non calcolabile.")
            elif source_name == MetricsSyncService.SAJ_SOURCE_NAME:
                selection_mode = snapshot.raw_payload.get("selection_mode")
                if selection_mode == "storage_inverter_fallback":
                    notes.append(
                        "Fonte energia SAJ: storage_inverter (fallback). Weather station non disponibile."
                    )
                else:
                    notes.append("Fonte energia SAJ: inverter. Weather station non disponibile.")
        if snapshot.inverters_count and snapshot.inverters_ok is not None:
            notes.append(
                f"Device energetici locali: {snapshot.inverters_count}; device con dati letti: {snapshot.inverters_ok}."
            )
        if snapshot.missing_inverters:
            notes.append(f"Device senza dati: {', '.join(snapshot.missing_inverters)}.")
        return " ".join(notes)
