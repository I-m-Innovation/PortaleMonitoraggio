from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

from ..models import FotovoltaicoStatoEconomico, ImpiantoAnagrafica

logger = logging.getLogger(__name__)


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


def _to_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _extract_plant_name(item: dict) -> str:
    return _normalize_plant_name(item.get("impianto") or item.get("Impianto"))


def _extract_invoice_year(item: dict) -> int | None:
    raw_value = item.get("ListinoDataRif")
    if not raw_value:
        return None
    try:
        return date.fromisoformat(str(raw_value)).year
    except ValueError:
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
        nome_impianto = _extract_plant_name(item)
        if not nome_impianto:
            continue

        fatturato = _to_decimal(item.get("fatturato_totale"))
        if fatturato is None:
            continue

        fatturato_by_impianto[nome_impianto] = fatturato

    return fatturato_by_impianto


def _load_decimal_value_per_impianto(
    url: str,
    timeout: float,
    value_key: str,
) -> dict[str, Decimal]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning(
            "Errore nel caricamento valori decimali per impianto da endpoint Zilio",
            extra={"url": url, "value_key": value_key, "error": str(exc)},
        )
        return {}

    if payload.get("status") != "ok":
        logger.warning(
            "Endpoint Zilio ha restituito uno status non valido",
            extra={"url": url, "value_key": value_key, "status": payload.get("status")},
        )
        return {}

    values_by_impianto: dict[str, Decimal] = {}
    for item in payload.get("data", []):
        nome_impianto = _extract_plant_name(item)
        if not nome_impianto:
            continue

        value = _to_decimal(item.get(value_key))
        if value is None:
            continue

        values_by_impianto[nome_impianto] = value

    logger.info(
        "Valori decimali per impianto caricati da endpoint Zilio",
        extra={
            "url": url,
            "value_key": value_key,
            "items_received": len(payload.get("data", [])),
            "items_mapped": len(values_by_impianto),
        },
    )
    return values_by_impianto


def _load_integer_value_per_impianto(
    url: str,
    timeout: float,
    value_key: str,
) -> dict[str, int]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return {}

    if payload.get("status") != "ok":
        return {}

    values_by_impianto: dict[str, int] = {}
    for item in payload.get("data", []):
        nome_impianto = _extract_plant_name(item)
        if not nome_impianto:
            continue

        value = _to_int(item.get(value_key))
        if value is None:
            continue

        values_by_impianto[nome_impianto] = value

    return values_by_impianto


def _persist_costo_straordinario_to_db(costo_by_impianto: dict[str, Decimal]) -> None:
    if not costo_by_impianto:
        logger.info("Nessun costo straordinario da persistire su database")
        return

    impianti_fotovoltaici = ImpiantoAnagrafica.objects.filter(
        tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
    )
    impianti_by_name = {
        _normalize_plant_name(impianto.nome_impianto): impianto
        for impianto in impianti_fotovoltaici
        if impianto.nome_impianto
    }

    updated_count = 0
    created_count = 0
    missing_in_db: list[str] = []

    for normalized_name, costo in costo_by_impianto.items():
        impianto = impianti_by_name.get(normalized_name)
        if impianto is None:
            missing_in_db.append(normalized_name)
            logger.warning(
                "Impianto endpoint costo straordinario non trovato in anagrafica DB",
                extra={"normalized_name": normalized_name},
            )
            continue

        stato_economico, created = FotovoltaicoStatoEconomico.objects.get_or_create(
            impianto=impianto,
        )
        stato_economico.costo_sostenuto_straordinario = costo
        stato_economico.save(update_fields=["costo_sostenuto_straordinario", "updated_at"])

        if created:
            created_count += 1
        else:
            updated_count += 1

    logger.info(
        "Persistenza costi straordinari completata",
        extra={
            "endpoint_items": len(costo_by_impianto),
            "updated_count": updated_count,
            "created_count": created_count,
            "missing_in_db_count": len(missing_in_db),
        },
    )


def _load_canoni_incassati_oem_per_impianto(url: str, timeout: float) -> dict[str, Decimal]:
    if not url:
        return {}

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning(
            "Errore nel caricamento canoni incassati O&M da endpoint Zilio",
            extra={"url": url, "error": str(exc)},
        )
        return {}

    if payload.get("status") != "ok":
        logger.warning(
            "Endpoint canoni incassati O&M ha restituito uno status non valido",
            extra={"url": url, "status": payload.get("status")},
        )
        return {}

    current_year = date.today().year
    incassato_by_impianto: dict[str, Decimal] = {}
    for item in payload.get("data", []):
        nome_impianto = _extract_plant_name(item)
        if not nome_impianto:
            continue

        esito_match = str(item.get("EsitoMatch") or item.get("esito_match") or "").strip().upper()
        if esito_match != "MATCH":
            continue

        invoice_year = _extract_invoice_year(item)
        if invoice_year != current_year:
            continue

        importo = _to_decimal(item.get("TotaleDocumento"))
        if importo is None:
            importo = _to_decimal(item.get("ImportoUdc"))
        if importo is None:
            continue

        incassato_by_impianto[nome_impianto] = (
            incassato_by_impianto.get(nome_impianto, Decimal("0")) + importo
        )

    logger.info(
        "Canoni incassati O&M per impianto caricati da endpoint Zilio",
        extra={
            "url": url,
            "items_received": len(payload.get("data", [])),
            "items_mapped": len(incassato_by_impianto),
        },
    )
    return incassato_by_impianto


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


def get_numero_fatture_straordinarie_anno_corrente_per_impianto() -> dict[str, int]:
    return _load_integer_value_per_impianto(
        settings.ZILIO_FATTURE_STRAORDINARIE_ANNUO_URL,
        settings.ZILIO_FATTURE_STRAORDINARIE_ANNUO_TIMEOUT,
        "numero_fatture",
    )


def get_numero_fatture_straordinarie_totali_per_impianto() -> dict[str, int]:
    return _load_integer_value_per_impianto(
        settings.ZILIO_FATTURE_STRAORDINARIE_TOTALI_URL,
        settings.ZILIO_FATTURE_STRAORDINARIE_TOTALI_TIMEOUT,
        "numero_fatture",
    )


def get_costo_straordinario_totale_per_impianto() -> dict[str, Decimal]:
    costo_by_impianto = _load_decimal_value_per_impianto(
        settings.ZILIO_COSTO_STRAORDINARIO_TOTALE_URL,
        settings.ZILIO_COSTO_STRAORDINARIO_TOTALE_TIMEOUT,
        "costo_totale",
    )
    _persist_costo_straordinario_to_db(costo_by_impianto)
    return costo_by_impianto


def get_canoni_incassati_oem_per_impianto() -> dict[str, Decimal]:
    url = getattr(settings, "ZILIO_CANONI_INCASSATI_OEM_URL", "")
    raw_timeout = getattr(settings, "ZILIO_CANONI_INCASSATI_OEM_TIMEOUT", 10)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        timeout = 10.0

    return _load_canoni_incassati_oem_per_impianto(url, timeout)
