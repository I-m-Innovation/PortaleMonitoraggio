from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from .services.providers.isc import IscMetricsProvider
from .services.providers.saj import SajMetricsProvider


class IscEnergyRangeTests(SimpleTestCase):
    def test_fetch_portale_energy_kwh_for_range_uses_requested_window(self):
        provider = IscMetricsProvider()
        impianto = SimpleNamespace(nome_impianto="Impianto PPU")
        sorgente = SimpleNamespace(identificativo_esterno="isc-1")

        provider._login = Mock(return_value="token")
        provider._find_matching_portale_plant = Mock(return_value={"ps_id": "42"})
        provider._get_portale_inverter_keys = Mock(return_value=["inv-1"])
        provider._fetch_energy_kwh = Mock(return_value=123.45)

        result = provider.fetch_portale_energy_kwh_for_range(
            impianto,
            sorgente,
            date(2026, 1, 1),
            date(2026, 5, 25),
        )

        self.assertEqual(result, 123.45)
        window = provider._fetch_energy_kwh.call_args.kwargs["window"]
        self.assertEqual(window.start_date, date(2026, 1, 1))
        self.assertEqual(window.end_date, date(2026, 5, 25))

    def test_fetch_portale_energy_kwh_for_range_rejects_inverted_dates(self):
        with self.assertRaises(ValueError):
            IscMetricsProvider().fetch_portale_energy_kwh_for_range(
                SimpleNamespace(nome_impianto="Impianto PPU"),
                SimpleNamespace(identificativo_esterno="isc-1"),
                date(2026, 5, 25),
                date(2026, 1, 1),
            )


class SajEnergyRangeTests(SimpleTestCase):
    @patch("PortaleZilioService.services.providers.saj.saj_client.build_headers", return_value={"token": "token"})
    @patch("PortaleZilioService.services.providers.saj.saj_client.get_token", return_value="token")
    def test_fetch_portale_energy_kwh_for_range_uses_requested_window(self, _get_token, _build_headers):
        provider = SajMetricsProvider()
        impianto = SimpleNamespace(nome_impianto="Impianto PPU")
        sorgente = SimpleNamespace(identificativo_esterno="saj-1")

        provider._find_matching_portale_plant = Mock(return_value={"plantId": "42"})
        provider._get_portale_energy_device_serials = Mock(return_value=(["inv-1"], "inverter"))
        provider._compute_window_energy_kwh = Mock(return_value=(456.78, 1, []))

        result = provider.fetch_portale_energy_kwh_for_range(
            impianto,
            sorgente,
            date(2026, 1, 1),
            date(2026, 5, 25),
        )

        self.assertEqual(result, 456.78)
        window = provider._compute_window_energy_kwh.call_args.kwargs["window"]
        self.assertEqual(window.start_date, date(2026, 1, 1))
        self.assertEqual(window.end_date, date(2026, 5, 25))

    def test_fetch_portale_energy_kwh_for_range_rejects_inverted_dates(self):
        with self.assertRaises(ValueError):
            SajMetricsProvider().fetch_portale_energy_kwh_for_range(
                SimpleNamespace(nome_impianto="Impianto PPU"),
                SimpleNamespace(identificativo_esterno="saj-1"),
                date(2026, 5, 25),
                date(2026, 1, 1),
            )
