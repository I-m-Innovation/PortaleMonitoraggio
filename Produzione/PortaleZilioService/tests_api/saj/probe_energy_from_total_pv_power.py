"""Read SAJ totalPVPower samples for two fixed test dates.

Example:
    python Produzione/PortaleZilioService/tests_api/saj/probe_energy_from_total_pv_power.py ^
        --device-sn C6V9104J2421E01334
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time
from pathlib import Path
import sys

import requests

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client


PROBE_DATES = (date(2026, 1, 1), date(2026, 5, 25))


def _safe_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_latest_total_pv_power(
    headers: dict[str, str],
    device_sn: str,
    probe_date: date,
) -> tuple[str | None, float | None]:
    start_dt = datetime.combine(probe_date, time(0, 0, 0))
    end_dt = datetime.combine(probe_date, time(23, 59, 59))
    response = requests.get(
        f"{saj_client.BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn": device_sn,
            "startTime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": "deviceSn,dataTime,totalPVPower",
        },
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json().get("data") or []
    if not rows:
        return None, None

    latest = max(rows, key=lambda row: str(row.get("dataTime") or ""))
    return latest.get("dataTime"), _safe_float(latest.get("totalPVPower"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read SAJ totalPVPower on fixed test dates.")
    parser.add_argument("--device-sn", required=True, help="SAJ inverter serial number.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    headers = saj_client.build_headers(saj_client.get_token())

    for probe_date in PROBE_DATES:
        data_time, total_pv_power_w = _get_latest_total_pv_power(
            headers,
            args.device_sn,
            probe_date,
        )
        value = f"{total_pv_power_w:.2f}" if total_pv_power_w is not None else "N/D"
        print(
            f"{probe_date.isoformat()} | device={args.device_sn} | "
            f"dataTime={data_time or 'N/D'} | totalPVPower_W={value}"
        )


if __name__ == "__main__":
    main()
