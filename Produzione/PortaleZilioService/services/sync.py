from __future__ import annotations

from django.db import transaction

from MonitoraggioImpianti.models import Impianto

from .calculators import DefaultMetricsCalculator
from .dtos import SyncOutcome
from .persistence import persist_metrics_to_impianto
from .registry import ProviderRegistry
from .windows import MetricsWindow, rolling_12_months_until_yesterday


class MetricsSyncService:
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
