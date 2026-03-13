from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Tuple

from API_iSolarCloud import _post, login_ISC
from api_config import ENDPOINTS, LOGIN_PARAMS, PAGE_SIZE, DEVICE_PAGE_SIZE


def _load_sample_plant() -> Dict[str, Any]:
    path = Path("plants_data.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    plants = data.get("plants", [])
    with_inverters = [p for p in plants if p.get("inverters")]
    if not with_inverters:
        raise RuntimeError("No plant with inverters found in plants_data.json")
    return with_inverters[0]


def _build_payloads(token: str, sample_plant: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    plant_id = sample_plant["plant_id"]
    inverter_keys = sample_plant.get("inverters", [])
    first_inv = inverter_keys[0]

    now = datetime.now()
    start_ts = (now - timedelta(hours=1)).strftime("%Y%m%d%H%M%S")
    end_ts = now.strftime("%Y%m%d%H%M%S")
    today = now.strftime("%Y%m%d")

    return {
        "plant_list": {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "curPage": "1",
            "size": str(PAGE_SIZE),
        },
        "device_list": {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "ps_id": plant_id,
            "curPage": "1",
            "size": str(DEVICE_PAGE_SIZE),
        },
        "plant_detail": {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "ps_id": plant_id,
        },
        "plant_data": {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "ps_id": plant_id,
            "ps_key_list": inverter_keys,
            "start_time_stamp": start_ts,
            "end_time_stamp": end_ts,
            "points": "p24",
        },
        "inv_status": {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "ps_key_list": inverter_keys,
        },
        "plant_data_daily": {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "query_type": "1",
            "data_type": "2",
            "ps_key_list": [first_inv],
            "data_point": "p1",
            "start_time": today,
            "end_time": today,
            "order": 0,
        },
        "batch_ps_detail": {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "ps_ids": str(plant_id),
            "is_get_ps_remarks": "1",
            "lang": "_en_US",
        },
    }


def _probe_endpoint(endpoint_key: str, payload: Dict[str, Any]) -> Tuple[str, str]:
    try:
        resp = _post(endpoint_key, payload)
        return "ACCESSIBLE", f"result_code={resp.get('result_code')} result_msg={resp.get('result_msg')}"
    except Exception as exc:
        return "FAIL", str(exc)


def main() -> None:
    print("== iSolarCloud Endpoint Probe ==")
    print(f"Configured endpoints: {len(ENDPOINTS)}")

    login_resp = login_ISC()
    token = login_resp.get("result_data", {}).get("token")
    if not token:
        raise RuntimeError("Login failed: missing token")
    print("Login: ACCESSIBLE")

    sample_plant = _load_sample_plant()
    payloads = _build_payloads(token, sample_plant)

    print(f"Sample plant: {sample_plant.get('plant_name')} ({sample_plant.get('plant_id')})")
    print("")
    print(f"{'ENDPOINT KEY':<18} {'STATUS':<12} DETAILS")
    print("-" * 90)

    # login is already tested above
    print(f"{'login':<18} {'ACCESSIBLE':<12} result_code={login_resp.get('result_code')} result_msg={login_resp.get('result_msg')}")

    for key in ENDPOINTS:
        if key == "login":
            continue
        payload = payloads.get(key)
        if payload is None:
            print(f"{key:<18} {'SKIPPED':<12} no payload builder")
            continue
        status, details = _probe_endpoint(key, payload)
        print(f"{key:<18} {status:<12} {details}")


if __name__ == "__main__":
    main()
