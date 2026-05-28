from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.utils.safestring import mark_safe

from ..models import FotovoltaicoMetadata, ImpiantoAnagrafica, ImpiantoDispositivo
from ..view_models import (
    AgrivoltaicoRow,
    FotovoltaicoClientiRow,
    FotovoltaicoInCostruzioneRow,
    FotovoltaicoPPURow,
    FotovoltaicoProprietaRow,
)

logger = logging.getLogger(__name__)

ENDPOINT_ERROR_LABEL = "API ERR"


def _fmt_date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "--"


def _fmt_not_defined(value: str | None) -> str:
    if value is None:
        return "not yet defined"
    stripped = value.strip()
    return stripped or "not yet defined"


def _fmt_number_it(value: Decimal | float | None, decimals: int = 2) -> str:
    if value is None:
        return "--"
    formatted = f"{float(value):,.{decimals}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _fmt_with_unit(formatted_value: str, unit: str, unit_class: str = "metric-unit") -> str:
    if formatted_value == "--":
        return formatted_value
    return mark_safe(f"{formatted_value} <span class=\"{unit_class}\">{unit}</span>")


def _fmt_equivalent_hours(value: Decimal | float | None) -> str:
    return _fmt_with_unit(_fmt_number_it(value, decimals=2), "h")


def _fmt_performance_ratio(value: Decimal | float | None) -> str:
    if value is None:
        return "--"
    return _fmt_with_unit(_fmt_number_it(float(value) * 100, decimals=2), "%", unit_class="metric-unit metric-unit-strong")


def _fmt_contractual_pr(value: Decimal | float | None) -> str:
    return _fmt_with_unit(_fmt_number_it(value, decimals=2), "%", unit_class="metric-unit metric-unit-strong")


def _fmt_decimal(value: Decimal | float | None) -> str:
    return _fmt_number_it(value, decimals=2)


def _fmt_integer(value: int | None, missing_label: str = "--") -> str:
    if value is None:
        return missing_label
    return str(value)


def _fmt_power(value: Decimal | float | None) -> str:
    return _fmt_with_unit(_fmt_number_it(value, decimals=2), "kW")


def _fmt_currency_accounting(value: Decimal | float | None, missing_label: str = "--") -> str:
    if value is None:
        return missing_label
    numeric_value = float(value)
    if numeric_value < 0:
        # \u20ac simbolo dell'euro 
        return f"- \u20ac {_fmt_number_it(abs(numeric_value), decimals=2)}"
    return f"\u20ac {_fmt_number_it(numeric_value, decimals=2)}"


def _normalize_plant_name(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split()).casefold()


def _normalize_plant_tag(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _resolve_endpoint_value(impianto, values_by_impianto, endpoint_name: str):
    if not values_by_impianto:
        return None

    normalized_tag = _normalize_plant_tag(impianto.tag_impianto)
    by_tag = getattr(values_by_impianto, "by_tag", None)
    if by_tag and normalized_tag in by_tag:
        return by_tag[normalized_tag]
    return None


def _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto):
    endpoint_value = _resolve_endpoint_value(
        impianto,
        fatturato_by_impianto,
        endpoint_name="fatturato_ordinario_anno_corrente_per_impianto",
    )
    return endpoint_value


def _resolve_incassato_value(
    impianto,
    stato_economico,
    incassato_by_impianto,
):
    if not incassato_by_impianto or not getattr(incassato_by_impianto, "is_available", False):
        return None

    endpoint_value = _resolve_endpoint_value(
        impianto,
        incassato_by_impianto,
        endpoint_name="canoni_incassati_oem_per_impianto",
    )
    if endpoint_value is not None:
        return endpoint_value
    return Decimal("0")


def _resolve_totale_fatturato_straordinario_value(
    impianto,
    stato_economico,
    fatturato_straordinario_by_impianto,
):
    endpoint_value = _resolve_endpoint_value(
        impianto,
        fatturato_straordinario_by_impianto,
        endpoint_name="fatturato_straordinario_totale_per_impianto",
    )
    return endpoint_value


def _resolve_costo_straordinario_totale_value(
    impianto,
    stato_economico,
    costo_straordinario_by_impianto,
):
    endpoint_value = _resolve_endpoint_value(
        impianto,
        costo_straordinario_by_impianto,
        endpoint_name="costo_straordinario_totale_per_impianto",
    )
    return endpoint_value


def _resolve_numero_fatture_straordinarie_annuo_value(
    impianto,
    stato_economico,
    fatture_straordinarie_annuo_by_impianto,
):
    endpoint_value = _resolve_endpoint_value(
        impianto,
        fatture_straordinarie_annuo_by_impianto,
        endpoint_name="numero_fatture_straordinarie_anno_corrente_per_impianto",
    )
    return endpoint_value


def _resolve_numero_fatture_straordinarie_totali_value(
    impianto,
    stato_economico,
    fatture_straordinarie_totali_by_impianto,
):
    endpoint_value = _resolve_endpoint_value(
        impianto,
        fatture_straordinarie_totali_by_impianto,
        endpoint_name="numero_fatture_straordinarie_totali_per_impianto",
    )
    return endpoint_value


def _margine_straordinario_cell(
    impianto,
    stato_economico,
    costo_straordinario_by_impianto: dict[str, Decimal] | None,
    fatturato_straordinario_by_impianto: dict[str, Decimal] | None,
) -> tuple[str, str]:
    costo = _resolve_costo_straordinario_totale_value(
        impianto,
        stato_economico,
        costo_straordinario_by_impianto,
    )
    fatturato = _resolve_totale_fatturato_straordinario_value(
        impianto,
        stato_economico,
        fatturato_straordinario_by_impianto,
    )

    if costo is not None and fatturato is not None:
        margine = Decimal(str(fatturato)) - Decimal(str(costo))
        if margine > 0:
            return _fmt_currency_accounting(margine), "metric-delta metric-delta-gain"
        if margine < 0:
            return _fmt_currency_accounting(margine), "metric-delta metric-delta-loss"
        return _fmt_currency_accounting(margine), "metric-delta metric-delta-neutral"

    return ENDPOINT_ERROR_LABEL, "endpoint-error-badge"


def _calcola_anni_contratto(data_inizio: date | None, data_fine: date | None) -> str:
    if not data_inizio or not data_fine:
        return "--"
    anni = (data_fine - data_inizio).days / 365.25
    return f"{anni:.1f}"


def _maturato_value(stato_economico, today: date | None = None) -> Decimal | None:
    if stato_economico is None:
        logger.debug("[maturato-annuale] stato_economico assente")
        return None

    data_inizio = getattr(stato_economico, "data_inizio_contratto", None)
    periodicita_mesi = getattr(stato_economico, "periodicita_canone_mesi", None)
    importo_canone_periodico = getattr(stato_economico, "compute_importo_canone_periodico", lambda: None)()
    if importo_canone_periodico is None:
        importo_canone_periodico = getattr(stato_economico, "importo_canone_periodico", None)

    if not data_inizio or periodicita_mesi in (None, 0) or importo_canone_periodico is None:
        logger.debug(
            "[maturato-annuale] dati insufficienti impianto=%s data_inizio=%s periodicita=%s importo_canone=%s",
            getattr(getattr(stato_economico, "impianto", None), "nome_impianto", "-"),
            data_inizio,
            periodicita_mesi,
            importo_canone_periodico,
        )
        return None

    today = today or date.today()
    year_start = date(today.year, 1, 1)
    year_end = date(today.year, 12, 31)

    if data_inizio > today:
        logger.debug(
            "[maturato-annuale] contratto non ancora iniziato impianto=%s anno=%s data_inizio=%s today=%s",
            getattr(getattr(stato_economico, "impianto", None), "nome_impianto", "-"),
            today.year,
            data_inizio,
            today,
        )
        return Decimal("0")

    data_fine = getattr(stato_economico, "data_fine_contratto", None)
    effective_end = min(today, data_fine) if data_fine else today
    effective_end = min(effective_end, year_end)
    if effective_end < year_start or effective_end < data_inizio:
        logger.debug(
            "[maturato-annuale] nessun periodo utile impianto=%s anno=%s data_inizio=%s data_fine=%s effective_end=%s",
            getattr(getattr(stato_economico, "impianto", None), "nome_impianto", "-"),
            today.year,
            data_inizio,
            data_fine,
            effective_end,
        )
        return Decimal("0")

    numero_canoni_maturati = 0
    scadenze_maturate: list[str] = []
    scadenza = _add_months(data_inizio, periodicita_mesi)

    while scadenza <= effective_end:
        if scadenza >= year_start:
            numero_canoni_maturati += 1
            scadenze_maturate.append(scadenza.isoformat())
        scadenza = _add_months(scadenza, periodicita_mesi)

    maturato = Decimal(numero_canoni_maturati) * Decimal(str(importo_canone_periodico))
    logger.debug(
        "[maturato-annuale] impianto=%s anno=%s canoni=%s importo_canone=%s maturato=%s scadenze=%s",
        getattr(getattr(stato_economico, "impianto", None), "nome_impianto", "-"),
        today.year,
        numero_canoni_maturati,
        importo_canone_periodico,
        maturato,
        scadenze_maturate,
    )
    return maturato


def _add_months(base_date: date, months: int) -> date:
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def _next_invoice_state(stato_economico) -> tuple[date | None, bool]:
    if stato_economico is None:
        return None, False

    data_inizio = getattr(stato_economico, "data_inizio_contratto", None)
    periodicita_mesi = getattr(stato_economico, "periodicita_canone_mesi", None)
    if not data_inizio or periodicita_mesi in (None, 0):
        return None, False

    data_fine = getattr(stato_economico, "data_fine_contratto", None)
    today = date.today()

    next_invoice_date = data_inizio
    while next_invoice_date < today:
        next_invoice_date = _add_months(next_invoice_date, periodicita_mesi)

    if data_fine and next_invoice_date > data_fine:
        return None, True

    return next_invoice_date, False


def _next_invoice_date_cell(stato_economico) -> tuple[str, str]:
    next_invoice_date, is_contract_ended = _next_invoice_state(stato_economico)
    if next_invoice_date is None:
        return "--", ""

    today = date.today()
    css_class = "invoice-date-today" if next_invoice_date == today else ""
    return _fmt_date(next_invoice_date), css_class


def _next_invoice_amount_cell(stato_economico) -> str:
    next_invoice_date, is_contract_ended = _next_invoice_state(stato_economico)
    if is_contract_ended:
        return "Fine contratto"
    if next_invoice_date is None:
        return "--"

    importo_canone_periodico = getattr(stato_economico, "compute_importo_canone_periodico", lambda: None)()
    if importo_canone_periodico is None:
        importo_canone_periodico = getattr(stato_economico, "importo_canone_periodico", None)
    if importo_canone_periodico is None:
        return "--"

    return _fmt_currency_accounting(importo_canone_periodico)


def _pr_ultimi_12_mesi_text(impianto, metriche) -> str:
    pr_value = getattr(metriche, "pr_ultimi_12_mesi", None)
    if pr_value is not None:
        return _fmt_performance_ratio(pr_value)

    has_weather_station = impianto.dispositivi.filter(
        tipo_dispositivo=ImpiantoDispositivo.TipoDispositivo.WEATHER_STATION,
        attivo=True,
    ).exists()
    if not has_weather_station:
        return "SM"
    return "ERR"


def _mancata_produzione_cell(impianto, metriche) -> tuple[str, str]:
    value = getattr(metriche, "mancata_produzione", None)
    if value is not None:
        numeric_value = float(value)
        if numeric_value > 0:
            return f"\u2193 {_fmt_decimal(abs(numeric_value))}", "metric-delta metric-delta-loss"
        if numeric_value < 0:
            return f"\u2191 {_fmt_decimal(abs(numeric_value))}", "metric-delta metric-delta-gain"
        return _fmt_decimal(0), "metric-delta metric-delta-neutral"

    has_weather_station = impianto.dispositivi.filter(
        tipo_dispositivo=ImpiantoDispositivo.TipoDispositivo.WEATHER_STATION,
        attivo=True,
    ).exists()
    if not has_weather_station:
        return "SM", "metric-delta-soft-loss"
    return "ERR", "metric-delta metric-delta-muted"


def _status_class_portale(metriche) -> str:
    status = getattr(metriche, "stato_operativo", None)
    if status == "online":
        return "status-dot-green"
    if status == "offline":
        return "status-dot-red"
    if status == "warning":
        return "status-dot-yellow"
    return "status-dot-gray"


def build_fotovoltaico_clienti_rows_portale(
    fatturato_by_impianto: dict[str, Decimal] | None = None,
    incassato_by_impianto: dict[str, Decimal] | None = None,
    fatturato_straordinario_by_impianto: dict[str, Decimal] | None = None,
    costo_straordinario_by_impianto: dict[str, Decimal] | None = None,
    fatture_straordinarie_annuo_by_impianto: dict[str, int] | None = None,
    fatture_straordinarie_totali_by_impianto: dict[str, int] | None = None,
):
    queryset = _build_fotovoltaico_clienti_portale_queryset()

    rows: list[FotovoltaicoClientiRow] = []
    for impianto in queryset:
        metadata = impianto.fotovoltaico_metadata
        stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)
        metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)
        data_prossima_fattura, data_prossima_fattura_class = _next_invoice_date_cell(stato_economico)

        mancata_produzione, mancata_produzione_class = _mancata_produzione_cell(impianto, metriche)
        margine_straordinario, margine_straordinario_class = _margine_straordinario_cell(
            impianto,
            stato_economico,
            costo_straordinario_by_impianto,
            fatturato_straordinario_by_impianto,
        )
        rows.append(
            FotovoltaicoClientiRow(
                status_class=_status_class_portale(metriche),
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
                potenza_contratto=_fmt_power(getattr(metadata, "potenza_contratto_kw", None)),
                potenza_installata=_fmt_power(impianto.potenza_installata_kw),
                pr_contrattuale=_fmt_contractual_pr(metadata.pr_contrattuale),
                pr_ultimi_12_mesi=_pr_ultimi_12_mesi_text(impianto, metriche),
                mancata_produzione=mancata_produzione,
                mancata_produzione_class=mancata_produzione_class,
                ore_equivalenti=_fmt_equivalent_hours(
                    getattr(metriche, "ore_equivalenti_ultimi_12_mesi", None)
                ),
                inizio_contratto=_fmt_date(
                    getattr(stato_economico, "data_inizio_contratto", None)
                ),
                fine_contratto=_fmt_date(
                    getattr(stato_economico, "data_fine_contratto", None)
                ),
                totale_anni_contratto=_calcola_anni_contratto(
                    getattr(stato_economico, "data_inizio_contratto", None),
                    getattr(stato_economico, "data_fine_contratto", None),
                ),
                totale_contratto=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_contratto", None)
                ),
                totale_annuale_su_MW=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_annuale_su_mw", None)
                ),
                totale_annuo=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_annuo", None)
                ),
                totale_maturato=_fmt_currency_accounting(_maturato_value(stato_economico)),
                fatturato=_fmt_currency_accounting(
                    _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                totale_incassato=_fmt_currency_accounting(
                    _resolve_incassato_value(impianto, stato_economico, incassato_by_impianto),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                data_prossima_fattura=data_prossima_fattura,
                data_prossima_fattura_class=data_prossima_fattura_class,
                importo_prossima_fattura=_next_invoice_amount_cell(stato_economico),
                totale_ordinato_straordinario=_fmt_currency_accounting(
                    _resolve_costo_straordinario_totale_value(
                        impianto,
                        stato_economico,
                        costo_straordinario_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                totale_fatturato_straordinario=_fmt_currency_accounting(
                    _resolve_totale_fatturato_straordinario_value(
                        impianto,
                        stato_economico,
                        fatturato_straordinario_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                margine_straordinario=margine_straordinario,
                margine_straordinario_class=margine_straordinario_class,
                numero_fatture_straordinarie_annuo=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_annuo_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_annuo_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                numero_fatture_straordinarie_totali=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_totali_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_totali_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
            )
        )

    return rows


def build_fotovoltaico_proprieta_rows_portale(
    fatturato_by_impianto: dict[str, Decimal] | None = None,
    incassato_by_impianto: dict[str, Decimal] | None = None,
    fatturato_straordinario_by_impianto: dict[str, Decimal] | None = None,
    costo_straordinario_by_impianto: dict[str, Decimal] | None = None,
    fatture_straordinarie_annuo_by_impianto: dict[str, int] | None = None,
    fatture_straordinarie_totali_by_impianto: dict[str, int] | None = None,
):
    queryset = _build_fotovoltaico_proprieta_portale_queryset()

    rows: list[FotovoltaicoProprietaRow] = []
    for impianto in queryset:
        metadata = impianto.fotovoltaico_metadata
        stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)
        metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)
        data_prossima_fattura, data_prossima_fattura_class = _next_invoice_date_cell(stato_economico)
        mancata_produzione, mancata_produzione_class = _mancata_produzione_cell(impianto, metriche)
        margine_straordinario, margine_straordinario_class = _margine_straordinario_cell(
            impianto,
            stato_economico,
            costo_straordinario_by_impianto,
            fatturato_straordinario_by_impianto,
        )

        rows.append(
            FotovoltaicoProprietaRow(
                status_class=_status_class_portale(metriche),
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
                potenza_contratto=_fmt_power(getattr(metadata, "potenza_contratto_kw", None)),
                potenza_installata=_fmt_power(impianto.potenza_installata_kw),
                pr_contrattuale=_fmt_contractual_pr(metadata.pr_contrattuale),
                pr_ultimi_12_mesi=_pr_ultimi_12_mesi_text(impianto, metriche),
                mancata_produzione=mancata_produzione,
                mancata_produzione_class=mancata_produzione_class,
                ore_equivalenti=_fmt_equivalent_hours(
                    getattr(metriche, "ore_equivalenti_ultimi_12_mesi", None)
                ),
                inizio_contratto=_fmt_date(
                    getattr(stato_economico, "data_inizio_contratto", None)
                ),
                fine_contratto=_fmt_date(
                    getattr(stato_economico, "data_fine_contratto", None)
                ),
                totale_anni_contratto=_calcola_anni_contratto(
                    getattr(stato_economico, "data_inizio_contratto", None),
                    getattr(stato_economico, "data_fine_contratto", None),
                ),
                totale_contratto=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_contratto", None)
                ),
                totale_annuale_su_MW=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_annuale_su_mw", None)
                ),
                totale_annuo=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_annuo", None)
                ),
                totale_maturato=_fmt_currency_accounting(_maturato_value(stato_economico)),
                fatturato=_fmt_currency_accounting(
                    _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                totale_incassato=_fmt_currency_accounting(
                    _resolve_incassato_value(impianto, stato_economico, incassato_by_impianto),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                data_prossima_fattura=data_prossima_fattura,
                data_prossima_fattura_class=data_prossima_fattura_class,
                importo_prossima_fattura=_next_invoice_amount_cell(stato_economico),
                totale_ordinato_straordinario=_fmt_currency_accounting(
                    _resolve_costo_straordinario_totale_value(
                        impianto,
                        stato_economico,
                        costo_straordinario_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                totale_fatturato_straordinario=_fmt_currency_accounting(
                    _resolve_totale_fatturato_straordinario_value(
                        impianto,
                        stato_economico,
                        fatturato_straordinario_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                margine_straordinario=margine_straordinario,
                margine_straordinario_class=margine_straordinario_class,
                numero_fatture_straordinarie_annuo=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_annuo_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_annuo_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                numero_fatture_straordinarie_totali=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_totali_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_totali_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
            )
        )

    return rows


def build_fotovoltaico_in_costruzione_rows_portale(
    fatturato_by_impianto: dict[str, Decimal] | None = None,
    incassato_by_impianto: dict[str, Decimal] | None = None,
    fatturato_straordinario_by_impianto: dict[str, Decimal] | None = None,
    costo_straordinario_by_impianto: dict[str, Decimal] | None = None,
    fatture_straordinarie_annuo_by_impianto: dict[str, int] | None = None,
    fatture_straordinarie_totali_by_impianto: dict[str, int] | None = None,
):
    queryset = _build_fotovoltaico_in_costruzione_portale_queryset()

    rows: list[FotovoltaicoInCostruzioneRow] = []
    for impianto in queryset:
        metadata = getattr(impianto, "fotovoltaico_metadata", None)
        stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)
        metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)
        data_prossima_fattura, data_prossima_fattura_class = _next_invoice_date_cell(stato_economico)
        mancata_produzione, mancata_produzione_class = _mancata_produzione_cell(impianto, metriche)
        margine_straordinario, margine_straordinario_class = _margine_straordinario_cell(
            impianto,
            stato_economico,
            costo_straordinario_by_impianto,
            fatturato_straordinario_by_impianto,
        )

        rows.append(
            FotovoltaicoInCostruzioneRow(
                impianto_id=impianto.id,
                status_class=_status_class_portale(metriche),
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
                categoria_fv=getattr(metadata, "categoria_fv", "") or "",
                tipologia_contratto="--",
                potenza=_fmt_power(impianto.potenza_installata_kw),
                pr_contrattuale=_fmt_contractual_pr(getattr(metadata, "pr_contrattuale", None)),
                pr_ultimi_12_mesi=_pr_ultimi_12_mesi_text(impianto, metriche),
                mancata_produzione=mancata_produzione,
                mancata_produzione_class=mancata_produzione_class,
                ore_equivalenti=_fmt_equivalent_hours(
                    getattr(metriche, "ore_equivalenti_ultimi_12_mesi", None)
                ),
                inizio_contratto=_fmt_date(
                    getattr(stato_economico, "data_inizio_contratto", None)
                ),
                fine_contratto=_fmt_date(
                    getattr(stato_economico, "data_fine_contratto", None)
                ),
                totale_anni_contratto=_calcola_anni_contratto(
                    getattr(stato_economico, "data_inizio_contratto", None),
                    getattr(stato_economico, "data_fine_contratto", None),
                ),
                totale_contratto=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_contratto", None)
                ),
                totale_annuale_su_MW=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_annuale_su_mw", None)
                ),
                totale_annuo=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_annuo", None)
                ),
                totale_maturato=_fmt_currency_accounting(_maturato_value(stato_economico)),
                fatturato=_fmt_currency_accounting(
                    _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                totale_incassato=_fmt_currency_accounting(
                    _resolve_incassato_value(impianto, stato_economico, incassato_by_impianto),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                data_prossima_fattura=data_prossima_fattura,
                data_prossima_fattura_class=data_prossima_fattura_class,
                importo_prossima_fattura=_next_invoice_amount_cell(stato_economico),
                totale_ordinato_straordinario=_fmt_currency_accounting(
                    _resolve_costo_straordinario_totale_value(
                        impianto,
                        stato_economico,
                        costo_straordinario_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                totale_fatturato_straordinario=_fmt_currency_accounting(
                    _resolve_totale_fatturato_straordinario_value(
                        impianto,
                        stato_economico,
                        fatturato_straordinario_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                margine_straordinario=margine_straordinario,
                margine_straordinario_class=margine_straordinario_class,
                numero_fatture_straordinarie_annuo=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_annuo_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_annuo_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                numero_fatture_straordinarie_totali=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_totali_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_totali_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
            )
        )

    return rows


def build_agrivoltaico_rows_portale(
    fatturato_by_impianto: dict[str, Decimal] | None = None,
    incassato_by_impianto: dict[str, Decimal] | None = None,
    fatturato_straordinario_by_impianto: dict[str, Decimal] | None = None,
    costo_straordinario_by_impianto: dict[str, Decimal] | None = None,
    fatture_straordinarie_annuo_by_impianto: dict[str, int] | None = None,
    fatture_straordinarie_totali_by_impianto: dict[str, int] | None = None,
):
    queryset = _build_fotovoltaico_agrivoltaico_portale_queryset()

    rows: list[AgrivoltaicoRow] = []
    for impianto in queryset:
        metadata = getattr(impianto, "fotovoltaico_metadata", None)
        stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)
        metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)
        data_prossima_fattura, data_prossima_fattura_class = _next_invoice_date_cell(stato_economico)
        mancata_produzione, mancata_produzione_class = _mancata_produzione_cell(impianto, metriche)
        margine_straordinario, margine_straordinario_class = _margine_straordinario_cell(
            impianto,
            stato_economico,
            costo_straordinario_by_impianto,
            fatturato_straordinario_by_impianto,
        )

        rows.append(
            AgrivoltaicoRow(
                status_class=_status_class_portale(metriche),
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
                potenza_contratto=_fmt_power(getattr(metadata, "potenza_contratto_kw", None)),
                potenza_installata=_fmt_power(impianto.potenza_installata_kw),
                pr_contrattuale=_fmt_contractual_pr(getattr(metadata, "pr_contrattuale", None)),
                pr_ultimi_12_mesi=_pr_ultimi_12_mesi_text(impianto, metriche),
                mancata_produzione=mancata_produzione,
                mancata_produzione_class=mancata_produzione_class,
                ore_equivalenti=_fmt_equivalent_hours(
                    getattr(metriche, "ore_equivalenti_ultimi_12_mesi", None)
                ),
                inizio_contratto=_fmt_date(
                    getattr(stato_economico, "data_inizio_contratto", None)
                ),
                fine_contratto=_fmt_date(
                    getattr(stato_economico, "data_fine_contratto", None)
                ),
                totale_anni_contratto=_calcola_anni_contratto(
                    getattr(stato_economico, "data_inizio_contratto", None),
                    getattr(stato_economico, "data_fine_contratto", None),
                ),
                totale_contratto=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_contratto", None)
                ),
                totale_annuale_su_MW=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_annuale_su_mw", None)
                ),
                totale_annuo=_fmt_currency_accounting(
                    getattr(stato_economico, "totale_annuo", None)
                ),
                totale_maturato=_fmt_currency_accounting(_maturato_value(stato_economico)),
                fatturato=_fmt_currency_accounting(
                    _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                totale_incassato=_fmt_currency_accounting(
                    _resolve_incassato_value(impianto, stato_economico, incassato_by_impianto),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                data_prossima_fattura=data_prossima_fattura,
                data_prossima_fattura_class=data_prossima_fattura_class,
                importo_prossima_fattura=_next_invoice_amount_cell(stato_economico),
                totale_ordinato_straordinario=_fmt_currency_accounting(
                    _resolve_costo_straordinario_totale_value(
                        impianto,
                        stato_economico,
                        costo_straordinario_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                totale_fatturato_straordinario=_fmt_currency_accounting(
                    _resolve_totale_fatturato_straordinario_value(
                        impianto,
                        stato_economico,
                        fatturato_straordinario_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                margine_straordinario=margine_straordinario,
                margine_straordinario_class=margine_straordinario_class,
                numero_fatture_straordinarie_annuo=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_annuo_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_annuo_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
                numero_fatture_straordinarie_totali=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_totali_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_totali_by_impianto,
                    ),
                    missing_label=ENDPOINT_ERROR_LABEL,
                ),
            )
        )

    return rows


def build_fotovoltaico_ppu_rows_portale():
    queryset = _build_fotovoltaico_ppu_portale_queryset()

    rows: list[FotovoltaicoPPURow] = []
    for impianto in queryset:
        stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)
        metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)

        _prodotta_kwh: Decimal | None = getattr(metriche, "energia_prodotta_anno_corrente_kwh", None)
        _immessa_kwh: Decimal | None = getattr(metriche, "energia_immessa_anno_corrente_kwh", None)
        _autoconsumata_kwh: Decimal | None = (
            _prodotta_kwh - _immessa_kwh
            if _prodotta_kwh is not None and _immessa_kwh is not None
            else None
        )
        _percentuale_autoconsumo: float | None = (
            float(_autoconsumata_kwh) / float(_prodotta_kwh) * 100
            if _autoconsumata_kwh is not None and _prodotta_kwh and _prodotta_kwh > 0
            else None
        )
        _tariffa_ppu_mwh: Decimal | None = getattr(stato_economico, "tariffa_ppu_mwh", None)
        _maturato_ppu_euro: Decimal | None = (
            _autoconsumata_kwh * _tariffa_ppu_mwh / 1000
            if _autoconsumata_kwh is not None and _tariffa_ppu_mwh is not None
            else None
        )

        rows.append(
            FotovoltaicoPPURow(
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
                tariffa_mwh=_fmt_with_unit(
                    _fmt_number_it(getattr(stato_economico, "tariffa_ppu_mwh", None), decimals=2),
                    "EUR/MWh",
                ),
                strumento_di_contabilizzazione=(
                    getattr(stato_economico, "strumento_contabilizzazione_ppu", None) or "--"
                ),
                energia_prodotta_anno_corrente=_fmt_with_unit(
                    _fmt_number_it(_prodotta_kwh, decimals=2),
                    "kWh",
                ),
                energia_immessa_anno_corrente=_fmt_with_unit(
                    _fmt_number_it(_immessa_kwh, decimals=2),
                    "kWh",
                ),
                energia_autoconsumata_anno_corrente=_fmt_with_unit(
                    _fmt_number_it(_autoconsumata_kwh, decimals=2),
                    "kWh",
                ),
                percentuale_autoconsumo_anno_corrente=_fmt_with_unit(
                    _fmt_number_it(_percentuale_autoconsumo, decimals=1),
                    "%",
                    unit_class="metric-unit metric-unit-strong",
                ),
                maturato_ppu_anno_corrente_euro=_fmt_with_unit(
                    _fmt_number_it(_maturato_ppu_euro, decimals=2),
                    "€",
                ),
                fatturato_dall_inizio="--",
                tipologia_di_pagamento=(
                    getattr(stato_economico, "tipologia_pagamento_ppu", None) or "--"
                ),
                data_di_inizio=_fmt_date(
                    getattr(stato_economico, "data_inizio_contratto", None)
                ),
                data_di_fine=_fmt_date(
                    getattr(stato_economico, "data_fine_contratto", None)
                ),
                totale_anni_contratto=_calcola_anni_contratto(
                    getattr(stato_economico, "data_inizio_contratto", None),
                    getattr(stato_economico, "data_fine_contratto", None),
                ),
                pr_stimato_annuo="--",
                energia_stimata_annua="--",
                mancata_produzione="--",
                fatturato_previsto="--",
            )
        )

    return rows


def _build_fotovoltaico_overview_base_queryset():
    return (
        ImpiantoAnagrafica.objects.select_related(
            "fotovoltaico_metadata",
            "fotovoltaico_stato_economico",
            "fotovoltaico_metriche_tecniche",
        )
        .prefetch_related("dispositivi", "sorgenti_dati")
        .filter(
            tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
        )
        .exclude(stato_impianto=ImpiantoAnagrafica.StatoImpianto.IN_COSTRUZIONE)
    )


def _build_fotovoltaico_clienti_portale_queryset():
    return (
        _build_fotovoltaico_overview_base_queryset()
        .filter(
            fotovoltaico_metadata__categoria_fv=FotovoltaicoMetadata.CategoriaFV.CLIENTE,
            fotovoltaico_metadata__is_oem=True,
        )
        .order_by("nome_cliente", "nome_impianto")
    )


def _build_fotovoltaico_proprieta_portale_queryset():
    return (
        _build_fotovoltaico_overview_base_queryset()
        .filter(
            fotovoltaico_metadata__categoria_fv=FotovoltaicoMetadata.CategoriaFV.PROPRIETA,
            fotovoltaico_metadata__is_oem=True,
        )
        .order_by("nome_cliente", "nome_impianto")
    )


def _build_fotovoltaico_agrivoltaico_portale_queryset():
    return (
        _build_fotovoltaico_overview_base_queryset()
        .filter(
            fotovoltaico_metadata__is_agrivoltaico=True,
            fotovoltaico_metadata__is_oem=True,
        )
        .order_by("nome_cliente", "nome_impianto")
    )


def _build_fotovoltaico_ppu_portale_queryset():
    return (
        _build_fotovoltaico_overview_base_queryset()
        .filter(
            fotovoltaico_metadata__is_ppu=True,
        )
        .order_by("nome_cliente", "nome_impianto")
    )


def _build_fotovoltaico_in_costruzione_portale_queryset():
    return (
        ImpiantoAnagrafica.objects.select_related(
            "fotovoltaico_metadata",
            "fotovoltaico_stato_economico",
            "fotovoltaico_metriche_tecniche",
        )
        .prefetch_related("dispositivi")
        .filter(
            tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
            stato_impianto=ImpiantoAnagrafica.StatoImpianto.IN_COSTRUZIONE,
        )
        .order_by("nome_cliente", "nome_impianto")
    )

