"""Manual probe for expected energy on a rolling 12-month window for all iSolarCloud PV plants.

Run:
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_expected_energy_all_plants.py
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PortaleImpianti_project.settings")
import django

django.setup()

from PortaleZilioService.models import FotovoltaicoMetadata, ImpiantoAnagrafica, ImpiantoSorgenteDati
from PortaleZilioService.API_inverter.API_iSolarCloud import find_weather_station_device, login_ISC
from PortaleZilioService.tests_api.isolarcloud.probe_irradiation import (
    _ensure_utf8_stdout,
    _fetch_irradiation_kwh_m2,
)
from PortaleZilioService.services.windows import rolling_12_months_until_yesterday

IRRADIATION_ALIAS_BY_PLANT_NAME = {
    "3F - Plastica": "3F - Ferro",
}


def _normalize_pr_fraction(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    pr_value = float(value)
    if pr_value <= 0:
        return None
    if pr_value > 1:
        return pr_value / 100.0
    return pr_value


def _resolve_external_plant_id(impianto: ImpiantoAnagrafica) -> int | None:
    sorgente = impianto.sorgenti_dati.filter(
        tipo_sorgente=ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
        nome_sorgente="iSolarCloud",
        attiva=True,
    ).first()
    if not sorgente or not sorgente.identificativo_esterno:
        return None
    return int(sorgente.identificativo_esterno)


def _fetch_plant_irradiation_with_alias(
    token: str,
    impianto: ImpiantoAnagrafica,
    plant_id_by_name: dict[str, int],
    irradiation_cache: dict[int, float | str],
    start_date,
    end_date,
) -> tuple[float | str, str | None]:
    source_name = IRRADIATION_ALIAS_BY_PLANT_NAME.get(impianto.nome_impianto, impianto.nome_impianto)
    source_plant_id = plant_id_by_name.get(source_name)
    if source_plant_id is None:
        return "WSM", source_name if source_name != impianto.nome_impianto else None

    cached_value = irradiation_cache.get(source_plant_id)
    if cached_value is not None:
        return cached_value, source_name if source_name != impianto.nome_impianto else None

    weather_station = find_weather_station_device(token=token, plant_id=source_plant_id)
    if not weather_station:
        irradiation_cache[source_plant_id] = "WSM"
        return "WSM", source_name if source_name != impianto.nome_impianto else None

    weather_station_ps_key = weather_station.get("ps_key")
    if not weather_station_ps_key:
        irradiation_cache[source_plant_id] = "WSM"
        return "WSM", source_name if source_name != impianto.nome_impianto else None

    irradiation_kwh_m2 = _fetch_irradiation_kwh_m2(
        token=token,
        weather_station_ps_key=weather_station_ps_key,
        start_date=start_date,
        end_date=end_date,
    )
    irradiation_cache[source_plant_id] = irradiation_kwh_m2
    return irradiation_kwh_m2, source_name if source_name != impianto.nome_impianto else None


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

    login_response = login_ISC()
    token = login_response.get("result_data", {}).get("token")
    if not token:
        raise RuntimeError("Login ISC failed: token missing")

    window = rolling_12_months_until_yesterday()
    start_date = window.start_date
    end_date = window.end_date
    plant_id_by_name = {}
    for impianto in impianti:
        plant_id = _resolve_external_plant_id(impianto)
        if plant_id is not None:
            plant_id_by_name[impianto.nome_impianto] = plant_id
    irradiation_cache: dict[int, float | str] = {}

    print("== iSolarCloud expected energy all plants probe ==")
    print(f"plants_found: {impianti.count()}")
    print(f"window_start: {start_date.isoformat()}")
    print(f"window_end: {end_date.isoformat()}")
    print("")

    for impianto in impianti:
        metadata: FotovoltaicoMetadata | None = getattr(impianto, "fotovoltaico_metadata", None)
        power_kw = float(impianto.potenza_installata_kw) if impianto.potenza_installata_kw is not None else None
        pr_fraction = _normalize_pr_fraction(getattr(metadata, "pr_contrattuale", None))

        plant_id = _resolve_external_plant_id(impianto)

        if plant_id is None:
            print(f"{impianto.nome_impianto:<30} | expected_energy_kwh=NO_PLANT_ID")
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
            print(f"{impianto.nome_impianto:<30} | expected_energy_kwh=WSM")
            continue

        if power_kw is None or power_kw <= 0:
            print(f"{impianto.nome_impianto:<30} | expected_energy_kwh=MISSING_POWER")
            continue

        if pr_fraction is None:
            print(f"{impianto.nome_impianto:<30} | expected_energy_kwh=MISSING_PR")
            continue

        irradiation_kwh_m2 = float(irradiation_value)
        expected_energy_kwh = power_kw * irradiation_kwh_m2 * pr_fraction

        alias_suffix = ""
        if irradiation_source_name:
            alias_suffix = f" | irradiation_source={irradiation_source_name}"

        print(
            f"{impianto.nome_impianto:<30} | "
            f"power_kw={round(power_kw, 3):<8} | "
            f"pr={round(pr_fraction, 4):<6} | "
            f"irradiation_kwh_m2={round(irradiation_kwh_m2, 4):<10} | "
            f"expected_energy_kwh={round(expected_energy_kwh, 4)}"
            f"{alias_suffix}"
        )


if __name__ == "__main__":
    main()
