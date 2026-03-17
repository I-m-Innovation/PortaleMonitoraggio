from __future__ import annotations

from datetime import date, timedelta

from ..dtos import ProviderPlantSnapshot
from ..windows import MetricsWindow
from ...API_inverter.API_iSolarCloud import (
    _date_chunks,
    _post,
    _sum_point_from_result_data,
    find_weather_station_device,
    get_all_plants,
    login_ISC,
)

try:
    from ...API_inverter.api_config import LOGIN_PARAMS, PAGE_SIZE
except ImportError:
    from API_inverter.api_config import LOGIN_PARAMS, PAGE_SIZE


class IscMetricsProvider:
    """
    Provider adapter per iSolarCloud.

    Questa classe non scrive su DB e non conosce la UI.
    Converte solo l'API ISC nel DTO interno `ProviderPlantSnapshot`.
    """

    source_name = "API_ISC"

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

        energy_kwh = self._fetch_energy_kwh(
            token=token,
            inverter_keys=[],
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

    def _fetch_energy_kwh(self, token: str, inverter_keys: list[str], plant_id: int, window: MetricsWindow) -> float:
        ps_keys = inverter_keys or [str(plant_id)]
        total_wh = 0.0
        for chunk_start, chunk_end in _date_chunks(window.start_date, window.end_date, max_days=100):
            payload = {
                "appkey": LOGIN_PARAMS["appkey"],
                "token": token,
                "query_type": "1",
                "data_type": "2",
                "ps_key_list": ps_keys,
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
