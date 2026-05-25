from __future__ import annotations

from datetime import datetime, timedelta
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
