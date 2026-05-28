"""Probe SAJ EMS daily produced/exported/self-consumed energy for multiple plants.

Edit `EMS_PLANTS` below to add or change plants.

Usage from repo root:
    python Produzione/PortaleZilioService/tests_api/saj/probe_ems_daily_energy_multi.py
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


# SAJ espone gli stessi valori business tramite endpoint diversi a seconda
# della famiglia impianto/device. La maggior parte degli impianti testati qui
# pubblica la card energia della dashboard tramite storico EMS
# (`parallTodayPVEnergy` e `parallTodaySellEnergy`).
# Col Roigo e' l'eccezione emersa durante il probe: il communication module e'
# valido e `emsHistoryData` risponde `code=200`, ma senza record. Per questo
# impianto gli stessi valori giornalieri sono disponibili nello storico dello
# storage inverter (`historyDataCommon`) tramite `todayPvEnergy` e
# `todaySellEnergy`.
#
# Mantenere `device_sn` configurato per gli impianti che possono fare fallback
# sullo storico device quando la preflight EMS torna con zero record.
EMS_PLANTS = {
    "acquanova1150": {
        "label": "Acquanova 1 - 150",
        "plant_id": "26049021801",
        "ems_sn": "M5530J2541000285",
    },
    "acquanova290": {
        "label": "Acquanova 2 - 290",
        "plant_id": "26051023789",
        "ems_sn": "M5530J2541000287",
    },
    "ziliogroup281kw": {
        "label": "Zilio Group 281kW",
        "plant_id": "24031286133",
        "ems_sn": "M5530J2428000038",
    },
    "rctbramante": {
        "label": "RCT-Bramante",
        "plant_id": "25520042620",
        "ems_sn": "M5530J2428000023",
    },
    "colroigo50kwp" : {
        "label": "Col Roigo 50 kWp",
        "plant_id": "24110165619",
        "ems_sn": "M5380J2415071297",
        "device_sn": "CSV6503J2416E00004",
    },
}
# Add more plants here:
# "nomechiave": {
#     "label": "Nome leggibile",
#     "plant_id": "SAJ_PLANT_ID",
#     "ems_sn": "M55...",
# },


DEFAULT_START_DATE = date(2026, 5, 21)
DEFAULT_END_DATE = date(2026, 5, 27)
MAX_EMS_WINDOW = timedelta(hours=1, minutes=55)


def force_new_saj_headers() -> dict[str, str]:
    saj_client._cached_token = None
    saj_client._cached_token_valid_until = 0.0
    return saj_client.build_headers(saj_client.get_token())


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
    debug_empty: bool = False,
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
    chunk_summaries: list[str] = []
    first_payload_data_row: dict | None = None
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
        chunk_summaries.append(
            f"{window_start:%H:%M}-{window_end:%H:%M}: "
            f"code={(payload or {}).get('code')} msg={(payload or {}).get('msg')} records={len(rows)}"
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            if first_payload_data_row is None:
                first_payload_data_row = row
            data_time = row.get("dataTime")
            if data_time:
                merged_by_time[str(data_time)] = row
        sleep_time.sleep(max(0.0, chunk_delay))

    if debug_empty and not merged_by_time:
        print("  debug_empty_chunks:")
        for summary in chunk_summaries:
            print(f"    {summary}")
    elif debug_empty and first_payload_data_row is not None:
        print(f"  debug_first_record_keys: {', '.join(first_payload_data_row.keys())}")

    return [merged_by_time[key] for key in sorted(merged_by_time)]


def preflight_ems_call(
    headers: dict[str, str],
    plant_id: str,
    ems_sn: str,
    probe_date: date,
) -> tuple[str | None, str | None, int]:
    start_dt = datetime.combine(probe_date, time(12, 0, 0))
    end_dt = start_dt + timedelta(minutes=5)
    response = requests.get(
        f"{saj_client.BASE_URL}/open/api/device/emsHistoryData",
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
    payload = response.json()
    rows = payload.get("data") or []
    return str(payload.get("code")), payload.get("msg"), len(rows)


DEVICE_HISTORY_FIELDS = (
    "deviceSn,dataTime,todayPvEnergy,todaySellEnergy,todayFeedInEnergy,todayLoadEnergy,"
    "totalPvEnergy,totalSellEnergy,totalFeedInEnergy,totalTotalLoadEnergy"
)


def fetch_device_history_rows_for_day(
    headers: dict[str, str],
    device_sn: str,
    probe_date: date,
) -> list[dict]:
    start_dt = datetime.combine(probe_date, time(0, 0, 0))
    end_dt = datetime.combine(probe_date, time(23, 59, 59))
    response = requests.get(
        f"{saj_client.BASE_URL}/open/api/device/historyDataCommon",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        params={
            "deviceSn": device_sn,
            "startTime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": DEVICE_HISTORY_FIELDS,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data") or []
    return [row for row in rows if isinstance(row, dict)]


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


def get_device_daily_energy_values(rows: list[dict]) -> tuple[float | None, float | None, float | None]:
    candidates: list[tuple[datetime, dict]] = []
    for row in rows:
        timestamp = _parse_timestamp(row.get("dataTime"))
        produced = _safe_float(row.get("todayPvEnergy"))
        if timestamp is not None and produced is not None:
            candidates.append((timestamp, row))
    if not candidates:
        return None, None, None

    _, latest = max(candidates, key=lambda item: item[0])
    produced_kwh = _safe_float(latest.get("todayPvEnergy"))
    exported_kwh = _safe_float(latest.get("todaySellEnergy"))
    self_consumed_kwh = (
        produced_kwh - exported_kwh
        if produced_kwh is not None and exported_kwh is not None
        else None
    )
    return produced_kwh, exported_kwh, self_consumed_kwh


def _format_value(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "N/D"


def print_row(
    impianto: str,
    source: str,
    row_date: str,
    produced_kwh,
    exported_kwh,
    self_consumed_kwh,
) -> None:
    print(
        f"{impianto:<24} | "
        f"{source:<14} | "
        f"{row_date:<10} | "
        f"{_format_value(produced_kwh):>16} | "
        f"{_format_value(exported_kwh):>15} | "
        f"{_format_value(self_consumed_kwh):>21}"
    )


def print_header() -> None:
    print(
        f"{'impianto':<24} | "
        f"{'sorgente':<14} | "
        f"{'data':<10} | "
        f"{'energia prodotta':>16} | "
        f"{'energia immessa':>15} | "
        f"{'energia autoconsumata':>21}"
    )
    print("-" * 115)


def print_preflight_header() -> None:
    print("preflight emsHistoryData")
    print(
        f"{'impianto':<24} | "
        f"{'plant_id':<12} | "
        f"{'ems_sn':<16} | "
        f"{'code':<6} | "
        f"{'records':>7} | "
        f"msg"
    )
    print("-" * 100)


def print_preflight_row(impianto: str, plant_id: str, ems_sn: str, code, msg, records: int) -> None:
    print(
        f"{impianto:<24} | "
        f"{plant_id:<12} | "
        f"{ems_sn:<16} | "
        f"{str(code):<6} | "
        f"{records:>7} | "
        f"{msg or ''}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print SAJ EMS daily produced/exported/self-consumed energy for multiple plants."
    )
    parser.add_argument("--start-date", type=date.fromisoformat, default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", type=date.fromisoformat, default=DEFAULT_END_DATE)
    parser.add_argument(
        "--plant",
        action="append",
        choices=sorted(EMS_PLANTS),
        help="Plant key to probe. Can be repeated. Defaults to all EMS_PLANTS.",
    )
    parser.add_argument(
        "--chunk-delay",
        type=float,
        default=0.25,
        help="Seconds to wait after each EMS chunk request.",
    )
    parser.add_argument(
        "--debug-empty",
        action="store_true",
        help="Print EMS chunk diagnostics when no useful daily value is found.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.end_date < args.start_date:
        raise SystemExit("--end-date must be greater than or equal to --start-date")

    selected_keys = args.plant or list(EMS_PLANTS)
    source_by_plant: dict[str, str] = {}
    print_preflight_header()
    for plant_key in selected_keys:
        plant = EMS_PLANTS[plant_key]
        headers = force_new_saj_headers()
        code, msg, records = preflight_ems_call(
            headers,
            plant["plant_id"],
            plant["ems_sn"],
            args.start_date,
        )
        print_preflight_row(plant["label"], plant["plant_id"], plant["ems_sn"], code, msg, records)
        # Una risposta EMS valida ma con zero record non basta per calcolare la
        # card energia giornaliera. In quel caso prova l'endpoint device-level
        # se l'impianto ha un `device_sn` configurato; per Col Roigo e'
        # necessario.
        if records == 0 and plant.get("device_sn"):
            source_by_plant[plant_key] = "device_history"
        else:
            source_by_plant[plant_key] = "ems_history"
        sleep_time.sleep(max(0.0, args.chunk_delay))
    print("")

    print_header()
    for plant_key in selected_keys:
        plant = EMS_PLANTS[plant_key]
        headers = force_new_saj_headers()
        for probe_date in _date_range(args.start_date, args.end_date):
            if source_by_plant.get(plant_key) == "device_history":
                rows = fetch_device_history_rows_for_day(headers, plant["device_sn"], probe_date)
                produced_kwh, exported_kwh, self_consumed_kwh = get_device_daily_energy_values(rows)
            else:
                rows = fetch_ems_history_rows_for_day(
                    headers,
                    plant["plant_id"],
                    plant["ems_sn"],
                    probe_date,
                    chunk_delay=args.chunk_delay,
                    debug_empty=args.debug_empty,
                )
                produced_kwh, exported_kwh, self_consumed_kwh = get_daily_energy_values(rows)
            print_row(
                plant["label"],
                source_by_plant.get(plant_key, "ems_history"),
                probe_date.isoformat(),
                produced_kwh,
                exported_kwh,
                self_consumed_kwh,
            )


if __name__ == "__main__":
    main()
