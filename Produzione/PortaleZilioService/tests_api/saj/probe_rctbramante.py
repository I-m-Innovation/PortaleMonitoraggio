"""Probe SAJ ems_history data for the RCT-Bramante plant and display an interactive Plotly chart.

Plant info:
    name:    RCT-Bramante
    id:      25520042620
    ems_sn:  M5530J2428000023
    devices:    C6VC125J2430E03394 (inverter C6)
                CSV6503J2506E00137 (S12)
                CSV6503J2506E00141 (S12)

Usage (from repo root):
    python Produzione/PortaleZilioService/tests_api/saj/probe_rctbramante.py
    python Produzione/PortaleZilioService/tests_api/saj/probe_rctbramante.py --date 2026-03-31
    python Produzione/PortaleZilioService/tests_api/saj/probe_rctbramante.py --start-time "2026-03-31 06:00:00" --end-time "2026-03-31 20:00:00"
    python Produzione/PortaleZilioService/tests_api/saj/probe_rctbramante.py --dump-json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import plotly.graph_objects as go

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client

RCT_BRAMANTE_PLANT_ID = "25520042620"
RCT_BRAMANTE_EMS_SN = "M5530J2428000023"
RCT_BRAMANTE_DEVICES = [
    "C6VC125J2430E03394",  # inverter C6
    "CSV6503J2506E00137",  # S12
    "CSV6503J2506E00141",  # S12
]

MAX_WINDOW = timedelta(hours=1, minutes=55)


def _safe_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _print_generic_row_excerpt(row: dict, max_items: int = 30) -> None:
    excerpt = {key: row[key] for key in list(row.keys())[:max_items]}
    print(json.dumps(excerpt, ensure_ascii=False, indent=2))


def fetch_ems_history(
    headers: dict[str, str],
    plant_id: str,
    ems_sn: str,
    start: datetime,
    end: datetime,
    dump_json: bool = False,
) -> list[dict]:
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + MAX_WINDOW, end)
        windows.append((cursor, window_end))
        if window_end >= end:
            break
        cursor = window_end + timedelta(minutes=5)

    print(f"chunk_count: {len(windows)}")

    merged_by_time: dict[str, dict] = {}
    raw_payloads: list[dict] = []

    for idx, (window_start, window_end) in enumerate(windows, start=1):
        print(
            f"  chunk {idx}/{len(windows)}: "
            f"{window_start.strftime('%Y-%m-%d %H:%M:%S')} -> {window_end.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        payload = None
        for attempt in range(4):
            response = __import__("requests").get(
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
                wait = 0.6 * (attempt + 1)
                print(f"    rate-limit hit, retrying in {wait:.1f}s")
                time.sleep(wait)
                continue
            break

        if payload is None:
            continue

        raw_payloads.append(payload)
        chunk_rows = payload.get("data") or []
        print(f"    code={payload.get('code')} msg={payload.get('msg')} records={len(chunk_rows)}")

        for record in chunk_rows:
            if not isinstance(record, dict):
                continue
            data_time = record.get("dataTime")
            if data_time:
                merged_by_time[str(data_time)] = record

    if dump_json:
        print("\n== RAW PAYLOADS ==")
        print(json.dumps(raw_payloads, ensure_ascii=False, indent=2))
        print("=" * 80)

    return [merged_by_time[key] for key in sorted(merged_by_time)]


def parse_rows(rows: list[dict]) -> list[dict]:
    parsed = []
    for row in rows:
        dt_raw = row.get("dataTime")
        if not dt_raw:
            continue
        try:
            dt = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        parsed.append(
            {
                "dataTime": dt,
                "parallMeterPower": _safe_float(row.get("parallMeterPower")),
                "parallTotalPvPower": _safe_float(row.get("parallTotalPvPower")),
                "parallPVPower": _safe_float(row.get("parallPVPower")),
                "parallLoadPower": _safe_float(row.get("parallLoadPower")),
                "parallBatPower": _safe_float(row.get("parallBatPower")),
                "parallGridPower": _safe_float(row.get("parallGridPower")),
                "parallSOC": _safe_float(row.get("parallSOC")),
                "parallTodayPVEnergy": _safe_float(row.get("parallTodayPVEnergy")),
                "updateDate": row.get("updateDate"),
            }
        )
    return parsed


def build_html_report(
    parsed_ems: list[dict],
    aggregated_devices: list[dict],
    start: datetime,
    end: datetime,
) -> str:
    """Build interactive Plotly report with both EMS and device-history series."""
    fig = go.Figure()

    # ── Metodo 1: EMS history ────────────────────────────────────────────────
    if parsed_ems:
        x_ems = [row["dataTime"] for row in parsed_ems]

        def _add_ems(field: str, name: str, yaxis: str = "y", opacity: float = 1.0, dash: str = "solid") -> None:
            fig.add_trace(
                go.Scatter(
                    x=x_ems,
                    y=[row[field] for row in parsed_ems],
                    mode="lines+markers",
                    name=name,
                    yaxis=yaxis,
                    opacity=opacity,
                    line=dict(dash=dash),
                    hovertemplate=f"%{{x|%Y-%m-%d %H:%M:%S}}<br>{name}=%{{y:.3f}}<extra></extra>",
                )
            )

        _add_ems("parallMeterPower", "[EMS] parallMeterPower")
        _add_ems("parallTotalPvPower", "[EMS] parallTotalPvPower", dash="dot")
        _add_ems("parallPVPower", "[EMS] parallPVPower", dash="dot")
        _add_ems("parallLoadPower", "[EMS] parallLoadPower", dash="dot")
        _add_ems("parallBatPower", "[EMS] parallBatPower", dash="dot")
        _add_ems("parallGridPower", "[EMS] parallGridPower", dash="dot")
        _add_ems("parallSOC", "[EMS] parallSOC (%)", yaxis="y2", opacity=0.5)

    # ── Metodo 2: device historyDataCommon aggregato ─────────────────────────
    if aggregated_devices:
        x_dev = [row["dataTime"] for row in aggregated_devices]
        fig.add_trace(
            go.Scatter(
                x=x_dev,
                y=[row["totalPVPower_kW"] for row in aggregated_devices],
                mode="lines+markers",
                name="[Devices] sum(totalPVPower) kW",
                line=dict(width=2.5, color="green"),
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>sum_totalPVPower=%{y:.3f} kW<extra></extra>",
            )
        )

    fig.update_layout(
        title=f"SAJ — RCT-Bramante — {start.strftime('%Y-%m-%d')} — Confronto EMS vs Devices",
        xaxis_title="Timestamp",
        yaxis_title="Power [W] (EMS) / Power [kW] (Devices)",
        yaxis2=dict(title="SOC %", overlaying="y", side="right"),
        hovermode="x unified",
        template="plotly_white",
        height=650,
    )

    html_path = os.path.join(
        tempfile.gettempdir(),
        f"saj_rctbramante_{start.strftime('%Y%m%d_%H%M')}_{end.strftime('%H%M')}.html",
    )
    fig.write_html(html_path, auto_open=False, include_plotlyjs=True)

    # ── Tabella EMS ──────────────────────────────────────────────────────────
    ems_table = ""
    if parsed_ems:
        ems_rows_html = "\n".join(
            (
                "<tr>"
                f"<td>{row['dataTime'].strftime('%Y-%m-%d %H:%M:%S')}</td>"
                f"<td>{row['parallMeterPower']}</td>"
                f"<td>{row['parallTotalPvPower']}</td>"
                f"<td>{row['parallPVPower']}</td>"
                f"<td>{row['parallLoadPower']}</td>"
                f"<td>{row['parallBatPower']}</td>"
                f"<td>{row['parallGridPower']}</td>"
                f"<td>{row['parallSOC']}</td>"
                f"<td>{row['parallTodayPVEnergy']}</td>"
                "</tr>"
            )
            for row in parsed_ems
        )
        ems_table = f"""
<hr>
<h2>[Metodo 1 — EMS] emsHistoryData ({len(parsed_ems)} punti)</h2>
<table border="1" cellspacing="0" cellpadding="4" style="font-size:12px;font-family:monospace">
  <thead><tr>
    <th>dataTime</th><th>parallMeterPower</th><th>parallTotalPvPower</th>
    <th>parallPVPower</th><th>parallLoadPower</th><th>parallBatPower</th>
    <th>parallGridPower</th><th>parallSOC</th><th>parallTodayPVEnergy</th>
  </tr></thead>
  <tbody>{ems_rows_html}</tbody>
</table>"""

    # ── Tabella device aggregata ─────────────────────────────────────────────
    dev_table = ""
    if aggregated_devices:
        dev_rows_html = "\n".join(
            f"<tr><td>{row['dataTime'].strftime('%Y-%m-%d %H:%M:%S')}</td><td>{row['totalPVPower_kW']:.4f}</td></tr>"
            for row in aggregated_devices
        )
        dev_table = f"""
<hr>
<h2>[Metodo 2 — Devices] sum(totalPVPower) ({len(aggregated_devices)} punti)</h2>
<table border="1" cellspacing="0" cellpadding="4" style="font-size:12px;font-family:monospace">
  <thead><tr><th>dataTime (bucket 5min)</th><th>totalPVPower_kW (somma devices)</th></tr></thead>
  <tbody>{dev_rows_html}</tbody>
</table>"""

    with open(html_path, "a", encoding="utf-8") as f:
        f.write(ems_table + dev_table)

    return html_path


DEVICE_HISTORY_FIELDS = (
    "deviceSn,dataTime,totalPVPower,todayPvEnergy,"
    "pv1power,pv2power,pv3power,pv4power,pv5power,pv6power,"
    "pv7power,pv8power,pv9power,pv10power,pv11power,pv12power"
)


def _round_to_5min(dt: datetime) -> datetime:
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)


def fetch_single_device_history(
    headers: dict[str, str],
    device_sn: str,
    start: datetime,
    end: datetime,
) -> tuple[list[dict], int | None, str | None]:
    import requests as _requests
    response = _requests.get(
        f"{saj_client.BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn": device_sn,
            "startTime": start.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": DEVICE_HISTORY_FIELDS,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("data") or [], payload.get("code"), payload.get("msg")


def fetch_all_devices_aggregated(
    headers: dict[str, str],
    device_sns: list[str],
    start: datetime,
    end: datetime,
) -> tuple[list[dict], dict[str, list[dict]]]:
    """Query historyDataCommon for each device, aggregate totalPVPower into 5-min buckets.

    Returns:
        aggregated: list of {"dataTime": dt, "totalPVPower_kW": float} sorted by time
        per_device: {device_sn: list of raw rows} for detailed inspection
    """
    buckets: dict[datetime, float] = {}
    per_device: dict[str, list[dict]] = {}

    for device_sn in device_sns:
        rows, code, msg = fetch_single_device_history(headers, device_sn, start, end)
        per_device[device_sn] = rows
        print(f"  device={device_sn}  code={code} msg={msg}  records={len(rows)}")
        if rows:
            available_keys = sorted({key for row in rows[:3] for key in row.keys()})
            print(f"    fields: {available_keys}")
            non_zero = sum(1 for r in rows if _safe_float(r.get("totalPVPower")) not in (None, 0.0))
            print(f"    totalPVPower non-zero: {non_zero}/{len(rows)}")

        for row in rows:
            dt_raw = row.get("dataTime")
            if not dt_raw:
                continue
            try:
                dt = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            power_w = _safe_float(row.get("totalPVPower"))
            if power_w is None:
                continue
            bucket = _round_to_5min(dt)
            buckets[bucket] = buckets.get(bucket, 0.0) + power_w

    aggregated = [
        {"dataTime": bucket, "totalPVPower_kW": watts / 1000.0}
        for bucket, watts in sorted(buckets.items())
    ]
    return aggregated, per_device


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe SAJ ems_history for RCT-Bramante.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Data YYYY-MM-DD (default: oggi).")
    parser.add_argument("--start-time", default=None, help="Inizio finestra 'YYYY-MM-DD HH:MM:SS'.")
    parser.add_argument("--end-time", default=None, help="Fine finestra 'YYYY-MM-DD HH:MM:SS'.")
    parser.add_argument("--dump-json", action="store_true", help="Stampa JSON grezzo delle risposte API.")
    args = parser.parse_args()

    start = datetime.strptime(args.start_time or f"{args.date} 00:00:00", "%Y-%m-%d %H:%M:%S")
    end = datetime.strptime(args.end_time or f"{args.date} 23:55:00", "%Y-%m-%d %H:%M:%S")

    print("== SAJ ems_history probe — RCT-Bramante ==")
    print(f"plant_id : {RCT_BRAMANTE_PLANT_ID}")
    print(f"ems_sn   : {RCT_BRAMANTE_EMS_SN}")
    print(f"finestra : {start} -> {end}")
    print("")

    token = saj_client.get_token()
    headers = saj_client.build_headers(token)

    # ── 1. DEVICE DISCOVERY ─────────────────────────────────────────────────
    print("== [1/3] Device discovery ==")
    devices = saj_client.get_devices(headers, plant_id=RCT_BRAMANTE_PLANT_ID)
    print(f"device_count: {len(devices)}")
    for device in devices:
        print(
            f"  deviceSn={device.get('deviceSn')}  "
            f"deviceType={device.get('deviceType')}  "
            f"isOnline={device.get('isOnline')}  "
            f"isAlarm={device.get('isAlarm')}"
        )
    ems_candidates = [
        d.get("deviceSn") for d in devices
        if str(d.get("deviceSn", "")).upper().startswith("M55")
    ]
    if ems_candidates:
        print(f"  >> EMS trovati tra i device: {ems_candidates}")
    else:
        print("  >> Nessun device M55* trovato — EMS potrebbe non essere esposto da questo endpoint")
    print("")

    # ── 2. METODO 2: historyDataCommon su tutti i device ────────────────────
    print("== [2/3] Metodo 2 — historyDataCommon (tutti i device) ==")
    aggregated_devices, per_device_rows = fetch_all_devices_aggregated(
        headers, RCT_BRAMANTE_DEVICES, start, end
    )
    print(f"  punti aggregati (5-min bucket): {len(aggregated_devices)}")
    if aggregated_devices:
        max_dev_power = max(r["totalPVPower_kW"] for r in aggregated_devices)
        print(f"  picco sum(totalPVPower): {max_dev_power:.3f} kW")
        print(f"  primo bucket: {aggregated_devices[0]}")
        print(f"  ultimo bucket: {aggregated_devices[-1]}")
    else:
        print("  >> Nessun dato dai device — impianto non attivo o data senza produzione")
    print("")

    # ── 3. METODO 1: emsHistoryData ──────────────────────────────────────────
    print("== [3/3] Metodo 1 — emsHistoryData ==")
    ems_rows = fetch_ems_history(
        headers=headers,
        plant_id=RCT_BRAMANTE_PLANT_ID,
        ems_sn=RCT_BRAMANTE_EMS_SN,
        start=start,
        end=end,
        dump_json=args.dump_json,
    )
    print(f"  records_after_merge: {len(ems_rows)}")

    parsed_ems: list[dict] = []
    if ems_rows:
        available_keys = sorted({key for row in ems_rows[:5] for key in row.keys()})
        print(f"  FIELDS: {available_keys}")
        print("  primo record:")
        _print_generic_row_excerpt(ems_rows[0])
        print("  ultimo record:")
        _print_generic_row_excerpt(ems_rows[-1])
        parsed_ems = parse_rows(ems_rows)
        last_energy = next(
            (r["parallTodayPVEnergy"] for r in reversed(parsed_ems) if r["parallTodayPVEnergy"] is not None),
            None,
        )
        max_meter = max((r["parallMeterPower"] for r in parsed_ems if r["parallMeterPower"] is not None), default=None)
        print(f"  parallTodayPVEnergy (ultimo): {last_energy}")
        print(f"  parallMeterPower (picco): {max_meter} W")
    else:
        print("  >> 0 record dall'EMS.")
        if aggregated_devices:
            print(f"  >> I device hanno dati ma l'EMS no — EMS SN '{RCT_BRAMANTE_EMS_SN}' probabilmente errato.")
        else:
            print("  >> Anche i device non hanno dati — impianto non attivo per questa data.")

    if not parsed_ems and not aggregated_devices:
        print("\nNessun dato da nessuna delle due sorgenti. Niente da visualizzare.")
        return

    html_path = build_html_report(parsed_ems, aggregated_devices, start, end)
    print(f"\nReport HTML: {html_path}")
    os.startfile(html_path)


if __name__ == "__main__":
    main()
