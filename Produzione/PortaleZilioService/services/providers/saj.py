from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging

from django.db.models import Q

from ...API_inverter import saj_client
from ...models import ImpiantoDispositivo
from ..dtos import ProviderPlantSnapshot
from ..windows import MetricsWindow


logger = logging.getLogger(__name__)


class SajMetricsProvider:
    source_name = "Saj - Elekeeper"

    # Configurazione per il calcolo dell'energia immessa per impianto.
    # Chiave: sorgente.identificativo_esterno (codice corto nel DB, es. "121AG2").
    # strategy "ems"    → legge parallYearSellEnergy via emsHistoryData (YTD, si azzera a inizio anno).
    # strategy "device" → delta totalSellEnergy via historyDataCommon (contatore lifetime cumulativo).
    #
    # plant_id = SAJ plantId numerico (necessario per la chiamata emsHistoryData).
    # Fonte: probe_ems_yearly_energy_multi.py (EMS_PLANTS) + shell Django (ImpiantoSorgenteDati).
    # Col Roigo usa "device" perché il suo EMS (M5380J2415071297) risponde con data vuota.
    _SAJ_EXPORTED_ENERGY_CONFIG: dict[str, dict] = {
        "121AG2": {"strategy": "ems",    "plant_id": "26049021801", "ems_sn": "M5530J2541000285"},  # Acquanova 1 - 150 kWp
        "39ERI0": {"strategy": "ems",    "plant_id": "26051023789", "ems_sn": "M5530J2541000287"},  # Acquanova 2 - 90 kWp
        "168UEE": {"strategy": "ems",    "plant_id": "24031286133", "ems_sn": "M5530J2428000038"},  # Zilio Group 281 kW
        "7269Q6": {"strategy": "ems",    "plant_id": "25520042620", "ems_sn": "M5530J2428000023"},  # RCT 2 - Bramante
        "529SGS": {"strategy": "device", "device_sn": "CSV6503J2416E00004"},                        # Col Roigo 50 kWp
    }
    _SAJ_PRODUCED_YTD_CONFIG: dict[str, dict] = {
        "168UEE": {"plant_id": "24031286133", "ems_sn": "M5530J2428000038"},  # Zilio Group
        "7269Q6": {"plant_id": "25520042620", "ems_sn": "M5530J2428000023"},  # RCT 2 - Bramante
    }

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

    def fetch_portale_exported_kwh_for_range(
        self,
        impianto,
        sorgente,
        start_date: date,
        end_date: date,
    ) -> float:
        """Calcola l'energia immessa in rete YTD per il range start_date..end_date.

        Strategia per impianto definita in _SAJ_EXPORTED_ENERGY_CONFIG:
        - "ems":    legge parallYearSellEnergy via emsHistoryData (valore YTD che si
                    azzera a inizio anno — nessun delta necessario).
        - "device": delta totalSellEnergy via historyDataCommon (contatore lifetime,
                    usato per Col Roigo dove l'EMS non restituisce dati).
        """
        window = self._energy_window_for_range(start_date, end_date)
        id_esterno = str(getattr(sorgente, "identificativo_esterno", None) or "")
        config = self._SAJ_EXPORTED_ENERGY_CONFIG.get(id_esterno)
        if config is None:
            raise NotImplementedError(
                f"No exported energy config for plant {impianto.nome_impianto!r} "
                f"(identificativo_esterno={id_esterno!r}). Aggiungere una voce a _SAJ_EXPORTED_ENERGY_CONFIG."
            )

        token = saj_client.get_token()
        headers = saj_client.build_headers(token)
        strategy = config["strategy"]

        logger.warning(
            "[saj-annual-exported] impianto=%s strategy=%s id_esterno=%s range=%s..%s",
            impianto.nome_impianto,
            strategy,
            id_esterno,
            window.start_date,
            window.end_date,
        )

        if strategy == "ems":
            plant_id = config["plant_id"]
            ems_sn = config["ems_sn"]
            # Per i contatori YTD EMS (parallYearSellEnergy) si legge il valore
            # corrente in tempo reale: si usa date.today() invece di window.end_date
            # per garantire di avere almeno un record EMS nelle ore di luce odierne.
            exported_kwh = saj_client.get_ems_year_sell_energy_kwh(
                headers, plant_id, ems_sn, date.today()
            )
            if exported_kwh is None:
                raise NotImplementedError(
                    f"EMS returned no data for plant {impianto.nome_impianto!r} "
                    f"(ems_sn={ems_sn!r}, plant_id={plant_id!r})"
                )
            result = round(exported_kwh, 2)

        else:  # strategy == "device"
            device_sn = config["device_sn"]
            start_dt = datetime.combine(window.start_date, time(23, 59, 59))
            end_dt = datetime.combine(window.end_date, time(23, 59, 59))
            sell_start = saj_client.get_device_sell_energy_snapshot(headers, device_sn, start_dt)
            sell_end = saj_client.get_device_sell_energy_snapshot(headers, device_sn, end_dt)
            logger.warning(
                "[saj-annual-exported] device=%s sell_start=%s sell_end=%s",
                device_sn,
                sell_start,
                sell_end,
            )
            if sell_start is None or sell_end is None:
                raise NotImplementedError(
                    f"No device snapshot data for plant {impianto.nome_impianto!r} "
                    f"(device_sn={device_sn!r})"
                )
            result = round(max(0.0, sell_end - sell_start), 2)

        logger.warning(
            "[saj-annual-exported] impianto=%s exported_kwh=%s",
            impianto.nome_impianto,
            result,
        )
        return result

    def fetch_portale_produced_ytd_kwh(
        self,
        impianto,
        sorgente,
        end_date: date,
    ) -> float:
        """Legge energia prodotta YTD da EMS per impianti configurati.

        Attualmente usato solo per Zilio Group, dove la supervisione SAJ usa
        il dato aggregato EMS e non la somma dei singoli inverter storici.
        """
        id_esterno = str(getattr(sorgente, "identificativo_esterno", None) or "")
        config = self._SAJ_PRODUCED_YTD_CONFIG.get(id_esterno)
        if config is None:
            raise NotImplementedError(
                f"No produced YTD EMS config for plant {impianto.nome_impianto!r} "
                f"(identificativo_esterno={id_esterno!r})"
            )

        token = saj_client.get_token()
        headers = saj_client.build_headers(token)
        produced_kwh = saj_client.get_ems_year_pv_energy_kwh(
            headers,
            config["plant_id"],
            config["ems_sn"],
            end_date,
        )
        if produced_kwh is None:
            raise NotImplementedError(
                f"EMS returned no produced YTD data for plant {impianto.nome_impianto!r} "
                f"(ems_sn={config['ems_sn']!r}, plant_id={config['plant_id']!r})"
            )

        result = round(produced_kwh, 2)
        logger.warning(
            "[saj-annual-produced-ytd] impianto=%s id_esterno=%s produced_kwh=%s end_date=%s",
            impianto.nome_impianto,
            id_esterno,
            result,
            end_date,
        )
        return result

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

        matched_devices, _ = self._get_portale_annual_energy_devices(impianto)
        logger.warning(
            "[saj-annual-energy] impianto=%s range=%s..%s devices=%s",
            impianto.nome_impianto,
            window.start_date,
            window.end_date,
            [device.codice_dispositivo for device in matched_devices],
        )
        energy_kwh, devices_with_data, missing_serials = self._compute_range_daily_energy_kwh(
            selected_devices=matched_devices,
            start_date=window.start_date,
            end_date=window.end_date,
        )
        if devices_with_data == 0 or missing_serials:
            raise NotImplementedError(
                f"No usable SAJ energy data found for plant {impianto.nome_impianto!r}; "
                f"incomplete devices: {', '.join(missing_serials)}"
            )
        logger.warning(
            "[saj-annual-energy] impianto=%s completed energy_kwh=%s range=%s..%s",
            impianto.nome_impianto,
            energy_kwh,
            window.start_date,
            window.end_date,
        )
        return energy_kwh

    def _compute_range_daily_energy_kwh(
        self,
        selected_devices: list,
        start_date: date,
        end_date: date,
    ) -> tuple[float, int, list[str]]:
        total_energy_kwh = 0.0
        devices_with_data = 0
        missing_serials: list[str] = []

        for device in selected_devices:
            device_sn = device.codice_dispositivo
            device_start_date = max(
                start_date,
                getattr(device, "data_inizio_monitoraggio", None) or start_date,
            )
            device_end_date = min(
                end_date,
                getattr(device, "data_fine_monitoraggio", None) or end_date,
            )
            if device_start_date > device_end_date:
                logger.warning(
                    "[saj-annual-energy] device=%s skipped outside_monitoring_period requested=%s..%s monitoring=%s..%s",
                    device_sn,
                    start_date,
                    end_date,
                    getattr(device, "data_inizio_monitoraggio", None),
                    getattr(device, "data_fine_monitoraggio", None),
                )
                continue

            device_total_kwh = 0.0
            days_with_data = 0
            logger.warning(
                "[saj-annual-energy] device=%s start range=%s..%s monitoring=%s..%s",
                device_sn,
                device_start_date,
                device_end_date,
                getattr(device, "data_inizio_monitoraggio", None),
                getattr(device, "data_fine_monitoraggio", None),
            )

            # Itera mese per mese: ogni mese parte con un nuovo login SAJ
            # per evitare che la sessione scada o venga throttled su range lunghi.
            current_month_start = device_start_date.replace(day=1)
            while current_month_start <= device_end_date:
                # Primo giorno del mese successivo e ultimo giorno del mese corrente
                next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
                month_end = next_month_start - timedelta(days=1)

                # Limita ai confini del device
                month_start_clamped = max(current_month_start, device_start_date)
                month_end_clamped = min(month_end, device_end_date)

                # Nuovo login per ogni mese
                token = saj_client.get_token(force_refresh=True)
                headers = saj_client.build_headers(token)
                logger.warning(
                    "[saj-annual-energy] device=%s month=%s fresh_token=True",
                    device_sn,
                    current_month_start.strftime("%Y-%m"),
                )

                month_kwh = 0.0
                current_date = month_start_clamped
                while current_date <= month_end_clamped:
                    daily_energy_kwh = saj_client.get_device_daily_pv_energy_kwh(
                        headers,
                        device_sn,
                        current_date,
                    )
                    if daily_energy_kwh is None:
                        logger.warning(
                            "[saj-annual-energy] device=%s no records date=%s skipped accumulated_kwh=%s",
                            device_sn,
                            current_date,
                            round(device_total_kwh + month_kwh, 2),
                        )
                    else:
                        month_kwh += daily_energy_kwh
                        days_with_data += 1
                        logger.warning(
                            "[saj-annual-energy] device=%s date=%s daily_kwh=%s accumulated_kwh=%s",
                            device_sn,
                            current_date,
                            round(daily_energy_kwh, 2),
                            round(device_total_kwh + month_kwh, 2),
                        )
                    current_date += timedelta(days=1)

                logger.warning(
                    "[saj-annual-energy] device=%s month=%s month_kwh=%s",
                    device_sn,
                    current_month_start.strftime("%Y-%m"),
                    round(month_kwh, 2),
                )
                device_total_kwh += month_kwh
                current_month_start = next_month_start

            if days_with_data == 0:
                missing_serials.append(device_sn)
                continue
            total_energy_kwh += device_total_kwh
            devices_with_data += 1
            logger.warning(
                "[saj-annual-energy] device=%s completed days_with_data=%s energy_kwh=%s",
                device_sn,
                days_with_data,
                round(device_total_kwh, 2),
            )

        return round(total_energy_kwh, 2), devices_with_data, missing_serials

    def _get_portale_energy_device_serials(self, headers: dict[str, str], impianto, plant) -> tuple[list[str], str]:
        matched_devices, selection_mode = self._get_portale_energy_devices(headers, impianto, plant)
        return [device.codice_dispositivo for device in matched_devices], selection_mode

    def _get_portale_annual_energy_devices(self, impianto) -> tuple[list, str]:
        local_devices = list(
            impianto.dispositivi.filter(
                Q(attivo=True)
                | Q(data_inizio_monitoraggio__isnull=False)
                | Q(data_fine_monitoraggio__isnull=False)
            ).order_by("codice_dispositivo")
        )
        return self._select_energy_devices(local_devices)

    def _get_portale_energy_devices(self, headers: dict[str, str], impianto, plant) -> tuple[list, str]:
        local_devices = list(impianto.dispositivi.filter(attivo=True).order_by("codice_dispositivo"))
        selected_devices, selection_mode = self._select_energy_devices(local_devices)
        remote_devices = saj_client.get_devices(headers, plant_id=str(plant["plantId"]))
        remote_serials = {
            str(device.get("deviceSn"))
            for device in remote_devices
            if device.get("deviceSn")
        }

        matched_devices = [
            device
            for device in selected_devices
            if device.codice_dispositivo in remote_serials
        ]
        if not matched_devices:
            raise NotImplementedError(
                f"No matching SAJ devices found for plant {impianto.nome_impianto!r}"
            )
        return matched_devices, selection_mode

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
        id_esterno = str(getattr(sorgente, "identificativo_esterno", None) or "")
        config_plant_id = (self._SAJ_EXPORTED_ENERGY_CONFIG.get(id_esterno) or {}).get("plant_id")
        candidates = {
            self._normalize(id_esterno),
            self._normalize(getattr(impianto, "codice_impianto", None)),
            self._normalize(getattr(sorgente, "nome_riferimento_esterno", None)),
            self._normalize(getattr(impianto, "tag_impianto", None)),
            self._normalize(getattr(impianto, "nome_impianto", None)),
            self._normalize(config_plant_id),
        }
        candidates.discard("")
        for attempt in range(1, 3):
            plants = saj_client.get_plants(headers)
            logger.warning(
                "[saj-plant-match] impianto=%s attempt=%s candidates=%s remote_plants_count=%s remote_plants=%s",
                impianto.nome_impianto,
                attempt,
                sorted(candidates),
                len(plants),
                [
                    {
                        "plantId": plant.get("plantId"),
                        "plantName": plant.get("plantName"),
                    }
                    for plant in plants
                ],
            )
            for plant in plants:
                plant_keys = {
                    self._normalize(str(plant.get("plantId"))),
                    self._normalize(plant.get("plantName")),
                }
                if candidates & plant_keys:
                    logger.warning(
                        "[saj-plant-match] impianto=%s matched_plant_id=%s matched_plant_name=%s attempt=%s",
                        impianto.nome_impianto,
                        plant.get("plantId"),
                        plant.get("plantName"),
                        attempt,
                    )
                    return plant
            if attempt == 1:
                logger.warning("[saj-plant-match] impianto=%s no_match retrying", impianto.nome_impianto)
        logger.warning("[saj-plant-match] impianto=%s no_match", impianto.nome_impianto)
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
