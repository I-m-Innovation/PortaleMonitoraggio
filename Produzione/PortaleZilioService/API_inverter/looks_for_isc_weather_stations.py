from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
PRODUZIONE_DIR = CURRENT_FILE.parents[2]

if str(PRODUZIONE_DIR) not in sys.path:
    sys.path.insert(0, str(PRODUZIONE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PortaleImpianti_project.settings")

import django

django.setup()

from PortaleZilioService.API_inverter.API_iSolarCloud import (  # noqa: E402
    WEATHER_STATION_DEVICE_TYPE,
    get_all_devices,
    login_ISC,
)
from PortaleZilioService.models import ImpiantoAnagrafica  # noqa: E402


def print_weather_stations() -> int:
    login_resp = login_ISC()
    token = login_resp.get("result_data", {}).get("token")
    if not token:
        print("Login failed: missing iSolarCloud token")
        return 2

    plants = list(
        ImpiantoAnagrafica.objects.filter(
            tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
        )
        .exclude(codice_impianto__isnull=True)
        .exclude(codice_impianto="")
        .order_by("nome_impianto")
    )

    created = []
    not_found = []
    errors = []

    for impianto in plants:
        plant_id = str(impianto.codice_impianto).strip()
        try:
            devices = get_all_devices(token=token, plant_id=int(plant_id))
            meteo_devices = [
                device
                for device in devices
                if str(device.get("device_type")) == WEATHER_STATION_DEVICE_TYPE
            ]

            if not meteo_devices:
                not_found.append((impianto.nome_impianto, plant_id))
                continue

            for device in meteo_devices:
                ps_key = str(device.get("ps_key") or "").strip()
                if not ps_key:
                    continue
                created.append((impianto.nome_impianto, plant_id, ps_key))
        except Exception as exc:
            errors.append((impianto.nome_impianto, plant_id, repr(exc)))

    print("Mode: print only")
    print(f"weather_stations_found: {len(created)}")
    for item in created:
        print(f"  - {item[0]} [{item[1]}] -> {item[2]}")

    print(f"not_found: {len(not_found)}")
    for item in not_found:
        print(f"  - {item[0]} [{item[1]}]")

    print(f"errors: {len(errors)}")
    for item in errors:
        print(f"  ! {item[0]} [{item[1]}] -> {item[2]}")

    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print weather station devices from iSolarCloud for active FV plants."
    )
    parser.parse_args()
    return print_weather_stations()


if __name__ == "__main__":
    raise SystemExit(main())
