from dataclasses import dataclass


'''
Nota: dobbiamo stabilire come quali tabelle farci preparare da Sistemi e capire come funzionano le API
'''



# region FOTOVOLTAICO
@dataclass(frozen=True)
class FotovoltaicoClientiRow:
    # COLONNE ORDINARIO 
    status_class: str
    nome_impianto: str
    nome_cliente: str
    potenza: str
    pr_contrattuale: str  # 78% di solito secondo nicola e comunque lo deve inserire lui 
    pr_ultimi_12_mesi: str # prima era 3 mesi calcolato attraverso i dati dalle API  
    mancata_produzione: str
    ore_equivalenti: str   # Nicola capisce se sono a contratto o no
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_contratto: str
    totale_annuale_su_MW: str
    totale_annuo: str
    totale_maturato: str
    fatturato: str
    totale_incassato: str
    data_prossima_fattura: str # da togliere ? 
    importo_prossima_fattura: str # da togliere ?

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    totale_ordinato_straordinario: str
    totale_fatturato_straordinario: str
    margine_straordinario: str
    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str


@dataclass(frozen=True)
class FotovoltaicoProprietaRow:
    # COLONNE ORDINARIO 
    status_class: str
    nome_impianto: str
    nome_cliente: str
    potenza: str
    pr_contrattuale: str  # 78% di solito secondo nicola e comunque lo deve inserire lui 
    pr_ultimi_12_mesi: str # prima era 3 mesi calcolato attraverso i dati dalle API  
    mancata_produzione: str
    ore_equivalenti: str   # Nicola capisce se sono a contratto o no
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_contratto: str
    totale_annuale_su_MW: str
    totale_annuo: str
    totale_maturato: str
    fatturato: str
    totale_incassato: str
    data_prossima_fattura: str # da togliere ? 
    importo_prossima_fattura: str # da togliere ?

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    totale_ordinato_straordinario: str
    totale_fatturato_straordinario: str
    margine_straordinario: str
    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str


@dataclass(frozen=True)
class FotovoltaicoInCostruzioneRow:
    # COLONNE ORDINARIO 
    status_class: str
    nome_impianto: str
    nome_cliente: str
    tipologia_contratto: str
    potenza: str
    pr_contrattuale: str  # 78% di solito secondo nicola e comunque lo deve inserire lui 
    pr_ultimi_12_mesi: str # prima era 3 mesi calcolato attraverso i dati dalle API  
    mancata_produzione: str
    ore_equivalenti: str   # Nicola capisce se sono a contratto o no
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_contratto: str
    totale_annuale_su_MW: str
    totale_annuo: str
    totale_maturato: str
    fatturato: str
    totale_incassato: str
    data_prossima_fattura: str # da togliere ? 
    importo_prossima_fattura: str # da togliere ?

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    totale_ordinato_straordinario: str
    totale_fatturato_straordinario: str
    margine_straordinario: str
    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str
    
@dataclass(frozen=True)
class AgrivoltaicoRow:
    # COLONNE ORDINARIO 
    status_class: str
    nome_impianto: str
    nome_cliente: str
    potenza: str
    pr_contrattuale: str  # 78% di solito secondo nicola e comunque lo deve inserire lui 
    pr_ultimi_12_mesi: str # prima era 3 mesi calcolato attraverso i dati dalle API  
    mancata_produzione: str
    ore_equivalenti: str   # Nicola capisce se sono a contratto o no
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_contratto: str
    totale_annuale_su_MW: str
    totale_annuo: str
    totale_maturato: str
    fatturato: str
    totale_incassato: str
    data_prossima_fattura: str # da togliere ? 
    importo_prossima_fattura: str # da togliere ?

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    totale_ordinato_straordinario: str
    totale_fatturato_straordinario: str
    margine_straordinario: str
    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str

@dataclass(frozen=True)
class FotovoltaicoPPURow:
    nome_impianto: str
    nome_cliente: str
    tariffa_mwh: str
    strumento_di_contabilizzazione: str   # contatore, supervisione SAJ, Sungrow
    # lettura_contatore_iniziale: str
    maturato_dall_inizio: str # stima da misure contatore 
    fatturato_dall_inizio: str  # fatturato preso da gestionale esolver 
    tipologia_di_pagamento: str  # mensile, trimestrale, semestrale, annuale
    data_di_inizio: str
    data_di_fine: str
    totale_anni_contratto: str
    pr_stimato_annuo: str 
    energia_stimata_annua: str # annuo ? da verificare 
    mancata_produzione: str
    fatturato_previsto: str  # annuo ? da verificare
    importo_reale_annuo: str  # annuo ? da verificare


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

# endregion 


