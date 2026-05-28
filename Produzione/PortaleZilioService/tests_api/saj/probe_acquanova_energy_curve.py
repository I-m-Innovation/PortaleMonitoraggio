"""Probe SAJ power and self-consumption candidate curves for Acquanova.

The script reads the Acquanova power field used by the monitoring flow from SAJ
`historyDataCommon`, plus candidate instantaneous fields for self-consumption,
and writes an interactive Plotly HTML chart.

Usage from repo root:
    python Produzione/PortaleZilioService/tests_api/saj/probe_acquanova_energy_curve.py
    python Produzione/PortaleZilioService/tests_api/saj/probe_acquanova_energy_curve.py --plant acquanova290
    python Produzione/PortaleZilioService/tests_api/saj/probe_acquanova_energy_curve.py --date 2026-05-27
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import plotly.graph_objects as go
import requests

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client


ACQUANOVA_PLANTS = {
    "acquanova1150": {
        "label": "Acquanova 1 - 150",
        "plant_id": "26049021801",
        "device_sn": "C6V9104J2421E01334",
        "ems_sn": "M5530J2541000285",
    },
    "acquanova290": {
        "label": "Acquanova 2 - 90",
        "plant_id": "26051023789",
        "device_sn": "C6T9104J2314E00560",
    },
}

DEFAULT_DATE = date(2026, 5, 27)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "reports"
MAX_EMS_WINDOW = timedelta(hours=1, minutes=55)
HISTORY_FIELDS = (
    "deviceSn,dataTime,todayPvEnergy,totalPvEnergy,totalPVPower,totalGridPowerWatt,"
    "gridDirection,totalLoadPowerWatt,sysTotalLoadWatt,sysGridPowerWatt,"
    "batPower,totalBatteryPower,batteryDirection,"
    "todaySellEnergy,todayFeedInEnergy,todayLoadEnergy"
)


def _safe_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _watts_to_kw(value) -> float | None:
    parsed_value = _safe_float(value)
    return parsed_value / 1000.0 if parsed_value is not None else None


def _candidate_min_pv_load_kw(pv_power_kw: float | None, load_power_kw: float | None) -> float | None:
    if pv_power_kw is None or load_power_kw is None:
        return None
    return max(0.0, min(pv_power_kw, load_power_kw))


def _candidate_pv_minus_export_kw(
    pv_power_kw: float | None,
    grid_power_kw: float | None,
    grid_direction,
) -> float | None:
    if pv_power_kw is None or grid_power_kw is None:
        return None
    export_power_kw = abs(grid_power_kw) if str(grid_direction) == "1" else 0.0
    return max(0.0, pv_power_kw - export_power_kw)


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


def fetch_history_rows(
    headers: dict[str, str],
    device_sn: str,
    probe_date: date,
) -> list[dict]:
    start_dt = datetime.combine(probe_date, time(0, 0, 0))
    end_dt = datetime.combine(probe_date, time(23, 59, 59))
    response = requests.get(
        f"{saj_client.BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn": device_sn,
            "startTime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": HISTORY_FIELDS,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data") or []
    return [row for row in rows if isinstance(row, dict)]


def fetch_plant_statistics(
    headers: dict[str, str],
    plant_id: str,
    probe_date: date,
) -> dict:
    client_date = datetime.combine(probe_date, time(23, 59, 59)).strftime("%Y-%m-%d %H:%M:%S")
    response = requests.get(
        f"{saj_client.BASE_URL}/open/api/plant/getPlantStatisticsData",
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
    payload = response.json()
    data = payload.get("data") or {}
    return data if isinstance(data, dict) else {}


def discover_ems_sn(headers: dict[str, str], plant_id: str) -> str | None:
    devices = saj_client.get_devices(headers, plant_id=plant_id)
    for device in devices:
        device_sn = str(device.get("deviceSn") or "").strip()
        if device_sn.upper().startswith("M55"):
            return device_sn
    return None


def fetch_ems_history_rows(
    headers: dict[str, str],
    plant_id: str,
    ems_sn: str,
    probe_date: date,
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
    for window_start, window_end in windows:
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
        rows = payload.get("data") or []
        chunk_summaries.append(
            f"{window_start:%H:%M}-{window_end:%H:%M}: code={payload.get('code')} records={len(rows)}"
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            data_time = row.get("dataTime")
            if not data_time:
                continue
            merged_by_time[str(data_time)] = row

    print("ems_chunks:")
    for summary in chunk_summaries:
        print(f"  {summary}")
    return [merged_by_time[key] for key in sorted(merged_by_time)]


def parse_power_rows(rows: list[dict]) -> list[dict]:
    parsed_rows: list[dict] = []
    for row in rows:
        timestamp = _parse_timestamp(row.get("dataTime"))
        grid_power_w = _safe_float(row.get("totalGridPowerWatt"))
        if timestamp is None or grid_power_w is None:
            continue
        total_pv_power_kw = _watts_to_kw(row.get("totalPVPower"))
        total_load_power_kw = _watts_to_kw(row.get("totalLoadPowerWatt"))
        total_grid_power_kw = grid_power_w / 1000.0
        sys_total_load_kw = _watts_to_kw(row.get("sysTotalLoadWatt"))
        sys_grid_power_kw = _watts_to_kw(row.get("sysGridPowerWatt"))
        parsed_rows.append(
            {
                "timestamp": timestamp,
                "power_kw": total_grid_power_kw,
                "today_energy_kwh": _safe_float(row.get("todayPvEnergy")),
                "total_pv_energy_kwh": _safe_float(row.get("totalPvEnergy")),
                "total_pv_power_kw": total_pv_power_kw,
                "total_load_power_kw": total_load_power_kw,
                "grid_power_kw": total_grid_power_kw,
                "grid_direction": row.get("gridDirection"),
                "sys_total_load_kw": sys_total_load_kw,
                "sys_grid_power_kw": sys_grid_power_kw,
                "battery_power_kw": _watts_to_kw(row.get("totalBatteryPower"))
                or _watts_to_kw(row.get("batPower")),
                "battery_direction": row.get("batteryDirection"),
                "self_min_pv_load_kw": _candidate_min_pv_load_kw(
                    total_pv_power_kw,
                    total_load_power_kw,
                ),
                "self_pv_minus_export_kw": _candidate_pv_minus_export_kw(
                    total_pv_power_kw,
                    total_grid_power_kw,
                    row.get("gridDirection"),
                ),
                "self_min_pv_sys_load_kw": _candidate_min_pv_load_kw(
                    total_pv_power_kw,
                    sys_total_load_kw,
                ),
            }
        )
    return sorted(parsed_rows, key=lambda item: item["timestamp"])


def get_daily_energy_summary(plant_statistics: dict) -> dict:
    today_pv_energy_kwh = _safe_float(plant_statistics.get("todayPvEnergy"))
    if today_pv_energy_kwh is None:
        return {}
    summary = {
        "dataTime": plant_statistics.get("dataTime"),
        "updateDate": plant_statistics.get("updateDate"),
        "todayPvEnergy": today_pv_energy_kwh,
        "todayLoadEnergy": _safe_float(plant_statistics.get("todayLoadEnergy")),
        "todayChargeEnergy": _safe_float(plant_statistics.get("todayChargeEnergy")),
        "todayDisChargeEnergy": _safe_float(plant_statistics.get("todayDisChargeEnergy")),
        "todayBuyEnergy": _safe_float(plant_statistics.get("todayBuyEnergy")),
        "todaySellEnergy": _safe_float(plant_statistics.get("todaySellEnergy")),
        "batEnergyPercent": _safe_float(plant_statistics.get("batEnergyPercent")),
        "deviceStatus": plant_statistics.get("deviceStatus"),
    }
    pv_energy = summary["todayPvEnergy"]
    sell_energy = summary["todaySellEnergy"]
    summary["todayPvEnergy - todaySellEnergy"] = (
        pv_energy - sell_energy if sell_energy is not None else None
    )
    return summary


def get_ems_daily_energy_summary(ems_rows: list[dict]) -> dict:
    candidates: list[tuple[datetime, dict]] = []
    for row in ems_rows:
        timestamp = _parse_timestamp(row.get("dataTime"))
        today_pv_energy = _safe_float(row.get("parallTodayPVEnergy"))
        if timestamp is None or today_pv_energy is None:
            continue
        candidates.append((timestamp, row))
    if not candidates:
        return {}

    _, latest = max(candidates, key=lambda item: item[0])
    summary = {
        "deviceSn": latest.get("deviceSn"),
        "dataTime": latest.get("dataTime"),
        "updateDate": latest.get("updateDate"),
        "parallTodayPVEnergy": _safe_float(latest.get("parallTodayPVEnergy")),
        "parallTodaySellEnergy": _safe_float(latest.get("parallTodaySellEnergy")),
        "parallTodayFeedInEnergy": _safe_float(latest.get("parallTodayFeedInEnergy")),
        "parallTodayTotalLoadEnergy": _safe_float(latest.get("parallTodayTotalLoadEnergy")),
        "parallTodayBatChgEnergy": _safe_float(latest.get("parallTodayBatChgEnergy")),
        "parallTodayBatDisEnergy": _safe_float(latest.get("parallTodayBatDisEnergy")),
        "gridDirection": latest.get("gridDirection"),
        "batteryDirection": latest.get("batteryDirection"),
    }
    pv_energy = summary["parallTodayPVEnergy"]
    sell_energy = summary["parallTodaySellEnergy"]
    feed_in_energy = summary["parallTodayFeedInEnergy"]
    summary["parallTodayPVEnergy - parallTodaySellEnergy"] = (
        pv_energy - sell_energy if pv_energy is not None and sell_energy is not None else None
    )
    summary["parallTodayPVEnergy - parallTodayFeedInEnergy"] = (
        pv_energy - feed_in_energy if pv_energy is not None and feed_in_energy is not None else None
    )
    return summary


def _format_kwh(value: float | None) -> str:
    return f"{value:.3f} kWh" if value is not None else "N/D"


def print_daily_energy_markdown_table(summary: dict) -> None:
    if not summary:
        print("| field | value |")
        print("|---|---:|")
        print("| todayPvEnergy | N/D |")
        return

    print("| field | value |")
    print("|---|---:|")
    print(f"| dataTime | {summary['dataTime'] or 'N/D'} |")
    print(f"| updateDate | {summary['updateDate'] or 'N/D'} |")
    print(f"| todayPvEnergy | {_format_kwh(summary['todayPvEnergy'])} |")
    print(f"| todaySellEnergy | {_format_kwh(summary['todaySellEnergy'])} |")
    print(f"| todayLoadEnergy | {_format_kwh(summary['todayLoadEnergy'])} |")
    print(f"| todayBuyEnergy | {_format_kwh(summary['todayBuyEnergy'])} |")
    print(f"| todayChargeEnergy | {_format_kwh(summary['todayChargeEnergy'])} |")
    print(f"| todayDisChargeEnergy | {_format_kwh(summary['todayDisChargeEnergy'])} |")
    print(f"| batEnergyPercent | {summary['batEnergyPercent'] if summary['batEnergyPercent'] is not None else 'N/D'} |")
    print(f"| deviceStatus | {summary['deviceStatus'] or 'N/D'} |")
    print(
        "| todayPvEnergy - todaySellEnergy | "
        f"{_format_kwh(summary['todayPvEnergy - todaySellEnergy'])} |"
    )


def print_ems_daily_energy_markdown_table(summary: dict) -> None:
    if not summary:
        print("| field | value |")
        print("|---|---:|")
        print("| parallTodayPVEnergy | N/D |")
        return

    print("| field | value |")
    print("|---|---:|")
    print(f"| deviceSn | {summary['deviceSn'] or 'N/D'} |")
    print(f"| dataTime | {summary['dataTime'] or 'N/D'} |")
    print(f"| updateDate | {summary['updateDate'] or 'N/D'} |")
    print(f"| parallTodayPVEnergy | {_format_kwh(summary['parallTodayPVEnergy'])} |")
    print(f"| parallTodaySellEnergy | {_format_kwh(summary['parallTodaySellEnergy'])} |")
    print(f"| parallTodayFeedInEnergy | {_format_kwh(summary['parallTodayFeedInEnergy'])} |")
    print(f"| parallTodayTotalLoadEnergy | {_format_kwh(summary['parallTodayTotalLoadEnergy'])} |")
    print(f"| parallTodayBatChgEnergy | {_format_kwh(summary['parallTodayBatChgEnergy'])} |")
    print(f"| parallTodayBatDisEnergy | {_format_kwh(summary['parallTodayBatDisEnergy'])} |")
    print(f"| gridDirection | {summary['gridDirection']} |")
    print(f"| batteryDirection | {summary['batteryDirection']} |")
    print(
        "| parallTodayPVEnergy - parallTodaySellEnergy | "
        f"{_format_kwh(summary['parallTodayPVEnergy - parallTodaySellEnergy'])} |"
    )
    print(
        "| parallTodayPVEnergy - parallTodayFeedInEnergy | "
        f"{_format_kwh(summary['parallTodayPVEnergy - parallTodayFeedInEnergy'])} |"
    )


def write_chart(
    parsed_rows: list[dict],
    *,
    plant_label: str,
    plant_key: str,
    device_sn: str,
    probe_date: date,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"saj_{plant_key}_power_curve_{probe_date:%Y%m%d}.html"

    fig = go.Figure()
    x_values = [row["timestamp"] for row in parsed_rows]

    def add_power_trace(field_name: str, label: str, *, visible=True, mode="lines") -> None:
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=[row[field_name] for row in parsed_rows],
                mode=mode,
                name=label,
                visible=visible,
                hovertemplate=f"%{{x|%Y-%m-%d %H:%M:%S}}<br>{label}=%{{y:.3f}} kW<extra></extra>",
            )
        )

    add_power_trace("power_kw", "totalGridPowerWatt", mode="lines+markers")
    add_power_trace("total_pv_power_kw", "totalPVPower")
    add_power_trace("total_load_power_kw", "totalLoadPowerWatt")
    add_power_trace("self_min_pv_load_kw", "candidate: min(totalPVPower,totalLoadPowerWatt)")
    add_power_trace("self_pv_minus_export_kw", "candidate: totalPVPower - export(gridDirection)")
    add_power_trace("sys_total_load_kw", "sysTotalLoadWatt", visible="legendonly")
    add_power_trace("sys_grid_power_kw", "sysGridPowerWatt", visible="legendonly")
    add_power_trace("self_min_pv_sys_load_kw", "candidate: min(totalPVPower,sysTotalLoadWatt)", visible="legendonly")
    add_power_trace("battery_power_kw", "battery power", visible="legendonly")

    fig.update_layout(
        title=f"SAJ - {plant_label} - curve autoconsumo candidate - {probe_date.isoformat()}",
        xaxis_title="Ora",
        yaxis_title="Potenza (kW)",
        template="plotly_white",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        margin={"l": 70, "r": 70, "t": 90, "b": 60},
    )
    fig.write_html(html_path, auto_open=False, include_plotlyjs=True)
    return html_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot SAJ Acquanova power and self-consumption candidates.")
    parser.add_argument(
        "--plant",
        choices=sorted(ACQUANOVA_PLANTS),
        default="acquanova1150",
        help="Acquanova SAJ plant to probe.",
    )
    parser.add_argument("--date", type=date.fromisoformat, default=DEFAULT_DATE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--ems-sn",
        default=None,
        help="EMS serial number. If omitted, the script tries to discover the first M55* device in the plant.",
    )
    parser.add_argument("--dump-json", action="store_true", help="Print the first raw SAJ row.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plant_config = ACQUANOVA_PLANTS[args.plant]
    headers = saj_client.build_headers(saj_client.get_token())

    rows = fetch_history_rows(headers, plant_config["device_sn"], args.date)
    parsed_rows = parse_power_rows(rows)
    ems_sn = args.ems_sn or plant_config.get("ems_sn") or discover_ems_sn(headers, plant_config["plant_id"])
    if ems_sn:
        ems_rows = fetch_ems_history_rows(headers, plant_config["plant_id"], ems_sn, args.date)
    else:
        ems_rows = []
    daily_energy_summary = get_ems_daily_energy_summary(ems_rows)

    print("== SAJ Acquanova power/self-consumption candidates probe ==")
    print(f"plant: {args.plant} ({plant_config['label']})")
    print(f"plant_id: {plant_config['plant_id']}")
    print(f"device_sn: {plant_config['device_sn']}")
    print(f"ems_sn: {ems_sn or 'N/D'}")
    print(f"date: {args.date.isoformat()}")
    print(f"raw_records: {len(rows)}")
    print(f"power_points: {len(parsed_rows)}")
    print(f"ems_records: {len(ems_rows)}")
    print_ems_daily_energy_markdown_table(daily_energy_summary)

    if args.dump_json and rows:
        print("first_raw_row:")
        print(json.dumps(rows[0], ensure_ascii=False, indent=2))
    if args.dump_json and ems_rows:
        print("first_ems_raw_row:")
        print(json.dumps(ems_rows[0], ensure_ascii=False, indent=2))

    if not parsed_rows:
        raise SystemExit("No usable totalGridPowerWatt records returned by SAJ.")

    first = parsed_rows[0]
    last = parsed_rows[-1]
    print(
        "first_point: "
        f"{first['timestamp']:%Y-%m-%d %H:%M:%S} | {first['power_kw']:.3f} kW"
    )
    print(
        "last_point: "
        f"{last['timestamp']:%Y-%m-%d %H:%M:%S} | {last['power_kw']:.3f} kW"
    )


    html_path = write_chart(
        parsed_rows,
        plant_label=plant_config["label"],
        plant_key=args.plant,
        device_sn=plant_config["device_sn"],
        probe_date=args.date,
        output_dir=args.output_dir,
    )
    print(f"chart: {html_path}")


if __name__ == "__main__":
    main()
