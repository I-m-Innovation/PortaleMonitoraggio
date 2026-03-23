from __future__ import annotations

from .providers.fallback import FallbackMetricsProvider
from .providers.isc import IscMetricsProvider
from .providers.saj import SajMetricsProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers = {
            "API_ISC": IscMetricsProvider(),
            "iSolarCloud": IscMetricsProvider(),
            "Saj - Elekeeper": SajMetricsProvider(),
            "---": FallbackMetricsProvider(),
            None: FallbackMetricsProvider(),
        }

    def get_provider(self, source_name: str | None):
        return self._providers.get(source_name, FallbackMetricsProvider())
