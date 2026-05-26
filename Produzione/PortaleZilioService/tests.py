from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from .services.providers.isc import IscMetricsProvider
from .services.providers.saj import SajMetricsProvider
from .services.sync import MetricsSyncService


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
        provider._compute_range_daily_energy_kwh = Mock(return_value=(456.78, 1, []))

        result = provider.fetch_portale_energy_kwh_for_range(
            impianto,
            sorgente,
            date(2026, 1, 1),
            date(2026, 5, 25),
        )

        self.assertEqual(result, 456.78)
        call_args = provider._compute_range_daily_energy_kwh.call_args.kwargs
        self.assertEqual(call_args["start_date"], date(2026, 1, 1))
        self.assertEqual(call_args["end_date"], date(2026, 5, 25))

    def test_fetch_portale_energy_kwh_for_range_rejects_inverted_dates(self):
        with self.assertRaises(ValueError):
            SajMetricsProvider().fetch_portale_energy_kwh_for_range(
                SimpleNamespace(nome_impianto="Impianto PPU"),
                SimpleNamespace(identificativo_esterno="saj-1"),
                date(2026, 5, 25),
                date(2026, 1, 1),
            )

    @patch("PortaleZilioService.services.providers.saj.saj_client.get_device_daily_pv_energy_kwh")
    def test_compute_range_daily_energy_sums_devices_and_days(self, get_daily_energy):
        get_daily_energy.side_effect = [1.25, 2.25, 3.50, 4.00]

        result = SajMetricsProvider._compute_range_daily_energy_kwh(
            headers={},
            selected_serials=["inv-1", "inv-2"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
        )

        self.assertEqual(result, (11.0, 2, []))

    @patch("PortaleZilioService.services.providers.saj.saj_client.get_device_daily_pv_energy_kwh")
    def test_compute_range_daily_energy_skips_day_without_records(self, get_daily_energy):
        get_daily_energy.side_effect = [1.25, None, 2.50]

        result = SajMetricsProvider._compute_range_daily_energy_kwh(
            headers={},
            selected_serials=["inv-1"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )

        self.assertEqual(result, (3.75, 1, []))

    @patch("PortaleZilioService.services.providers.saj.saj_client.get_device_daily_pv_energy_kwh")
    def test_compute_range_daily_energy_reports_device_without_any_records(self, get_daily_energy):
        get_daily_energy.side_effect = [None, None]

        result = SajMetricsProvider._compute_range_daily_energy_kwh(
            headers={},
            selected_serials=["inv-1"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
        )

        self.assertEqual(result, (0.0, 0, ["inv-1"]))


class SajAnnualProducedEnergySyncTests(SimpleTestCase):
    def test_initial_sync_starts_at_first_day_of_year(self):
        start_date, base_energy = MetricsSyncService._annual_energy_resume_state(
            None,
            date(2026, 5, 25),
        )

        self.assertEqual(start_date, date(2026, 1, 1))
        self.assertEqual(base_energy, Decimal("0"))

    def test_incremental_sync_starts_after_checkpoint(self):
        metriche = SimpleNamespace(
            energia_prodotta_anno_corrente_kwh=Decimal("100.00"),
            energia_prodotta_anno_corrente_aggiornata_al=date(2026, 5, 23),
        )

        start_date, base_energy = MetricsSyncService._annual_energy_resume_state(
            metriche,
            date(2026, 5, 25),
        )

        self.assertEqual(start_date, date(2026, 5, 24))
        self.assertEqual(base_energy, Decimal("100.00"))

    def test_new_year_resets_accumulated_energy(self):
        metriche = SimpleNamespace(
            energia_prodotta_anno_corrente_kwh=Decimal("999.00"),
            energia_prodotta_anno_corrente_aggiornata_al=date(2025, 12, 31),
        )

        start_date, base_energy = MetricsSyncService._annual_energy_resume_state(
            metriche,
            date(2026, 1, 2),
        )

        self.assertEqual(start_date, date(2026, 1, 1))
        self.assertEqual(base_energy, Decimal("0"))
