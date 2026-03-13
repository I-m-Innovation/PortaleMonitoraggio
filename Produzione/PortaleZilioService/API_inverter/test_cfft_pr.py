from __future__ import annotations

import json
from datetime import date
from pathlib import Path

try:
    import os
    import sys

    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PortaleImpianti_project.settings")

    import django
    django.setup()

    from MonitoraggioImpianti.models import Impianto
    from .API_iSolarCloud import (
        _post,
        _sum_point_from_result_data,
        find_weather_station_device,
        load_plants,
        login_ISC,
    )
    from .api_config import LOGIN_PARAMS
except ImportError:
    import os
    import sys

    ROOT_DIR = Path(__file__).resolve().parents[2]
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PortaleImpianti_project.settings")

    import django
    django.setup()

    from MonitoraggioImpianti.models import Impianto
    from API_iSolarCloud import (
        _post,
        _sum_point_from_result_data,
        find_weather_station_device,
        load_plants,
        login_ISC,
    )
    from api_config import LOGIN_PARAMS


DEFAULT_JSON_PATH = Path(__file__).with_name("plants_data.json")
PLANT_NAME = "CFFT"
POINTS = (
    "p2003",
    "p2005",
    "p2006",
    "p2007",
    "p2002",
    "p2001",
    "p10821",
    "p2004",
    "p2008",
)


def _calc_pr(energy_kwh: float, power_kw: float, irradiation_kwh_m2: float | None) -> float | None:
    if not irradiation_kwh_m2 or irradiation_kwh_m2 <= 0 or power_kw <= 0:
        return None
    return energy_kwh / (power_kw * irradiation_kwh_m2)


def main() -> int:
    plants = load_plants(str(DEFAULT_JSON_PATH))
    plant = plants.get(PLANT_NAME)
    if not plant:
        print(f"Plant not found in JSON: {PLANT_NAME}")
        return 1

    login_resp = login_ISC()
    token = login_resp.get("result_data", {}).get("token")
    if not token:
        print("Login failed")
        print(json.dumps(login_resp, ensure_ascii=False, indent=2))
        return 2

    weather_station = find_weather_station_device(token=token, plant_id=int(plant["plant_id"]))
    if not weather_station:
        print("Weather station not found")
        return 3

    impianto = Impianto.objects.get(nome_impianto=PLANT_NAME)
    ps_key = weather_station.get("ps_key")
    energy_kwh = float(impianto.energia_annua_kwh or 0.0)
    power_kw = float(impianto.potenza_installata or 0.0)
    current_year = date.today().year
    end_date = date.today()

    print(f"Plant: {PLANT_NAME}")
    print(f"Plant ID: {plant['plant_id']}")
    print(f"Power kW: {power_kw}")
    print(f"Energy YTD kWh: {energy_kwh}")
    print(f"Weather station ps_key: {ps_key}")
    print("")

    for point in POINTS:
        total_wh_m2 = 0.0
        chunk_start = date(current_year, 1, 1)
        chunk_end = end_date

        payload = {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "query_type": "1",
            "data_type": "2",
            "ps_key_list": [ps_key],
            "data_point": point,
            "start_time": chunk_start.strftime("%Y%m%d"),
            "end_time": chunk_end.strftime("%Y%m%d"),
            "order": 0,
            "is_get_point_dict": "1",
        }

        print(f"=== Testing {point} ===")
        try:
            resp = _post("plant_data_daily", payload)
            result_data = resp.get("result_data", {})
            total_wh_m2 = _sum_point_from_result_data(
                result_data,
                point_key=point,
                data_type_key="2",
            )
            irradiation_kwh_m2 = total_wh_m2 / 1000.0 if total_wh_m2 else None
            pr = _calc_pr(energy_kwh, power_kw, irradiation_kwh_m2)

            print(f"result_code: {resp.get('result_code')}")
            print(f"result_msg: {resp.get('result_msg')}")
            print(f"irradiation_wh_m2: {round(total_wh_m2, 4) if total_wh_m2 else None}")
            print(f"irradiation_kwh_m2: {round(irradiation_kwh_m2, 4) if irradiation_kwh_m2 else None}")
            print(f"pr: {round(pr, 4) if pr is not None else None}")

            preview = json.dumps(result_data, ensure_ascii=False, indent=2)
            print(preview[:1500] + ("\n... [truncated]" if len(preview) > 1500 else ""))
        except Exception as error:
            print(f"ERROR: {type(error).__name__}: {error}")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
