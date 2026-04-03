"""Manual probe for missed energy delta on a rolling 12-month window for all iSolarCloud PV plants.

Run:
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_missed_energy_all_plants.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PortaleImpianti_project.settings")
import django

django.setup()

from PortaleZilioService.models import ImpiantoAnagrafica, ImpiantoSorgenteDati
from PortaleZilioService.services.providers.isc import IscMetricsProvider
from PortaleZilioService.services.windows import rolling_12_months_until_yesterday
from PortaleZilioService.tests_api.isolarcloud.probe_expected_energy_all_plants import (
    _ensure_utf8_stdout,
    _fetch_plant_irradiation_with_alias,
    _normalize_pr_fraction,
    _resolve_external_plant_id,
)


def main() -> None:
    _ensure_utf8_stdout()

    impianti = (
        ImpiantoAnagrafica.objects.filter(
            tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
            sorgenti_dati__tipo_sorgente=ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
            sorgenti_dati__nome_sorgente="iSolarCloud",
            sorgenti_dati__attiva=True,
        )
        .select_related("fotovoltaico_metadata")
        .order_by("nome_impianto")
        .distinct()
    )

    provider = IscMetricsProvider()
    window = rolling_12_months_until_yesterday()
    start_date = window.start_date
    end_date = window.end_date

    token = provider._login()
    if not token:
        raise RuntimeError("Login ISC failed: token missing")

    plant_id_by_name = {}
    for impianto in impianti:
        plant_id = _resolve_external_plant_id(impianto)
        if plant_id is not None:
            plant_id_by_name[impianto.nome_impianto] = plant_id
    irradiation_cache: dict[int, float | str] = {}

    print("== iSolarCloud missed energy all plants probe ==")
    print(f"plants_found: {impianti.count()}")
    print(f"window_start: {start_date.isoformat()}")
    print(f"window_end: {end_date.isoformat()}")
    print("")

    for impianto in impianti:
        metadata = getattr(impianto, "fotovoltaico_metadata", None)
        power_kw = float(impianto.potenza_installata_kw) if impianto.potenza_installata_kw is not None else None
        pr_fraction = _normalize_pr_fraction(getattr(metadata, "pr_contrattuale", None))

        sorgente = impianto.sorgenti_dati.filter(
            tipo_sorgente=ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
            nome_sorgente="iSolarCloud",
            attiva=True,
        ).first()
        if not sorgente:
            print(f"{impianto.nome_impianto:<30} | missed_energy_delta_kwh=NO_SOURCE")
            continue

        try:
            snapshot = provider.fetch_portale_snapshot(impianto, sorgente, window)
            real_energy_kwh = float(snapshot.window_energy_kwh) if snapshot.window_energy_kwh is not None else None
        except Exception as exc:
            print(f"{impianto.nome_impianto:<30} | missed_energy_delta_kwh=REAL_ENERGY_ERROR | detail={exc}")
            continue

        if real_energy_kwh is None:
            print(f"{impianto.nome_impianto:<30} | missed_energy_delta_kwh=MISSING_REAL")
            continue

        irradiation_value, irradiation_source_name = _fetch_plant_irradiation_with_alias(
            token=token,
            impianto=impianto,
            plant_id_by_name=plant_id_by_name,
            irradiation_cache=irradiation_cache,
            start_date=start_date,
            end_date=end_date,
        )
        if irradiation_value == "WSM":
            print(
                f"{impianto.nome_impianto:<30} | real_energy_kwh={round(real_energy_kwh, 4):<12} | "
                f"expected_energy_kwh=WSM | missed_energy_delta_kwh=WSM"
            )
            continue

        if power_kw is None or power_kw <= 0:
            print(f"{impianto.nome_impianto:<30} | missed_energy_delta_kwh=MISSING_POWER")
            continue

        if pr_fraction is None:
            print(f"{impianto.nome_impianto:<30} | missed_energy_delta_kwh=MISSING_PR")
            continue

        irradiation_kwh_m2 = float(irradiation_value)
        expected_energy_kwh = power_kw * irradiation_kwh_m2 * pr_fraction
        missed_energy_delta_kwh = expected_energy_kwh - real_energy_kwh

        alias_suffix = ""
        if irradiation_source_name:
            alias_suffix = f" | irradiation_source={irradiation_source_name}"

        print(
            f"{impianto.nome_impianto:<30} | "
            f"real_energy_kwh={round(real_energy_kwh, 4):<12} | "
            f"expected_energy_kwh={round(expected_energy_kwh, 4):<12} | "
            f"missed_energy_delta_kwh={round(missed_energy_delta_kwh, 4)}"
            f"{alias_suffix}"
        )


if __name__ == "__main__":
    main()
