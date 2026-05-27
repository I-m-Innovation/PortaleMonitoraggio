"""Read and accumulate SAJ todayPvEnergy from 2026-01-01 through today.

Example:
    python Produzione/PortaleZilioService/tests_api/saj/probe_today_pv_energy_dates.py ^
        --device-sn C6V9104J2421E01334
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta
from pathlib import Path
import sys

import requests

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client


START_DATE = date(2026, 1, 1)


def _date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _safe_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_latest_today_pv_energy(
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
            "fields": "deviceSn,dataTime,todayPvEnergy",
        },
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json().get("data") or []
    if not rows:
        return None, None

    latest = max(rows, key=lambda row: str(row.get("dataTime") or ""))
    return latest.get("dataTime"), _safe_float(latest.get("todayPvEnergy"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Accumulate SAJ todayPvEnergy from 2026-01-01 through today."
    )
    parser.add_argument("--device-sn", required=True, help="SAJ inverter serial number.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    headers = saj_client.build_headers(saj_client.get_token())
    total_kwh = 0.0

    for probe_date in _date_range(START_DATE, date.today()):
        data_time, energy_kwh = _get_latest_today_pv_energy(
            headers,
            args.device_sn,
            probe_date,
        )
        if energy_kwh is not None:
            total_kwh += energy_kwh
        value = f"{energy_kwh:.2f}" if energy_kwh is not None else "N/D"
        print(
            f"{probe_date.isoformat()} | device={args.device_sn} | "
            f"dataTime={data_time or 'N/D'} | todayPvEnergy_kWh={value} | "
            f"total_kWh={total_kwh:.2f}"
        )

    print(f"TOTAL_KWH={total_kwh:.2f}")


if __name__ == "__main__":
    main()
