"""
Probe: confronto metodi energia prodotta YTD per Zilio Group.

Obiettivo:
- vedere quanto produce il perimetro "solo inverter attivi";
- vedere quanto aggiungono gli inverter storici/rimossi fino alla loro data fine;
- confrontare il risultato con il campo EMS annuale della supervisione SAJ;
- confrontare tutto con il valore salvato dal portale.

Endpoint usati:
- device daily: GET /open/api/device/historyDataCommon
  fields=deviceSn,dataTime,todayPvEnergy
- EMS yearly:   GET /open/api/device/emsHistoryData
  campo letto: parallYearPVEnergy
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import os
import sys

import django
import requests


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PortaleImpianti_project.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from PortaleZilioService.API_inverter import saj_client
from PortaleZilioService.models import ImpiantoAnagrafica


DEFAULT_START = date(2026, 1, 1)
DEFAULT_END = date(2026, 5, 28)
DEFAULT_SUPERVISION_KWH = Decimal("23094.55")

ZILIO_PLANT_NAME = "Zilio Group"
ZILIO_PLANT_ID = "24031286133"
ZILIO_EMS_SN = "M5530J2428000038"


@dataclass(frozen=True)
class DevicePeriod:
    sn: str
    start: date
    end: date | None
    label: str
    active: bool


@dataclass
class DeviceResult:
    sn: str
    label: str
    start: date | None
    end: date | None
    total_kwh: Decimal
    days_ok: int
    days_skip: int
    missing_dates: list[date]


@dataclass
class ScenarioResult:
    key: str
    label: str
    endpoint: str
    field: str
    total_kwh: Decimal | None
    details: list[DeviceResult]
    note: str = ""


DEVICES = [
    DevicePeriod(
        sn="C6T9104J2315E00670",
        start=date(2025, 1, 9),
        end=None,
        label="attivo 1",
        active=True,
    ),
    DevicePeriod(
        sn="C6V9104G2424E00228",
        start=date(2025, 1, 9),
        end=None,
        label="attivo 2",
        active=True,
    ),
    DevicePeriod(
        sn="C6V9104J2421E01334",
        start=date(2025, 1, 9),
        end=date(2026, 5, 18),
        label="storico/rimosso 1",
        active=False,
    ),
    DevicePeriod(
        sn="C6T9104J2314E00560",
        start=date(2025, 1, 9),
        end=date(2026, 5, 19),
        label="storico/rimosso 2",
        active=False,
    ),
]


def decimal_kwh(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def clamp_period(device: DevicePeriod, start_date: date, end_date: date) -> tuple[date, date] | None:
    start = max(device.start, start_date)
    end = min(device.end or end_date, end_date)
    if start > end:
        return None
    return start, end


def calc_device_daily_today_pv_energy(
    device: DevicePeriod,
    start_date: date,
    end_date: date,
    *,
    renew_token_monthly: bool = True,
    verbose: bool = True,
) -> DeviceResult:
    clamped = clamp_period(device, start_date, end_date)
    if clamped is None:
        return DeviceResult(device.sn, device.label, None, None, Decimal("0.00"), 0, 0, [])

    start, end = clamped
    total = Decimal("0.00")
    days_ok = 0
    days_skip = 0
    missing_dates: list[date] = []
    headers = None
    current_month = None

    if verbose:
        total_days = (end - start).days + 1
        print(f"  - {device.sn} ({device.label}): {start}..{end} ({total_days} giorni)")

    for current in date_range(start, end):
        if headers is None or (renew_token_monthly and current.month != current_month):
            token = saj_client.get_token(force_refresh=True)
            headers = saj_client.build_headers(token)
            current_month = current.month
            if verbose:
                print(f"    token nuovo mese={current:%Y-%m}")

        value = saj_client.get_device_daily_pv_energy_kwh(headers, device.sn, current)
        if value is None:
            days_skip += 1
            missing_dates.append(current)
        else:
            total += decimal_kwh(value)
            days_ok += 1

    result = DeviceResult(device.sn, device.label, start, end, total, days_ok, days_skip, missing_dates)
    if verbose:
        print(
            f"    totale={result.total_kwh} kWh "
            f"(giorni con dati={days_ok}, skip={days_skip})"
        )
        if missing_dates:
            preview = ", ".join(d.isoformat() for d in missing_dates[:20])
            suffix = " ..." if len(missing_dates) > 20 else ""
            print(f"    date senza dati: {preview}{suffix}")
    return result


def fetch_device_daily_results(
    devices: list[DevicePeriod],
    start_date: date,
    end_date: date,
    *,
    verbose: bool,
) -> dict[str, DeviceResult]:
    print(f"\n{'=' * 80}")
    print("DOWNLOAD DEVICE historyDataCommon")
    print(f"{'=' * 80}")
    print("Ogni device viene scaricato una sola volta; gli scenari A/B/C riusano questi risultati.")
    results: dict[str, DeviceResult] = {}
    for device in devices:
        results[device.sn] = calc_device_daily_today_pv_energy(
            device,
            start_date,
            end_date,
            verbose=verbose,
        )
    return results


def build_device_daily_scenario(
    key: str,
    label: str,
    devices: list[DevicePeriod],
    results_by_sn: dict[str, DeviceResult],
    note: str = "",
) -> ScenarioResult:
    print(f"\n{'=' * 80}")
    print(f"{label}")
    print(f"{'=' * 80}")
    print("Metodo: historyDataCommon / todayPvEnergy, somma risultati device gia' scaricati")

    details = [results_by_sn[device.sn] for device in devices]
    total = sum((result.total_kwh for result in details), Decimal("0.00"))
    for result in details:
        date_range_text = (
            f"{result.start}..{result.end}"
            if result.start is not None and result.end is not None
            else "fuori range"
        )
        print(
            f"  - {result.sn} ({result.label}): {result.total_kwh} kWh "
            f"(giorni con dati={result.days_ok}, skip={result.days_skip}, range={date_range_text})"
        )
    print(f"TOTALE {label}: {total} kWh")
    return ScenarioResult(
        key=key,
        label=label,
        endpoint="/open/api/device/historyDataCommon",
        field="todayPvEnergy",
        total_kwh=total,
        details=details,
        note=note,
    )


def get_ems_year_pv_energy_kwh(at_date: date) -> tuple[Decimal | None, str | None]:
    token = saj_client.get_token(force_refresh=True)
    headers = saj_client.build_headers(token)
    now = datetime.now()
    end_dt = min(datetime.combine(at_date, time(23, 59, 59)), now)
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
            "emsSn": ZILIO_EMS_SN,
            "plantId": ZILIO_PLANT_ID,
        },
        timeout=30,
    )
    response.raise_for_status()
    records = response.json().get("data") or []
    if not records:
        return None, None

    latest = max(records, key=lambda record: str(record.get("dataTime") or ""))
    value = latest.get("parallYearPVEnergy")
    if value in (None, ""):
        return None, latest.get("dataTime")
    return decimal_kwh(value), latest.get("dataTime")


def run_ems_yearly_scenario(end_date: date) -> ScenarioResult:
    print(f"\n{'=' * 80}")
    print("EMS yearly SAJ supervisione")
    print(f"{'=' * 80}")
    print("Metodo: emsHistoryData / parallYearPVEnergy, valore YTD aggregato EMS")
    value, data_time = get_ems_year_pv_energy_kwh(end_date)
    printable = f"{value} kWh" if value is not None else "N/D"
    print(f"TOTALE EMS yearly: {printable} (dataTime={data_time or 'N/D'})")
    return ScenarioResult(
        key="ems_yearly",
        label="EMS yearly SAJ",
        endpoint="/open/api/device/emsHistoryData",
        field="parallYearPVEnergy",
        total_kwh=value,
        details=[],
        note=f"dataTime={data_time or 'N/D'}",
    )


def get_saved_portale_value() -> tuple[Decimal | None, date | None]:
    impianto = ImpiantoAnagrafica.objects.filter(nome_impianto=ZILIO_PLANT_NAME).first()
    if impianto is None:
        return None, None
    metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)
    if metriche is None:
        return None, None
    value = getattr(metriche, "energia_prodotta_anno_corrente_kwh", None)
    updated_at = getattr(metriche, "energia_prodotta_anno_corrente_aggiornata_al", None)
    return (Decimal(str(value)).quantize(Decimal("0.01")) if value is not None else None), updated_at


def print_comparison_table(results: list[ScenarioResult], supervision_kwh: Decimal) -> None:
    saved_value, saved_date = get_saved_portale_value()

    print(f"\n{'=' * 80}")
    print("CONFRONTO FINALE")
    print(f"{'=' * 80}")
    print(f"Supervisione SAJ indicata: {supervision_kwh} kWh")
    if saved_value is not None:
        print(f"Valore salvato portale:   {saved_value} kWh (aggiornato al {saved_date})")
    else:
        print("Valore salvato portale:   N/D")

    print()
    print(
        f"{'metodo':<34} {'endpoint':<36} {'campo':<22} "
        f"{'kWh':>12} {'delta supervisione':>20}"
    )
    print("-" * 132)
    for result in results:
        total = result.total_kwh
        if total is None:
            total_text = "N/D"
            delta_text = "N/D"
        else:
            total_text = f"{total:.2f}"
            delta_text = f"{(total - supervision_kwh):+.2f}"
        print(
            f"{result.label:<34} {result.endpoint:<36} {result.field:<22} "
            f"{total_text:>12} {delta_text:>20}"
        )

    active = next((r for r in results if r.key == "active_only"), None)
    all_periods = next((r for r in results if r.key == "all_with_periods"), None)
    historical = next((r for r in results if r.key == "historical_only"), None)
    if active and all_periods and active.total_kwh is not None and all_periods.total_kwh is not None:
        print()
        print(f"Differenza tutti con periodi - solo attivi: {(all_periods.total_kwh - active.total_kwh):.2f} kWh")
    if historical and historical.total_kwh is not None:
        print(f"Contributo inverter storici/rimossi:       {historical.total_kwh:.2f} kWh")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Confronta i metodi YTD SAJ per Zilio Group.")
    parser.add_argument("--start-date", type=date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end-date", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument(
        "--supervision-kwh",
        type=Decimal,
        default=DEFAULT_SUPERVISION_KWH,
        help="Valore produzione YTD visto in supervisione SAJ.",
    )
    parser.add_argument(
        "--skip-ems",
        action="store_true",
        help="Non chiamare emsHistoryData.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Nasconde il dettaglio dei singoli device.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.end_date < args.start_date:
        raise SystemExit("--end-date deve essere >= --start-date")

    active_devices = [device for device in DEVICES if device.active]
    historical_devices = [device for device in DEVICES if not device.active]
    verbose = not args.quiet

    print("Zilio Group - probe energia prodotta YTD")
    print(f"Range richiesto: {args.start_date}..{args.end_date}")
    print(f"Supervisione SAJ indicata: {args.supervision_kwh} kWh")

    device_results = fetch_device_daily_results(
        DEVICES,
        args.start_date,
        args.end_date,
        verbose=verbose,
    )

    results = [
        build_device_daily_scenario(
            "active_only",
            "A - solo inverter attivi",
            active_devices,
            device_results,
            note="Perimetro vicino alla supervisione live.",
        ),
        build_device_daily_scenario(
            "historical_only",
            "B - solo inverter storici/rimossi",
            historical_devices,
            device_results,
            note="Energia aggiunta dagli inverter rimossi fino a data_fine_monitoraggio.",
        ),
        build_device_daily_scenario(
            "all_with_periods",
            "C - tutti con periodi DB",
            DEVICES,
            device_results,
            note="Replica il ragionamento del sync annuale prodotto.",
        ),
    ]

    if not args.skip_ems:
        results.append(run_ems_yearly_scenario(args.end_date))

    print_comparison_table(results, args.supervision_kwh)


if __name__ == "__main__":
    main()
