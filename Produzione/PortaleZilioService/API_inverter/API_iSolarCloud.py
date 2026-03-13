from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
import requests

try:
    from .api_config import DEVICE_PAGE_SIZE, ENDPOINTS, DEFAULT_HEADERS, LOGIN_PARAMS, PAGE_SIZE, REQUEST_TIMEOUT
except ImportError:
    from api_config import DEVICE_PAGE_SIZE, ENDPOINTS, DEFAULT_HEADERS, LOGIN_PARAMS, PAGE_SIZE, REQUEST_TIMEOUT


WEATHER_STATION_DEVICE_TYPE = "5"
WEATHER_STATION_KEYWORDS = (
    "meteo",
    "meteo station",
    "weather",
    "weather station",
    "meteor",
    "env",
    "sensor box",
)

def load_plants(json_path: str = "plants_data.json") -> Dict[str, Dict[str, Any]]:
    """Load plant config from JSON and return dict indexed by plant_name."""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Plant data file not found: {json_path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    plants: Dict[str, Dict[str, Any]] = {}

    for item in raw.get("plants", []):
        name = item["plant_name"]
        plants[name] = {
            "plant_name": name,
            "plant_id": item["plant_id"],
            "peak_power_kw": item.get("peak_power_kw", 0),
            "inverters": item.get("inverters", []),
        }

    return plants


def _post(endpoint_key: str, payload: Dict[str, Any], timeout: int = REQUEST_TIMEOUT) -> Dict[str, Any]:
    url = ENDPOINTS[endpoint_key]
    response = requests.post(url, headers=DEFAULT_HEADERS, data=json.dumps(payload), timeout=timeout)
    response.raise_for_status()

    data = response.json()
    if isinstance(data, dict) and data.get("result_code") not in (None, "1"):
        raise RuntimeError(f"{endpoint_key}: {data.get('result_msg', 'Unknown API error')}")
    return data


def login_ISC() -> Dict[str, Any]:
    """Authenticate and return raw login response."""
    return _post("login", LOGIN_PARAMS)


def getPlantList(token: str, cur_page: int = 1, size: int = PAGE_SIZE) -> Dict[str, Any]:
    """Fetch one page of plants."""
    payload = {
        "appkey": LOGIN_PARAMS["appkey"],
        "token": token,
        "curPage": str(cur_page),
        "size": str(size),
    }
    return _post("plant_list", payload)


def get_all_plants(token: str, size: int = PAGE_SIZE) -> list[Dict[str, Any]]:
    """Fetch all plants by iterating API pages."""
    first_page = getPlantList(token=token, cur_page=1, size=size)
    first_data = first_page.get("result_data", {})

    plants = list(first_data.get("pageList", []))
    row_count = int(first_data.get("rowCount", len(plants)))

    if row_count <= len(plants):
        return plants

    total_pages = max(1, math.ceil(row_count / size))
    for page in range(2, total_pages + 1):
        resp = getPlantList(token=token, cur_page=page, size=size)
        page_items = resp.get("result_data", {}).get("pageList", [])
        plants.extend(page_items)

    return plants


def get_device_list(
    token: str,
    plant_id: int,
    cur_page: int = 1,
    size: int = DEVICE_PAGE_SIZE,
) -> Dict[str, Any]:
    payload = {
        "appkey": LOGIN_PARAMS["appkey"],
        "token": token,
        "ps_id": plant_id,
        "curPage": str(cur_page),
        "size": str(size),
    }
    return _post("device_list", payload)


def get_all_devices(token: str, plant_id: int, size: int = DEVICE_PAGE_SIZE) -> list[Dict[str, Any]]:
    first_page = get_device_list(token=token, plant_id=plant_id, cur_page=1, size=size)
    first_data = first_page.get("result_data", {})

    devices = list(first_data.get("pageList", []))
    row_count = int(first_data.get("rowCount", len(devices)))

    if row_count <= len(devices):
        return devices

    total_pages = max(1, math.ceil(row_count / size))
    for page in range(2, total_pages + 1):
        resp = get_device_list(token=token, plant_id=plant_id, cur_page=page, size=size)
        page_items = resp.get("result_data", {}).get("pageList", [])
        devices.extend(page_items)

    return devices


def _device_text(device: Dict[str, Any]) -> str:
    parts = [
        device.get("device_name"),
        device.get("device_type"),
        device.get("device_type_name"),
        device.get("device_model"),
        device.get("dev_type_text"),
    ]
    return " ".join(str(part).lower() for part in parts if part)


def find_weather_station_device(token: str, plant_id: int) -> Optional[Dict[str, Any]]:
    devices = get_all_devices(token=token, plant_id=plant_id)

    for device in devices:
        if str(device.get("device_type")) == WEATHER_STATION_DEVICE_TYPE:
            return device

    for device in devices:
        text = _device_text(device)
        if any(keyword in text for keyword in WEATHER_STATION_KEYWORDS):
            return device

    return None


def get_device_point_minute_data(
    token: str,
    ps_key_list: list[str],
    start_time_stamp: str,
    end_time_stamp: str,
    points: str,
    minute_interval: int = 10,
) -> Dict[str, Any]:
    payload = {
        "appkey": LOGIN_PARAMS["appkey"],
        "token": token,
        "ps_key_list": ps_key_list,
        "start_time_stamp": start_time_stamp,
        "end_time_stamp": end_time_stamp,
        "points": points,
        "minute_interval": minute_interval,
        "is_get_data_acquisition_time": "1",
    }
    return _post("plant_data", payload)




def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return _to_float(value)
    if isinstance(value, dict) and "value" in value:
        return _extract_numeric(value["value"])
    return None


def _date_chunks(start: date, end: date, max_days: int = 100):
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=max_days - 1), end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def _sum_point_from_result_data(obj: Any, point_key: str = "p1", data_type_key: str = "2") -> float:
    """
    Sum numeric values for a point in nested iSolarCloud result_data.

    Common shape:
      { "<ps_key>": { "p1": [ {"2":"123.4","time_stamp":"YYYYMMDD"}, ... ] } }
    """
    total = 0.0

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == point_key:
                if isinstance(value, list):
                    for rec in value:
                        if not isinstance(rec, dict):
                            continue
                        num = _extract_numeric(rec.get(data_type_key))
                        if num is None:
                            num = _extract_numeric(rec.get("value"))
                        if num is None:
                            num = _extract_numeric(rec.get(point_key))
                        if num is not None:
                            total += num
                else:
                    num = _extract_numeric(value)
                    if num is not None:
                        total += num

            total += _sum_point_from_result_data(value, point_key=point_key, data_type_key=data_type_key)

    elif isinstance(obj, list):
        for item in obj:
            total += _sum_point_from_result_data(item, point_key=point_key, data_type_key=data_type_key)

    return total
def _extract_inv_year_wh(result_data: Dict[str, Any], inv_key: str, data_point: str = "p88") -> Optional[float]:
    """
    Prova a estrarre il valore annuo (Wh) per un inverter da formati risposta diversi.
    """

    # Caso A: result_data[inv_key] = [ {...}, {...} ]
    node = result_data.get(inv_key)
    if isinstance(node, list):
        vals = []
        for rec in node:
            if isinstance(rec, dict):
                # formato classico: {"p88": "..."}
                v = _to_float(rec.get(data_point))
                if v is not None:
                    vals.append(v)
        if vals:
            return sum(vals)

    # Caso B: result_data["point_data_list"] con ps_key
    point_list = result_data.get("point_data_list")
    if isinstance(point_list, list):
        for item in point_list:
            if not isinstance(item, dict):
                continue
            if item.get("ps_key") != inv_key:
                continue

            # possibili contenitori
            data_list = item.get("data_list") or item.get("list") or item.get("point_data_list") or []
            if isinstance(data_list, list):
                vals = []
                for rec in data_list:
                    if not isinstance(rec, dict):
                        continue
                    v = _to_float(rec.get(data_point))
                    if v is None:
                        # fallback generico
                        v = _to_float(rec.get("value"))
                    if v is not None:
                        vals.append(v)
                if vals:
                    return sum(vals)

    return None


def _sum_minute_point_energy(result_data: Dict[str, Any], ps_key: str, point_key: str, minute_interval: int) -> float:
    total_kwh_m2 = 0.0
    node = result_data.get(ps_key)
    if not isinstance(node, list):
        return 0.0

    for rec in node:
        if not isinstance(rec, dict):
            continue
        value = _extract_numeric(rec.get(point_key))
        if value is None:
            continue
        total_kwh_m2 += (value * (minute_interval / 60.0)) / 1000.0

    return total_kwh_m2


def get_plant_year_performance_ratio(
    token: str,
    plant: Dict[str, Any],
    year: int,
    irradiation_point: str = "p2005",
) -> Dict[str, Any]:
    plant_name = plant.get("plant_name", "Unknown")
    plant_id = plant.get("plant_id")
    plant_power_kw = _to_float(plant.get("peak_power_kw")) or 0.0
    energy_year_kwh = _to_float(plant.get("energy_year_kwh"))
    if not plant_id:
        return {
            "has_weather_station": False,
            "weather_station_ps_key": None,
            "irradiation_year_kwh_m2": None,
            "performance_ratio_year": None,
        }

    weather_station = find_weather_station_device(token=token, plant_id=int(plant_id))
    if not weather_station:
        return {
            "has_weather_station": False,
            "weather_station_ps_key": None,
            "irradiation_year_kwh_m2": None,
            "performance_ratio_year": None,
        }

    weather_station_ps_key = weather_station.get("ps_key")
    if not weather_station_ps_key:
        return {
            "has_weather_station": True,
            "weather_station_ps_key": None,
            "irradiation_year_kwh_m2": None,
            "performance_ratio_year": None,
        }

    total_irradiation_kwh_m2 = 0.0
    start_date = date(year, 1, 1)
    today = date.today()
    end_date = min(date(year, 12, 31), today) if year == today.year else date(year, 12, 31)

    for chunk_start, chunk_end in _date_chunks(start_date, end_date, max_days=100):
        payload = {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "query_type": "1",
            "data_type": "2",
            "ps_key_list": [weather_station_ps_key],
            "data_point": irradiation_point,
            "start_time": chunk_start.strftime("%Y%m%d"),
            "end_time": chunk_end.strftime("%Y%m%d"),
            "order": 0,
            "is_get_point_dict": "1",
        }
        resp = _post("plant_data_daily", payload)
        total_irradiation_kwh_m2 += _sum_point_from_result_data(
            resp.get("result_data", {}),
            point_key=irradiation_point,
            data_type_key="2",
        )
    total_irradiation_kwh_m2 = total_irradiation_kwh_m2 / 1000.0

    if total_irradiation_kwh_m2 > 0 and plant_power_kw > 0 and energy_year_kwh is not None:
        performance_ratio = energy_year_kwh / (plant_power_kw * total_irradiation_kwh_m2)
    else:
        performance_ratio = None

    return {
        "has_weather_station": True,
        "weather_station_ps_key": weather_station_ps_key,
        "irradiation_year_kwh_m2": round(total_irradiation_kwh_m2, 4) if total_irradiation_kwh_m2 > 0 else None,
        "performance_ratio_year": round(performance_ratio, 4) if performance_ratio is not None else None,
    }


def get_plant_year_equivalent_hours(
    token: str, 
    plant: Dict[str, Any], 
    year: int, 
    data_point: str = "p88") -> Dict:
    plant_name = plant.get("plant_name", "Unknown")
    plant_power_kw = _to_float(plant.get("peak_power_kw")) or 0.0
    inverter_keys = plant.get("inverters", [])
    #-------------------
    if not inverter_keys:
        return {
            "plant_name": plant_name,
            "year": year,
            "energy_year_wh": 0.0,
            "energy_year_kwh": 0.0,
            "equivalent_hours_year": None,
            "inverters_count": 0,
            "inverters_ok": 0,
            "missing_inverters": [],
        }
    payload = {
        "appkey": LOGIN_PARAMS["appkey"],
        "token": token,
        "query_type": "3",  # Query Type: (Query Daily Data: day; Query Monthly Data: month; Query Yearly Data: year)
        "data_type" : "4", # total -> 1: Mean; 2: Peak; 3: Trough; 4: Total (only monthly and yearly data has a "total" value). Separate multiple values with commas. If data can be aggregated, then: data_type is 2 when querying daily data, and 4 when querying monthly or yearly data
        "ps_key_list": inverter_keys,  # Device ps_key Collection (devices of the same type)
        "data_point": data_point, # p88, yield this year 
        "start_time": str(year),  # yyyy
        "end_time": str(year),    # yyyy
        "order": 0,
    }
    
    resp = _post("plant_data_daily", payload)
    result_data = resp.get("result_data", {})
    
    total_wh = 0.0
    ok = 0
    missing = []
    
    
    for inv_key in inverter_keys:
        inv_wh = _extract_inv_year_wh(result_data, inv_key, data_point=data_point)
        if inv_wh is None:
            missing.append(inv_key)
            continue
        total_wh += inv_wh
        ok += 1
        
    total_kwh = total_wh / 1000.0
    if plant_power_kw > 0:
        eq_hours = total_kwh / plant_power_kw
    else:
        eq_hours = None
    coverage = (ok / len(inverter_keys)) if inverter_keys else 0.0
    return {
        "plant_name": plant_name,
        "year": year,
        "energy_year_wh": round(total_wh, 3),
        "energy_year_kwh": round(total_kwh, 3),
        "equivalent_hours_year": round(eq_hours, 4) if eq_hours is not None else None,
        "inverters_count": len(inverter_keys),
        "inverters_ok": ok,
        "coverage": round(coverage, 4),
        "missing_inverters": missing,
    }


def save_plants_status(json_path: str = "plants_data.json") -> Dict[str, int]:
    """
    Update plants_data.json with online/offline status for each plant.

    Adds/updates fields:
    - status: "online" | "offline" | "unknown"
    - equivalent_hours_day: float | None
    """
    
    # region --Load existing plant data from JSON
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Plant data file not found: {json_path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    plants_in_file = data.get("plants", [])
    # endregion
    # region --fetch token 
    login_resp = login_ISC()
    token = login_resp.get("result_data", {}).get("token")
    if not token:
        raise RuntimeError("Login succeeded but no token was returned")
    #endregion
    # region --Fetch all plants from API and build status/equivalent_hours dicts
    api_plants = get_all_plants(token=token, size=PAGE_SIZE)
    status_by_id: Dict[int, str] = {}
    eq_hours_by_id: Dict[int, Optional[float]] = {}
    for plant in api_plants:
        ps_id = plant.get("ps_id")
        ps_status = plant.get("ps_status")
        if ps_id is None:
            continue
        plant_id = int(ps_id)
        status_by_id[plant_id] = "online" if ps_status == 1 else "offline"

        eq_raw = plant.get("equivalent_hour", {})
        eq_value = eq_raw.get("value") if isinstance(eq_raw, dict) else None
        try:
            eq_hours_by_id[plant_id] = float(eq_value) if eq_value is not None else None
        except (TypeError, ValueError):
            eq_hours_by_id[plant_id] = None
    # endregion
    # region --Update plant data with status and equivalent hours
    updated = 0
    unknown = 0
    for plant in plants_in_file:
        plant_id = int(plant.get("plant_id"))
        status = status_by_id.get(plant_id, "unknown")
        plant["status"] = status
        plant["equivalent_hours_day"] = eq_hours_by_id.get(plant_id)
        if status == "unknown":
            unknown += 1
        else:
            updated += 1

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"updated": updated, "unknown": unknown, "total": len(plants_in_file)}
    # endregion


def save_plants_year_equivalent_hours(
    year: int,
    json_path: str = "plants_data.json",
    data_point: str = "p1",
) -> Dict[str, int]:
    """
    Compute and save annual equivalent hours for each plant into plants_data.json.

    Adds/updates fields:
    - energy_year_kwh
    - equivalent_hours_year
    - inverters_count
    - inverters_ok
    - coverage
    - missing_inverters
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Plant data file not found: {json_path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    plants_in_file = data.get("plants", [])

    login_resp = login_ISC()
    token = login_resp.get("result_data", {}).get("token")
    if not token:
        raise RuntimeError("Login succeeded but no token was returned")

    updated = 0
    for plant in plants_in_file:
        plant_name = plant.get("plant_name", "Unknown")
        peak_power_kw = _to_float(plant.get("peak_power_kw")) or 0.0
        inverter_keys = plant.get("inverters", []) or []

        if not inverter_keys:
            result = {
                "plant_name": plant_name,
                "year": year,
                "energy_year_kwh": 0.0,
                "equivalent_hours_year": None,
                "inverters_count": 0,
                "inverters_ok": 0,
                "coverage": 0.0,
                "missing_inverters": [],
            }
        else:
            total_wh = 0.0
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

            for chunk_start, chunk_end in _date_chunks(start_date, end_date, max_days=100):
                payload = {
                    "appkey": LOGIN_PARAMS["appkey"],
                    "token": token,
                    "query_type": "1",
                    "data_type": "2",
                    "ps_key_list": inverter_keys,
                    "data_point": data_point,
                    "start_time": chunk_start.strftime("%Y%m%d"),
                    "end_time": chunk_end.strftime("%Y%m%d"),
                    "order": 0,
                    "is_get_point_dict": "1",
                }
                resp = _post("plant_data_daily", payload)
                total_wh += _sum_point_from_result_data(resp.get("result_data", {}), point_key=data_point, data_type_key="2")

            total_kwh = total_wh / 1000.0
            eq_hours = (total_kwh / peak_power_kw) if peak_power_kw > 0 else None
            result = {
                "plant_name": plant_name,
                "year": year,
                "energy_year_kwh": round(total_kwh, 3),
                "equivalent_hours_year": round(eq_hours, 4) if eq_hours is not None else None,
                "inverters_count": len(inverter_keys),
                "inverters_ok": len(inverter_keys),
                "coverage": 1.0,
                "missing_inverters": [],
            }

        plant["energy_year_kwh"] = result["energy_year_kwh"]
        plant["equivalent_hours_year"] = result["equivalent_hours_year"]
        plant["inverters_count"] = result["inverters_count"]
        plant["inverters_ok"] = result["inverters_ok"]
        plant["coverage"] = result["coverage"]
        plant["missing_inverters"] = result["missing_inverters"]
        plant["has_weather_station"] = None
        plant["irradiation_year_kwh_m2"] = None
        plant["performance_ratio_year"] = None

        try:
            pr_result = get_plant_year_performance_ratio(
                token=token,
                plant=plant,
                year=year,
            )
            plant["has_weather_station"] = pr_result["has_weather_station"]
            plant["irradiation_year_kwh_m2"] = pr_result["irradiation_year_kwh_m2"]
            plant["performance_ratio_year"] = pr_result["performance_ratio_year"]
        except Exception:
            try:
                plant["has_weather_station"] = find_weather_station_device(
                    token=token,
                    plant_id=int(plant.get("plant_id")),
                ) is not None
            except Exception:
                plant["has_weather_station"] = None
            plant["irradiation_year_kwh_m2"] = None
            plant["performance_ratio_year"] = None

        updated += 1

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"updated": updated, "total": len(plants_in_file)}


def refresh_plants_snapshot(
    year: int,
    json_path: str = "plants_data.json",
    year_data_point: str = "p1",
) -> Dict[str, Any]:
    """
    Run the full refresh pipeline and return a single summary object.

    Steps:
    1) Save online/offline status + daily equivalent hours
    2) Save yearly energy + yearly equivalent hours
    """
    daily_result = save_plants_status(json_path=json_path)
    yearly_result = save_plants_year_equivalent_hours(
        year=year,
        json_path=json_path,
        data_point=year_data_point,
    )
    return {
        "year": year,
        "daily": daily_result,
        "yearly": yearly_result,
    }
