from __future__ import annotations

from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings


def _normalize_plant_name(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split()).casefold()


def _to_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _load_fatturato_per_impianto(url: str, timeout: float) -> dict[str, Decimal]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return {}

    if payload.get("status") != "ok":
        return {}

    fatturato_by_impianto: dict[str, Decimal] = {}
    for item in payload.get("data", []):
        nome_impianto = _normalize_plant_name(item.get("impianto"))
        if not nome_impianto:
            continue

        fatturato = _to_decimal(item.get("fatturato_totale"))
        if fatturato is None:
            continue

        fatturato_by_impianto[nome_impianto] = fatturato

    return fatturato_by_impianto


def get_fatturato_ordinario_anno_corrente_per_impianto() -> dict[str, Decimal]:
    return _load_fatturato_per_impianto(
        settings.ZILIO_FATTURATO_ORDINARIO_URL,
        settings.ZILIO_FATTURATO_ORDINARIO_TIMEOUT,
    )


def get_fatturato_straordinario_totale_per_impianto() -> dict[str, Decimal]:
    return _load_fatturato_per_impianto(
        settings.ZILIO_FATTURATO_STRAORDINARIO_URL,
        settings.ZILIO_FATTURATO_STRAORDINARIO_TIMEOUT,
    )
