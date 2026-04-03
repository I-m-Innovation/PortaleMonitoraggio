"""Manual probe for iSolarCloud irradiation on a rolling 12-month window for all plants.

Run:
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_irradiation_all_plants.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter.API_iSolarCloud import find_weather_station_device, get_all_plants, login_ISC
from PortaleZilioService.API_inverter.api_config import PAGE_SIZE
from PortaleZilioService.tests_api.isolarcloud.probe_irradiation import (
    _ensure_utf8_stdout,
    _fetch_irradiation_kwh_m2,
)
from PortaleZilioService.services.windows import rolling_12_months_until_yesterday


def main() -> None:
    _ensure_utf8_stdout()

    login_response = login_ISC()
    token = login_response.get("result_data", {}).get("token")
    if not token:
        raise RuntimeError("Login ISC failed: token missing")

    plants = get_all_plants(token=token, size=PAGE_SIZE)
    window = rolling_12_months_until_yesterday()
    start_date = window.start_date
    end_date = window.end_date

    print("== iSolarCloud irradiation all plants probe ==")
    print(f"plants_found: {len(plants)}")
    print(f"window_start: {start_date.isoformat()}")
    print(f"window_end: {end_date.isoformat()}")
    print("")

    available_count = 0
    missing_station_count = 0

    for plant in plants:
        plant_id = int(plant["ps_id"])
        plant_name = plant.get("ps_name") or "<unnamed plant>"
        weather_station = find_weather_station_device(token=token, plant_id=plant_id)

        if not weather_station:
            missing_station_count += 1
            print(f"{plant_name:<30} | ps_id={plant_id:<8} | no weather station")
            continue

        weather_station_ps_key = weather_station.get("ps_key")
        if not weather_station_ps_key:
            missing_station_count += 1
            print(f"{plant_name:<30} | ps_id={plant_id:<8} | weather station without ps_key")
            continue

        irradiation_kwh_m2 = _fetch_irradiation_kwh_m2(
            token=token,
            weather_station_ps_key=weather_station_ps_key,
            start_date=start_date,
            end_date=end_date,
        )
        available_count += 1
        print(
            f"{plant_name:<30} | ps_id={plant_id:<8} | "
            f"weather_ps_key={weather_station_ps_key:<18} | irradiation_kwh_m2={round(irradiation_kwh_m2, 4)}"
        )

    print("")
    print(f"plants_with_irradiation: {available_count}")
    print(f"plants_without_irradiation: {missing_station_count}")


if __name__ == "__main__":
    main()
