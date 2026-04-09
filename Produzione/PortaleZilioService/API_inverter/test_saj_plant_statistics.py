from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timedelta

import matplotlib
import requests
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import plotly.graph_objects as go

from saj_client import BASE_URL, build_headers, get_devices, get_plants, get_token


ZILIO_GROUP_490KW_PLANT_ID = "168UEE"
ZILIO_GROUP_490KW_DEVICES = [
    "C6T9104J2314E00560",
    "C6T9104J2315E00670",
    "C6V9104G2424E00228",
    "C6V9104J2421E01334",
    "CSV6503J2416E00023",
    "CSV6503J2416E00036",
    "CSV6503J2416E00047",
]

ZILIO_GROUP_490KW_C6_DEVICES = [
    "C6T9104J2314E00560",
    "C6T9104J2315E00670",
    "C6V9104G2424E00228",
    "C6V9104J2421E01334",
]

ZILIO_GROUP_490KW_S12_DEVICES = [
    "CSV6503J2416E00023",
    "CSV6503J2416E00036",
    "CSV6503J2416E00047",
]

ZILIO_GROUP_490KW_S12_LABELS = {
    "CSV6503J2416E00023": "S12_1",
    "CSV6503J2416E00036": "S12_2",
    "CSV6503J2416E00047": "S12_3",
}

COL_ROIGO_PLANT_ID = "24110165619"
COL_ROIGO_EMS_SN = "M5380J2415071297"


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


def get_ems_history_data_4_meter(
    headers: dict[str, str],
    start_time: str,
    end_time: str,
    ems_sn: str,
    plant_id: str,
) -> dict:
    response = requests.get(
        f"{BASE_URL}/open/api/device/emsHistoryData4Meter",
        headers={
            **headers,
            "Content-Type": "application/json",
            "content-language": "en_US",
        },
        params={
            "startTime": start_time,
            "endTime": end_time,
            "emsSn": ems_sn,
            "plantId": plant_id,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_ems_history_data(
    headers: dict[str, str],
    start_time: str,
    end_time: str,
    ems_sn: str,
    plant_id: str,
) -> dict:
    response = requests.get(
        f"{BASE_URL}/open/api/device/emsHistoryData",
        headers={
            **headers,
            "Content-Type": "application/json",
            "content-language": "en_US",
        },
        params={
            "startTime": start_time,
            "endTime": end_time,
            "emsSn": ems_sn,
            "plantId": plant_id,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_plant_energy(
    headers: dict[str, str],
    plant_id: str,
    device_sns: str,
    client_date: str,
) -> dict:
    response = requests.get(
        f"{BASE_URL}/open/api/plant/energy",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        params={
            "plantId": plant_id,
            "deviceSns": device_sns,
            "clientDate": client_date,
        },
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


def _parse_history_rows(rows: list[dict]) -> list[tuple[datetime, dict]]:
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
    return parsed_rows


def _round_to_5min(dt: datetime) -> datetime:
    minute_bucket = (dt.minute // 5) * 5
    return dt.replace(minute=minute_bucket, second=0, microsecond=0)


def _print_json_block(title: str, payload) -> None:
    print(title)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("-" * 140)


def _print_row_excerpt(row: dict) -> None:
    excerpt = {
        "dataTime": row.get("dataTime"),
        "totalPVPower": row.get("totalPVPower"),
        "todayPvEnergy": row.get("todayPvEnergy"),
        "totalPvEnergy": row.get("totalPvEnergy"),
    }
    for idx in range(1, 7):
        excerpt[f"pv{idx}power"] = row.get(f"pv{idx}power")
    print(json.dumps(excerpt, ensure_ascii=False, indent=2))


def _print_generic_row_excerpt(row: dict, max_items: int = 20) -> None:
    excerpt = {key: row[key] for key in list(row.keys())[:max_items]}
    print(json.dumps(excerpt, ensure_ascii=False, indent=2))


def run_ems_meter_debug(headers: dict[str, str], args: argparse.Namespace) -> None:
    start_time = args.start_time or f"{args.date} 00:00:00"
    end_time = args.end_time or f"{args.date} 02:00:00"

    if not args.ems_sn:
        raise ValueError("--ems-sn is required for ems-meter mode")

    print("== SAJ EMS meter debug ==")
    print(f"plant_id: {args.plant_id}")
    print(f"ems_sn: {args.ems_sn}")
    print(f"window: {start_time} -> {end_time}")
    print("")

    payload = get_ems_history_data_4_meter(
        headers=headers,
        start_time=start_time,
        end_time=end_time,
        ems_sn=args.ems_sn,
        plant_id=args.plant_id,
    )
    rows = payload.get("data") or []
    print(f"code: {payload.get('code')}")
    print(f"msg: {payload.get('msg')}")
    print(f"records: {len(rows)}")
    print("")

    if rows:
        available_keys = sorted({key for row in rows[:10] for key in row.keys()})
        print(f"FIELDS DEBUG first_keys={available_keys}")
        print("ROW DEBUG first_row:")
        _print_generic_row_excerpt(rows[0])
        print("ROW DEBUG last_row:")
        _print_generic_row_excerpt(rows[-1])
    else:
        print("ROW DEBUG no rows returned")

    if args.dump_json:
        print("")
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_ems_history_debug(headers: dict[str, str], args: argparse.Namespace) -> None:
    start_time = args.start_time or f"{args.date} 00:00:00"
    end_time = args.end_time or f"{args.date} 02:00:00"

    if not args.ems_sn:
        raise ValueError("--ems-sn is required for ems-history mode")

    print("== SAJ EMS history debug ==")
    print(f"plant_id: {args.plant_id}")
    print(f"ems_sn: {args.ems_sn}")
    print(f"window: {start_time} -> {end_time}")
    print("")

    start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    if end_dt < start_dt:
        raise ValueError("end-time must be greater than or equal to start-time")

    windows: list[tuple[datetime, datetime]] = []
    cursor = start_dt
    max_span = timedelta(hours=1, minutes=55)
    while cursor <= end_dt:
        window_end = min(cursor + max_span, end_dt)
        windows.append((cursor, window_end))
        if window_end >= end_dt:
            break
        cursor = window_end + timedelta(minutes=5)

    print(f"chunk_count: {len(windows)}")

    rows: list[dict] = []
    payloads: list[dict] = []
    for idx, (window_start, window_end) in enumerate(windows, start=1):
        print(
            f"chunk {idx}/{len(windows)}: "
            f"{window_start.strftime('%Y-%m-%d %H:%M:%S')} -> {window_end.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        payload = None
        for attempt in range(4):
            payload = get_ems_history_data(
                headers=headers,
                start_time=window_start.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=window_end.strftime("%Y-%m-%d %H:%M:%S"),
                ems_sn=args.ems_sn,
                plant_id=args.plant_id,
            )
            if payload.get("code") == 429:
                wait_seconds = 0.6 * (attempt + 1)
                print(f"  rate limit hit, retrying after {wait_seconds:.1f}s")
                time.sleep(wait_seconds)
                continue
            break
        if payload is None:
            continue
        payloads.append(payload)
        chunk_rows = payload.get("data") or []
        print(f"  code: {payload.get('code')} msg: {payload.get('msg')} records: {len(chunk_rows)}")
        rows.extend(chunk_rows)

    deduped_rows_by_time: dict[str, dict] = {}
    for row in rows:
        dt_raw = row.get("dataTime")
        if not dt_raw:
            continue
        deduped_rows_by_time[dt_raw] = row
    rows = [deduped_rows_by_time[key] for key in sorted(deduped_rows_by_time)]

    print("")
    print(f"records_after_merge: {len(rows)}")

    if not rows:
        print("ROW DEBUG no rows returned")
        if args.dump_json:
            print("")
            print(json.dumps(payloads, ensure_ascii=False, indent=2))
        return

    available_keys = sorted({key for row in rows[:10] for key in row.keys()})
    print(f"FIELDS DEBUG first_keys={available_keys}")
    print("ROW DEBUG first_row:")
    _print_generic_row_excerpt(rows[0], max_items=30)
    print("ROW DEBUG last_row:")
    _print_generic_row_excerpt(rows[-1], max_items=30)

    parsed_rows = []
    for row in rows:
        dt_raw = row.get("dataTime")
        if not dt_raw:
            continue
        try:
            dt = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        parsed_rows.append(
            {
                "dataTime": dt,
                "parallTotalPvPower": _safe_float(row.get("parallTotalPvPower")),
                "parallPVPower": _safe_float(row.get("parallPVPower")),
                "parallLoadPower": _safe_float(row.get("parallLoadPower")),
                "parallBatPower": _safe_float(row.get("parallBatPower")),
                "parallGridPower": _safe_float(row.get("parallGridPower")),
                "parallMeterPower": _safe_float(row.get("parallMeterPower")),
                "parallSOC": _safe_float(row.get("parallSOC")),
                "updateDate": row.get("updateDate"),
            }
        )

    html_path = os.path.join(
        tempfile.gettempdir(),
        f"saj_ems_history_{args.date.replace('-', '')}_{args.ems_sn}.html",
    )

    x = [row["dataTime"] for row in parsed_rows]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["parallTotalPvPower"] for row in parsed_rows],
            mode="lines+markers",
            name="parallTotalPvPower",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>parallTotalPvPower=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["parallPVPower"] for row in parsed_rows],
            mode="lines+markers",
            name="parallPVPower",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>parallPVPower=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["parallLoadPower"] for row in parsed_rows],
            mode="lines+markers",
            name="parallLoadPower",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>parallLoadPower=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["parallBatPower"] for row in parsed_rows],
            mode="lines+markers",
            name="parallBatPower",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>parallBatPower=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["parallGridPower"] for row in parsed_rows],
            mode="lines+markers",
            name="parallGridPower",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>parallGridPower=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["parallMeterPower"] for row in parsed_rows],
            mode="lines+markers",
            name="parallMeterPower",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>parallMeterPower=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["parallSOC"] for row in parsed_rows],
            mode="lines",
            name="parallSOC",
            yaxis="y2",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>parallSOC=%{y:.2f}<extra></extra>",
            opacity=0.5,
        )
    )
    fig.update_layout(
        title=f"SAJ emsHistoryData - {args.date} {start_time[-8:]} to {end_time[-8:]}",
        xaxis_title="Timestamp",
        yaxis_title="Power",
        yaxis2=dict(title="SOC %", overlaying="y", side="right"),
        hovermode="x unified",
        template="plotly_white",
    )
    fig.write_html(html_path, auto_open=False, include_plotlyjs=True)

    table_rows = "\n".join(
        (
            "<tr>"
            f"<td>{row['dataTime'].strftime('%Y-%m-%d %H:%M:%S')}</td>"
            f"<td>{row['parallTotalPvPower']}</td>"
            f"<td>{row['parallPVPower']}</td>"
            f"<td>{row['parallLoadPower']}</td>"
            f"<td>{row['parallBatPower']}</td>"
            f"<td>{row['parallGridPower']}</td>"
            f"<td>{row['parallMeterPower']}</td>"
            f"<td>{row['parallSOC']}</td>"
            f"<td>{row['updateDate']}</td>"
            "</tr>"
        )
        for row in parsed_rows
    )
    with open(html_path, "a", encoding="utf-8") as report_file:
        report_file.write(
            f"""
<hr>
<h2>Queried points</h2>
<table border="1" cellspacing="0" cellpadding="4">
  <thead>
    <tr>
      <th>dataTime</th>
      <th>parallTotalPvPower</th>
      <th>parallPVPower</th>
      <th>parallLoadPower</th>
      <th>parallBatPower</th>
      <th>parallGridPower</th>
      <th>parallMeterPower</th>
      <th>parallSOC</th>
      <th>updateDate</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>
"""
        )

    print(f"PLOT DEBUG opening EMS history HTML report: {html_path}")
    os.startfile(html_path)

    if args.dump_json:
        print("")
        print(json.dumps(payloads, ensure_ascii=False, indent=2))


def run_plant_stats_day_probe(headers: dict[str, str], args: argparse.Namespace) -> None:
    day_start = datetime.strptime(f"{args.date} 00:00:00", "%Y-%m-%d %H:%M:%S")
    timestamps = [day_start + timedelta(minutes=5 * idx) for idx in range(288)]

    print("== SAJ plant statistics day probe ==")
    print(f"plant_id: {args.plant_id}")
    print(f"points_to_query: {len(timestamps)}")
    print("")

    rows = []
    for idx, probe_dt in enumerate(timestamps, start=1):
        client_date = probe_dt.strftime("%Y-%m-%d %H:%M:%S")
        payload = get_plant_statistics(headers, args.plant_id, client_date)
        data = payload.get("data") or {}
        row = {
            "clientDate": client_date,
            "dataTime": data.get("dataTime"),
            "powerNow": _safe_float(data.get("powerNow")),
            "todayPvEnergy": _safe_float(data.get("todayPvEnergy")),
            "todayLoadEnergy": _safe_float(data.get("todayLoadEnergy")),
            "todayChargeEnergy": _safe_float(data.get("todayChargeEnergy")),
            "todayDisChargeEnergy": _safe_float(data.get("todayDisChargeEnergy")),
            "todayBuyEnergy": _safe_float(data.get("todayBuyEnergy")),
            "todaySellEnergy": _safe_float(data.get("todaySellEnergy")),
            "batEnergyPercent": _safe_float(data.get("batEnergyPercent")),
            "deviceStatus": data.get("deviceStatus"),
            "code": payload.get("code"),
            "msg": payload.get("msg"),
        }
        rows.append(row)
        if idx % 24 == 0:
            print(f"progress: {idx}/{len(timestamps)} queried")

    print("")
    print(f"rows_collected: {len(rows)}")
    print("sample first rows:")
    print(json.dumps(rows[:5], ensure_ascii=False, indent=2))

    html_path = os.path.join(
        tempfile.gettempdir(),
        f"saj_plant_stats_day_{args.date.replace('-', '')}.html",
    )

    x = [datetime.strptime(row["clientDate"], "%Y-%m-%d %H:%M:%S") for row in rows]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["powerNow"] for row in rows],
            mode="lines+markers",
            name="powerNow",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>powerNow=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["batEnergyPercent"] for row in rows],
            mode="lines",
            name="batEnergyPercent",
            yaxis="y2",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>SOC=%{y:.2f}%<extra></extra>",
            opacity=0.5,
        )
    )
    fig.update_layout(
        title=f"SAJ plant getPlantStatisticsData every 5 minutes - {args.date}",
        xaxis_title="Timestamp",
        yaxis_title="powerNow",
        yaxis2=dict(title="SOC %", overlaying="y", side="right"),
        hovermode="x unified",
        template="plotly_white",
    )
    fig.write_html(html_path, auto_open=False, include_plotlyjs=True)

    table_rows = "\n".join(
        (
            "<tr>"
            f"<td>{row['clientDate']}</td>"
            f"<td>{row['dataTime']}</td>"
            f"<td>{row['powerNow']}</td>"
            f"<td>{row['todayPvEnergy']}</td>"
            f"<td>{row['todayLoadEnergy']}</td>"
            f"<td>{row['todayChargeEnergy']}</td>"
            f"<td>{row['todayDisChargeEnergy']}</td>"
            f"<td>{row['todayBuyEnergy']}</td>"
            f"<td>{row['todaySellEnergy']}</td>"
            f"<td>{row['batEnergyPercent']}</td>"
            f"<td>{row['deviceStatus']}</td>"
            "</tr>"
        )
        for row in rows
    )
    with open(html_path, "a", encoding="utf-8") as report_file:
        report_file.write(
            f"""
<hr>
<h2>Queried points</h2>
<table border="1" cellspacing="0" cellpadding="4">
  <thead>
    <tr>
      <th>clientDate</th>
      <th>dataTime</th>
      <th>powerNow</th>
      <th>todayPvEnergy</th>
      <th>todayLoadEnergy</th>
      <th>todayChargeEnergy</th>
      <th>todayDisChargeEnergy</th>
      <th>todayBuyEnergy</th>
      <th>todaySellEnergy</th>
      <th>batEnergyPercent</th>
      <th>deviceStatus</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>
"""
        )

    print(f"PLOT DEBUG opening plant stats HTML report: {html_path}")
    os.startfile(html_path)


def run_plant_energy_day_probe(headers: dict[str, str], args: argparse.Namespace) -> None:
    day_start = datetime.strptime(f"{args.date} 00:00:00", "%Y-%m-%d %H:%M:%S")
    timestamps = [day_start + timedelta(minutes=5 * idx) for idx in range(288)]

    if args.device_group == "c6":
        selected_devices = ZILIO_GROUP_490KW_C6_DEVICES
    elif args.device_group == "s12":
        selected_devices = ZILIO_GROUP_490KW_S12_DEVICES
    else:
        selected_devices = ZILIO_GROUP_490KW_DEVICES

    device_sns = ",".join(selected_devices)

    print("== SAJ plant energy day probe ==")
    print(f"plant_id: {args.plant_id}")
    print(f"device_group: {args.device_group}")
    print(f"device_sns: {device_sns}")
    print(f"points_to_query: {len(timestamps)}")
    print("")

    rows = []
    for idx, probe_dt in enumerate(timestamps, start=1):
        client_date = probe_dt.strftime("%Y-%m-%d %H:%M:%S")
        payload = get_plant_energy(
            headers=headers,
            plant_id=args.plant_id,
            device_sns=device_sns,
            client_date=client_date,
        )
        data = payload.get("data") or {}
        rows.append(
            {
                "clientDate": client_date,
                "powerNow": _safe_float(data.get("powerNow")),
                "todayPvEnergy": _safe_float(data.get("todayPvEnergy")),
                "monthPvEnergy": _safe_float(data.get("monthPvEnergy")),
                "yearPvEnergy": _safe_float(data.get("yearPvEnergy")),
                "totalPvEnergy": _safe_float(data.get("totalPvEnergy")),
                "batEnergyPercent": _safe_float(data.get("batEnergyPercent")),
                "deviceStatus": data.get("deviceStatus"),
                "updateDate": data.get("updateDate"),
                "code": payload.get("code"),
                "msg": payload.get("msg"),
            }
        )
        if idx % 24 == 0:
            print(f"progress: {idx}/{len(timestamps)} queried")

    print("")
    print(f"rows_collected: {len(rows)}")
    print("sample first rows:")
    print(json.dumps(rows[:5], ensure_ascii=False, indent=2))

    html_path = os.path.join(
        tempfile.gettempdir(),
        f"saj_plant_energy_day_{args.device_group}_{args.date.replace('-', '')}.html",
    )
    x = [datetime.strptime(row["clientDate"], "%Y-%m-%d %H:%M:%S") for row in rows]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["powerNow"] for row in rows],
            mode="lines+markers",
            name=f"powerNow ({args.device_group})",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>powerNow=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[row["batEnergyPercent"] for row in rows],
            mode="lines",
            name="batEnergyPercent",
            yaxis="y2",
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>SOC=%{y:.2f}%<extra></extra>",
            opacity=0.5,
        )
    )
    fig.update_layout(
        title=f"SAJ plant energy every 5 minutes ({args.device_group}) - {args.date}",
        xaxis_title="Timestamp",
        yaxis_title="powerNow",
        yaxis2=dict(title="SOC %", overlaying="y", side="right"),
        hovermode="x unified",
        template="plotly_white",
    )
    fig.write_html(html_path, auto_open=False, include_plotlyjs=True)

    table_rows = "\n".join(
        (
            "<tr>"
            f"<td>{row['clientDate']}</td>"
            f"<td>{row['powerNow']}</td>"
            f"<td>{row['todayPvEnergy']}</td>"
            f"<td>{row['monthPvEnergy']}</td>"
            f"<td>{row['yearPvEnergy']}</td>"
            f"<td>{row['totalPvEnergy']}</td>"
            f"<td>{row['batEnergyPercent']}</td>"
            f"<td>{row['deviceStatus']}</td>"
            f"<td>{row['updateDate']}</td>"
            "</tr>"
        )
        for row in rows
    )
    with open(html_path, "a", encoding="utf-8") as report_file:
        report_file.write(
            f"""
<hr>
<h2>Queried points</h2>
<table border="1" cellspacing="0" cellpadding="4">
  <thead>
    <tr>
      <th>clientDate</th>
      <th>powerNow</th>
      <th>todayPvEnergy</th>
      <th>monthPvEnergy</th>
      <th>yearPvEnergy</th>
      <th>totalPvEnergy</th>
      <th>batEnergyPercent</th>
      <th>deviceStatus</th>
      <th>updateDate</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>
"""
        )

    print(f"PLOT DEBUG opening plant energy HTML report: {html_path}")
    os.startfile(html_path)


def run_zilio_debug(headers: dict[str, str], args: argparse.Namespace) -> None:
    start_time = args.start_time or f"{args.date} 00:00:00"
    end_time = args.end_time or f"{args.date} 23:55:00"
    plant_id = args.plant_id or ZILIO_GROUP_490KW_PLANT_ID

    print("== SAJ Zilio Group 490kW debug ==")
    print(f"plant_id: {plant_id}")
    print(f"window: {start_time} -> {end_time}")
    print(f"configured_devices: {len(ZILIO_GROUP_490KW_DEVICES)}")
    print("")

    plants = get_plants(headers)
    matching_plants = [
        plant for plant in plants
        if str(plant.get("plantId")) == plant_id or str(plant.get("plantName", "")).strip() == "Zilio Group"
    ]
    print(f"plants_returned: {len(plants)}")
    print(f"matching_plants: {len(matching_plants)}")
    for plant in matching_plants:
        print(
            f"PLANT DEBUG plantId={plant.get('plantId')} "
            f"plantName={plant.get('plantName')} "
            f"status={plant.get('plantStatus')} "
            f"installedCapacity={plant.get('installedCapacity')}"
        )
    print("-" * 140)

    devices = get_devices(headers, plant_id=plant_id)
    print(f"devices_returned_by_api: {len(devices)}")
    for device in devices:
        print(
            f"DEVICE DEBUG deviceSn={device.get('deviceSn')} "
            f"deviceType={device.get('deviceType')} "
            f"isOnline={device.get('isOnline')} isAlarm={device.get('isAlarm')}"
        )
    print("-" * 140)

    selected_devices = [
        str(device.get("deviceSn"))
        for device in devices
        if str(device.get("deviceSn")) in ZILIO_GROUP_490KW_DEVICES
    ]
    print(f"selected_devices_present: {len(selected_devices)}")
    print(f"selected_device_list: {selected_devices}")
    print("-" * 140)

    aggregated_totalpv_by_bucket: dict[datetime, float] = {}
    aggregated_sumpv_by_bucket: dict[datetime, float] = {}
    aggregated_c6_by_bucket: dict[datetime, float] = {}
    aggregated_s12_by_bucket: dict[datetime, float] = {}
    aggregated_s12_single_by_device = {
        device_sn: {} for device_sn in ZILIO_GROUP_490KW_S12_DEVICES
    }
    total_non_zero_samples = 0

    for device_sn in selected_devices:
        payload = get_device_history(
            headers,
            device_sn=device_sn,
            start_time=start_time,
            end_time=end_time,
            fields=args.fields,
        )
        rows = payload.get("data") or []
        parsed_rows = _parse_history_rows(rows)
        available_keys = sorted({key for row in rows[:5] for key in row.keys()})

        total_values = [_safe_float(row.get("totalPVPower")) for _, row in parsed_rows]
        total_values = [value for value in total_values if value is not None]
        sum_values = [_sum_pv_channels(row) for _, row in parsed_rows]
        sum_values = [value for value in sum_values if value is not None]
        non_zero_total = sum(1 for value in total_values if abs(value) > 0)
        non_zero_sum = sum(1 for value in sum_values if abs(value) > 0)
        total_non_zero_samples += non_zero_total

        print(
            f"REQUEST DEBUG device={device_sn} code={payload.get('code')} msg={payload.get('msg')} "
            f"raw_rows={len(rows)} parsed_rows={len(parsed_rows)}"
        )
        print(f"FIELDS DEBUG device={device_sn} first_keys={available_keys}")
        print(
            f"VALUE DEBUG device={device_sn} totalPVPower_non_zero={non_zero_total}/{len(total_values)} "
            f"sumPvChannels_non_zero={non_zero_sum}/{len(sum_values)} "
            f"totalPVPower_min={min(total_values) if total_values else None} "
            f"totalPVPower_max={max(total_values) if total_values else None} "
            f"sumPvChannels_min={min(sum_values) if sum_values else None} "
            f"sumPvChannels_max={max(sum_values) if sum_values else None}"
        )

        if parsed_rows:
            first_dt, first_row = parsed_rows[0]
            last_dt, last_row = parsed_rows[-1]
            print(f"ROW DEBUG device={device_sn} first_row:")
            _print_row_excerpt(first_row)
            print(f"ROW DEBUG device={device_sn} last_row:")
            _print_row_excerpt(last_row)

            sample_rows = []
            for dt, row in parsed_rows:
                total_power = _safe_float(row.get("totalPVPower"))
                pv_sum = _sum_pv_channels(row)
                bucket = _round_to_5min(dt)
                if total_power is not None:
                    aggregated_totalpv_by_bucket[bucket] = (
                        aggregated_totalpv_by_bucket.get(bucket, 0.0) + (total_power / 1000.0)
                    )
                if pv_sum is not None:
                    aggregated_sumpv_by_bucket[bucket] = (
                        aggregated_sumpv_by_bucket.get(bucket, 0.0) + (pv_sum / 1000.0)
                    )
                    if device_sn in ZILIO_GROUP_490KW_C6_DEVICES:
                        aggregated_c6_by_bucket[bucket] = (
                            aggregated_c6_by_bucket.get(bucket, 0.0) + (pv_sum / 1000.0)
                        )
                    if device_sn in ZILIO_GROUP_490KW_S12_DEVICES:
                        aggregated_s12_by_bucket[bucket] = (
                            aggregated_s12_by_bucket.get(bucket, 0.0) + (pv_sum / 1000.0)
                        )
                        aggregated_s12_single_by_device[device_sn][bucket] = (
                            aggregated_s12_single_by_device[device_sn].get(bucket, 0.0) + (pv_sum / 1000.0)
                        )

            for dt, row in parsed_rows[:10]:
                total_power = _safe_float(row.get("totalPVPower"))
                pv_sum = _sum_pv_channels(row)
                sample_rows.append(
                    {
                        "dataTime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "totalPVPower": total_power,
                        "sumPvChannels": pv_sum,
                        "todayPvEnergy": _safe_float(row.get("todayPvEnergy")),
                    }
                )

            print(f"SAMPLE DEBUG device={device_sn} first_10_rows:")
            print(json.dumps(sample_rows, ensure_ascii=False, indent=2))
            print(
                f"TIME DEBUG device={device_sn} first_dt={first_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                f"last_dt={last_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            print(f"ROW DEBUG device={device_sn} no parsed rows")

        if args.dump_json:
            _print_json_block(f"FULL PAYLOAD DEBUG device={device_sn}", payload)

        print("-" * 140)

    sorted_totalpv_buckets = sorted(aggregated_totalpv_by_bucket.items(), key=lambda item: item[0])
    sorted_sumpv_buckets = sorted(aggregated_sumpv_by_bucket.items(), key=lambda item: item[0])
    sorted_c6_buckets = sorted(aggregated_c6_by_bucket.items(), key=lambda item: item[0])
    sorted_s12_buckets = sorted(aggregated_s12_by_bucket.items(), key=lambda item: item[0])
    sorted_s12_single_buckets = {
        device_sn: sorted(series.items(), key=lambda item: item[0])
        for device_sn, series in aggregated_s12_single_by_device.items()
    }
    diff_buckets = sorted(
        {
            bucket: aggregated_c6_by_bucket.get(bucket, 0.0) - aggregated_s12_by_bucket.get(bucket, 0.0)
            for bucket in set(aggregated_c6_by_bucket) | set(aggregated_s12_by_bucket)
        }.items(),
        key=lambda item: item[0],
    )
    diff_single_buckets = {
        device_sn: sorted(
            {
                bucket: aggregated_c6_by_bucket.get(bucket, 0.0) - aggregated_s12_single_by_device[device_sn].get(bucket, 0.0)
                for bucket in set(aggregated_c6_by_bucket) | set(aggregated_s12_single_by_device[device_sn])
            }.items(),
            key=lambda item: item[0],
        )
        for device_sn in ZILIO_GROUP_490KW_S12_DEVICES
    }
    print(
        f"AGGREGATION DEBUG totalpv_bucket_count={len(sorted_totalpv_buckets)} "
        f"sumpv_bucket_count={len(sorted_sumpv_buckets)} "
        f"c6_bucket_count={len(sorted_c6_buckets)} "
        f"s12_bucket_count={len(sorted_s12_buckets)} "
        f"total_non_zero_samples={total_non_zero_samples}"
    )
    if sorted_sumpv_buckets:
        print("AGGREGATION DEBUG first_20_buckets:")
        first_buckets = [
            {
                "t": bucket.strftime("%Y-%m-%d %H:%M:%S"),
                "totalPVPower_kw": round(aggregated_totalpv_by_bucket.get(bucket, 0.0), 3),
                "sumPvChannels_kw": round(power_kw, 3),
                "c6_sum_kw": round(aggregated_c6_by_bucket.get(bucket, 0.0), 3),
                "s12_sum_kw": round(aggregated_s12_by_bucket.get(bucket, 0.0), 3),
                "c6_minus_s12_kw": round(
                    aggregated_c6_by_bucket.get(bucket, 0.0) - aggregated_s12_by_bucket.get(bucket, 0.0), 3
                ),
            }
            for bucket, power_kw in sorted_sumpv_buckets[:20]
        ]
        print(json.dumps(first_buckets, ensure_ascii=False, indent=2))

        x_totalpv = [bucket for bucket, _ in sorted_totalpv_buckets]
        y_totalpv = [power_kw for _, power_kw in sorted_totalpv_buckets]
        x_sumpv = [bucket for bucket, _ in sorted_sumpv_buckets]
        y_sumpv = [power_kw for _, power_kw in sorted_sumpv_buckets]
        x_c6 = [bucket for bucket, _ in sorted_c6_buckets]
        y_c6 = [power_kw for _, power_kw in sorted_c6_buckets]
        x_s12 = [bucket for bucket, _ in sorted_s12_buckets]
        y_s12 = [power_kw for _, power_kw in sorted_s12_buckets]
        x_diff = [bucket for bucket, _ in diff_buckets]
        y_diff = [power_kw for _, power_kw in diff_buckets]
        single_diff_axes = {
            device_sn: {
                "x": [bucket for bucket, _ in diff_single_buckets[device_sn]],
                "y": [power_kw for _, power_kw in diff_single_buckets[device_sn]],
                "label": ZILIO_GROUP_490KW_S12_LABELS[device_sn],
            }
            for device_sn in ZILIO_GROUP_490KW_S12_DEVICES
        }

        fig, ax = plt.subplots(figsize=(16, 7))
        ax.plot(x_c6, y_c6, label="4 inverter C6 from sum(pv1..pv16)", linewidth=2)
        ax.plot(x_s12, y_s12, label="3 storage S12 from sum(pv1..pv16)", linewidth=2)
        ax.plot(x_diff, y_diff, label="C6 - S12", linewidth=2.2)
        for device_sn in ZILIO_GROUP_490KW_S12_DEVICES:
            ax.plot(
                single_diff_axes[device_sn]["x"],
                single_diff_axes[device_sn]["y"],
                label=f"C6 - {single_diff_axes[device_sn]['label']}",
                linewidth=1.8,
            )
        ax.plot(x_sumpv, y_sumpv, label="All 7 devices from sum(pv1..pv16)", linewidth=1.5, alpha=0.5)
        ax.plot(x_totalpv, y_totalpv, label="All 7 devices from totalPVPower", linewidth=1.2, alpha=0.5)
        ax.set_title(f"SAJ Zilio Group 490kW debug - {args.date}")
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Power [kW]")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()

        report_path = os.path.join(
            tempfile.gettempdir(),
            f"saj_zilio_debug_{args.date.replace('-', '')}.html",
        )
        fig_plotly = go.Figure()
        fig_plotly.add_trace(
            go.Scatter(
                x=x_c6,
                y=y_c6,
                mode="lines+markers",
                name="4 inverter C6 from sum(pv1..pv16)",
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>C6=%{y:.3f} kW<extra></extra>",
            )
        )
        fig_plotly.add_trace(
            go.Scatter(
                x=x_s12,
                y=y_s12,
                mode="lines+markers",
                name="3 storage S12 from sum(pv1..pv16)",
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>S12=%{y:.3f} kW<extra></extra>",
            )
        )
        fig_plotly.add_trace(
            go.Scatter(
                x=x_diff,
                y=y_diff,
                mode="lines+markers",
                name="C6 - S12",
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>C6-S12=%{y:.3f} kW<extra></extra>",
            )
        )
        for device_sn in ZILIO_GROUP_490KW_S12_DEVICES:
            fig_plotly.add_trace(
                go.Scatter(
                    x=single_diff_axes[device_sn]["x"],
                    y=single_diff_axes[device_sn]["y"],
                    mode="lines+markers",
                    name=f"C6 - {single_diff_axes[device_sn]['label']}",
                    hovertemplate=(
                        "%{x|%Y-%m-%d %H:%M:%S}<br>"
                        f"C6-{single_diff_axes[device_sn]['label']}=%{{y:.3f}} kW<extra></extra>"
                    ),
                )
            )
        fig_plotly.add_trace(
            go.Scatter(
                x=x_sumpv,
                y=y_sumpv,
                mode="lines",
                name="All 7 devices from sum(pv1..pv16)",
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>All7 sum=%{y:.3f} kW<extra></extra>",
                opacity=0.45,
            )
        )
        fig_plotly.add_trace(
            go.Scatter(
                x=x_totalpv,
                y=y_totalpv,
                mode="lines",
                name="All 7 devices from totalPVPower",
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>All7 totalPV=%{y:.3f} kW<extra></extra>",
                opacity=0.45,
            )
        )
        fig_plotly.update_layout(
            title=f"SAJ Zilio Group 490kW debug - {args.date}",
            xaxis_title="Timestamp",
            yaxis_title="Power [kW]",
            hovermode="x unified",
            template="plotly_white",
        )
        fig_plotly.write_html(report_path, auto_open=False, include_plotlyjs=True)

        print(f"PLOT DEBUG opening HTML report: {report_path}")
        os.startfile(report_path)
        plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe SAJ endpoints for plant statistics and device history."
    )
    parser.add_argument(
        "--endpoint",
        choices=["plant-stats", "device-history", "plant-devices-compare", "zilio-debug", "ems-meter", "ems-history", "plant-stats-day", "plant-energy-day", "col-roigo-ems-last-hour"],
        default="zilio-debug",
        help="Which SAJ endpoint to probe.",
    )
    parser.add_argument("--plant-id", default=ZILIO_GROUP_490KW_PLANT_ID, help="SAJ plantId to query.")
    parser.add_argument("--device-sn", default="CSV6503J2416E00004", help="SAJ device serial number.")
    parser.add_argument("--ems-sn", default=None, help="SAJ EMS serial number for ems-meter mode.")
    parser.add_argument(
        "--device-group",
        choices=["all", "c6", "s12"],
        default="all",
        help="Device subset for plant-energy day probe.",
    )
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

    if args.endpoint == "col-roigo-ems-last-hour":
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        args.plant_id = COL_ROIGO_PLANT_ID
        args.ems_sn = COL_ROIGO_EMS_SN
        args.start_time = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")
        args.end_time = now.strftime("%Y-%m-%d %H:%M:%S")
        args.dump_json = True
        run_ems_history_debug(headers, args)
        return

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

    if args.endpoint == "plant-stats-day":
        run_plant_stats_day_probe(headers, args)
        return

    if args.endpoint == "plant-energy-day":
        run_plant_energy_day_probe(headers, args)
        return

    if args.endpoint == "ems-history":
        run_ems_history_debug(headers, args)
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

    if args.endpoint == "zilio-debug":
        run_zilio_debug(headers, args)
        return

    if args.endpoint == "ems-meter":
        run_ems_meter_debug(headers, args)
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
