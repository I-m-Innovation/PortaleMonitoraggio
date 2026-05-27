"""Calculate SAJ produced energy for a plant over a requested date range.

Example:
    python Produzione/PortaleZilioService/tests_api/saj/probe_energy_range.py ^
        --device-sn C6V9104J2421E01334 ^
        --start-date 2026-01-01 --end-date 2026-05-25
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import sys
import time
from pathlib import Path

import requests

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client


def _date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _get_daily_produced_energy_kwh(
    headers: dict[str, str],
    device_sn: str,
    probe_date: date,
) -> float | None:
    end_dt = datetime.combine(probe_date, datetime.max.time()).replace(microsecond=0)
    response = requests.get(
        f"{saj_client.BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn": device_sn,
            "startTime": (end_dt - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        },
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json().get("data") or []
    if not rows:
        return None

    latest = max(rows, key=lambda row: str(row.get("dataTime") or ""))
    value = latest.get("todayPvEnergy")
    return float(value) if value not in (None, "") else None


def calculate_energy_kwh(
    device_sns: list[str],
    start_date: date,
    end_date: date,
    daily_delay: float,
) -> float:
    headers = saj_client.build_headers(saj_client.get_token())
    total_kwh = 0.0

    for device_sn in device_sns:
        for probe_date in _date_range(start_date, end_date):
            daily_kwh = _get_daily_produced_energy_kwh(headers, device_sn, probe_date)
            if daily_kwh is not None:
                total_kwh += daily_kwh
            daily_label = f"{daily_kwh:.2f}" if daily_kwh is not None else "N/D"
            print(
                f"{probe_date.isoformat()} | device={device_sn} | "
                f"energia_giornaliera_kwh={daily_label} | "
                f"energia_cumulata_kwh={total_kwh:.2f}"
            )
            time.sleep(max(0.0, daily_delay))

    return round(total_kwh, 2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calculate SAJ produced energy over a date range.")
    parser.add_argument(
        "--device-sn",
        required=True,
        nargs="+",
        help="One or more SAJ inverter serial numbers.",
    )
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--daily-delay",
        type=float,
        default=1.0,
        help="Seconds to wait after each SAJ daily request.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.end_date < args.start_date:
        raise SystemExit("--end-date must be greater than or equal to --start-date")

    energy_kwh = calculate_energy_kwh(
        args.device_sn,
        args.start_date,
        args.end_date,
        args.daily_delay,
    )
    print(f"{energy_kwh:.2f}")


if __name__ == "__main__":
    main()


r'''
py Produzione\PortaleZilioService\tests_api\saj\probe_energy_range.py 
--device-sn C6V9104J2421E01334 --start-date 2026-01-01 --end-date 2026-05-25 --daily-delay 1

2026-01-01 | device=C6V9104J2421E01334 | energia_giornaliera_kwh=72.45 | energia_cumulata_kwh=72.45
2026-01-02 | device=C6V9104J2421E01334 | energia_giornaliera_kwh=63.48 | energia_cumulata_kwh=135.93
2026-01-03 | device=C6V9104J2421E01334 | energia_giornaliera_kwh=65.00 | energia_cumulata_kwh=200.93
...
2026-05-24 | device=C6V9104J2421E01334 | energia_giornaliera_kwh=437.00 | energia_cumulata_kwh=9988.53
2026-05-25 | device=C6V9104J2421E01334 | energia_giornaliera_kwh=421.09 | energia_cumulata_kwh=10409.62
10409.62

'''
