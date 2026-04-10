from __future__ import annotations

import logging
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


def _fmt_integer(value: int | None) -> str:
    if value is None:
        return "--"
    return str(value)


def _fmt_power(value: Decimal | float | None) -> str:
    return _fmt_with_unit(_fmt_number_it(value, decimals=2), "kW")


def _fmt_currency_accounting(value: Decimal | float | None) -> str:
    if value is None:
        return "--"
    numeric_value = float(value)
    if numeric_value < 0:
        return f"- € {_fmt_number_it(abs(numeric_value), decimals=2)}"
    return f"€ {_fmt_number_it(numeric_value, decimals=2)}"


def _normalize_plant_name(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split()).casefold()


def _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto: dict[str, Decimal] | None):
    if fatturato_by_impianto:
        normalized_name = _normalize_plant_name(impianto.nome_impianto)
        if normalized_name in fatturato_by_impianto:
            return fatturato_by_impianto[normalized_name]
    return getattr(stato_economico, "fatturato", None)


def _resolve_totale_fatturato_straordinario_value(
    impianto,
    stato_economico,
    fatturato_straordinario_by_impianto: dict[str, Decimal] | None,
):
    if fatturato_straordinario_by_impianto:
        normalized_name = _normalize_plant_name(impianto.nome_impianto)
        if normalized_name in fatturato_straordinario_by_impianto:
            return fatturato_straordinario_by_impianto[normalized_name]
    return getattr(stato_economico, "totale_fatturato_straordinario", None)


def _resolve_costo_straordinario_totale_value(
    impianto,
    stato_economico,
    costo_straordinario_by_impianto: dict[str, Decimal] | None,
):
    if costo_straordinario_by_impianto:
        normalized_name = _normalize_plant_name(impianto.nome_impianto)
        if normalized_name in costo_straordinario_by_impianto:
            return costo_straordinario_by_impianto[normalized_name]
        logger.info(
            "Costo straordinario non trovato nel payload endpoint per impianto fotovoltaico",
            extra={"impianto": impianto.nome_impianto, "normalized_name": normalized_name},
        )
    return getattr(stato_economico, "costo_sostenuto_straordinario", None)


def _resolve_numero_fatture_straordinarie_annuo_value(
    impianto,
    stato_economico,
    fatture_straordinarie_annuo_by_impianto: dict[str, int] | None,
):
    if fatture_straordinarie_annuo_by_impianto:
        normalized_name = _normalize_plant_name(impianto.nome_impianto)
        if normalized_name in fatture_straordinarie_annuo_by_impianto:
            return fatture_straordinarie_annuo_by_impianto[normalized_name]
    return getattr(stato_economico, "numero_fatture_straordinarie_annuo", None)


def _resolve_numero_fatture_straordinarie_totali_value(
    impianto,
    stato_economico,
    fatture_straordinarie_totali_by_impianto: dict[str, int] | None,
):
    if fatture_straordinarie_totali_by_impianto:
        normalized_name = _normalize_plant_name(impianto.nome_impianto)
        if normalized_name in fatture_straordinarie_totali_by_impianto:
            return fatture_straordinarie_totali_by_impianto[normalized_name]
    return getattr(stato_economico, "numero_fatture_straordinarie_totali", None)


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

    fallback = getattr(stato_economico, "margine_straordinario", None)
    if fallback is None:
        return "--", "metric-delta metric-delta-muted"

    numeric_fallback = Decimal(str(fallback))
    if numeric_fallback > 0:
        return _fmt_currency_accounting(numeric_fallback), "metric-delta metric-delta-gain"
    if numeric_fallback < 0:
        return _fmt_currency_accounting(numeric_fallback), "metric-delta metric-delta-loss"
    return _fmt_currency_accounting(numeric_fallback), "metric-delta metric-delta-neutral"


def _calcola_anni_contratto(data_inizio: date | None, data_fine: date | None) -> str:
    if not data_inizio or not data_fine:
        return "--"
    anni = (data_fine - data_inizio).days / 365.25
    return f"{anni:.1f}"


def _maturato_value(stato_economico) -> Decimal | None:
    if stato_economico is None:
        return None

    data_inizio = getattr(stato_economico, "data_inizio_contratto", None)
    periodicita_mesi = getattr(stato_economico, "periodicita_canone_mesi", None)
    importo_canone_periodico = getattr(stato_economico, "importo_canone_periodico", None)

    if not data_inizio or periodicita_mesi in (None, 0) or importo_canone_periodico is None:
        return None

    today = date.today()
    if data_inizio > today:
        return Decimal("0")

    data_fine = getattr(stato_economico, "data_fine_contratto", None)
    effective_end = min(today, data_fine) if data_fine else today
    if effective_end < data_inizio:
        return Decimal("0")

    elapsed_months = (
        (effective_end.year - data_inizio.year) * 12
        + (effective_end.month - data_inizio.month)
    )
    if effective_end.day < data_inizio.day:
        elapsed_months -= 1

    if elapsed_months < periodicita_mesi:
        return Decimal("0")

    numero_canoni_maturati = elapsed_months // periodicita_mesi
    return Decimal(numero_canoni_maturati) * Decimal(str(importo_canone_periodico))


def _pr_ultimi_12_mesi_text(impianto, metriche) -> str:
    pr_value = getattr(metriche, "pr_ultimi_12_mesi", None)
    if pr_value is not None:
        return _fmt_performance_ratio(pr_value)

    has_weather_station = impianto.dispositivi.filter(
        tipo_dispositivo=ImpiantoDispositivo.TipoDispositivo.WEATHER_STATION,
        attivo=True,
    ).exists()
    if not has_weather_station:
        return "WSM"
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
        return "WSM", "metric-delta metric-delta-muted"
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
                totale_annuale_su_MW=_fmt_decimal(
                    getattr(stato_economico, "totale_annuale_su_mw", None)
                ),
                totale_annuo=_fmt_decimal(
                    getattr(stato_economico, "totale_annuo", None)
                ),
                totale_maturato=_fmt_decimal(_maturato_value(stato_economico)),
                fatturato=_fmt_currency_accounting(
                    _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto)
                ),
                totale_incassato=_fmt_decimal(
                    getattr(stato_economico, "incassato", None)
                ),
                data_prossima_fattura=_fmt_date(
                    getattr(stato_economico, "data_prossima_fattura", None)
                ),
                importo_prossima_fattura=_fmt_decimal(
                    getattr(stato_economico, "importo_prossima_fattura", None)
                ),
                totale_ordinato_straordinario=_fmt_currency_accounting(
                    _resolve_costo_straordinario_totale_value(
                        impianto,
                        stato_economico,
                        costo_straordinario_by_impianto,
                    )
                ),
                totale_fatturato_straordinario=_fmt_currency_accounting(
                    _resolve_totale_fatturato_straordinario_value(
                        impianto,
                        stato_economico,
                        fatturato_straordinario_by_impianto,
                    )
                ),
                margine_straordinario=margine_straordinario,
                margine_straordinario_class=margine_straordinario_class,
                numero_fatture_straordinarie_annuo=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_annuo_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_annuo_by_impianto,
                    )
                ),
                numero_fatture_straordinarie_totali=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_totali_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_totali_by_impianto,
                    )
                ),
            )
        )

    return rows


def build_fotovoltaico_proprieta_rows_portale(
    fatturato_by_impianto: dict[str, Decimal] | None = None,
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
                totale_annuale_su_MW=_fmt_decimal(
                    getattr(stato_economico, "totale_annuale_su_mw", None)
                ),
                totale_annuo=_fmt_decimal(
                    getattr(stato_economico, "totale_annuo", None)
                ),
                totale_maturato=_fmt_decimal(_maturato_value(stato_economico)),
                fatturato=_fmt_currency_accounting(
                    _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto)
                ),
                totale_incassato=_fmt_decimal(
                    getattr(stato_economico, "incassato", None)
                ),
                data_prossima_fattura=_fmt_date(
                    getattr(stato_economico, "data_prossima_fattura", None)
                ),
                importo_prossima_fattura=_fmt_decimal(
                    getattr(stato_economico, "importo_prossima_fattura", None)
                ),
                totale_ordinato_straordinario=_fmt_currency_accounting(
                    _resolve_costo_straordinario_totale_value(
                        impianto,
                        stato_economico,
                        costo_straordinario_by_impianto,
                    )
                ),
                totale_fatturato_straordinario=_fmt_currency_accounting(
                    _resolve_totale_fatturato_straordinario_value(
                        impianto,
                        stato_economico,
                        fatturato_straordinario_by_impianto,
                    )
                ),
                margine_straordinario=margine_straordinario,
                margine_straordinario_class=margine_straordinario_class,
                numero_fatture_straordinarie_annuo=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_annuo_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_annuo_by_impianto,
                    )
                ),
                numero_fatture_straordinarie_totali=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_totali_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_totali_by_impianto,
                    )
                ),
            )
        )

    return rows


def build_fotovoltaico_in_costruzione_rows_portale(
    fatturato_by_impianto: dict[str, Decimal] | None = None,
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
        mancata_produzione, mancata_produzione_class = _mancata_produzione_cell(impianto, metriche)
        margine_straordinario, margine_straordinario_class = _margine_straordinario_cell(
            impianto,
            stato_economico,
            costo_straordinario_by_impianto,
            fatturato_straordinario_by_impianto,
        )

        rows.append(
            FotovoltaicoInCostruzioneRow(
                status_class=_status_class_portale(metriche),
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
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
                totale_annuale_su_MW=_fmt_decimal(
                    getattr(stato_economico, "totale_annuale_su_mw", None)
                ),
                totale_annuo=_fmt_decimal(
                    getattr(stato_economico, "totale_annuo", None)
                ),
                totale_maturato=_fmt_decimal(_maturato_value(stato_economico)),
                fatturato=_fmt_currency_accounting(
                    _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto)
                ),
                totale_incassato=_fmt_decimal(
                    getattr(stato_economico, "incassato", None)
                ),
                data_prossima_fattura=_fmt_date(
                    getattr(stato_economico, "data_prossima_fattura", None)
                ),
                importo_prossima_fattura=_fmt_decimal(
                    getattr(stato_economico, "importo_prossima_fattura", None)
                ),
                totale_ordinato_straordinario=_fmt_currency_accounting(
                    _resolve_costo_straordinario_totale_value(
                        impianto,
                        stato_economico,
                        costo_straordinario_by_impianto,
                    )
                ),
                totale_fatturato_straordinario=_fmt_currency_accounting(
                    _resolve_totale_fatturato_straordinario_value(
                        impianto,
                        stato_economico,
                        fatturato_straordinario_by_impianto,
                    )
                ),
                margine_straordinario=margine_straordinario,
                margine_straordinario_class=margine_straordinario_class,
                numero_fatture_straordinarie_annuo=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_annuo_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_annuo_by_impianto,
                    )
                ),
                numero_fatture_straordinarie_totali=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_totali_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_totali_by_impianto,
                    )
                ),
            )
        )

    return rows


def build_agrivoltaico_rows_portale(
    fatturato_by_impianto: dict[str, Decimal] | None = None,
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
                totale_annuale_su_MW=_fmt_decimal(
                    getattr(stato_economico, "totale_annuale_su_mw", None)
                ),
                totale_annuo=_fmt_decimal(
                    getattr(stato_economico, "totale_annuo", None)
                ),
                totale_maturato=_fmt_decimal(_maturato_value(stato_economico)),
                fatturato=_fmt_currency_accounting(
                    _resolve_fatturato_value(impianto, stato_economico, fatturato_by_impianto)
                ),
                totale_incassato=_fmt_decimal(
                    getattr(stato_economico, "incassato", None)
                ),
                data_prossima_fattura=_fmt_date(
                    getattr(stato_economico, "data_prossima_fattura", None)
                ),
                importo_prossima_fattura=_fmt_decimal(
                    getattr(stato_economico, "importo_prossima_fattura", None)
                ),
                totale_ordinato_straordinario=_fmt_currency_accounting(
                    _resolve_costo_straordinario_totale_value(
                        impianto,
                        stato_economico,
                        costo_straordinario_by_impianto,
                    )
                ),
                totale_fatturato_straordinario=_fmt_currency_accounting(
                    _resolve_totale_fatturato_straordinario_value(
                        impianto,
                        stato_economico,
                        fatturato_straordinario_by_impianto,
                    )
                ),
                margine_straordinario=margine_straordinario,
                margine_straordinario_class=margine_straordinario_class,
                numero_fatture_straordinarie_annuo=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_annuo_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_annuo_by_impianto,
                    )
                ),
                numero_fatture_straordinarie_totali=_fmt_integer(
                    _resolve_numero_fatture_straordinarie_totali_value(
                        impianto,
                        stato_economico,
                        fatture_straordinarie_totali_by_impianto,
                    )
                ),
            )
        )

    return rows


def build_fotovoltaico_ppu_rows_portale():
    queryset = _build_fotovoltaico_ppu_portale_queryset()

    rows: list[FotovoltaicoPPURow] = []
    for impianto in queryset:
        stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)

        rows.append(
            FotovoltaicoPPURow(
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
                tariffa_mwh="--",
                strumento_di_contabilizzazione="--",
                maturato_dall_inizio="--",
                fatturato_dall_inizio="--",
                tipologia_di_pagamento="--",
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
                importo_reale_annuo="--",
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
        .prefetch_related("dispositivi")
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
