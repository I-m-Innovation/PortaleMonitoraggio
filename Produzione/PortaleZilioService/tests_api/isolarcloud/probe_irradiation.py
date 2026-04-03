"""Probe irradiazione impianti iSolarCloud - script indipendente.

Run:
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_irradiation.py
"""


from __future__ import annotations
import json
import math # per il confronto con NaN
import requests
from datetime import datetime, timedelta

# Configurazione API iSolarCloud
BASE_URL = "https://gateway.isolarcloud.eu/openapi"

HEADERS = {
    "accept": "application/json",
    "x-access-key": "dpiixeb8cnn34widwp7ihg5nzfb8eybw",
    "sys_code": "901",
    "Content-Type": "application/json",
}

LOGIN_PARAMS = {
    "appkey": "AAA324AF620903ED6ECCDDEA0B6BC866",
    "user_account": "tecnico@zilioservice.com",
    "user_password": "monitorinG_eesco22",
    "lang": "_it_IT",
}

WEATHER_STATION_DEVICE_TYPE = "5"

# Helper http 
def post_json(endpoint: str, payload: dict) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    response = requests.post(url, headers=HEADERS, data = json.dumps(payload), timeout=40)
    response.raise_for_status()
    return response.json()


def login() -> str:
    response = post_json("login", LOGIN_PARAMS)
    token = response.get("result_data", {}).get("token")
    if not token:
        raise ValueError("Login failed, token not found")
    return token

def get_all_plants(token: str) -> list[dict]:
    payload = {
        "appkey": LOGIN_PARAMS["appkey"],
        "token": token,
        "curPage": "1",
        "size": "100",
    }
    resp = post_json("getPowerStationList", payload)
    return resp.get("result_data", {}).get("pageList", [])


def get_all_devices(token: str, plant_id: int) -> list[dict]:
    payload = {
        "appkey": LOGIN_PARAMS["appkey"],
        "token": token,
        "ps_id": plant_id,
        "curPage": "1",
        "size": "50",
    }
    resp = post_json("getDeviceList", payload)
    return resp.get("result_data", {}).get("pageList", [])


def find_weather_station(devices: list[dict]) -> dict | None:
    for device in devices:
        if str(device.get("device_type")) == WEATHER_STATION_DEVICE_TYPE:
            return device
    return None


def _sum_p2005(result_data: dict) -> float:
    """Somma ricorsiva dei valori p2005 (irradiazione) nella risposta ISC."""
    total = 0.0
    if isinstance(result_data, dict):
        for key, value in result_data.items():
            if key == "p2005":
                if isinstance(value, list):
                    for rec in value:
                        if isinstance(rec, dict):
                            raw = rec.get("2") or rec.get("value") or rec.get("p2005")
                            try:
                                total += float(raw) if raw is not None else 0.0
                            except (TypeError, ValueError):
                                pass
                else:
                    try:
                        total += float(value) if value is not None else 0.0
                    except (TypeError, ValueError):
                        pass
            else:
                total += _sum_p2005(value)
    elif isinstance(result_data, list):
        for item in result_data:
            total += _sum_p2005(item)
    return total


def fetch_irradiation_kwh_m2(token: str, ps_key: str, start_date, end_date) -> float:
    """Recupera irradiazione totale in kWh/m² per una finestra temporale.
    Spezza in chunk da 100 giorni (limite API ISC).
    """
    total_wh_m2 = 0.0
    current = start_date
    while current <= end_date:
        chunk_end = min(current + timedelta(days=99), end_date)
        payload = {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "query_type": "1",
            "data_type": "2",
            "ps_key_list": [ps_key],
            "data_point": "p2005",
            "start_time": current.strftime("%Y%m%d"),
            "end_time": chunk_end.strftime("%Y%m%d"),
            "order": 0,
            "is_get_point_dict": "1",
        }
        resp = post_json("getDevicePointsDayMonthYearDataList", payload)
        total_wh_m2 += _sum_p2005(resp.get("result_data", {}))
        current = chunk_end + timedelta(days=1)
    return total_wh_m2 / 1000.0


def main() -> None:
    end_date = datetime.today().date() - timedelta(days=1)
    start_date = end_date.replace(year=end_date.year - 1) + timedelta(days=1)

    print(f"Finestra: {start_date.isoformat()} -> {end_date.isoformat()}")
    print("-" * 80)

    token = login()
    plants = get_all_plants(token)
    print(f"Impianti trovati su ISC: {len(plants)}")
    print("")

    for plant in plants:
        plant_id = int(plant["ps_id"])
        plant_name = plant.get("ps_name") or f"<id={plant_id}>"

        devices = get_all_devices(token, plant_id)
        weather_station = find_weather_station(devices)

        if weather_station is None:
            print(f"{plant_name:<45} nessuna stazione meteo")
            continue

        ps_key = weather_station.get("ps_key")
        if not ps_key:
            print(f"{plant_name:<45} stazione meteo senza ps_key")
            continue

        try:
            irradiation = fetch_irradiation_kwh_m2(token, ps_key, start_date, end_date)
            print(f"{plant_name:<45} irradiazione: {round(irradiation, 2)} kWh/m²")
        except Exception as e:
            print(f"{plant_name:<45} ERRORE: {e}")


if __name__ == "__main__":
    main()

