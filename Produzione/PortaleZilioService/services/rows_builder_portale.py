from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..models import ImpiantoAnagrafica, ImpiantoDispositivo
from ..view_models import FotovoltaicoClientiRow, FotovoltaicoProprietaRow


def _fmt_date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "--"


def _fmt_not_defined(value: str | None) -> str:
    if value is None:
        return "not yet defined"
    stripped = value.strip()
    return stripped or "not yet defined"


def _fmt_equivalent_hours(value: Decimal | float | None) -> str:
    if value is None:
        return "--"
    return f"{float(value):.2f}"


def _fmt_performance_ratio(value: Decimal | float | None) -> str:
    if value is None:
        return "--"
    return f"{float(value) * 100:.2f}%"


def _fmt_decimal(value: Decimal | float | None) -> str:
    if value is None:
        return "--"
    return f"{float(value):.2f}"


def _fmt_power(value: Decimal | float | None) -> str:
    if value is None:
        return "--"
    return f"{float(value):.2f} kW"


def _calcola_anni_contratto(data_inizio: date | None, data_fine: date | None) -> str:
    if not data_inizio or not data_fine:
        return "--"
    anni = (data_fine - data_inizio).days / 365.25
    return f"{anni:.1f}"


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


def _status_class_portale(metriche) -> str:
    status = getattr(metriche, "stato_operativo", None)
    if status == "online":
        return "status-dot-green"
    if status == "offline":
        return "status-dot-red"
    if status == "warning":
        return "status-dot-yellow"
    return "status-dot-gray"


def build_fotovoltaico_clienti_rows_portale():
    queryset = (
        _build_fotovoltaico_portale_queryset(categoria_fv="cliente")
    )

    rows: list[FotovoltaicoClientiRow] = []
    for impianto in queryset:
        metadata = impianto.fotovoltaico_metadata
        stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)
        metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)

        rows.append(
            FotovoltaicoClientiRow(
                status_class=_status_class_portale(metriche),
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
                potenza=_fmt_power(impianto.potenza_installata_kw),
                pr_contrattuale=_fmt_decimal(metadata.pr_contrattuale),
                pr_ultimi_12_mesi=_pr_ultimi_12_mesi_text(impianto, metriche),
                mancata_produzione="--",
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
                totale_contratto="--",
                totale_annuale_su_MW="--",
                totale_annuo="--",
                totale_maturato="--",
                fatturato="--",
                totale_incassato="--",
                data_prossima_fattura="--",
                importo_prossima_fattura="--",
                totale_ordinato_straordinario="--",
                totale_fatturato_straordinario="--",
                margine_straordinario="--",
                numero_fatture_straordinarie_annuo="--",
                numero_fatture_straordinarie_totali="--",
            )
        )

    return rows


def build_fotovoltaico_proprieta_rows_portale():
    queryset = _build_fotovoltaico_portale_queryset(categoria_fv="proprieta")

    rows: list[FotovoltaicoProprietaRow] = []
    for impianto in queryset:
        metadata = impianto.fotovoltaico_metadata
        stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)
        metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)

        rows.append(
            FotovoltaicoProprietaRow(
                status_class=_status_class_portale(metriche),
                nome_impianto=impianto.nome_impianto or "--",
                nome_cliente=_fmt_not_defined(impianto.nome_cliente),
                potenza=_fmt_power(impianto.potenza_installata_kw),
                pr_contrattuale=_fmt_decimal(metadata.pr_contrattuale),
                pr_ultimi_12_mesi=_pr_ultimi_12_mesi_text(impianto, metriche),
                mancata_produzione="--",
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
                totale_contratto="--",
                totale_annuale_su_MW="--",
                totale_annuo="--",
                totale_maturato="--",
                fatturato="--",
                totale_incassato="--",
                data_prossima_fattura="--",
                importo_prossima_fattura="--",
                totale_ordinato_straordinario="--",
                totale_fatturato_straordinario="--",
                margine_straordinario="--",
                numero_fatture_straordinarie_annuo="--",
                numero_fatture_straordinarie_totali="--",
            )
        )

    return rows


def _build_fotovoltaico_portale_queryset(*, categoria_fv: str):
    return (
        ImpiantoAnagrafica.objects.select_related(
            "fotovoltaico_metadata",
            "fotovoltaico_stato_economico",
            "fotovoltaico_metriche_tecniche",
        )
        .prefetch_related("dispositivi")
        .filter(
            tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
            fotovoltaico_metadata__categoria_fv=categoria_fv,
            fotovoltaico_metadata__is_ppu=False,
        )
        .exclude(stato_impianto=ImpiantoAnagrafica.StatoImpianto.IN_COSTRUZIONE)
        .order_by("nome_cliente", "nome_impianto")
    )
