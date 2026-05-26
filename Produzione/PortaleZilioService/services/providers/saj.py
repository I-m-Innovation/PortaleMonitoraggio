from __future__ import annotations

from datetime import date, datetime, time

from ...API_inverter import saj_client
from ...models import ImpiantoDispositivo
from ..dtos import ProviderPlantSnapshot
from ..windows import MetricsWindow


class SajMetricsProvider:
    source_name = "Saj - Elekeeper"

    def fetch_portale_snapshot(self, impianto, sorgente, window: MetricsWindow) -> ProviderPlantSnapshot:
        token = saj_client.get_token()
        headers = saj_client.build_headers(token)

        plant = self._find_matching_portale_plant(headers, impianto, sorgente)
        if plant is None:
            raise NotImplementedError(
                f"Plant {impianto.nome_impianto!r} not found on SAJ for source "
                f"{getattr(sorgente, 'identificativo_esterno', None)!r}"
            )

        matched_serials, selection_mode = self._get_portale_energy_device_serials(
            headers,
            impianto,
            plant,
        )

        energy_kwh, devices_with_data, missing_serials = self._compute_window_energy_kwh(
            headers=headers,
            selected_serials=matched_serials,
            window=window,
        )
        if devices_with_data == 0:
            raise NotImplementedError(
                f"No usable SAJ energy data found for plant {impianto.nome_impianto!r}"
            )

        coverage = round(devices_with_data / len(matched_serials), 4) if matched_serials else None
        return ProviderPlantSnapshot(
            source_name=self.source_name,
            plant_key=str(getattr(sorgente, "identificativo_esterno", None) or plant["plantId"]),
            plant_name=plant.get("plantName") or impianto.nome_impianto,
            window_start=window.start_date,
            window_end=window.end_date,
            peak_power_kw=self._safe_float(impianto.potenza_installata_kw),
            status=None,
            daily_equivalent_hours=None,
            total_equivalent_hours=None,
            window_energy_kwh=energy_kwh,
            window_irradiation_kwh_m2=None,
            has_weather_station=False,
            inverters_count=len(matched_serials),
            inverters_ok=devices_with_data,
            coverage=coverage,
            missing_inverters=missing_serials,
            raw_payload={
                "selection_mode": selection_mode,
                "selected_serials": matched_serials,
                "remote_plant_id": plant.get("plantId"),
            },
        )

    def fetch_portale_energy_kwh_for_range(
        self,
        impianto,
        sorgente,
        start_date: date,
        end_date: date,
    ) -> float:
        window = self._energy_window_for_range(start_date, end_date)
        token = saj_client.get_token()
        headers = saj_client.build_headers(token)

        plant = self._find_matching_portale_plant(headers, impianto, sorgente)
        if plant is None:
            raise NotImplementedError(
                f"Plant {impianto.nome_impianto!r} not found on SAJ for source "
                f"{getattr(sorgente, 'identificativo_esterno', None)!r}"
            )

        matched_serials, _ = self._get_portale_energy_device_serials(headers, impianto, plant)
        energy_kwh, devices_with_data, _ = self._compute_window_energy_kwh(
            headers=headers,
            selected_serials=matched_serials,
            window=window,
        )
        if devices_with_data == 0:
            raise NotImplementedError(
                f"No usable SAJ energy data found for plant {impianto.nome_impianto!r}"
            )
        return energy_kwh

    def _get_portale_energy_device_serials(self, headers: dict[str, str], impianto, plant) -> tuple[list[str], str]:
        local_devices = list(impianto.dispositivi.filter(attivo=True).order_by("codice_dispositivo"))
        selected_devices, selection_mode = self._select_energy_devices(local_devices)
        remote_devices = saj_client.get_devices(headers, plant_id=str(plant["plantId"]))
        remote_serials = {
            str(device.get("deviceSn"))
            for device in remote_devices
            if device.get("deviceSn")
        }

        matched_serials = [
            device.codice_dispositivo
            for device in selected_devices
            if device.codice_dispositivo in remote_serials
        ]
        if not matched_serials:
            raise NotImplementedError(
                f"No matching SAJ devices found for plant {impianto.nome_impianto!r}"
            )
        return matched_serials, selection_mode

    @staticmethod
    def _energy_window_for_range(start_date: date, end_date: date) -> MetricsWindow:
        if end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return MetricsWindow(
            start_date=start_date,
            end_date=end_date,
            label=f"energy {start_date.isoformat()} -> {end_date.isoformat()}",
        )

    def _find_matching_portale_plant(self, headers: dict[str, str], impianto, sorgente):
        plants = saj_client.get_plants(headers)
        candidates = {
            self._normalize(getattr(sorgente, "identificativo_esterno", None)),
            self._normalize(getattr(impianto, "codice_impianto", None)),
            self._normalize(getattr(sorgente, "nome_riferimento_esterno", None)),
            self._normalize(getattr(impianto, "tag_impianto", None)),
            self._normalize(getattr(impianto, "nome_impianto", None)),
        }
        candidates.discard("")
        for plant in plants:
            plant_keys = {
                self._normalize(str(plant.get("plantId"))),
                self._normalize(plant.get("plantName")),
            }
            if candidates & plant_keys:
                return plant
        return None

    def _select_energy_devices(self, local_devices):
        inverter_devices = [
            device
            for device in local_devices
            if device.tipo_dispositivo == ImpiantoDispositivo.TipoDispositivo.INVERTER
        ]
        if inverter_devices:
            return inverter_devices, "inverter"

        storage_devices = [
            device
            for device in local_devices
            if device.tipo_dispositivo == ImpiantoDispositivo.TipoDispositivo.STORAGE_INVERTER
        ]
        if storage_devices:
            return storage_devices, "storage_inverter_fallback"

        raise NotImplementedError("No usable SAJ devices found")

    def _compute_window_energy_kwh(self, headers: dict[str, str], selected_serials: list[str], window: MetricsWindow):
        start_dt = datetime.combine(window.start_date, time(0, 0, 0))
        end_dt = datetime.combine(window.end_date, time(23, 59, 59))
        total_energy_kwh = 0.0
        devices_with_data = 0
        missing_serials: list[str] = []

        for device_sn in selected_serials:
            start_value = saj_client.get_device_energy_snapshot(headers, device_sn, start_dt)
            end_value = saj_client.get_device_energy_snapshot(headers, device_sn, end_dt)
            if start_value is None or end_value is None:
                missing_serials.append(device_sn)
                continue

            total_energy_kwh += max(0.0, end_value - start_value)
            devices_with_data += 1

        return total_energy_kwh, devices_with_data, missing_serials

    @staticmethod
    def _normalize(value: str | None) -> str:
        if not value:
            return ""
        return "".join(ch for ch in str(value).lower() if ch.isalnum())

    @staticmethod
    def _safe_float(value) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
