from __future__ import annotations

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
from .dtos import SyncOutcome
from .persistence import (
    persist_metrics_to_fotovoltaico_metriche_tecniche,
    persist_metrics_to_impianto,
)
from .registry import ProviderRegistry
from .windows import MetricsWindow, rolling_12_months_until_yesterday


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

        for impianto in queryset:
            sorgente = self._get_portale_source(impianto)
            if sorgente is None:
                skipped += 1
                missing.append(impianto.nome_impianto)
                continue

            provider = self.registry.get_provider(sorgente.nome_sorgente)
            try:
                snapshot = provider.fetch_portale_snapshot(impianto, sorgente, active_window)
                metrics = self.calculator.compute(snapshot, active_window)
                results.append((impianto, metrics, self._build_portale_sync_note(snapshot, source_name)))
            except NotImplementedError:
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
            .exclude(codice_impianto__isnull=True)
            .exclude(codice_impianto="")
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

    def _get_portale_saj_queryset(self):
        energetic_device_filter = Q(
            dispositivi__tipo_dispositivo__in=[
                ImpiantoDispositivo.TipoDispositivo.INVERTER,
                ImpiantoDispositivo.TipoDispositivo.STORAGE_INVERTER,
            ],
            dispositivi__attivo=True,
        )
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
                    queryset=ImpiantoDispositivo.objects.filter(
                        tipo_dispositivo__in=[
                            ImpiantoDispositivo.TipoDispositivo.INVERTER,
                            ImpiantoDispositivo.TipoDispositivo.STORAGE_INVERTER,
                        ],
                        attivo=True,
                    ).order_by("id"),
                ),
            )
            .order_by("nome_impianto")
        )

    @staticmethod
    def _get_portale_source(impianto):
        sorgenti = list(impianto.sorgenti_dati.all())
        if not sorgenti:
            return None
        return sorgenti[0]

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
