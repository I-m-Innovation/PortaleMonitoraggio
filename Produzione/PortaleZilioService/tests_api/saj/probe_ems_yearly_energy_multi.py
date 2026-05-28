"""Probe SAJ EMS yearly energy fields for multiple plants.

The script reads one short EMS history window for each selected plant and
prints the yearly cumulative fields exposed by SAJ in that record.

Edit `EMS_PLANTS` to add or change plants.

Usage from repo root:
    python Produzione/PortaleZilioService/tests_api/saj/probe_ems_yearly_energy_multi.py
    python Produzione/PortaleZilioService/tests_api/saj/probe_ems_yearly_energy_multi.py --date 2026-05-28

─────────────────────────────────────────────────────────────────────────────
LOGICA DI CALCOLO ENERGIA ANNUALE
─────────────────────────────────────────────────────────────────────────────

Impianti normali (EMS):
    La maggior parte degli impianti espone l'energia annuale direttamente
    tramite l'endpoint `emsHistoryData`. I campi utilizzati sono:
        - `parallYearPVEnergy`  → energia prodotta dall'anno
        - `parallYearSellEnergy` → energia immessa in rete dall'anno
        - autoconsumo = parallYearPVEnergy - parallYearSellEnergy

Col Roigo 50 kWp — impianto con fallback device-level:
    Il communication module (ems_sn M5380J2415071297) risponde su
    `emsHistoryData` con code=200 ma senza record utili. I dati energetici
    sono disponibili solo tramite lo storage inverter (device_sn
    CSV6503J2416E00004) attraverso l'endpoint `historyDataCommon`.

    Strategia adottata (dopo probe e confronto con la dashboard SAJ):
        - Si scaricano tutti i record giornalieri dall'1 gennaio alla data
        target, iterando un giorno alla volta.
        - L'energia annuale viene calcolata come DELTA dei contatori cumulativi
        lifetime tra il primo e l'ultimo record dell'anno:
            produzione  = totalPvEnergy[ultimo]   - totalPvEnergy[primo]
            immessa     = totalSellEnergy[ultimo]  - totalSellEnergy[primo]
            autoconsumo = produzione - immessa

    Perché il delta e non la somma dei valori giornalieri (`todayPvEnergy`)?
    La somma sottostima perché alcuni giorni non hanno record (3 giorni
    mancanti su 148 nel probe del 28/05/2026 → −285 kWh di errore).
    Il delta dei contatori cumulativi ha prodotto uno scarto di soli ~3 kWh
    rispetto alla dashboard SAJ (18265 vs 18304 kWh), differenza spiegata
    dal tempo trascorso tra il probe e lo screenshot della dashboard.

    Perché `totalSellEnergy` e non `totalFeedInEnergy` per l'immessa?
    `totalFeedInEnergy` ha mostrato un delta di soli ~122 kWh sull'intero
    anno, chiaramente non rappresentativo per un impianto da 50 kWp.
    `totalSellEnergy` è coerente con il campo giornaliero `todaySellEnergy`
    e con i campi EMS degli altri impianti (`parallYearSellEnergy`).

─────────────────────────────────────────────────────────────────────────────
PROBLEMATICHE RISCONTRATE
─────────────────────────────────────────────────────────────────────────────

1. Token SAJ scaduto durante il fetch multi-impianto:
    Nel run che processa tutti e 5 gli impianti, i 4 impianti EMS vengono
    interrogati prima di Col Roigo. Quando poi parte il ciclo da 148 giorni
    di `fetch_device_history_rows`, il token acquisito all'inizio scade
    a metà ciclo (~giorno 30-31) e le risposte successive tornano vuote
    silenziosamente — senza errore HTTP, solo `data: []`.
    Sintomo osservato: `last_dataTime` fermo al 22/05 invece del 28/05,
    con ~1300 kWh persi.
    Fix: `fetch_device_history_rows` accetta un `headers_factory` callable
    e riacquista il token ogni `TOKEN_REFRESH_EVERY_DAYS` (30) giorni.

2. Strategia somma giornaliera (abbandonata):
    La versione precedente sommava `todayPvEnergy` per ogni giorno.
    Produceva −285 kWh rispetto alla dashboard per i 3 giorni mancanti.
    Sostituita con il delta dei contatori cumulativi (vedi sopra).
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
    "colroigo50kwp": {
        "label": "Col Roigo 50 kWp",
        "plant_id": "24110165619",
        "ems_sn": "M5380J2415071297",
        "device_sn": "CSV6503J2416E00004",
    },
}

DEFAULT_PROBE_DATE = date.today()


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


def fetch_ems_year_snapshot_rows(
    headers: dict[str, str],
    plant_id: str,
    ems_sn: str,
    probe_date: date,
) -> list[dict]:
    now = datetime.now()
    end_dt = min(datetime.combine(probe_date, time(23, 59, 59)), now)
    start_dt = end_dt - timedelta(minutes=10)
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
    return [row for row in rows if isinstance(row, dict)]


DEVICE_YEAR_FIELDS = (
    "deviceSn,dataTime,totalPvEnergy,totalFeedInEnergy,totalSellEnergy,"
    "todayPvEnergy,todaySellEnergy,todayFeedInEnergy"
)


TOKEN_REFRESH_EVERY_DAYS = 30


def fetch_device_history_rows(
    headers: dict[str, str],
    device_sn: str,
    start_date: date,
    end_date: date,
    *,
    progress_label: str | None = None,
    headers_factory: "Callable[[], dict[str, str]] | None" = None,
) -> list[dict]:
    rows_by_time: dict[str, dict] = {}
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    processed_days = 0
    while current_date <= end_date:
        processed_days += 1
        # Rinfresca il token ogni TOKEN_REFRESH_EVERY_DAYS per evitare che
        # scada durante run multi-impianto lunghi (es. 148 giorni per Col Roigo).
        if headers_factory is not None and processed_days % TOKEN_REFRESH_EVERY_DAYS == 1 and processed_days > 1:
            headers = headers_factory()
        if progress_label:
            print(
                f"{progress_label}: {processed_days}/{total_days} "
                f"giorni - {current_date.isoformat()}",
                flush=True,
            )
        start_dt = datetime.combine(current_date, time(0, 0, 0))
        if current_date == date.today():
            end_dt = datetime.now()
        else:
            end_dt = datetime.combine(current_date, time(23, 59, 59))
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
                "fields": DEVICE_YEAR_FIELDS,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        for row in payload.get("data") or []:
            if not isinstance(row, dict):
                continue
            data_time = row.get("dataTime")
            if data_time:
                rows_by_time[str(data_time)] = row
        current_date += timedelta(days=1)
    return [rows_by_time[key] for key in sorted(rows_by_time)]


def _latest_row(rows: list[dict]) -> dict:
    candidates: list[tuple[datetime, dict]] = []
    for row in rows:
        timestamp = _parse_timestamp(row.get("dataTime"))
        if timestamp is not None:
            candidates.append((timestamp, row))
    if not candidates:
        return {}
    return max(candidates, key=lambda item: item[0])[1]


def get_latest_yearly_fields(rows: list[dict]) -> dict:
    latest = _latest_row(rows)
    if not latest:
        return {}
    pv_energy = _safe_float(latest.get("parallYearPVEnergy"))
    # La card annuale della supervisione SAJ mostra:
    # - PV Energy: `parallYearPVEnergy`
    # - Export Energy: `parallYearSellEnergy`
    # - Self-Consumption Energy: differenza tra i due campi sopra
    #
    # Durante il probe `parallYearFeedInEnergy` sembrava un candidato naturale,
    # ma ha prodotto valori incoerenti con la supervisione (ad esempio molto
    # maggiori della produzione annua). Il campo corretto per "energia immessa"
    # nella card e' `parallYearSellEnergy`, coerente anche con il giornaliero
    # `parallTodaySellEnergy`.
    exported_energy = _safe_float(latest.get("parallYearSellEnergy"))
    return {
        "dataTime": latest.get("dataTime"),
        "parallYearPVEnergy": pv_energy,
        "parallYearSellEnergy": exported_energy,
        "parallYearPVEnergy - parallYearSellEnergy": (
            pv_energy - exported_energy
            if pv_energy is not None and exported_energy is not None
            else None
        ),
    }


def get_device_yearly_fields_from_history(rows: list[dict]) -> dict:
    sorted_rows = [
        (_parse_timestamp(row.get("dataTime")), row)
        for row in rows
        if _parse_timestamp(row.get("dataTime")) is not None
    ]
    if not sorted_rows:
        return {}
    sorted_rows.sort(key=lambda item: item[0])
    _, first = sorted_rows[0]
    _, latest = sorted_rows[-1]

    # Fallback device-level usato per Col Roigo: il communication module
    # risponde su `emsHistoryData` con code=200 ma senza record, mentre lo
    # storage inverter espone i dati tramite `historyDataCommon`.
    #
    # Strategia: delta dei contatori cumulativi `totalPvEnergy` e
    # `totalSellEnergy` tra il primo e l'ultimo record dell'anno. Il delta
    # e' risultato piu' accurato della somma dei valori giornalieri perche'
    # la somma sottostima quando alcuni giorni non hanno record.
    first_total_pv_energy = _safe_float(first.get("totalPvEnergy"))
    latest_total_pv_energy = _safe_float(latest.get("totalPvEnergy"))
    first_total_sell_energy = _safe_float(first.get("totalSellEnergy"))
    latest_total_sell_energy = _safe_float(latest.get("totalSellEnergy"))
    pv_energy = (
        latest_total_pv_energy - first_total_pv_energy
        if latest_total_pv_energy is not None and first_total_pv_energy is not None
        else None
    )
    exported_energy = (
        latest_total_sell_energy - first_total_sell_energy
        if latest_total_sell_energy is not None and first_total_sell_energy is not None
        else None
    )
    # Somme giornaliere mantenute come debug
    latest_pv_by_date: dict[date, float] = {}
    latest_sell_by_date: dict[date, float] = {}
    for timestamp, row in sorted_rows:
        pv_day_energy = _safe_float(row.get("todayPvEnergy"))
        if pv_day_energy is not None:
            latest_pv_by_date[timestamp.date()] = pv_day_energy
        sell_energy = _safe_float(row.get("todaySellEnergy"))
        if sell_energy is not None:
            latest_sell_by_date[timestamp.date()] = sell_energy
    pv_day_sum = sum(latest_pv_by_date.values()) if latest_pv_by_date else None
    sell_day_sum = sum(latest_sell_by_date.values()) if latest_sell_by_date else None
    return {
        "dataTime": latest.get("dataTime"),
        "parallYearPVEnergy": pv_energy,
        "parallYearSellEnergy": exported_energy,
        "parallYearPVEnergy - parallYearSellEnergy": (
            pv_energy - exported_energy
            if pv_energy is not None and exported_energy is not None
            else None
        ),
        "debug_first_dataTime": first.get("dataTime"),
        "debug_last_dataTime": latest.get("dataTime"),
        "debug_first_totalPvEnergy": first_total_pv_energy,
        "debug_latest_totalPvEnergy": latest_total_pv_energy,
        "debug_first_totalSellEnergy": first_total_sell_energy,
        "debug_latest_totalSellEnergy": latest_total_sell_energy,
        "debug_days_with_pv": len(latest_pv_by_date),
        "debug_todayPvEnergy_sum": pv_day_sum,
        "debug_todaySellEnergy_sum": sell_day_sum,
    }


def _format_value(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "N/D"


def print_header() -> None:
    print(
        f"{'impianto':<24} | "
        f"{'probe_date':<10} | "
        f"{'dataTime':<19} | "
        f"{'energia annuale generata':>25} | "
        f"{'energia annuale immessa':>24} | "
        f"{'autoconsumo annuale':>24}"
    )
    print(
        f"{'':<24} | "
        f"{'':<10} | "
        f"{'':<19} | "
        f"{'(parallYearPVEnergy)':>25} | "
        f"{'(parallYearSellEnergy)':>24} | "
        f"{'(PV - Sell)':>24}"
    )
    print("-" * 139)


def print_row(plant_label: str, probe_date: date, fields: dict) -> None:
    print(
        f"{plant_label:<24} | "
        f"{probe_date.isoformat():<10} | "
        f"{str(fields.get('dataTime') or 'N/D'):<19} | "
        f"{_format_value(fields.get('parallYearPVEnergy')):>25} | "
        f"{_format_value(fields.get('parallYearSellEnergy')):>24} | "
        f"{_format_value(fields.get('parallYearPVEnergy - parallYearSellEnergy')):>24}"
    )


def print_device_debug(fields: dict) -> None:
    print("  debug device_history:")
    print(f"    first_dataTime: {fields.get('debug_first_dataTime') or 'N/D'}")
    print(f"    last_dataTime: {fields.get('debug_last_dataTime') or 'N/D'}")
    print(f"    first_totalPvEnergy: {_format_value(fields.get('debug_first_totalPvEnergy'))}")
    print(f"    latest_totalPvEnergy: {_format_value(fields.get('debug_latest_totalPvEnergy'))}")
    print(f"    delta_totalPvEnergy (used): {_format_value(fields.get('parallYearPVEnergy'))}")
    print(f"    first_totalSellEnergy: {_format_value(fields.get('debug_first_totalSellEnergy'))}")
    print(f"    latest_totalSellEnergy: {_format_value(fields.get('debug_latest_totalSellEnergy'))}")
    print(f"    delta_totalSellEnergy (used): {_format_value(fields.get('parallYearSellEnergy'))}")
    print(f"    days_with_todayPvEnergy: {fields.get('debug_days_with_pv') or 0}")
    print(f"    sum_todayPvEnergy: {_format_value(fields.get('debug_todayPvEnergy_sum'))}")
    print(f"    sum_todaySellEnergy: {_format_value(fields.get('debug_todaySellEnergy_sum'))}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print SAJ EMS yearly energy fields.")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=DEFAULT_PROBE_DATE,
        help="Snapshot date to probe in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--plant",
        action="append",
        choices=sorted(EMS_PLANTS),
        help="Plant key to probe. Can be repeated. Defaults to all EMS_PLANTS.",
    )
    parser.add_argument(
        "--debug-device",
        action="store_true",
        help="Print device-history debug values for fallback plants like Col Roigo.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_keys = args.plant or list(EMS_PLANTS)

    print_header()
    for plant_key in selected_keys:
        plant = EMS_PLANTS[plant_key]
        headers = force_new_saj_headers()
        rows = fetch_ems_year_snapshot_rows(
            headers,
            plant["plant_id"],
            plant["ems_sn"],
            args.date,
        )
        if rows:
            fields = get_latest_yearly_fields(rows)
        elif plant.get("device_sn"):
            start_of_year = date(args.date.year, 1, 1)
            device_rows = fetch_device_history_rows(
                headers,
                plant["device_sn"],
                start_of_year,
                args.date,
                progress_label=plant["label"],
                headers_factory=force_new_saj_headers,
            )
            fields = get_device_yearly_fields_from_history(device_rows)
        else:
            fields = {}
        print_row(plant["label"], args.date, fields)
        if args.debug_device and fields.get("debug_first_dataTime"):
            print_device_debug(fields)


if __name__ == "__main__":
    main()
