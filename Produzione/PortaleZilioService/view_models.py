from dataclasses import dataclass





# region FOTOVOLTAICO
@dataclass(frozen=True)
class FotovoltaicoClientiRow:
    # COLONNE ORDINARIO 
    status_class: str
    nome_impianto: str
    nome_cliente: str
    potenza_contratto: str
    potenza_installata: str
    pr_contrattuale: str  # 78% di solito 
    pr_ultimi_12_mesi: str 
    mancata_produzione: str
    mancata_produzione_class: str
    ore_equivalenti: str  
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_contratto: str
    totale_annuale_su_MW: str
    totale_annuo: str
    totale_maturato: str
    fatturato: str
    totale_incassato: str
    data_prossima_fattura: str 
    data_prossima_fattura_class: str
    importo_prossima_fattura: str 

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    totale_ordinato_straordinario: str
    totale_fatturato_straordinario: str
    margine_straordinario: str
    margine_straordinario_class: str
    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str


@dataclass(frozen=True)
class FotovoltaicoProprietaRow:
    # COLONNE ORDINARIO 
    status_class: str
    nome_impianto: str
    nome_cliente: str
    potenza_contratto: str
    potenza_installata: str
    pr_contrattuale: str  # 78% di solito 
    pr_ultimi_12_mesi: str 
    mancata_produzione: str
    mancata_produzione_class: str
    ore_equivalenti: str  
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_contratto: str
    totale_annuale_su_MW: str
    totale_annuo: str
    totale_maturato: str
    fatturato: str
    totale_incassato: str
    data_prossima_fattura: str 
    data_prossima_fattura_class: str
    importo_prossima_fattura: str 

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    totale_ordinato_straordinario: str
    totale_fatturato_straordinario: str
    margine_straordinario: str
    margine_straordinario_class: str
    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str


@dataclass(frozen=True)
class FotovoltaicoInCostruzioneRow:
    # COLONNE ORDINARIO 
    impianto_id: int
    status_class: str
    nome_impianto: str
    nome_cliente: str
    categoria_fv: str
    tipologia_contratto: str
    potenza: str
    pr_contrattuale: str  # 78% di solito 
    pr_ultimi_12_mesi: str 
    mancata_produzione: str
    mancata_produzione_class: str
    ore_equivalenti: str  
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_contratto: str
    totale_annuale_su_MW: str
    totale_annuo: str
    totale_maturato: str
    fatturato: str
    totale_incassato: str
    data_prossima_fattura: str 
    data_prossima_fattura_class: str
    importo_prossima_fattura: str 

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    totale_ordinato_straordinario: str
    totale_fatturato_straordinario: str
    margine_straordinario: str
    margine_straordinario_class: str
    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str
    
@dataclass(frozen=True)
class AgrivoltaicoRow:
    # COLONNE ORDINARIO 
    status_class: str
    nome_impianto: str
    nome_cliente: str
    potenza_contratto: str
    potenza_installata: str
    pr_contrattuale: str  # 78% di solito 
    pr_ultimi_12_mesi: str 
    mancata_produzione: str
    mancata_produzione_class: str
    ore_equivalenti: str  
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_contratto: str
    totale_annuale_su_MW: str
    totale_annuo: str
    totale_maturato: str
    fatturato: str
    totale_incassato: str
    data_prossima_fattura: str 
    data_prossima_fattura_class: str
    importo_prossima_fattura: str 

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    totale_ordinato_straordinario: str
    totale_fatturato_straordinario: str
    margine_straordinario: str
    margine_straordinario_class: str
    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str

@dataclass(frozen=True)
class FotovoltaicoPPURow:
    nome_impianto: str
    nome_cliente: str
    tariffa_mwh: str
    strumento_di_contabilizzazione: str   # contatore, supervisione SAJ, Sungrow
    energia_prodotta_anno_corrente: str
    energia_immessa_anno_corrente: str
    energia_autoconsumata_anno_corrente: str
    percentuale_autoconsumo_anno_corrente: str
    maturato_ppu_anno_corrente_kwh: str
    maturato_ppu_anno_corrente_euro: str
    fatturato_dall_inizio: str  # fatturato preso da gestionale esolver 
    tipologia_di_pagamento: str  # mensile, trimestrale, semestrale, annuale
    data_di_inizio: str
    data_di_fine: str
    totale_anni_contratto: str
    pr_stimato_annuo: str 
    energia_stimata_annua: str # annuo ? da verificare 
    mancata_produzione: str
    fatturato_previsto: str  # annuo ? da verificare


# endregion


# region IDROELETTRICO

@dataclass(frozen=True)
class IdroelettricoProprietaRow:
    status_class: str
    nome: str
    potenza: str
    portata: str
    salto: str
    lettura_dati: str
    stato_contratto: str
    dettaglio_url: str


@dataclass(frozen=True)
class IdroelettricoGSERow:
    nome_impianto: str
    nome_cliente: str
    tariffa_mwh: str
    strumento_di_contabilizzazione: str
    maturato_dall_inizio: str
    fatturato_dall_inizio: str
    tipologia_di_pagamento: str
    data_di_inizio: str
    data_di_fine: str
    totale_anni_contratto: str
    pr_stimato_annuo: str
    energia_stimata_annua: str
    mancata_produzione: str
    fatturato_previsto: str
    importo_reale_annuo: str

# endregion 


