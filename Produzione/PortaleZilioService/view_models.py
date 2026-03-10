from dataclasses import dataclass


'''
Totale maturato (da inizio contratto): si calcola in automatico dalla data di inizio contratto applicando la periodicità al canone
Fatturato (andando a leggere su esolver le fatture effettivamente emesse)
Andando a leggere su esolver se è pagata

Riepilogo colonne sotto header ORDINARIO:
Contratto inizio | Contratto fine | Anni di contratto | Totale contratto | Totale annuo su MW | Totale annuo |
Maturato | Fatturato | Incassato | Data prossima fattura | Importo prossima fattura

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
    ore_equivalenti_pvsys: str   # era da cambiare ?
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_annuale_su_MW: str
    totale_contratto: str
    totale_annuale: str
    totale_maturato: str
    totale_fatturato: str
    totale_incassato: str
    data_prossima_fattura: str # da togliere ? 
    importo_prossima_fattura: str # da togliere ?

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str
    totale_fatturato_straordinario: str
    totale_ordinato_straordinario: str


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
    ore_equivalenti_pvsys: str   # era da cambiare ?
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_annuale_su_MW: str
    totale_contratto: str
    totale_annuale: str
    totale_maturato: str
    totale_fatturato: str
    totale_incassato: str
    data_prossima_fattura: str # da togliere ? 
    importo_prossima_fattura: str # da togliere ?

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str
    totale_fatturato_straordinario: str
    totale_ordinato_straordinario: str


@dataclass(frozen=True)
class FotovoltaicoInCostruzioneRow:
    # COLONNE ORDINARIO 
    status_class: str
    nome_impianto: str
    nome_cliente: str
    potenza: str
    pr_contrattuale: str  # 78% di solito secondo nicola e comunque lo deve inserire lui 
    pr_ultimi_12_mesi: str # prima era 3 mesi calcolato attraverso i dati dalle API  
    mancata_produzione: str
    ore_equivalenti: str   # Nicola capisce se sono a contratto o no
    ore_equivalenti_pvsys: str   # era da cambiare ?
    inizio_contratto: str
    fine_contratto: str
    totale_anni_contratto: str
    totale_annuale_su_MW: str
    totale_contratto: str
    totale_annuale: str
    totale_maturato: str
    totale_fatturato: str
    totale_incassato: str
    data_prossima_fattura: str # da togliere ? 
    importo_prossima_fattura: str # da togliere ?

    # COLONNE STRAORDINARIO  - separate da una linea rossa 

    numero_fatture_straordinarie_annuo: str
    numero_fatture_straordinarie_totali: str
    totale_fatturato_straordinario: str
    totale_ordinato_straordinario: str


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
    importo_stimato_annuo: str  # annuo ? da verificare
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



''' 
STARTING POINT MODELS

@dataclass(frozen=True)
class FotovoltaicoClientiRow:
    status_class: str
    nome: str
    potenza: str
    pr_atteso: str
    pr_ultimi_3_mesi: str
    ore_equiv: str
    inizio_contratto: str
    fine_contratto: str
    totale_contratto: str
    fatturato: str
    da_incassare: str
    dettaglio_url: str


@dataclass(frozen=True)
class FotovoltaicoPPURow:
    status_class: str
    nome: str
    potenza: str
    produzione_mese: str
    prezzo_medio: str
    ricavo_mese: str
    ultimo_aggiornamento: str
    dettaglio_url: str
'''
