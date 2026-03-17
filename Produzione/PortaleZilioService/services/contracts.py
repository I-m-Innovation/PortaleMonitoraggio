from __future__ import annotations

from typing import Protocol

from .dtos import ComputedPlantMetrics, ProviderPlantSnapshot
from .windows import MetricsWindow


class PlantMetricsProvider(Protocol):
    source_name: str

    def fetch_snapshot(self, impianto, window: MetricsWindow) -> ProviderPlantSnapshot:
        """Fetch and normalize raw provider data for one plant and one time window."""


class PlantMetricsCalculator(Protocol):
    def compute(self, snapshot: ProviderPlantSnapshot, window: MetricsWindow) -> ComputedPlantMetrics:
        """Convert normalized provider data into UI/database-ready metrics."""
