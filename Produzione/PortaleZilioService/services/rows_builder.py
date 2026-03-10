from datetime import date

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


def _calcola_anni_contratto(data_inizio: date | None, data_fine: date | None) -> str:
    if not data_inizio or not data_fine:
        return "--"
    anni = (data_fine - data_inizio).days / 365.25
    return f"{anni:.1f}"


def _potenza_text(meta: FvMetadata) -> str:
    #just two number after the ,
    return f"{meta.potenza:.2f} kW" if meta.potenza is not None else "--"

def _build_om_row(meta: FvMetadata, row_class):
    return row_class(
        status_class= "--",
        nome_impianto=meta.nome_impianto or "--",
        nome_cliente=meta.nome_cliente or "--",
        potenza=_potenza_text(meta),
        pr_contrattuale=str(meta.pr_contrattuale) if meta.pr_contrattuale is not None else "--",
        pr_ultimi_12_mesi="--",
        mancata_produzione="--",
        ore_equivalenti="--",
        ore_equivalenti_pvsys="--",
        inizio_contratto=_fmt_date(meta.data_inizio_contratto),
        fine_contratto=_fmt_date(meta.data_fine_contratto),
        totale_anni_contratto=_calcola_anni_contratto(meta.data_inizio_contratto, meta.data_fine_contratto),
        totale_annuale_su_MW="--",
        totale_contratto="--",
        totale_annuale="--",
        totale_maturato="--",
        totale_fatturato="--",
        totale_incassato="--",
        data_prossima_fattura="--",
        importo_prossima_fattura="--",
        numero_fatture_straordinarie_annuo="--",
        numero_fatture_straordinarie_totali="--",
        totale_fatturato_straordinario="--",
        totale_ordinato_straordinario="--",
    )


# Orchestration module that builds row objects/lists for each table shown in home.html.
def build_fotovoltaico_clienti_rows():
    q = FvMetadata.objects.select_related("impianto").filter(
        categoria_fv=FvMetadata.CategoriaFv.CLIENTE,
        is_in_costruzione=False,
    ).order_by("nome_cliente")
    return [_build_om_row(meta, FotovoltaicoClientiRow) for meta in q]


def build_fotovoltaico_proprieta_rows():
    q = FvMetadata.objects.select_related("impianto").filter(
        categoria_fv=FvMetadata.CategoriaFv.PROPRIETA,
        is_in_costruzione=False,
    ).order_by("nome_impianto")
    return [_build_om_row(meta, FotovoltaicoProprietaRow) for meta in q]


def build_fotovoltaico_in_costruzione_rows():
    q = FvMetadata.objects.select_related("impianto").filter(
        is_in_costruzione=True,
    ).order_by("nome_impianto")
    return [_build_om_row(meta, FotovoltaicoInCostruzioneRow) for meta in q]


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
                importo_stimato_annuo="--",
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
