import json
from datetime import date, timedelta

from API_iSolarCloud import login_ISC, _post, load_plants
from api_config import LOGIN_PARAMS


def daterange_chunks(start: date, end: date, max_days: int = 100):
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=max_days - 1), end)
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def extract_numeric(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except Exception:
            return None
    if isinstance(v, dict):
        if "value" in v:
            return extract_numeric(v["value"])
    return None


def sum_p1_from_result_data(obj, data_type_key: str = "2") -> float:
    total_wh = 0.0

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "p1":
                # Common shape:
                # "p1": [{"2":"123.4","time_stamp":"20250101"}, ...]
                if isinstance(value, list):
                    for rec in value:
                        if isinstance(rec, dict):
                            num = extract_numeric(rec.get(data_type_key))
                            if num is None:
                                num = extract_numeric(rec.get("value"))
                            if num is None:
                                num = extract_numeric(rec.get("p1"))
                            if num is not None:
                                total_wh += num
                else:
                    num = extract_numeric(value)
                    if num is not None:
                        total_wh += num
            total_wh += sum_p1_from_result_data(value, data_type_key=data_type_key)

    elif isinstance(obj, list):
        for item in obj:
            total_wh += sum_p1_from_result_data(item, data_type_key=data_type_key)

    return total_wh


def main():
    token = login_ISC()["result_data"]["token"]
    plants = load_plants("plants_data.json")

    plant_name = "Cavarzan"
    peak_power_kw = plants[plant_name]["peak_power_kw"]
    inverter_keys = plants[plant_name]["inverters"]

    start = date(2026, 1, 1)
    end = date(2026, 3, 11)

    total_wh = 0.0
    chunks = 0

    for s, e in daterange_chunks(start, end, 100):
        chunks += 1
        payload = {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "query_type": "1",
            "data_type": "2",
            "ps_key_list": inverter_keys,
            "data_point": "p1",
            "start_time": s.strftime("%Y%m%d"),
            "end_time": e.strftime("%Y%m%d"),
            "order": 0,
            "is_get_point_dict": "1",
        }

        resp = _post("plant_data_daily", payload)
        result_data = resp.get("result_data", {})

        if chunks == 1:
            print("\nFirst chunk raw result_data preview:")
            print(json.dumps(result_data, ensure_ascii=False, indent=2)[:4000])

        chunk_wh = sum_p1_from_result_data(result_data)
        total_wh += chunk_wh

        print(f"Chunk {chunks}: {s} -> {e} | chunk_wh={chunk_wh:.2f}")

    total_kwh = total_wh / 1000.0
    eq_hours = total_kwh / peak_power_kw if peak_power_kw > 0 else None

    print("\n=== RESULT ===")
    print("plant:", plant_name)
    print("year: 2025")
    print("energy_wh:", round(total_wh, 2))
    print("energy_kwh:", round(total_kwh, 2))
    print("peak_power_kw:", peak_power_kw)
    print("equivalent_hours_2025:", round(eq_hours, 4) if eq_hours is not None else None)


if __name__ == "__main__":
    main()
