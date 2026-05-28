from __future__ import annotations

from datetime import date, datetime, time as datetime_time, timedelta
import threading
import time

import requests


APP_ID = "VH_rQtUpniM"
APP_SECRET = "hiDHa5riPzzTl2vixkVCWh4kpniM6ZrJZxkjunfShyuVrQtUFmPCbKu6oUaw7WAi"
BASE_URL = "https://developer.saj-electric.com/prod-api"
TOKEN_CACHE_SECONDS = 30 * 60

_token_lock = threading.Lock()
_cached_token: str | None = None
_cached_token_valid_until = 0.0


class SajApiError(RuntimeError):
    pass


def get_token() -> str:
    global _cached_token, _cached_token_valid_until

    now = time.monotonic()
    with _token_lock:
        if _cached_token and now < _cached_token_valid_until:
            return _cached_token

        response = requests.get(
            f"{BASE_URL}/open/api/access_token",
            params={"appId": APP_ID, "appSecret": APP_SECRET},
            timeout=30,
        )
        response.raise_for_status()
        token = response.json().get("data", {}).get("access_token")
        if not token:
            raise SajApiError("Missing SAJ access token in API response")

        _cached_token = token
        _cached_token_valid_until = time.monotonic() + TOKEN_CACHE_SECONDS
        return token


def build_headers(token: str) -> dict[str, str]:
    return {
        "accessToken": token,
        "clientSecret": APP_SECRET,
        "content-language": "en_US",
    }


def get_plants(headers: dict[str, str], page_size: int = 100) -> list[dict]:
    response = requests.get(
        f"{BASE_URL}/open/api/developer/plant/page",
        headers=headers,
        params={"appId": APP_ID, "pageSize": page_size, "pageNum": 1},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("rows", [])


def get_devices(headers: dict[str, str], plant_id: str, page_size: int = 100) -> list[dict]:
    response = requests.get(
        f"{BASE_URL}/open/api/developer/device/page",
        headers=headers,
        params={
            "appId": APP_ID,
            "plantId": plant_id,
            "pageSize": page_size,
            "pageNum": 1,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("rows", [])


def get_device_energy_snapshot(headers: dict[str, str], device_sn: str, at_time: datetime) -> float | None:
    response = requests.get(
        f"{BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn": device_sn,
            "startTime": (at_time - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": at_time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        timeout=30,
    )
    response.raise_for_status()
    records = response.json().get("data", [])
    if not records:
        return None
    return float(records[-1].get("totalPvEnergy", 0) or 0)


def get_device_sell_energy_snapshot(headers: dict[str, str], device_sn: str, at_time: datetime) -> float | None:
    """Restituisce il valore cumulativo lifetime di totalSellEnergy (kWh) del
    dispositivo nell'ultima misurazione disponibile nella finestra di 24h che
    termina a `at_time`.

    Usato per calcolare l'energia immessa in rete su un intervallo come delta
    tra due snapshot: sell_end - sell_start.
    """
    response = requests.get(
        f"{BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn": device_sn,
            "startTime": (at_time - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": at_time.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": "deviceSn,dataTime,totalSellEnergy",
        },
        timeout=30,
    )
    response.raise_for_status()
    records = response.json().get("data", [])
    if not records:
        return None
    latest = max(records, key=lambda record: str(record.get("dataTime") or ""))
    value = latest.get("totalSellEnergy")
    return float(value) if value not in (None, "") else None


def get_ems_year_sell_energy_kwh(
    headers: dict[str, str],
    plant_id: str,
    ems_sn: str,
    at_date: date,
) -> float | None:
    """Legge parallYearSellEnergy dall'EMS (energia immessa YTD, si azzera a inizio anno).

    Replica esattamente fetch_ems_year_snapshot_rows del probe: finestra di 10 minuti
    che termina a min(at_date 23:59:59, now). Finestre più lunghe causano codice 10171.
    """
    now = datetime.now()
    end_dt = min(datetime.combine(at_date, datetime_time(23, 59, 59)), now)
    start_dt = end_dt - timedelta(minutes=10)
    response = requests.get(
        f"{BASE_URL}/open/api/device/emsHistoryData",
        headers={
            **headers,
            "Content-Type": "application/json",
            "content-language": "en_US",
        },
        params={
            "startTime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "emsSn": ems_sn,
            "plantId": plant_id,
        },
        timeout=30,
    )
    response.raise_for_status()
    records = response.json().get("data") or []
    if not records:
        return None
    latest = max(records, key=lambda record: str(record.get("dataTime") or ""))
    value = latest.get("parallYearSellEnergy")
    return float(value) if value not in (None, "") else None


def get_device_daily_pv_energy_kwh(headers: dict[str, str], device_sn: str, energy_date: date) -> float | None:
    start_dt = datetime.combine(energy_date, datetime_time(0, 0, 0))
    end_dt = datetime.combine(energy_date, datetime_time(23, 59, 59))
    response = requests.get(
        f"{BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn": device_sn,
            "startTime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": "deviceSn,dataTime,todayPvEnergy",
        },
        timeout=30,
    )
    response.raise_for_status()
    records = response.json().get("data", [])
    if not records:
        return None
    latest = max(records, key=lambda record: str(record.get("dataTime") or ""))
    value = latest.get("todayPvEnergy")
    return float(value) if value not in (None, "") else None
