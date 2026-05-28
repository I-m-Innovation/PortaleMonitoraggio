"""Probe per validare il calcolo dell'energia immessa in rete di Col Roigo
usando solo 2 chiamate HTTP (delta contatori cumulativi totalSellEnergy),
invece del loop giorno-per-giorno usato nel probe esplorativo.

Logica:
    - Chiamata 1: snapshot di totalSellEnergy intorno all'inizio del range
                  (finestra di 24h centrata su start_date)
    - Chiamata 2: snapshot di totalSellEnergy intorno alla fine del range
                  (finestra di 24h centrata su end_date)
    - energia_immessa = valore_fine - valore_inizio

Confrontare il risultato con:
    - Dashboard SAJ (Export Energy)
    - Output del probe giornaliero (somma todaySellEnergy)
    - Output del probe annuale (delta totalSellEnergy su tutti i 148 giorni)

Usage from repo root:
    python Produzione/PortaleZilioService/tests_api/saj/probe_colroigo_sell_energy_snapshot.py
    python Produzione/PortaleZilioService/tests_api/saj/probe_colroigo_sell_energy_snapshot.py --start-date 2026-01-01 --end-date 2026-05-27
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import requests

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client


DEVICE_SN = "CSV6503J2416E00004"
FIELDS = "deviceSn,dataTime,totalPvEnergy,totalSellEnergy,totalFeedInEnergy"


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


def fetch_snapshot_at(headers: dict[str, str], target_date: date, label: str) -> dict:
    """Scarica l'ultimo record disponibile nella finestra di 24h che termina
    a fine giornata di target_date (o all'ora corrente se è oggi)."""
    if target_date == date.today():
        end_dt = datetime.now()
    else:
        end_dt = datetime.combine(target_date, time(23, 59, 59))
    start_dt = end_dt - timedelta(hours=24)

    print(f"\n--- snapshot {label} ({target_date}) ---")
    print(f"  window: {start_dt} → {end_dt}")

    response = requests.get(
        f"{saj_client.BASE_URL}/open/api/device/historyDataCommon",
        headers={**headers, "Content-Type": "application/json"},
        params={
            "deviceSn": DEVICE_SN,
            "startTime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": FIELDS,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data") or []
    print(f"  code={payload.get('code')} msg={payload.get('msg')} records={len(rows)}")

    if not rows:
        print("  ATTENZIONE: nessun record trovato per questa finestra")
        return {}

    # Prendi il record con il timestamp più recente
    candidates = [
        (ts, row)
        for row in rows
        if isinstance(row, dict) and (ts := _parse_timestamp(row.get("dataTime"))) is not None
    ]
    if not candidates:
        print("  ATTENZIONE: record trovati ma nessun dataTime valido")
        return {}

    _, latest = max(candidates, key=lambda x: x[0])
    print(f"  dataTime utilizzato:    {latest.get('dataTime')}")
    print(f"  totalPvEnergy:          {latest.get('totalPvEnergy')}")
    print(f"  totalSellEnergy:        {latest.get('totalSellEnergy')}")
    print(f"  totalFeedInEnergy:      {latest.get('totalFeedInEnergy')}")
    return latest


def parse_args() -> argparse.Namespace:
    yesterday = date.today() - timedelta(days=1)
    parser = argparse.ArgumentParser(
        description="Valida il calcolo energia immessa Col Roigo con 2 sole chiamate HTTP."
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date(date.today().year, 1, 1),
        help="Inizio range (default: 1 gennaio anno corrente)",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=yesterday,
        help="Fine range (default: ieri)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.end_date < args.start_date:
        raise SystemExit("--end-date deve essere >= --start-date")

    print(f"Col Roigo 50 kWp — device_sn: {DEVICE_SN}")
    print(f"Range: {args.start_date} → {args.end_date}")

    headers = force_new_saj_headers()
    snap_start = fetch_snapshot_at(headers, args.start_date, "inizio range")
    snap_end = fetch_snapshot_at(headers, args.end_date, "fine range")

    total_pv_start = _safe_float(snap_start.get("totalPvEnergy"))
    total_pv_end = _safe_float(snap_end.get("totalPvEnergy"))
    total_sell_start = _safe_float(snap_start.get("totalSellEnergy"))
    total_sell_end = _safe_float(snap_end.get("totalSellEnergy"))
    total_feedin_start = _safe_float(snap_start.get("totalFeedInEnergy"))
    total_feedin_end = _safe_float(snap_end.get("totalFeedInEnergy"))

    def delta(a, b):
        if a is not None and b is not None:
            return round(b - a, 3)
        return None

    def fmt(v):
        return f"{v:.3f} kWh" if v is not None else "N/D"

    pv_delta = delta(total_pv_start, total_pv_end)
    sell_delta = delta(total_sell_start, total_sell_end)
    feedin_delta = delta(total_feedin_start, total_feedin_end)
    autoconsumo = round(pv_delta - sell_delta, 3) if pv_delta is not None and sell_delta is not None else None

    print("\n" + "=" * 60)
    print("RISULTATO (delta 2 snapshot, 2 chiamate HTTP totali)")
    print("=" * 60)
    print(f"  Energia prodotta   (delta totalPvEnergy):    {fmt(pv_delta)}")
    print(f"  Energia immessa    (delta totalSellEnergy):  {fmt(sell_delta)}")
    print(f"  Energia autoconsumata (prodotta - immessa):  {fmt(autoconsumo)}")
    print(f"  [debug] delta totalFeedInEnergy:             {fmt(feedin_delta)}")
    print("=" * 60)
    print("\nConfronta con la dashboard SAJ (Export Energy) e con")
    print("l'output del probe annuale (delta su 148 giorni).")


if __name__ == "__main__":
    main()
