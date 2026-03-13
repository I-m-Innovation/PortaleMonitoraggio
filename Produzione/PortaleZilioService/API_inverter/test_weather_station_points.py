from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    from .API_iSolarCloud import (
        find_weather_station_device,
        get_device_point_minute_data,
        load_plants,
        login_ISC,
    )
except ImportError:
    from API_iSolarCloud import (
        find_weather_station_device,
        get_device_point_minute_data,
        load_plants,
        login_ISC,
    )


DEFAULT_JSON_PATH = Path(__file__).with_name("plants_data.json")
CANDIDATE_POINTS = ("p2007",)


def _preview_result_data(result_data, limit: int = 1200) -> str:
    text = json.dumps(result_data, ensure_ascii=False, indent=2)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [truncated]"


def main() -> int:
    plants = load_plants(str(DEFAULT_JSON_PATH))

    plant_name = "Videndum F6"
    plant = plants.get(plant_name)
    if not plant:
        print(f"Plant not found in JSON: {plant_name}")
        return 1

    login_resp = login_ISC()
    token = login_resp.get("result_data", {}).get("token")
    if not token:
        print("Login failed: missing token")
        print(json.dumps(login_resp, ensure_ascii=False, indent=2))
        return 2

    weather_station = find_weather_station_device(token=token, plant_id=int(plant["plant_id"]))
    if not weather_station:
        print(f"Weather station not found for plant: {plant_name}")
        return 3

    ps_key = weather_station.get("ps_key")
    print(f"Plant: {plant_name}")
    print(f"Plant ID: {plant['plant_id']}")
    print(f"Weather station ps_key: {ps_key}")
    print(f"Weather station raw: {json.dumps(weather_station, ensure_ascii=False, indent=2)}")

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=2)
    start_ts = start_time.strftime("%Y%m%d%H%M%S")
    end_ts = end_time.strftime("%Y%m%d%H%M%S")

    print(f"Time window: {start_ts} -> {end_ts}")
    print("")

    for point in CANDIDATE_POINTS:
        print(f"=== Testing point {point} ===")
        try:
            resp = get_device_point_minute_data(
                token=token,
                ps_key_list=[ps_key],
                start_time_stamp=start_ts,
                end_time_stamp=end_ts,
                points=point,
                minute_interval=10,
            )
            print(f"result_code: {resp.get('result_code')}")
            print(f"result_msg: {resp.get('result_msg')}")
            print(_preview_result_data(resp.get("result_data")))
        except Exception as error:
            print(f"ERROR: {type(error).__name__}: {error}")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
