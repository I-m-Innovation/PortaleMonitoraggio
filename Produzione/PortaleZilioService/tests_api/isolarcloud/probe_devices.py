"""Manual probe for iSolarCloud devices, with weather station detection.

Optional:
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_devices.py
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_devices.py "<plant name or ps_id>"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter.API_iSolarCloud import (
    WEATHER_STATION_DEVICE_TYPE,
    find_weather_station_device,
    get_all_devices,
    get_all_plants,
    login_ISC,
)
from PortaleZilioService.API_inverter.api_config import PAGE_SIZE


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _match_plants(plants: list[dict], search_term: str | None) -> list[dict]:
    if not search_term:
        return plants
    needle = _normalize(search_term)
    matched = []
    for plant in plants:
        keys = {
            _normalize(plant.get("ps_name")),
            _normalize(str(plant.get("ps_id"))),
        }
        if needle in keys or any(needle in key for key in keys if key):
            matched.append(plant)
    return matched


def main() -> None:
    search_term = sys.argv[1] if len(sys.argv) > 1 else None

    login_response = login_ISC()
    token = login_response.get("result_data", {}).get("token")
    if not token:
        raise RuntimeError("Login ISC failed: token missing")

    all_plants = get_all_plants(token=token, size=PAGE_SIZE)
    plants = _match_plants(all_plants, search_term)

    print("== iSolarCloud devices probe ==")
    print(f"plants_considered: {len(plants)}")
    if search_term:
        print(f"search_term: {search_term}")

    for plant in plants:
        plant_id = int(plant["ps_id"])
        plant_name = plant.get("ps_name") or "<unnamed plant>"
        devices = get_all_devices(token=token, plant_id=plant_id)
        weather_station = find_weather_station_device(token=token, plant_id=plant_id)

        print("")
        print(f"plant_name: {plant_name}")
        print(f"plant_id: {plant_id}")
        print(f"devices_found: {len(devices)}")
        print(f"weather_station_found: {weather_station is not None}")

        for device in devices:
            excerpt = {
                "ps_key": device.get("ps_key"),
                "device_name": device.get("device_name"),
                "device_type": device.get("device_type"),
                "device_type_name": device.get("device_type_name"),
                "is_weather_station_by_type": str(device.get("device_type")) == WEATHER_STATION_DEVICE_TYPE,
            }
            print(json.dumps(excerpt, ensure_ascii=False))

        if weather_station:
            print("weather_station_full:")
            print(json.dumps(weather_station, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
