from django.shortcuts import render, get_object_or_404, redirect
from MonitoraggioImpianti.models import Impianto

from django.http import  JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import datetime
import calendar
import shutil
import os
from AutomazioneDati.models import  Contatore, LetturaContatore, regsegnanti
from MonitoraggioImpianti.models import Impianto as MonitoraggioImpianto
from django.contrib import messages
from django.urls.exceptions import NoReverseMatch
import re
from django.utils.dateparse import parse_datetime
from django.db import models
from django.utils import timezone


def home(request):
    from MonitoraggioImpianti.models import Impianto 
    # Filtriamo solo gli impianti con tipo "Idroelettrico"
    impianti = Impianto.objects.filter(tipo='Idroelettrico')
    return render(request, 'home.html', {'impianti': impianti})



def diarioenergie(request, nickname):
    print(f"\n========================= INIZIO diarioenergie =========================")
    print(f"DEBUG: Chiamata vista diarioenergie con nickname: {nickname}")
    # Ottieni l'impianto
    impianto = get_object_or_404(Impianto, nickname=nickname)
    print(f"DEBUG: Impianto trovato: ID={impianto.id}, Nickname={impianto.nickname}, Nome={getattr(impianto, 'nome', 'N/A')}")

    # Ottieni l'anno dalla query string, default all'anno corrente
    anno_corrente = request.GET.get('year', str(timezone.now().year))
    print(f"DEBUG: year dalla querystring: {anno_corrente}")
    anno_corrente = int(anno_corrente)
    print(f"DEBUG: Anno corrente (usato per la vista): {anno_corrente}")

    # Calcola le date di inizio e fine anno
    data_inizio_anno = datetime.date(anno_corrente, 1, 1)
    data_fine_anno = datetime.date(anno_corrente, 12, 31)
    print(f"DEBUG: Data inizio anno: {data_inizio_anno}, Data fine anno: {data_fine_anno}")

    # Filtra tutti i contatori (attivi e dismessi nell'anno corrente) per l'impianto selezionato
    # e ordina per data di installazione per facilitare l'identificazione attivo/sostituito
    contatori_all_types = Contatore.objects.filter(
        impianto_nickname=nickname,
        data_installazione__lte=data_fine_anno
    ).filter(
        models.Q(data_dismissione__isnull=True) | models.Q(data_dismissione__gte=data_inizio_anno)
    ).order_by('data_installazione')

    print(f"DEBUG: Contatori totali trovati per {nickname} nell'anno {anno_corrente}:")
    for i, c in enumerate(contatori_all_types, 1):
        print(f"  {i}. ID: {c.id}, Nome: {c.nome}, Tipologia: {c.tipologia}, Data installazione: {c.data_installazione}, Data dismissione: {c.data_dismissione}, K: {getattr(c,'k','')}, TipoFascio: {getattr(c,'tipologiafascio','')}")

    # Identifica il contatore "attivo" (quello non dismesso) per ciascuna tipologia
    contatore_produzione_attivo = contatori_all_types.filter(tipologia="Produzione", data_dismissione__isnull=True).first()
    contatore_scambio_attivo = contatori_all_types.filter(tipologia="Scambio", data_dismissione__isnull=True).first()
    contatore_ausiliare_attivo = contatori_all_types.filter(tipologia="Ausiliare", data_dismissione__isnull=True).first()

    print(f"DEBUG: contatore_produzione_attivo={contatore_produzione_attivo}")
    print(f"DEBUG: contatore_scambio_attivo={contatore_scambio_attivo}")
    print(f"DEBUG: contatore_ausiliare_attivo={contatore_ausiliare_attivo}")

    # Identifica il contatore "sostituito" (quello dismesso che era attivo durante l'anno) per ciascuna tipologia
    # Include tutti i contatori dismessi che erano attivi durante l'anno visualizzato, non solo quelli dismessi nell'anno corrente
    contatore_produzione_sostituito = contatori_all_types.filter(
        tipologia="Produzione", 
        data_dismissione__isnull=False
    ).order_by('-data_dismissione').first()

    contatore_scambio_sostituito = contatori_all_types.filter(
        tipologia="Scambio", 
        data_dismissione__isnull=False
    ).order_by('-data_dismissione').first()

    contatore_ausiliare_sostituito = contatori_all_types.filter(
        tipologia="Ausiliare", 
        data_dismissione__isnull=False
    ).order_by('-data_dismissione').first()

    print(f"DEBUG: Contatore Produzione Attivo: {contatore_produzione_attivo.nome if contatore_produzione_attivo else 'Nessuno'}")
    print(f"DEBUG: Contatore Produzione Sostituito: {contatore_produzione_sostituito.nome if contatore_produzione_sostituito else 'Nessuno'}")
    print(f"DEBUG: Contatore Scambio Attivo: {contatore_scambio_attivo.nome if contatore_scambio_attivo else 'Nessuno'}")
    print(f"DEBUG: Contatore Scambio Sostituito: {contatore_scambio_sostituito.nome if contatore_scambio_sostituito else 'Nessuno'}")
    print(f"DEBUG: Contatore Ausiliare Attivo: {contatore_ausiliare_attivo.nome if contatore_ausiliare_attivo else 'Nessuno'}")
    print(f"DEBUG: Contatore Ausiliare Sostituito: {contatore_ausiliare_sostituito.nome if contatore_ausiliare_sostituito else 'Nessuno'}")

    # Determina le variabili booleane per il template
    has_produzione = contatore_produzione_attivo is not None or contatore_produzione_sostituito is not None
    has_scambio = contatore_scambio_attivo is not None or contatore_scambio_sostituito is not None
    has_ausiliare = contatore_ausiliare_attivo is not None or contatore_ausiliare_sostituito is not None

    # Determina se c'è stata una sostituzione effettiva per una data tipologia
    has_sostituzione_produzione = contatore_produzione_sostituito is not None
    has_sostituzione_scambio = contatore_scambio_sostituito is not None
    has_sostituzione_ausiliare = contatore_ausiliare_sostituito is not None

    print(f"DEBUG: has_produzione: {has_produzione}")
    print(f"DEBUG: has_scambio: {has_scambio}")
    print(f"DEBUG: has_ausiliare: {has_ausiliare}")
    print(f"DEBUG: has_sostituzione_produzione: {has_sostituzione_produzione}")
    print(f"DEBUG: has_sostituzione_scambio: {has_sostituzione_scambio}")
    print(f"DEBUG: has_sostituzione_ausiliare: {has_sostituzione_ausiliare}")

    # Filtra i contatori da mostrare nella lista a lato (Elenco Contatori)
    contatori = contatori_all_types # Utilizza la lista completa per l'elenco a sinistra e dropdown

    # Ottieni l'ID del contatore specifico dalla query string
    contatore_id = request.GET.get('contatore_id')
    
    # DEBUG: Stampa tutti i contatori disponibili
    print(f"DEBUG: Contatori disponibili per impianto {nickname}: count={contatori.count()}")
    for cont in contatori:
        print(f"  - ID: {cont.id}, Nome: {cont.nome}, Tipologia: {cont.tipologia}, Data_inst: {cont.data_installazione}, Data_dism: {cont.data_dismissione}")

    # DEBUG: Stampa il contatore_id dalla query string
    print(f"DEBUG: contatore_id dalla query string: {contatore_id}")
    
    # Se è specificato un contatore specifico, selezionalo
    if contatore_id:
        print(f"DEBUG: Tentativo di selezione contatore con ID: {contatore_id}")
        contatore_selezionato = get_object_or_404(Contatore, id=contatore_id, impianto_nickname=nickname)
        print(f"DEBUG: Contatore selezionato tramite ID: {contatore_selezionato.nome} ({contatore_selezionato.tipologia})")
    else:
        # Altrimenti prendi il primo contatore disponibile
        contatore_selezionato = contatori.first() if contatori.exists() else None
        print(f"DEBUG: Contatore selezionato automaticamente: {contatore_selezionato.nome if contatore_selezionato else 'Nessuno'} ({contatore_selezionato.tipologia if contatore_selezionato else 'N/A'})")
    
    # Determina quali tipi di contatori sono presenti nell'impianto
    tipologie_presenti = list(contatori.values_list('tipologia', flat=True).distinct())
    print(f"DEBUG: Tipologie di contatori presenti nell'impianto: {tipologie_presenti}")
    
    # Conta quante colonne dovremo mostrare per regolare il layout
    numero_gruppi_colonne = 0
    if contatore_produzione_attivo:
        numero_gruppi_colonne += 5  # Prodotta (3) + Prelevata (2)
    if contatore_produzione_sostituito:
        numero_gruppi_colonne += 5  # Prodotta (3) + Prelevata (2) del contatore sostituito
    if contatore_scambio_attivo:
        numero_gruppi_colonne += 6  # Autoconsumata (3) + Immessa (3)
    if contatore_scambio_sostituito:
        numero_gruppi_colonne += 6  # Autoconsumata (3) + Immessa (3) del contatore sostituito
    if contatore_ausiliare_attivo:
        numero_gruppi_colonne += 3  # Ausiliare (3)
    if contatore_ausiliare_sostituito:
        numero_gruppi_colonne += 3  # Ausiliare (3) del contatore sostituito
    print(f"DEBUG: Numero gruppi colonne per tabella: {numero_gruppi_colonne}")

    dati_mensili_template = []

    # Helper function to calculate readings for a given counter
    def calculate_counter_data(counter_obj, current_year, month):
        data = {
            "campo": "", "ed": "", "gse": "",
            "campo_secondario": "", "ed_secondario": "", "gse_secondario": ""
        }
        if not counter_obj:
            #print(f"DEBUG: calculate_counter_data called with None counter (month={month})")
            return data

        print(f"DEBUG: === Calcolo dati per contatore {counter_obj.nome} (ID:{counter_obj.id}, Tipo:{counter_obj.tipologia}), anno={current_year}, mese={month}")

        install_date = counter_obj.data_installazione
        dismission_date = counter_obj.data_dismissione

        # Check if the month is within the counter's active period for the current year
        month_start_date = datetime.date(current_year, month, 1)
        month_end_date = datetime.date(current_year, month, calendar.monthrange(current_year, month)[1])

        is_active_for_month = (install_date <= month_end_date) and (dismission_date is None or dismission_date >= month_start_date)
        print(f"DEBUG:   install:{install_date}, dismission:{dismission_date}, month_start:{month_start_date}, month_end:{month_end_date}, is_active_for_month:{is_active_for_month}")

        if not is_active_for_month:
            print(f"DEBUG:   Contatore NON ATTIVO per questo mese ({month})/anno {current_year}")
            return data # Return empty data if not active for this month

        letture = LetturaContatore.objects.filter(
            contatore=counter_obj,
            anno__in=[current_year, current_year + 1]
        ).order_by('anno', 'mese')
        letture_dict = {(l.anno, l.mese): l for l in letture}
        print(f"DEBUG:   Trovate {len(letture)} letture per questo contatore nell'anno {current_year} e {current_year+1}")

        lettura_corrente = letture_dict.get((current_year, month))
        if month < 12:
            lettura_successiva = letture_dict.get((current_year, month + 1))
        else:
            lettura_successiva = letture_dict.get((current_year + 1, 1))

        print(f"DEBUG:   Lettura Corrente: {lettura_corrente}")
        print(f"DEBUG:   Lettura Successiva: {lettura_successiva}")

        k_factor = counter_obj.k if counter_obj.k else 1
        print(f"DEBUG:   Fattore k: {k_factor}")
        tipologia_fascio = counter_obj.tipologiafascio.lower() if counter_obj.tipologiafascio else None
        print(f"DEBUG:   tipologia_fascio: {tipologia_fascio}")

        valore_campo_principale = ""
        valore_campo_secondario = ""

        if lettura_corrente and lettura_successiva:
            try:
                if counter_obj.tipologia == "Produzione":
                    # Prodotta (Campo kWh)
                    if tipologia_fascio == "trifascio":
                        val_corrente_prod = float(lettura_corrente.totale_neg or 0)
                        val_successivo_prod = float(lettura_successiva.totale_neg or 0)
                    elif tipologia_fascio == "monofascio":
                        val_corrente_prod = float(lettura_corrente.totale_180n or 0)
                        val_successivo_prod = float(lettura_successiva.totale_180n or 0)
                    else:
                        val_corrente_prod = val_successivo_prod = 0
                    print(f"DEBUG:     [PROD] Prodotta: val_corrente_prod={val_corrente_prod}, val_successivo_prod={val_successivo_prod}, k={k_factor}")

                    if val_corrente_prod == 0 and val_successivo_prod == 0:
                        valore_campo_principale = ""
                    else:
                        calcolato = round((val_successivo_prod - val_corrente_prod) * k_factor, 3)
                        print(f"DEBUG:     [PROD] calcolato (prodotta)={calcolato}")
                        valore_campo_principale = calcolato if calcolato >= 0 else ""

                    # Prelevata (Campo kWh)
                    val_corrente_prel = float(lettura_corrente.totale_pos or 0)
                    val_successivo_prel = float(lettura_successiva.totale_pos or 0)
                    print(f"DEBUG:     [PROD] Prelevata: val_corrente_prel={val_corrente_prel}, val_successivo_prel={val_successivo_prel}, k={k_factor}")

                    if val_corrente_prel == 0 and val_successivo_prel == 0:
                        valore_campo_secondario = ""
                    else:
                        calcolato_prel = round((val_successivo_prel - val_corrente_prel) * k_factor, 3)
                        print(f"DEBUG:     [PROD] calcolato (prelevata)={calcolato_prel}")
                        valore_campo_secondario = calcolato_prel if calcolato_prel >= 0 else ""

                elif counter_obj.tipologia == "Scambio":
                    # Inversione logica per TRIFASCIO: 
                    # - Autoconsumata usa 2.8.0 se disponibile, altrimenti totale_pos
                    # - Immessa usa totale_neg
                    if tipologia_fascio == "trifascio":
                        if (getattr(lettura_corrente, 'totale_280n', None) is not None 
                            and getattr(lettura_successiva, 'totale_280n', None) is not None):
                            val_corrente_autocons = float(lettura_corrente.totale_280n or 0)
                            val_successivo_autocons = float(lettura_successiva.totale_280n or 0)
                            print(f"DEBUG:     [SCAMBIO] Autoconsumata (2.8.0 per TRIFASCIO): val_corrente_autocons={val_corrente_autocons}, val_successivo_autocons={val_successivo_autocons}, k={k_factor}")
                        else:
                            val_corrente_autocons = float(lettura_corrente.totale_pos or 0)
                            val_successivo_autocons = float(lettura_successiva.totale_pos or 0)
                            print(f"DEBUG:     [SCAMBIO] Autoconsumata (fallback totale_pos per TRIFASCIO): val_corrente_autocons={val_corrente_autocons}, val_successivo_autocons={val_successivo_autocons}, k={k_factor}")
                    elif tipologia_fascio == "monofascio":
                        val_corrente_autocons = float(lettura_corrente.totale_180n or 0)
                        val_successivo_autocons = float(lettura_successiva.totale_180n or 0)
                        print(f"DEBUG:     [SCAMBIO] Autoconsumata (MONOFASCIO): val_corrente_autocons={val_corrente_autocons}, val_successivo_autocons={val_successivo_autocons}, k={k_factor}")
                    else:
                        val_corrente_autocons = val_successivo_autocons = 0
                        print(f"DEBUG:     [SCAMBIO] Autoconsumata: tipologia_fascio non riconosciuta, valori a 0")

                    calcolato = round((val_successivo_autocons - val_corrente_autocons) * k_factor, 3)
                    print(f"DEBUG:     [SCAMBIO] calcolato (autocons)={calcolato}")
                    valore_campo_principale = calcolato if calcolato >= 0 else ""

                    # Immessa (Campo kWh)
                    if tipologia_fascio == "trifascio":
                        val_corrente_imm = float(lettura_corrente.totale_neg or 0)
                        val_successivo_imm = float(lettura_successiva.totale_neg or 0)
                        print(f"DEBUG:     [SCAMBIO] Immessa (totale_neg per TRIFASCIO): val_corrente_imm={val_corrente_imm}, val_successivo_imm={val_successivo_imm}, k={k_factor}")
                    else:
                        # Mantieni la logica esistente per altre tipologie
                        if (getattr(lettura_corrente, 'totale_280n', None) is not None 
                            and getattr(lettura_successiva, 'totale_280n', None) is not None):
                            val_corrente_imm = float(lettura_corrente.totale_280n or 0)
                            val_successivo_imm = float(lettura_successiva.totale_280n or 0)
                            print(f"DEBUG:     [SCAMBIO] Immessa (2.8.0): val_corrente_imm={val_corrente_imm}, val_successivo_imm={val_successivo_imm}, k={k_factor}")
                        else:
                            if tipologia_fascio == "monofascio":
                                val_corrente_imm = float(lettura_corrente.totale_180n or 0)
                                val_successivo_imm = float(lettura_successiva.totale_180n or 0)
                            else:
                                val_corrente_imm = val_successivo_imm = 0
                            print(f"DEBUG:     [SCAMBIO] Immessa (fallback): val_corrente_imm={val_corrente_imm}, val_successivo_imm={val_successivo_imm}, k={k_factor}")

                    calcolato_imm = round((val_successivo_imm - val_corrente_imm) * k_factor, 3)
                    print(f"DEBUG:     [SCAMBIO] calcolato (immessa)={calcolato_imm}")
                    valore_campo_secondario = calcolato_imm if calcolato_imm >= 0 else ""

                elif counter_obj.tipologia == "Ausiliare":
                    val_corrente_aus = float(lettura_corrente.totale_pos or 0)
                    val_successivo_aus = float(lettura_successiva.totale_pos or 0)
                    print(f"DEBUG:     [AUSILIARE] val_corrente_aus={val_corrente_aus}, val_successivo_aus={val_successivo_aus}, k={k_factor}")
                    calcolato = round((val_successivo_aus - val_corrente_aus) * k_factor, 3)
                    print(f"DEBUG:     [AUSILIARE] calcolato={calcolato}")
                    valore_campo_principale = calcolato if calcolato >= 0 else ""

            except Exception as e:
                print(f"ERRORE nel calcolo dei dati del contatore {counter_obj.nome} (ID: {counter_obj.id}): {e}")
                valore_campo_principale = ""
                valore_campo_secondario = ""

        reg_segnante = regsegnanti.objects.filter(
            contatore=counter_obj,
            anno=current_year,
            mese=month
        ).first()
        print(f"DEBUG:   regsegnante trovato: {reg_segnante}")

        # Popola il dizionario dei dati con i valori calcolati e dai reg_segnanti
        data["campo"] = valore_campo_principale if valore_campo_principale != "" else ""
        if counter_obj.tipologia == "Produzione":
            data["ed"] = reg_segnante.prod_ed if reg_segnante else ""
            data["gse"] = reg_segnante.prod_gse if reg_segnante else ""
            data["campo_secondario"] = valore_campo_secondario if valore_campo_secondario != "" else ""
            data["ed_secondario"] = reg_segnante.prel_ed if reg_segnante else ""
           
        elif counter_obj.tipologia == "Scambio":
            data["ed"] = reg_segnante.autocons_ed if reg_segnante else ""
            data["gse"] = reg_segnante.autocons_gse if reg_segnante else ""
            data["campo_secondario"] = valore_campo_secondario if valore_campo_secondario != "" else ""
            data["ed_secondario"] = reg_segnante.imm_ed if reg_segnante else ""
            data["gse_secondario"] = reg_segnante.imm_gse if reg_segnante else ""
        elif counter_obj.tipologia == "Ausiliare":
            data["ed"] = reg_segnante.aus_ed if reg_segnante else ""
            data["gse"] = reg_segnante.aus_gse if reg_segnante else ""

        print(f"DEBUG:   Ritorno dati: {data}")
        return data

    for mese in range(1, 13):
        nome_mese = calendar.month_name[mese].capitalize()
        print(f"\n---- Calcolo dati mensili per mese {mese} [{nome_mese}] ----")
        riga = {
            "mese_numero": mese,
            "mese_nome": nome_mese,
        }

        # --- Dati Produzione (Contatore Attivo) ---
        prod_data_attivo = calculate_counter_data(contatore_produzione_attivo, anno_corrente, mese)
        riga["prod_campo"] = prod_data_attivo.get("campo")
        riga["prod_ed"] = prod_data_attivo.get("ed")
        riga["prod_gse"] = prod_data_attivo.get("gse")
        riga["prel_campo"] = prod_data_attivo.get("campo_secondario")
        riga["prel_ed"] = prod_data_attivo.get("ed_secondario")
        print(f"DEBUG:   prod_data_attivo: {prod_data_attivo}")

        # --- Dati Produzione (Contatore Sostituito) ---
        if has_sostituzione_produzione:
            prod_data_sostituito = calculate_counter_data(contatore_produzione_sostituito, anno_corrente, mese)
            riga["prod_campo_sostituito"] = prod_data_sostituito.get("campo")
            riga["prod_ed_sostituito"] = prod_data_sostituito.get("ed")
            riga["prod_gse_sostituito"] = prod_data_sostituito.get("gse")
            riga["prel_campo_sostituito"] = prod_data_sostituito.get("campo_secondario")
            riga["prel_ed_sostituito"] = prod_data_sostituito.get("ed_secondario")
            print(f"DEBUG:   prod_data_sostituito: {prod_data_sostituito}")
        else:
            riga["prod_campo_sostituito"] = riga["prod_ed_sostituito"] = riga["prod_gse_sostituito"] = ""
            riga["prel_campo_sostituito"] = riga["prel_ed_sostituito"] = riga["prel_gse_sostituito"] = ""

        # --- Dati Scambio (Contatore Attivo) ---
        scambio_data_attivo = calculate_counter_data(contatore_scambio_attivo, anno_corrente, mese)
        riga["autocons_campo"] = scambio_data_attivo.get("campo")
        riga["autocons_ed"] = scambio_data_attivo.get("ed")
        riga["autocons_gse"] = scambio_data_attivo.get("gse")
        riga["imm_campo"] = scambio_data_attivo.get("campo_secondario")
        riga["imm_ed"] = scambio_data_attivo.get("ed_secondario")
        riga["imm_gse"] = scambio_data_attivo.get("gse_secondario")
        print(f"DEBUG:   scambio_data_attivo: {scambio_data_attivo}")

        # --- Dati Scambio (Contatore Sostituito) ---
        if has_sostituzione_scambio:
            scambio_data_sostituito = calculate_counter_data(contatore_scambio_sostituito, anno_corrente, mese)
            riga["autocons_campo_sostituito"] = scambio_data_sostituito.get("campo")
            riga["autocons_ed_sostituito"] = scambio_data_sostituito.get("ed")
            riga["autocons_gse_sostituito"] = scambio_data_sostituito.get("gse")
            riga["imm_campo_sostituito"] = scambio_data_sostituito.get("campo_secondario")
            riga["imm_ed_sostituito"] = scambio_data_sostituito.get("ed_secondario")
            riga["imm_gse_sostituito"] = scambio_data_sostituito.get("gse_secondario")
            print(f"DEBUG:   scambio_data_sostituito: {scambio_data_sostituito}")
        else:
            riga["autocons_campo_sostituito"] = riga["autocons_ed_sostituito"] = riga["autocons_gse_sostituito"] = ""
            riga["imm_campo_sostituito"] = riga["imm_ed_sostituito"] = riga["imm_gse_sostituito"] = ""
        
        # --- Dati Ausiliare (Contatore Attivo) ---
        ausiliare_data_attivo = calculate_counter_data(contatore_ausiliare_attivo, anno_corrente, mese)
        riga["aus_campo"] = ausiliare_data_attivo.get("campo")
        riga["aus_ed"] = ausiliare_data_attivo.get("ed")
        riga["aus_gse"] = ausiliare_data_attivo.get("gse")
        print(f"DEBUG:   ausiliare_data_attivo: {ausiliare_data_attivo}")

        # --- Dati Ausiliare (Contatore Sostituito) ---
        if has_sostituzione_ausiliare:
            ausiliare_data_sostituito = calculate_counter_data(contatore_ausiliare_sostituito, anno_corrente, mese)
            riga["aus_campo_sostituito"] = ausiliare_data_sostituito.get("campo")
            riga["aus_ed_sostituito"] = ausiliare_data_sostituito.get("ed")
            riga["aus_gse_sostituito"] = ausiliare_data_sostituito.get("gse")
            print(f"DEBUG:   ausiliare_data_sostituito: {ausiliare_data_sostituito}")
        else:
            riga["aus_campo_sostituito"] = riga["aus_ed_sostituito"] = riga["aus_gse_sostituito"] = ""

        dati_mensili_template.append(riga)
        print(f"DEBUG: RIGA COMPLETA ({mese}): {riga}")

    print(f"\nDEBUG: Contenuto finale di dati_mensili_template (primi 5 elementi):")
    for idx, item in enumerate(dati_mensili_template[:5]):
        print(f"  {idx+1}: {item}")
    print(f"DEBUG: Lunghezza totale dati_mensili_template: {len(dati_mensili_template)}")

    # Passa i dati al template
    context = {
        'impianto': impianto, 
        'contatori': contatori,
        'contatore': contatore_selezionato,
        'anno_corrente': anno_corrente,
        'has_produzione': has_produzione,
        'has_scambio': has_scambio,
        'has_ausiliare': has_ausiliare,
        'has_sostituzione_produzione': has_sostituzione_produzione,
        'has_sostituzione_scambio': has_sostituzione_scambio,
        'has_sostituzione_ausiliare': has_sostituzione_ausiliare,
        'numero_gruppi_colonne': numero_gruppi_colonne,
        'dati_mensili_template': dati_mensili_template,
        'contatore_produzione_attivo': contatore_produzione_attivo,
        'contatore_produzione_sostituito': contatore_produzione_sostituito,
        'contatore_scambio_attivo': contatore_scambio_attivo,
        'contatore_scambio_sostituito': contatore_scambio_sostituito,
        'contatore_ausiliare_attivo': contatore_ausiliare_attivo,
        'contatore_ausiliare_sostituito': contatore_ausiliare_sostituito,
    }
    
    print("========================= FINE diarioenergie =========================\n")
    return render(request, 'diarioenergie.html', context)

@csrf_exempt
@require_POST
def salva_diario_energie(request):
    try:
        data = json.loads(request.body)
        contatore_id = data.get('contatore_id')
        anno = int(data.get('anno'))
        dati_mensili = data.get('dati_mensili')

        if not all([contatore_id, anno, dati_mensili]):
            return JsonResponse({'error': 'Dati mancanti.'}, status=400)

        # Recupera il contatore principale per ottenere il nickname dell'impianto associato
        # Questo contatore_id proviene dall'attributo data-contatore-id della tabella principale
        main_contatore = get_object_or_404(Contatore, id=contatore_id)
        impianto_nickname = main_contatore.impianto_nickname

        # Calcola le date di inizio e fine anno
        data_inizio_anno = datetime.date(anno, 1, 1)
        data_fine_anno = datetime.date(anno, 12, 31)

        # Recupera tutti i contatori pertinenti per questo impianto e anno
        all_counters_for_impianto = Contatore.objects.filter(
            impianto_nickname=impianto_nickname,
            data_installazione__lte=data_fine_anno
        ).filter(
            models.Q(data_dismissione__isnull=True) | models.Q(data_dismissione__gte=data_inizio_anno)
        ).order_by('data_installazione')

        # Mappa per memorizzare i contatori attivi e sostituiti per tipologia
        # Allineata alla logica della vista GET: 
        # - attivo = data_dismissione is null
        # - sostituito = ultimo contatore dismesso (data_dismissione non null) per tipologia
        counters_by_type_status = {}
        for tipologia in ["Produzione", "Scambio", "Ausiliare"]:
            # Contatore attivo per tipologia
            attivo = next((c for c in all_counters_for_impianto if c.tipologia == tipologia and c.data_dismissione is None), None)
            if attivo:
                counters_by_type_status[f"{tipologia}_attivo"] = attivo

            # Ultimo contatore dismesso per tipologia (se presente nell'intervallo considerato)
            dismessi = [c for c in all_counters_for_impianto if c.tipologia == tipologia and c.data_dismissione is not None]
            if dismessi:
                dismessi.sort(key=lambda x: x.data_dismissione, reverse=True)
                counters_by_type_status[f"{tipologia}_sostituito"] = dismessi[0]

        # Debug: riepilogo mappatura contatori attivi/sostituiti
        try:
            print("DEBUG salva_diario_energie - counters_by_type_status:")
            for k, v in counters_by_type_status.items():
                print(f"  {k}: ID={v.id}, Nome={v.nome}, Dismissione={v.data_dismissione}")
        except Exception:
            pass

        # Definisci la mappatura dai nomi dei campi del frontend ai nomi dei campi del modello e all'oggetto contatore di destinazione
        field_mapping = {
            # Produzione Attivo
            "prod_campo": ("prod_campo", counters_by_type_status.get("Produzione_attivo")),
            "prod_ed": ("prod_ed", counters_by_type_status.get("Produzione_attivo")),
            "prod_gse": ("prod_gse", counters_by_type_status.get("Produzione_attivo")),
            "prel_campo": ("prel_campo", counters_by_type_status.get("Produzione_attivo")),
            "prel_ed": ("prel_ed", counters_by_type_status.get("Produzione_attivo")),
            

            # Produzione Sostituito
            "prod_campo_sostituito": ("prod_campo", counters_by_type_status.get("Produzione_sostituito")),
            "prod_ed_sostituito": ("prod_ed", counters_by_type_status.get("Produzione_sostituito")),
            "prod_gse_sostituito": ("prod_gse", counters_by_type_status.get("Produzione_sostituito")),
            "prel_campo_sostituito": ("prel_campo", counters_by_type_status.get("Produzione_sostituito")),
            "prel_ed_sostituito": ("prel_ed", counters_by_type_status.get("Produzione_sostituito")),
           

            # Scambio Attivo
            "autocons_campo": ("autocons_campo", counters_by_type_status.get("Scambio_attivo")),
            "autocons_ed": ("autocons_ed", counters_by_type_status.get("Scambio_attivo")),
            "autocons_gse": ("autocons_gse", counters_by_type_status.get("Scambio_attivo")),
            "imm_campo": ("imm_campo", counters_by_type_status.get("Scambio_attivo")),
            "imm_ed": ("imm_ed", counters_by_type_status.get("Scambio_attivo")),
            "imm_gse": ("imm_gse", counters_by_type_status.get("Scambio_attivo")),

            # Scambio Sostituito
            "autocons_campo_sostituito": ("autocons_campo", counters_by_type_status.get("Scambio_sostituito")),
            "autocons_ed_sostituito": ("autocons_ed", counters_by_type_status.get("Scambio_sostituito")),
            "autocons_gse_sostituito": ("autocons_gse", counters_by_type_status.get("Scambio_sostituito")),
            "imm_campo_sostituito": ("imm_campo", counters_by_type_status.get("Scambio_sostituito")),
            "imm_ed_sostituito": ("imm_ed", counters_by_type_status.get("Scambio_sostituito")),
            "imm_gse_sostituito": ("imm_gse", counters_by_type_status.get("Scambio_sostituito")),

            # Ausiliare Attivo
            "aus_campo": ("aus_campo", counters_by_type_status.get("Ausiliare_attivo")),
            "aus_ed": ("aus_ed", counters_by_type_status.get("Ausiliare_attivo")),
            "aus_gse": ("aus_gse", counters_by_type_status.get("Ausiliare_attivo")),

            # Ausiliare Sostituito
            "aus_campo_sostituito": ("aus_campo", counters_by_type_status.get("Ausiliare_sostituito")),
            "aus_ed_sostituito": ("aus_ed", counters_by_type_status.get("Ausiliare_sostituito")),
            "aus_gse_sostituito": ("aus_gse", counters_by_type_status.get("Ausiliare_sostituito")),
        }

        for mese_data in dati_mensili:
            mese_numero = int(mese_data.get('mese_numero'))
            if not mese_numero:
                continue

            # Dizionario per raccogliere gli oggetti regsegnanti da salvare per il mese corrente, indicizzati per counter_id
            regsegnanti_to_save_this_month = {}

            for field_name, value in mese_data.items():
                if field_name == 'mese_numero':
                    continue

                model_field_name, target_counter = field_mapping.get(field_name, (None, None))

                if not target_counter:
                    # Log utile se il campo fa riferimento ad un contatore sostituito ma non presente
                    if field_name.endswith('_sostituito'):
                        print(f"DEBUG salva_diario_energie - Nessun contatore sostituito trovato per campo '{field_name}' nel {anno}.")
                    continue # Nessun contatore valido trovato per questo campo in base ai contatori attivi/sostituiti correnti

                # Ottieni o crea l'oggetto regsegnanti per questo contatore specifico, anno, mese
                # Se lo abbiamo già recuperato per questo mese, usa quello esistente
                if target_counter.id not in regsegnanti_to_save_this_month:
                    reg_segnante_obj, created = regsegnanti.objects.get_or_create(
                        contatore=target_counter,
                        anno=anno,
                        mese=mese_numero
                    )
                    regsegnanti_to_save_this_month[target_counter.id] = reg_segnante_obj
                else:
                    reg_segnante_obj = regsegnanti_to_save_this_month[target_counter.id]

                                # Converti il valore in Decimal. Salva i valori maggiori o uguali a 0.
                if value is not None and value != '':
                    try:
                        decimal_value = Decimal(str(value))
                        # Salva se il valore è maggiore o uguale a 0 (include anche lo 0)
                        if decimal_value >= 0:
                            setattr(reg_segnante_obj, model_field_name, decimal_value)
                        else:
                            # Se il valore è negativo, imposta a None (non salvare)
                            setattr(reg_segnante_obj, model_field_name, None)
                    except (ValueError, InvalidOperation):
                        # Se la conversione fallisce, imposta a None
                        setattr(reg_segnante_obj, model_field_name, None)
                else:
                    # Se il valore è None o stringa vuota, imposta a None
                    setattr(reg_segnante_obj, model_field_name, None)

            # Salva tutti gli oggetti regsegnanti raccolti per il mese corrente
            for obj in regsegnanti_to_save_this_month.values():
                obj.save()

        # Dopo il salvataggio con successo, crea una copia di backup del database
        try:
            # Percorso del database corrente (nella root del progetto)
            current_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db.sqlite3')
            
            # Directory di destinazione per il backup
            backup_directory = r'C:\Users\Sviluppo_Software_ZG\ownCloud\LettureImpianti'
            
            # Crea la directory di destinazione se non esiste
            os.makedirs(backup_directory, exist_ok=True)
            
            # Nome fisso del file di backup (sovrascrive sempre lo stesso file)
            backup_filename = 'db_backup.sqlite3'
            backup_path = os.path.join(backup_directory, backup_filename)
            
            # Copia il database (sovrascrive il file esistente se presente)
            shutil.copy2(current_db_path, backup_path)
            
            print(f"Backup del database aggiornato con successo: {backup_path}")
            
        except Exception as backup_error:
            # Se il backup fallisce, registra l'errore ma non bloccare la risposta di successo
            print(f"Errore durante la creazione del backup del database: {backup_error}")
            # Il salvataggio dei dati è comunque riuscito, quindi continuiamo con la risposta di successo

        return JsonResponse({'message': 'Dati salvati con successo!'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Richiesta non valida, il formato JSON è malformato.'}, status=400)
    except Contatore.DoesNotExist:
        return JsonResponse({'error': 'Contatore non trovato.'}, status=404)
    except InvalidOperation:
        return JsonResponse({'error': 'Dati numerici non validi (assicurati che i campi siano numeri validi).'}, status=400)
    except Exception as e:
        print(f"Errore durante il salvataggio dei dati: {e}") # Registra l'errore per il debug
        return JsonResponse({'error': f'Errore interno del server: {str(e)}'}, status=500)

