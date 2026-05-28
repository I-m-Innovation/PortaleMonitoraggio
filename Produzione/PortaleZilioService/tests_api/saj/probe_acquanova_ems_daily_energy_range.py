"""Probe Acquanova EMS daily produced, exported and self-consumed energy.

Usage from repo root:
    python Produzione/PortaleZilioService/tests_api/saj/probe_acquanova_ems_daily_energy_range.py
    python Produzione/PortaleZilioService/tests_api/saj/probe_acquanova_ems_daily_energy_range.py --start-date 2026-05-19 --end-date 2026-05-28
"""

from __future__ import annotations

import argparse
import sys
import time as sleep_time
from datetime import date, datetime, time, timedelta
from pathlib import Path

import requests

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client


ACQUANOVA_1150 = {
    "plant_id": "26049021801",
    "ems_sn": "M5530J2541000285",
}
DEFAULT_START_DATE = date(2026, 5, 19)
MAX_EMS_WINDOW = timedelta(hours=1, minutes=55)


def _safe_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def fetch_ems_history_rows_for_day(
    headers: dict[str, str],
    plant_id: str,
    ems_sn: str,
    probe_date: date,
    *,
    chunk_delay: float,
) -> list[dict]:
    start_dt = datetime.combine(probe_date, time(0, 0, 0))
    end_dt = datetime.combine(probe_date, time(23, 59, 59))
    windows: list[tuple[datetime, datetime]] = []
    cursor = start_dt
    while cursor <= end_dt:
        window_end = min(cursor + MAX_EMS_WINDOW, end_dt)
        windows.append((cursor, window_end))
        if window_end >= end_dt:
            break
        cursor = window_end + timedelta(minutes=5)

    merged_by_time: dict[str, dict] = {}
    for window_start, window_end in windows:
        payload = None
        for attempt in range(4):
            response = requests.get(
                f"{saj_client.BASE_URL}/open/api/device/emsHistoryData",
                headers={
                    **headers,
                    "Content-Type": "application/json",
                    "content-language": "en_US",
                },
                params={
                    "startTime": window_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "endTime": window_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "emsSn": ems_sn,
                    "plantId": plant_id,
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") == 429:
                sleep_time.sleep(0.8 * (attempt + 1))
                continue
            break

        rows = (payload or {}).get("data") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            data_time = row.get("dataTime")
            if data_time:
                merged_by_time[str(data_time)] = row
        sleep_time.sleep(max(0.0, chunk_delay))

    return [merged_by_time[key] for key in sorted(merged_by_time)]


def get_daily_energy_values(rows: list[dict]) -> tuple[float | None, float | None, float | None]:
    candidates: list[tuple[datetime, dict]] = []
    for row in rows:
        timestamp = _parse_timestamp(row.get("dataTime"))
        produced = _safe_float(row.get("parallTodayPVEnergy"))
        if timestamp is not None and produced is not None:
            candidates.append((timestamp, row))
    if not candidates:
        return None, None, None

    _, latest = max(candidates, key=lambda item: item[0])
    produced_kwh = _safe_float(latest.get("parallTodayPVEnergy"))
    exported_kwh = _safe_float(latest.get("parallTodaySellEnergy"))
    self_consumed_kwh = (
        produced_kwh - exported_kwh
        if produced_kwh is not None and exported_kwh is not None
        else None
    )
    return produced_kwh, exported_kwh, self_consumed_kwh


def _format_value(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "N/D"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print Acquanova EMS daily produced, exported and self-consumed energy."
    )
    parser.add_argument("--start-date", type=date.fromisoformat, default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--plant-id", default=ACQUANOVA_1150["plant_id"])
    parser.add_argument("--ems-sn", default=ACQUANOVA_1150["ems_sn"])
    parser.add_argument(
        "--chunk-delay",
        type=float,
        default=0.25,
        help="Seconds to wait after each EMS chunk request.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.end_date < args.start_date:
        raise SystemExit("--end-date must be greater than or equal to --start-date")

    headers = saj_client.build_headers(saj_client.get_token())
    print("data | energia prodotta | energia immessa | energia autoconsumata")
    for probe_date in _date_range(args.start_date, args.end_date):
        rows = fetch_ems_history_rows_for_day(
            headers,
            args.plant_id,
            args.ems_sn,
            probe_date,
            chunk_delay=args.chunk_delay,
        )
        produced_kwh, exported_kwh, self_consumed_kwh = get_daily_energy_values(rows)
        print(
            f"{probe_date.isoformat()} | "
            f"{_format_value(produced_kwh)} | "
            f"{_format_value(exported_kwh)} | "
            f"{_format_value(self_consumed_kwh)}"
        )


if __name__ == "__main__":
    main()
