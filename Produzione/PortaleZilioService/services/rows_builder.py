from datetime import date
from decimal import Decimal

from ..models import FvMetadata, MonitoraggioImpianto
from ..view_models import (
    FotovoltaicoClientiRow,
    FotovoltaicoInCostruzioneRow,
    FotovoltaicoPPURow,
    FotovoltaicoProprietaRow,
    IdroelettricoProprietaRow,
)


def _fmt_date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "--"


def _fmt_equivalent_hours(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.2f}"


def _fmt_performance_ratio(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value * 100:.2f}%"


def _ore_equivalenti_text(meta: FvMetadata) -> str:
    if meta.impianto is None:
        return "--"
    return _fmt_equivalent_hours(meta.impianto.ore_equivalenti_annue)


def _pr_annuo_text(meta: FvMetadata) -> str:
    if meta.impianto is not None and meta.impianto.performance_ratio_annuo is not None:
        return _fmt_performance_ratio(meta.impianto.performance_ratio_annuo)

    if meta.nome_impianto:
        fallback = (
            MonitoraggioImpianto.objects.filter(
                nome_impianto__startswith=f"{meta.nome_impianto} -",
                performance_ratio_annuo__isnull=False,
            )
            .order_by("nome_impianto")
            .first()
        )
        if fallback is not None:
            return _fmt_performance_ratio(fallback.performance_ratio_annuo)

    return "--"


def _status_class(meta: FvMetadata) -> str:
    if meta.impianto is None or not meta.impianto.stato_operativo:
        return "--"

    status = meta.impianto.stato_operativo.lower()
    if status == "online":
        return "status-dot-green"
    if status == "offline":
        return "status-dot-red"
    if status in {"warning", "warn"}:
        return "status-dot-yellow"
    return "--"


def _calcola_anni_contratto(data_inizio: date | None, data_fine: date | None) -> str:
    if not data_inizio or not data_fine:
        return "--"
    anni = (data_fine - data_inizio).days / 365.25
    return f"{anni:.1f}"


def _potenza_text(meta: FvMetadata) -> str:
    return f"{meta.potenza:.2f} kW" if meta.potenza is not None else "--"


def _fmt_decimal(value: Decimal | None) -> str:
    if value is None:
        return "--"
    return f"{value:.2f}"


def build_fotovoltaico_clienti_rows():
    q = FvMetadata.objects.select_related("impianto").filter(
        categoria_fv=FvMetadata.CategoriaFv.CLIENTE,
        is_in_costruzione=False,
    ).order_by("nome_cliente")
    rows = []
    for meta in q:
        rows.append(
            FotovoltaicoClientiRow(
                status_class=_status_class(meta),
                nome_impianto=meta.nome_impianto or "--",
                nome_cliente=meta.nome_cliente or "--",
                potenza=_potenza_text(meta),
                pr_contrattuale=str(meta.pr_contrattuale) if meta.pr_contrattuale is not None else "--",
                pr_ultimi_12_mesi=_pr_annuo_text(meta),
                mancata_produzione="--",
                ore_equivalenti=_ore_equivalenti_text(meta),
                inizio_contratto=_fmt_date(meta.data_inizio_contratto),
                fine_contratto=_fmt_date(meta.data_fine_contratto),
                totale_anni_contratto=_calcola_anni_contratto(meta.data_inizio_contratto, meta.data_fine_contratto),
                totale_annuale_su_MW=_fmt_decimal(meta.totale_annuo_su_mv),
                totale_contratto=_fmt_decimal(meta.totale_contratto),
                totale_annuale=_fmt_decimal(meta.totale_annuo),
                totale_maturato="--",
                totale_fatturato="--",
                totale_incassato="--",
                data_prossima_fattura="--",
                importo_prossima_fattura="--",
                numero_fatture_straordinarie_annuo="--",
                numero_fatture_straordinarie_totali="--",
                totale_fatturato_straordinario="--",
                totale_ordinato_straordinario="--",
                margine_straordinario="--",
            )
        )
    return rows


def build_fotovoltaico_proprieta_rows():
    q = FvMetadata.objects.select_related("impianto").filter(
        categoria_fv=FvMetadata.CategoriaFv.PROPRIETA,
        is_in_costruzione=False,
    ).order_by("nome_impianto")
    rows = []
    for meta in q:
        rows.append(
            FotovoltaicoProprietaRow(
                status_class=_status_class(meta),
                nome_impianto=meta.nome_impianto or "--",
                nome_cliente=meta.nome_cliente or "--",
                potenza=_potenza_text(meta),
                pr_contrattuale=str(meta.pr_contrattuale) if meta.pr_contrattuale is not None else "--",
                pr_ultimi_12_mesi=_pr_annuo_text(meta),
                mancata_produzione="--",
                ore_equivalenti=_ore_equivalenti_text(meta),
                inizio_contratto=_fmt_date(meta.data_inizio_contratto),
                fine_contratto=_fmt_date(meta.data_fine_contratto),
                totale_anni_contratto=_calcola_anni_contratto(meta.data_inizio_contratto, meta.data_fine_contratto),
                totale_annuale_su_MW=_fmt_decimal(meta.totale_annuo_su_mv),
                totale_contratto=_fmt_decimal(meta.totale_contratto),
                totale_annuale=_fmt_decimal(meta.totale_annuo),
                totale_maturato="--",
                totale_fatturato="--",
                totale_incassato="--",
                data_prossima_fattura="--",
                importo_prossima_fattura="--",
                numero_fatture_straordinarie_annuo="--",
                numero_fatture_straordinarie_totali="--",
                totale_fatturato_straordinario="--",
                totale_ordinato_straordinario="--",
                margine_straordinario="--",
            )
        )
    return rows


def build_fotovoltaico_in_costruzione_rows():
    q = FvMetadata.objects.select_related("impianto").filter(
        is_in_costruzione=True,
    ).order_by("nome_impianto")
    rows = []
    for meta in q:
        rows.append(
            FotovoltaicoInCostruzioneRow(
                status_class=_status_class(meta),
                nome_impianto=meta.nome_impianto or "--",
                nome_cliente=meta.nome_cliente or "--",
                potenza=_potenza_text(meta),
                pr_contrattuale=str(meta.pr_contrattuale) if meta.pr_contrattuale is not None else "--",
                pr_ultimi_12_mesi=_pr_annuo_text(meta),
                mancata_produzione="--",
                ore_equivalenti=_ore_equivalenti_text(meta),
                inizio_contratto=_fmt_date(meta.data_inizio_contratto),
                fine_contratto=_fmt_date(meta.data_fine_contratto),
                totale_anni_contratto=_calcola_anni_contratto(meta.data_inizio_contratto, meta.data_fine_contratto),
                totale_annuale_su_MW=_fmt_decimal(meta.totale_annuo_su_mv),
                totale_contratto=_fmt_decimal(meta.totale_contratto),
                totale_annuale=_fmt_decimal(meta.totale_annuo),
                totale_maturato="--",
                totale_fatturato="--",
                totale_incassato="--",
                data_prossima_fattura="--",
                importo_prossima_fattura="--",
                numero_fatture_straordinarie_annuo="--",
                numero_fatture_straordinarie_totali="--",
                totale_fatturato_straordinario="--",
                totale_ordinato_straordinario="--",
                margine_straordinario="--",
            )
        )
    return rows


def build_fotovoltaico_ppu_rows():
    rows = []
    q = FvMetadata.objects.select_related("impianto").filter(is_ppu=True).order_by("nome_impianto")
    for meta in q:
        lettura_dati = "--"
        if meta.impianto is not None:
            lettura_dati = meta.impianto.lettura_dati or "--"

        rows.append(
            FotovoltaicoPPURow(
                nome_impianto=meta.nome_impianto or "--",
                nome_cliente=meta.nome_cliente or "--",
                tariffa_mwh="--",
                strumento_di_contabilizzazione=lettura_dati,
                maturato_dall_inizio="--",
                fatturato_dall_inizio="--",
                tipologia_di_pagamento="--",
                data_di_inizio=_fmt_date(meta.data_inizio_contratto),
                data_di_fine=_fmt_date(meta.data_fine_contratto),
                totale_anni_contratto=_calcola_anni_contratto(meta.data_inizio_contratto, meta.data_fine_contratto),
                pr_stimato_annuo="--",
                energia_stimata_annua="--",
                mancata_produzione="--",
                fatturato_previsto="--",
                importo_reale_annuo="--",
            )
        )
    return rows


def build_idroelettrico_proprieta_rows():
    return [
        IdroelettricoProprietaRow(
            status_class="status-dot-green",
            nome="San Teodoro",
            potenza="259.2 kW",
            portata="1.80 mc/s",
            salto="22.5 m",
            lettura_dati="API_ISC",
            stato_contratto="Attivo",
            dettaglio_url="#",
        )
    ]
