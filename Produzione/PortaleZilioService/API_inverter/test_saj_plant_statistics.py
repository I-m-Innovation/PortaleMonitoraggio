from __future__ import annotations

import argparse
import json
from datetime import datetime

import requests

from saj_client import BASE_URL, build_headers, get_devices, get_token


def get_plant_statistics(headers: dict[str, str], plant_id: str, client_date: str) -> dict:
    response = requests.get(
        f"{BASE_URL}/open/api/plant/getPlantStatisticsData",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        params={
            "plantId": plant_id,
            "clientDate": client_date,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_device_history(
    headers: dict[str, str],
    device_sn: str,
    start_time: str,
    end_time: str,
    fields: str | None = None,
) -> dict:
    params = {
        "deviceSn": device_sn,
        "startTime": start_time,
        "endTime": end_time,
    }
    if fields:
        params["fields"] = fields

    response = requests.get(
        f"{BASE_URL}/open/api/device/historyDataCommon",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _safe_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sum_pv_channels(row: dict) -> float | None:
    total = 0.0
    found = False
    for idx in range(1, 17):
        value = _safe_float(row.get(f"pv{idx}power"))
        if value is not None:
            total += value
            found = True
    return total if found else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe SAJ endpoints for plant statistics and device history."
    )
    parser.add_argument(
        "--endpoint",
        choices=["plant-stats", "device-history", "plant-devices-compare"],
        default="device-history",
        help="Which SAJ endpoint to probe.",
    )
    parser.add_argument("--plant-id", default="24110165619", help="SAJ plantId to query.")
    parser.add_argument("--device-sn", default="CSV6503J2416E00004", help="SAJ device serial number.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Date in YYYY-MM-DD format.")
    parser.add_argument(
        "--times",
        nargs="+",
        default=["00:00:00", "06:00:00", "09:00:00", "09:25:00", "12:00:00", "18:00:00", "23:55:00"],
        help="List of HH:MM:SS times to test on the given date for plant-stats mode.",
    )
    parser.add_argument(
        "--start-time",
        default=None,
        help="device-history mode: start time in 'YYYY-MM-DD HH:MM:SS'.",
    )
    parser.add_argument(
        "--end-time",
        default=None,
        help="device-history mode: end time in 'YYYY-MM-DD HH:MM:SS'.",
    )
    parser.add_argument(
        "--fields",
        default="deviceSn,dataTime,totalPVPower,todayPvEnergy,totalPvEnergy,pv1power,pv2power,pv3power,pv4power,pv5power,pv6power,pv7power,pv8power,pv9power,pv10power,pv11power,pv12power,pv13power,pv14power,pv15power,pv16power",
        help="device-history mode: comma-separated fields parameter.",
    )
    parser.add_argument(
        "--target-time",
        default=None,
        help="plant-devices-compare mode: target timestamp 'YYYY-MM-DD HH:MM:SS' to compare nearest samples.",
    )
    parser.add_argument(
        "--dump-json",
        action="store_true",
        help="Print the full JSON payload for each request.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = get_token()
    headers = build_headers(token)

    if args.endpoint == "plant-stats":
        print("== SAJ getPlantStatisticsData probe ==")
        print(f"plant_id: {args.plant_id}")
        print(f"date: {args.date}")
        print("")
        print(
            f"{'clientDate':<20} {'code':<6} {'dataTime':<20} {'powerNow':<12} "
            f"{'todayPvEnergy':<14} {'deviceStatus':<12} {'deviceSnList'}"
        )
        print("-" * 120)

        for probe_time in args.times:
            client_date = f"{args.date} {probe_time}"
            payload = get_plant_statistics(headers, args.plant_id, client_date)
            data = payload.get("data") or {}
            device_sn_list = ",".join(data.get("deviceSnList", []) or [])
            print(
                f"{client_date:<20} "
                f"{str(payload.get('code')):<6} "
                f"{str(data.get('dataTime', '')):<20} "
                f"{str(data.get('powerNow', '')):<12} "
                f"{str(data.get('todayPvEnergy', '')):<14} "
                f"{str(data.get('deviceStatus', '')):<12} "
                f"{device_sn_list}"
            )
            if args.dump_json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                print("-" * 120)
        return

    if args.endpoint == "plant-devices-compare":
        start_time = args.start_time or f"{args.date} 00:00:00"
        end_time = args.end_time or f"{args.date} 23:55:00"
        target_time = datetime.strptime(
            args.target_time or f"{args.date} 10:10:00",
            "%Y-%m-%d %H:%M:%S",
        )

        devices = get_devices(headers, plant_id=args.plant_id)
        print("== SAJ plant devices compare ==")
        print(f"plant_id: {args.plant_id}")
        print(f"target_time: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"window: {start_time} -> {end_time}")
        print(f"devices_found: {len(devices)}")
        print("")
        print(
            f"{'deviceSn':<22} {'deviceType':<12} {'nearestDataTime':<20} "
            f"{'delta_s':<10} {'totalPVPower_W':<15} {'sumPvPower_W':<15} {'todayPvEnergy'}"
        )
        print("-" * 130)

        for device in devices:
            device_sn = str(device.get("deviceSn", ""))
            payload = get_device_history(
                headers,
                device_sn=device_sn,
                start_time=start_time,
                end_time=end_time,
                fields=args.fields,
            )
            rows = payload.get("data") or []
            parsed_rows = []
            for row in rows:
                dt_raw = row.get("dataTime")
                if not dt_raw:
                    continue
                try:
                    dt = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                parsed_rows.append((dt, row))

            if not parsed_rows:
                print(
                    f"{device_sn:<22} {str(device.get('deviceType', '')):<12} "
                    f"{'NO_DATA':<20} {'':<10} {'':<15} {'':<15} {''}"
                )
                continue

            nearest_dt, nearest_row = min(
                parsed_rows,
                key=lambda item: abs((item[0] - target_time).total_seconds()),
            )
            delta_s = int((nearest_dt - target_time).total_seconds())
            total_pv_power = _safe_float(nearest_row.get("totalPVPower"))
            sum_pv_power = _sum_pv_channels(nearest_row)
            today_pv_energy = nearest_row.get("todayPvEnergy", "")

            print(
                f"{device_sn:<22} "
                f"{str(device.get('deviceType', '')):<12} "
                f"{nearest_dt.strftime('%Y-%m-%d %H:%M:%S'):<20} "
                f"{delta_s:<10} "
                f"{str(total_pv_power):<15} "
                f"{str(sum_pv_power):<15} "
                f"{today_pv_energy}"
            )
            if args.dump_json:
                print(json.dumps(nearest_row, ensure_ascii=False, indent=2))
                print("-" * 130)
        return

    start_time = args.start_time or f"{args.date} 00:00:00"
    end_time = args.end_time or f"{args.date} 23:55:00"

    print("== SAJ historyDataCommon probe ==")
    print(f"device_sn: {args.device_sn}")
    print(f"start_time: {start_time}")
    print(f"end_time: {end_time}")
    print(f"fields: {args.fields}")
    print("")

    payload = get_device_history(
        headers,
        device_sn=args.device_sn,
        start_time=start_time,
        end_time=end_time,
        fields=args.fields,
    )
    rows = payload.get("data") or []
    print(f"code: {payload.get('code')}")
    print(f"msg: {payload.get('msg')}")
    print(f"records: {len(rows)}")
    print("")
    print(
        f"{'dataTime':<20} {'totalPVPower':<14} {'todayPvEnergy':<14} "
        f"{'totalPvEnergy':<14} {'pv1power':<10} {'pv2power':<10} {'pv3power':<10}"
    )
    print("-" * 110)
    for row in rows[:20]:
        print(
            f"{str(row.get('dataTime', '')):<20} "
            f"{str(row.get('totalPVPower', '')):<14} "
            f"{str(row.get('todayPvEnergy', '')):<14} "
            f"{str(row.get('totalPvEnergy', '')):<14} "
            f"{str(row.get('pv1power', '')):<10} "
            f"{str(row.get('pv2power', '')):<10} "
            f"{str(row.get('pv3power', '')):<10}"
        )
    if len(rows) > 20:
        print(f"... truncated, showing 20 of {len(rows)} rows")
    if args.dump_json:
        print("")
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
