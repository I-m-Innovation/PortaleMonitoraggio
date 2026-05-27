from __future__ import annotations

from datetime import date, timedelta
import logging

from ...models import ImpiantoDispositivo
from ..dtos import ProviderPlantSnapshot
from ..windows import MetricsWindow
from ...API_inverter.API_iSolarCloud import (
    _date_chunks,
    _post,
    _sum_point_from_result_data,
    find_weather_station_device,
    get_all_devices,
    get_all_plants,
    login_ISC,
    WEATHER_STATION_DEVICE_TYPE,
)

try:
    from ...API_inverter.api_config import LOGIN_PARAMS, PAGE_SIZE
except ImportError:
    from API_inverter.api_config import LOGIN_PARAMS, PAGE_SIZE

logger = logging.getLogger(__name__)


class IscMetricsProvider:
    """
    Provider adapter per iSolarCloud.

    Questa classe non scrive su DB e non conosce la UI.
    Converte solo l'API ISC nel DTO interno `ProviderPlantSnapshot`.
    """

    source_name = "API_ISC"
    IRRADIATION_ALIAS_BY_PLANT_NAME = {
        "3F - Plastica": "3F - Ferro",
    }
    SPECIAL_PORTALE_PEAK_POWER_BY_SOURCE = {
        ("3F - Ferro e Plastica", "5079244"): 300.25,
        ("3F - Ferro e Plastica", "5079150"): 351.0,
    }
    SPECIAL_PORTALE_IRRADIATION_SOURCE_BY_SOURCE = {
        ("3F - Ferro e Plastica", "5079244"): "3F - Ferro",
        ("3F - Ferro e Plastica", "5079150"): "3F - Ferro",
    }

    def fetch_snapshot(self, impianto, window: MetricsWindow) -> ProviderPlantSnapshot:
        token = self._login()
        api_plant = self._find_matching_plant(token, impianto)
        if api_plant is None:
            raise NotImplementedError(f"Plant {impianto.nome_impianto!r} not found on iSolarCloud")

        plant_id = int(api_plant["ps_id"])
        plant_name = api_plant.get("ps_name") or impianto.nome_impianto
        peak_power_kw = self._safe_float(api_plant.get("installed_power")) or getattr(impianto, "potenza_installata", None)
        daily_equivalent_hours = self._extract_daily_equivalent_hours(api_plant)
        total_equivalent_hours = getattr(impianto, "ore_equivalenti_totali", None)
        status = "online" if api_plant.get("ps_status") == 1 else "offline"

        devices = get_all_devices(token=token, plant_id=plant_id)
        inverter_keys = [
            d["ps_key"]
            for d in devices
            if d.get("ps_key") and str(d.get("device_type")) != WEATHER_STATION_DEVICE_TYPE
        ]

        energy_kwh = self._fetch_energy_kwh(
            token=token,
            inverter_keys=inverter_keys,
            plant_id=plant_id,
            window=window,
        )
        weather_station = find_weather_station_device(token=token, plant_id=plant_id)
        irradiation_kwh_m2 = self._fetch_irradiation_kwh_m2(
            token=token,
            weather_station=weather_station,
            window=window,
        )

        return ProviderPlantSnapshot(
            source_name=self.source_name,
            plant_key=str(plant_id),
            plant_name=plant_name,
            window_start=window.start_date,
            window_end=window.end_date,
            peak_power_kw=peak_power_kw,
            status=status,
            daily_equivalent_hours=daily_equivalent_hours,
            total_equivalent_hours=total_equivalent_hours,
            window_energy_kwh=energy_kwh,
            window_irradiation_kwh_m2=irradiation_kwh_m2,
            contractual_pr=None,
            has_weather_station=weather_station is not None,
            inverters_count=None,
            inverters_ok=None,
            coverage=None,
            missing_inverters=[],
            raw_payload={
                "api_plant": api_plant,
                "weather_station": weather_station,
            },
        )

    def fetch_portale_snapshot(self, impianto, sorgente, window: MetricsWindow) -> ProviderPlantSnapshot:
        token = self._login()
        api_plant = self._find_matching_portale_plant(token, impianto, sorgente)
        if api_plant is None:
            raise NotImplementedError(
                f"Plant {impianto.nome_impianto!r} not found on iSolarCloud for source "
                f"{getattr(sorgente, 'identificativo_esterno', None)!r}"
            )

        plant_id = int(api_plant["ps_id"])
        plant_name = api_plant.get("ps_name") or impianto.nome_impianto
        installed_power_raw = api_plant.get("installed_power")
        peak_power_kw = self._safe_float(installed_power_raw)
        special_peak_power_kw = self._get_special_portale_peak_power_kw(impianto, sorgente)
        if special_peak_power_kw is not None:
            peak_power_kw = special_peak_power_kw
        if peak_power_kw is None:
            peak_power_kw = self._safe_float(impianto.potenza_installata_kw)
        contractual_pr = self._extract_contractual_pr(impianto)
        status = "online" if api_plant.get("ps_status") == 1 else "offline"

        inverter_keys = self._get_portale_inverter_keys(token, plant_id, impianto, sorgente)
        local_inverter_keys = self._get_local_inverter_keys_for_source(impianto, sorgente)
        local_inverters_count = self._count_local_inverters_for_source(impianto, sorgente)
        logger.warning(
            "[isc-provider] impianto=%s source_identifier=%r plant=%s plant_id=%s installed_power_raw=%r special_peak_power_kw=%r peak_power_kw=%r local_inverters_count=%s local_inverter_keys=%s remote_inverter_keys_count=%s remote_inverter_keys=%s",
            impianto.nome_impianto,
            getattr(sorgente, "identificativo_esterno", None),
            plant_name,
            plant_id,
            installed_power_raw,
            special_peak_power_kw,
            peak_power_kw,
            local_inverters_count,
            local_inverter_keys,
            len(inverter_keys),
            inverter_keys,
        )

        energy_kwh = None
        if inverter_keys:
            energy_kwh = self._fetch_energy_kwh(
                token=token,
                inverter_keys=inverter_keys,
                plant_id=plant_id,
                window=window,
            )
        irradiation_kwh_m2, irradiation_source_name = self._fetch_portale_irradiation_kwh_m2(
            token=token,
            impianto=impianto,
            sorgente=sorgente,
            plant_id=plant_id,
            window=window,
        )

        inverters_ok = len(inverter_keys)
        missing_inverters = local_inverter_keys if not inverter_keys else []
        coverage = None
        if local_inverters_count:
            coverage = round(inverters_ok / local_inverters_count, 4)

        return ProviderPlantSnapshot(
            source_name=getattr(sorgente, "nome_sorgente", self.source_name),
            plant_key=str(getattr(sorgente, "identificativo_esterno", None) or plant_id),
            plant_name=plant_name,
            window_start=window.start_date,
            window_end=window.end_date,
            peak_power_kw=peak_power_kw,
            status=status,
            daily_equivalent_hours=self._extract_daily_equivalent_hours(api_plant),
            total_equivalent_hours=None,
            window_energy_kwh=energy_kwh,
            window_irradiation_kwh_m2=irradiation_kwh_m2,
            contractual_pr=contractual_pr,
            has_weather_station=irradiation_kwh_m2 is not None,
            inverters_count=local_inverters_count,
            inverters_ok=inverters_ok,
            coverage=coverage,
            missing_inverters=missing_inverters,
            raw_payload={
                "api_plant": api_plant,
                "source_identifier": getattr(sorgente, "identificativo_esterno", None),
                "irradiation_source_name": irradiation_source_name,
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
        token = self._login()
        api_plant = self._find_matching_portale_plant(token, impianto, sorgente)
        if api_plant is None:
            raise NotImplementedError(
                f"Plant {impianto.nome_impianto!r} not found on iSolarCloud for source "
                f"{getattr(sorgente, 'identificativo_esterno', None)!r}"
            )

        plant_id = int(api_plant["ps_id"])
        inverter_keys = self._get_portale_inverter_keys(token, plant_id, impianto, sorgente)
        return self._fetch_energy_kwh(
            token=token,
            inverter_keys=inverter_keys,
            plant_id=plant_id,
            window=window,
        )

    def _get_portale_inverter_keys(self, token: str, plant_id: int, impianto, sorgente) -> list[str]:
        devices = get_all_devices(token=token, plant_id=plant_id)
        inverter_keys = [
            device["ps_key"]
            for device in devices
            if device.get("ps_key") and str(device.get("device_type")) != WEATHER_STATION_DEVICE_TYPE
        ]
        if self._is_special_portale_3f_aggregate(impianto):
            local_inverter_keys = self._get_local_inverter_keys_for_source(impianto, sorgente)
            inverter_keys = [
                key
                for key in inverter_keys
                if key in local_inverter_keys
            ]
        return inverter_keys

    @staticmethod
    def _energy_window_for_range(start_date: date, end_date: date) -> MetricsWindow:
        if end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return MetricsWindow(
            start_date=start_date,
            end_date=end_date,
            label=f"energy {start_date.isoformat()} -> {end_date.isoformat()}",
        )

    @staticmethod
    def _is_special_portale_3f_aggregate(impianto) -> bool:
        return getattr(impianto, "nome_impianto", None) == "3F - Ferro e Plastica"

    @classmethod
    def _get_special_portale_peak_power_kw(cls, impianto, sorgente) -> float | None:
        return cls.SPECIAL_PORTALE_PEAK_POWER_BY_SOURCE.get(
            (getattr(impianto, "nome_impianto", None), getattr(sorgente, "identificativo_esterno", None))
        )

    @staticmethod
    def _get_local_inverter_keys_for_source(impianto, sorgente) -> list[str]:
        queryset = impianto.dispositivi.filter(
            tipo_dispositivo=ImpiantoDispositivo.TipoDispositivo.INVERTER,
            attivo=True,
        ).order_by("codice_dispositivo")
        source_identifier = getattr(sorgente, "identificativo_esterno", None)
        if source_identifier:
            queryset = queryset.filter(codice_dispositivo__startswith=f"{source_identifier}_")
        return [device.codice_dispositivo for device in queryset]

    @staticmethod
    def _count_local_inverters_for_source(impianto, sorgente) -> int:
        local_inverter_keys = IscMetricsProvider._get_local_inverter_keys_for_source(impianto, sorgente)
        if local_inverter_keys:
            return len(local_inverter_keys)
        return impianto.dispositivi.filter(
            tipo_dispositivo=ImpiantoDispositivo.TipoDispositivo.INVERTER,
            attivo=True,
        ).count()

    def _login(self) -> str:
        login_resp = login_ISC()
        token = login_resp.get("result_data", {}).get("token")
        if not token:
            raise RuntimeError("Login succeeded but no token was returned")
        return token

    def _find_matching_plant(self, token: str, impianto):
        plants = get_all_plants(token=token, size=PAGE_SIZE)
        candidates = {
            self._normalize(getattr(impianto, "nome_impianto", None)),
            self._normalize(getattr(impianto, "nickname", None)),
            self._normalize(getattr(impianto, "tag", None)),
        }
        for plant in plants:
            plant_keys = {
                self._normalize(plant.get("ps_name")),
                self._normalize(str(plant.get("ps_id"))),
            }
            if candidates & plant_keys:
                return plant
        return None

    def _find_matching_portale_plant(self, token: str, impianto, sorgente):
        plants = get_all_plants(token=token, size=PAGE_SIZE)
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
                self._normalize(plant.get("ps_name")),
                self._normalize(str(plant.get("ps_id"))),
            }
            if candidates & plant_keys:
                return plant
        return None

    def _fetch_energy_kwh(self, token: str, inverter_keys: list[str], plant_id: int, window: MetricsWindow) -> float:
        if not inverter_keys:
            raise NotImplementedError(
                f"No inverter ps_keys found for plant_id={plant_id}. Cannot query energy data."
            )
        total_wh = 0.0
        for chunk_start, chunk_end in _date_chunks(window.start_date, window.end_date, max_days=100):
            payload = {
                "appkey": LOGIN_PARAMS["appkey"],
                "token": token,
                "query_type": "1",
                "data_type": "2",
                "ps_key_list": inverter_keys,
                "data_point": "p1",
                "start_time": chunk_start.strftime("%Y%m%d"),
                "end_time": chunk_end.strftime("%Y%m%d"),
                "order": 0,
                "is_get_point_dict": "1",
            }
            resp = _post("plant_data_daily", payload)
            total_wh += _sum_point_from_result_data(resp.get("result_data", {}), point_key="p1", data_type_key="2")
        return total_wh / 1000.0

    def _fetch_irradiation_kwh_m2(self, token: str, weather_station, window: MetricsWindow) -> float | None:
        if not weather_station:
            return None
        weather_station_ps_key = weather_station.get("ps_key")
        if not weather_station_ps_key:
            return None

        total_irradiation_wh_m2 = 0.0
        for chunk_start, chunk_end in _date_chunks(window.start_date, window.end_date, max_days=100):
            payload = {
                "appkey": LOGIN_PARAMS["appkey"],
                "token": token,
                "query_type": "1",
                "data_type": "2",
                "ps_key_list": [weather_station_ps_key],
                "data_point": "p2005",
                "start_time": chunk_start.strftime("%Y%m%d"),
                "end_time": chunk_end.strftime("%Y%m%d"),
                "order": 0,
                "is_get_point_dict": "1",
            }
            resp = _post("plant_data_daily", payload)
            total_irradiation_wh_m2 += _sum_point_from_result_data(
                resp.get("result_data", {}),
                point_key="p2005",
                data_type_key="2",
            )

        return total_irradiation_wh_m2 / 1000.0

    def _fetch_portale_irradiation_kwh_m2(
        self,
        token: str,
        impianto,
        sorgente,
        plant_id: int,
        window: MetricsWindow,
    ) -> tuple[float | None, str | None]:
        special_source_name = self.SPECIAL_PORTALE_IRRADIATION_SOURCE_BY_SOURCE.get(
            (getattr(impianto, "nome_impianto", None), getattr(sorgente, "identificativo_esterno", None))
        )
        source_name = special_source_name or self.IRRADIATION_ALIAS_BY_PLANT_NAME.get(
            impianto.nome_impianto,
            impianto.nome_impianto,
        )
        source_plant_id = plant_id
        if source_name != impianto.nome_impianto:
            alias_plant = self._find_plant_by_name(token, source_name)
            if alias_plant is None:
                return None, source_name
            source_plant_id = int(alias_plant["ps_id"])

        weather_station = find_weather_station_device(token=token, plant_id=source_plant_id)
        irradiation_kwh_m2 = self._fetch_irradiation_kwh_m2(
            token=token,
            weather_station=weather_station,
            window=window,
        )
        alias_name = source_name if source_name != impianto.nome_impianto else None
        return irradiation_kwh_m2, alias_name

    def _find_plant_by_name(self, token: str, plant_name: str):
        plants = get_all_plants(token=token, size=PAGE_SIZE)
        needle = self._normalize(plant_name)
        for plant in plants:
            plant_keys = {
                self._normalize(plant.get("ps_name")),
                self._normalize(str(plant.get("ps_id"))),
            }
            if needle in plant_keys or any(needle in key for key in plant_keys if key):
                return plant
        return None

    @staticmethod
    def _extract_contractual_pr(impianto) -> float | None:
        metadata = getattr(impianto, "fotovoltaico_metadata", None)
        if metadata is None:
            return None
        pr_value = IscMetricsProvider._safe_float(getattr(metadata, "pr_contrattuale", None))
        if pr_value is None or pr_value <= 0:
            return None
        if pr_value > 1:
            return pr_value / 100.0
        return pr_value

    @staticmethod
    def _normalize(value: str | None) -> str:
        if not value:
            return ""
        return "".join(ch for ch in value.lower() if ch.isalnum())

    @staticmethod
    def _extract_daily_equivalent_hours(api_plant) -> float | None:
        eq_raw = api_plant.get("equivalent_hour", {})
        if isinstance(eq_raw, dict):
            return IscMetricsProvider._safe_float(eq_raw.get("value"))
        return None

    @staticmethod
    def _safe_float(value) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
