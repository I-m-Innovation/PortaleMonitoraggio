from ..view_models import IdroelettricoGSERow, IdroelettricoProprietaRow


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


def build_idroelettrico_gse_rows():
    return [
        IdroelettricoGSERow(
            nome_impianto="San Teodoro",
            nome_cliente="GSE",
            tariffa_mwh="--",
            strumento_di_contabilizzazione="--",
            maturato_dall_inizio="--",
            fatturato_dall_inizio="--",
            tipologia_di_pagamento="--",
            data_di_inizio="--",
            data_di_fine="--",
            totale_anni_contratto="--",
            pr_stimato_annuo="--",
            energia_stimata_annua="--",
            mancata_produzione="--",
            fatturato_previsto="--",
            importo_reale_annuo="--",
        )
    ]
