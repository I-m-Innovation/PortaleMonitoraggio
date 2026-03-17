from __future__ import annotations


class FallbackMetricsProvider:
    source_name = "fallback"

    def fetch_snapshot(self, impianto, window):
        raise NotImplementedError(f"No provider configured for source {getattr(impianto, 'lettura_dati', None)!r}")
