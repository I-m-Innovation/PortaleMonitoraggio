import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from django.db import transaction

from MonitoraggioImpianti.models import Impianto
from PortaleZilioService.API_inverter.API_iSolarCloud import refresh_plants_snapshot


PLANTS_JSON_PATH = Path(__file__).resolve().parents[2] / "PortaleZilioService" / "API_inverter" / "plants_data.json"


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_isc_snapshot(json_path: Path = PLANTS_JSON_PATH) -> list[dict[str, Any]]:
    if not json_path.exists():
        raise FileNotFoundError(f"Plant data file not found: {json_path}")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    plants = payload.get("plants", [])
    return [plant for plant in plants if isinstance(plant, dict)]


def refresh_isc_snapshot(year: int | None = None, json_path: Path = PLANTS_JSON_PATH) -> dict[str, Any]:
    snapshot_year = year or datetime.now().year
    return refresh_plants_snapshot(year=snapshot_year, json_path=str(json_path), year_data_point="p1")


def build_isc_index(plants: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for plant in plants:
        names = {
            _normalize_name(plant.get("plant_name")),
            _normalize_name(str(plant.get("plant_id"))),
        }
        for key in names:
            if key:
                index[key] = plant
    return index


def sync_isc_impianti(refresh: bool = True, year: int | None = None) -> dict[str, Any]:
    refresh_result = None
    if refresh:
        refresh_result = refresh_isc_snapshot(year=year)

    plants = load_isc_snapshot()
    plants_index = build_isc_index(plants)

    updated = 0
    skipped = 0
    missing: list[str] = []

    queryset = Impianto.objects.filter(lettura_dati="API_ISC")

    with transaction.atomic():
        for impianto in queryset:
            match = None
            for candidate in (
                impianto.nome_impianto,
                impianto.nickname,
                impianto.tag,
            ):
                normalized = _normalize_name(candidate)
                if normalized and normalized in plants_index:
                    match = plants_index[normalized]
                    break

            if match is None:
                skipped += 1
                missing.append(impianto.nome_impianto)
                continue

            impianto.ore_equivalenti_giornaliere = _to_float(match.get("equivalent_hours_day"))
            impianto.ore_equivalenti_annue = _to_float(match.get("equivalent_hours_year"))
            impianto.ore_equivalenti_totali = _to_float(match.get("equivalent_hours"))
            impianto.stato_operativo = match.get("status")
            impianto.energia_annua_kwh = _to_float(match.get("energy_year_kwh"))
            impianto.ha_meteo_station = match.get("has_weather_station")
            impianto.irraggiamento_annuo_kwh_m2 = _to_float(match.get("irradiation_year_kwh_m2"))
            impianto.performance_ratio_annuo = _to_float(match.get("performance_ratio_year"))
            impianto.save(
                update_fields=[
                    "ore_equivalenti_giornaliere",
                    "ore_equivalenti_annue",
                    "ore_equivalenti_totali",
                    "stato_operativo",
                    "energia_annua_kwh",
                    "ha_meteo_station",
                    "irraggiamento_annuo_kwh_m2",
                    "performance_ratio_annuo",
                ]
            )
            updated += 1

    return {
        "updated": updated,
        "skipped": skipped,
        "missing": missing,
        "snapshot_refreshed": refresh_result is not None,
        "refresh_result": refresh_result,
        "json_path": str(PLANTS_JSON_PATH),
    }
