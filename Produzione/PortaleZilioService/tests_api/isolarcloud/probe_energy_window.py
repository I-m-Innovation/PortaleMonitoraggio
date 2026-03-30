"""Manual probe for iSolarCloud energy and irradiation on a rolling 12-month window.

Optional:
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_energy_window.py
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_energy_window.py "<plant name or ps_id>"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter.API_iSolarCloud import (
    _date_chunks,
    _last_12_month_window,
    _post,
    _sum_point_from_result_data,
    find_weather_station_device,
    get_all_devices,
    get_all_plants,
    login_ISC,
)
from PortaleZilioService.API_inverter.api_config import LOGIN_PARAMS, PAGE_SIZE


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _pick_plant(plants: list[dict], search_term: str | None) -> dict:
    if search_term:
        needle = _normalize(search_term)
        for plant in plants:
            keys = {
                _normalize(plant.get("ps_name")),
                _normalize(str(plant.get("ps_id"))),
            }
            if needle in keys or any(needle in key for key in keys if key):
                return plant
        raise RuntimeError(f"No ISC plant matched search term: {search_term}")

    for plant in plants:
        if plant.get("ps_id"):
            return plant
    raise RuntimeError("No ISC plant available to probe")


def _fetch_period_point_sum(token: str, ps_key_list: list[str], point: str, start_date, end_date) -> float:
    total = 0.0
    for chunk_start, chunk_end in _date_chunks(start_date, end_date, max_days=100):
        payload = {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "query_type": "1",
            "data_type": "2",
            "ps_key_list": ps_key_list,
            "data_point": point,
            "start_time": chunk_start.strftime("%Y%m%d"),
            "end_time": chunk_end.strftime("%Y%m%d"),
            "order": 0,
            "is_get_point_dict": "1",
        }
        response = _post("plant_data_daily", payload)
        total += _sum_point_from_result_data(
            response.get("result_data", {}),
            point_key=point,
            data_type_key="2",
        )
    return total


def main() -> None:
    search_term = sys.argv[1] if len(sys.argv) > 1 else None

    login_response = login_ISC()
    token = login_response.get("result_data", {}).get("token")
    if not token:
        raise RuntimeError("Login ISC failed: token missing")

    plants = get_all_plants(token=token, size=PAGE_SIZE)
    plant = _pick_plant(plants, search_term)

    plant_id = int(plant["ps_id"])
    plant_name = plant.get("ps_name") or "<unnamed plant>"
    peak_power_kw = float(plant.get("installed_power") or 0.0)

    devices = get_all_devices(token=token, plant_id=plant_id)
    inverter_keys = [device["ps_key"] for device in devices if device.get("ps_key") and str(device.get("device_type")) != "5"]
    weather_station = find_weather_station_device(token=token, plant_id=plant_id)

    start_date, end_date = _last_12_month_window()
    energy_wh = _fetch_period_point_sum(token, inverter_keys, "p1", start_date, end_date) if inverter_keys else 0.0
    energy_kwh = energy_wh / 1000.0

    irradiation_kwh_m2 = None
    if weather_station and weather_station.get("ps_key"):
        irradiation_wh_m2 = _fetch_period_point_sum(
            token,
            [weather_station["ps_key"]],
            "p2005",
            start_date,
            end_date,
        )
        irradiation_kwh_m2 = irradiation_wh_m2 / 1000.0

    equivalent_hours = (energy_kwh / peak_power_kw) if peak_power_kw > 0 else None
    performance_ratio = (
        energy_kwh / (peak_power_kw * irradiation_kwh_m2)
        if peak_power_kw > 0 and irradiation_kwh_m2 and irradiation_kwh_m2 > 0
        else None
    )

    print("== iSolarCloud energy window probe ==")
    print(f"plant_name: {plant_name}")
    print(f"plant_id: {plant_id}")
    print(f"window_start: {start_date.isoformat()}")
    print(f"window_end: {end_date.isoformat()}")
    print(f"peak_power_kw: {peak_power_kw}")
    print(f"inverters_found: {len(inverter_keys)}")
    print(f"weather_station_found: {weather_station is not None}")
    print(f"energy_kwh: {round(energy_kwh, 4)}")
    print(f"equivalent_hours: {round(equivalent_hours, 4) if equivalent_hours is not None else None}")
    print(f"irradiation_kwh_m2: {round(irradiation_kwh_m2, 4) if irradiation_kwh_m2 is not None else None}")
    print(f"performance_ratio: {round(performance_ratio, 4) if performance_ratio is not None else None}")
    print("")
    print("plant_excerpt:")
    print(
        json.dumps(
            {
                "ps_id": plant.get("ps_id"),
                "ps_name": plant.get("ps_name"),
                "ps_status": plant.get("ps_status"),
                "installed_power": plant.get("installed_power"),
                "equivalent_hour": plant.get("equivalent_hour"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if weather_station:
        print("weather_station_excerpt:")
        print(json.dumps(weather_station, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
