from django.shortcuts import render, get_object_or_404, redirect
from MonitoraggioImpianti.models import Impianto

from django.http import  JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import datetime
import calendar
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
    # Ottieni l'impianto
    impianto = get_object_or_404(Impianto, nickname=nickname)
    
    # Ottieni l'anno dalla query string, default all'anno corrente
    anno_corrente = request.GET.get('year', str(timezone.now().year))
    anno_corrente = int(anno_corrente)

    # Calcola le date di inizio e fine anno
    data_inizio_anno = datetime.date(anno_corrente, 1, 1)
    data_fine_anno = datetime.date(anno_corrente, 12, 31)

    # Filtra i contatori attivi per l'anno selezionato
    contatori = Contatore.objects.filter(
        impianto_nickname=nickname,
        data_installazione__lte=data_fine_anno
    ).filter(
        models.Q(data_dismissione__isnull=True) | models.Q(data_dismissione__gte=data_inizio_anno)
    )

    # Verifica se ci sono sostituzioni nell'anno corrente
    # Un contatore è stato sostituito se è stato dismesso nell'anno corrente
    contatori_dismessi_anno = contatori.filter(
        data_dismissione__year=anno_corrente
    )
    
    # Verifica se ci sono contatori installati nell'anno corrente (sostituzioni)
    contatori_installati_anno = contatori.filter(
        data_installazione__year=anno_corrente
    )

    # Determina se c'è una sostituzione per tipologia
    tipologie_sostituite = []
    
    for tipologia in ['Produzione', 'Scambio', 'Ausiliare']:
        # Conta quanti contatori di questa tipologia sono attivi nell'anno
        contatori_tipologia = contatori.filter(tipologia=tipologia)
        dismessi_tipologia = contatori_dismessi_anno.filter(tipologia=tipologia)
        installati_tipologia = contatori_installati_anno.filter(tipologia=tipologia)
        
        # Se abbiamo sia dismessi che installati della stessa tipologia, c'è una sostituzione
        if dismessi_tipologia.exists() and installati_tipologia.exists():
            tipologie_sostituite.append(tipologia)

    # Separa i contatori per tipologia (prendi il primo attivo)
    contatore_produzione = contatori.filter(tipologia="Produzione").first()
    contatore_scambio = contatori.filter(tipologia="Scambio").first()

    # Ottieni l'ID del contatore specifico dalla query string
    contatore_id = request.GET.get('contatore_id')
    
    # DEBUG: Stampa tutti i contatori disponibili
    print(f"DEBUG: Contatori disponibili per impianto {nickname}:")
    for cont in contatori:
        print(f"  - ID: {cont.id}, Nome: {cont.nome}, Tipologia: {cont.tipologia}")
    
    # DEBUG: Stampa il contatore_id dalla query string
    print(f"DEBUG: contatore_id dalla query string: {contatore_id}")
    
    # Se è specificato un contatore specifico, selezionalo
    if contatore_id:
        contatore_selezionato = get_object_or_404(Contatore, id=contatore_id, impianto_nickname=nickname)
        print(f"DEBUG: Contatore selezionato tramite ID: {contatore_selezionato.nome} ({contatore_selezionato.tipologia})")
    else:
        # Altrimenti prendi il primo contatore disponibile
        contatore_selezionato = contatori.first() if contatori.exists() else None
        print(f"DEBUG: Contatore selezionato automaticamente: {contatore_selezionato.nome if contatore_selezionato else 'Nessuno'} ({contatore_selezionato.tipologia if contatore_selezionato else 'N/A'})")
    
    # Determina quali tipi di contatori sono presenti nell'impianto
    tipologie_presenti = list(contatori.values_list('tipologia', flat=True).distinct())
    
    # Crea le variabili booleane per il template
    has_produzione = 'Produzione' in tipologie_presenti
    has_scambio = 'Scambio' in tipologie_presenti
    has_ausiliare = 'Ausiliare' in tipologie_presenti
    
    # NUOVE variabili per gestire le sostituzioni
    has_sostituzione_produzione = 'Produzione' in tipologie_sostituite
    has_sostituzione_scambio = 'Scambio' in tipologie_sostituite
    has_sostituzione_ausiliare = 'Ausiliare' in tipologie_sostituite
    
    # Conta quante colonne dovremo mostrare per regolare il layout
    numero_gruppi_colonne = 0
    if has_produzione:
        numero_gruppi_colonne += 2  # Prodotta + Prelevata
        if has_sostituzione_produzione:
            numero_gruppi_colonne += 2  # Prodotta + Prelevata del contatore sostituito
    if has_scambio:
        numero_gruppi_colonne += 2  # Autoconsumata + Immessa
        if has_sostituzione_scambio:
            numero_gruppi_colonne += 2  # Autoconsumata + Immessa del contatore sostituito
    if has_ausiliare:
        numero_gruppi_colonne += 1  # Solo Ausiliare
        if has_sostituzione_ausiliare:
            numero_gruppi_colonne += 1  # Ausiliare del contatore sostituito

    # Recupera il contatore selezionato per i calcoli
    contatore = contatore_selezionato

    # Prepara la lista dei dati mensili per il template
    dati_mensili_template = []

    for mese in range(1, 13):
        nome_mese = calendar.month_name[mese].capitalize()
        riga = {
            "mese_numero": mese,
            "mese_nome": nome_mese,
        }

        # --- Dati Produzione ---
        if contatore_produzione:
            # Recupera le letture
            letture_prod = LetturaContatore.objects.filter(
                contatore=contatore_produzione,
                anno__in=[anno_corrente, anno_corrente + 1]
            ).order_by('anno', 'mese')
            letture_dict_prod = {(l.anno, l.mese): l for l in letture_prod}
            lettura_corrente_prod = letture_dict_prod.get((anno_corrente, mese))
            if mese < 12:
                lettura_successiva_prod = letture_dict_prod.get((anno_corrente, mese + 1))
            else:
                lettura_successiva_prod = letture_dict_prod.get((anno_corrente + 1, 1))
            k_prod = contatore_produzione.k if contatore_produzione.k else 1
            tipologiafascio_prod = contatore_produzione.tipologiafascio.lower() if contatore_produzione.tipologiafascio else None
            valore_calcolato_prod = ""
            valore_calcolato_prel = ""
            if lettura_corrente_prod and lettura_successiva_prod:
                try:
                    if tipologiafascio_prod == "trifascio":
                        val_corrente = float(lettura_corrente_prod.totale_neg or 0)
                        val_successivo = float(lettura_successiva_prod.totale_neg or 0)
                    elif tipologiafascio_prod == "monofascio":
                        val_corrente = float(lettura_corrente_prod.totale_180n or 0)
                        val_successivo = float(lettura_successiva_prod.totale_180n or 0)
                    else:
                        val_corrente = val_successivo = 0
                    valore_calcolato_prod = round((val_successivo - val_corrente) * k_prod, 3)

                    val_corrente_pos = float(lettura_corrente_prod.totale_pos or 0)
                    val_successivo_pos = float(lettura_successiva_prod.totale_pos or 0)
                    valore_calcolato_prel = round((val_successivo_pos - val_corrente_pos) * k_prod, 3)
                except Exception:
                    valore_calcolato_prod = ""
                    valore_calcolato_prel = ""
            reg_segnante_prod = regsegnanti.objects.filter(
                contatore=contatore_produzione,
                anno=anno_corrente,
                mese=mese
            ).first()
            riga["prod_campo"] = valore_calcolato_prod if valore_calcolato_prod != "" else ""
            riga["prod_ed"] = reg_segnante_prod.prod_ed if reg_segnante_prod and reg_segnante_prod.prod_ed else ""
            riga["prod_gse"] = reg_segnante_prod.prod_gse if reg_segnante_prod and reg_segnante_prod.prod_gse else ""
            riga["prel_campo"] = valore_calcolato_prel if valore_calcolato_prel != "" else ""
            riga["prel_ed"] = reg_segnante_prod.prel_ed if reg_segnante_prod and reg_segnante_prod.prel_ed else ""
            riga["prel_gse"] = reg_segnante_prod.prel_gse if reg_segnante_prod and reg_segnante_prod.prel_gse else ""
            
            # Se c'è una sostituzione, gestisci anche il contatore dismesso
            if has_sostituzione_produzione:
                # Trova il contatore di produzione dismesso nell'anno corrente
                contatore_produzione_dismesso = contatori_dismessi_anno.filter(tipologia="Produzione").first()
                if contatore_produzione_dismesso:
                    # Calcola i dati per il contatore dismesso
                    # (stessa logica del contatore principale, ma usando contatore_produzione_dismesso)
                    # Salva i risultati in campi come prod_campo_sostituito, prod_ed_sostituito, ecc.
                    pass
        else:
            riga["prod_campo"] = riga["prod_ed"] = riga["prod_gse"] = ""
            riga["prel_campo"] = riga["prel_ed"] = riga["prel_gse"] = ""

        # --- Dati Scambio ---
        if contatore_scambio:
            letture_scambio = LetturaContatore.objects.filter(
                contatore=contatore_scambio,
                anno__in=[anno_corrente, anno_corrente + 1]
            ).order_by('anno', 'mese')
            letture_dict_scambio = {(l.anno, l.mese): l for l in letture_scambio}
            lettura_corrente_scambio = letture_dict_scambio.get((anno_corrente, mese))
            if mese < 12:
                lettura_successiva_scambio = letture_dict_scambio.get((anno_corrente, mese + 1))
            else:
                lettura_successiva_scambio = letture_dict_scambio.get((anno_corrente + 1, 1))
            k_scambio = contatore_scambio.k if contatore_scambio.k else 1
            valore_calcolato_scambio = ""
            valore_calcolato_imm = ""
            if lettura_corrente_scambio and lettura_successiva_scambio:
                try:
                    val_corrente_autoconsumo = float(lettura_corrente_scambio.totale_neg or 0)
                    val_successivo_autoconsumo = float(lettura_successiva_scambio.totale_neg or 0)
                    # MODIFICA: Ora usiamo sempre totale_180n per il calcolo dell'autoconsumo "Campo kWh",
                    # come richiesto, indipendentemente dalla tipologia fascio.
                    val_corrente_autoconsumo = float(lettura_corrente_scambio.totale_180n or 0)
                    val_successivo_autoconsumo = float(lettura_successiva_scambio.totale_180n or 0)
                    
                    valore_calcolato_scambio = round((val_successivo_autoconsumo - val_corrente_autoconsumo) * k_scambio, 3)

                    # MODIFICA: Ora usiamo totale_280n per il calcolo dell'immessa "Campo kWh",
                    val_corrente_pos = float(lettura_corrente_scambio.totale_pos or 0)
                    val_successivo_pos = float(lettura_successiva_scambio.totale_pos or 0)
                    valore_calcolato_imm = round((val_successivo_pos - val_corrente_pos) * k_scambio, 3)
                    # come richiesto.
                    val_corrente_pos = float(lettura_corrente_scambio.totale_280n or 0)
                    val_successivo_pos = float(lettura_successiva_scambio.totale_280n or 0)
                    valore_calcolato_imm = round((val_successivo_pos - val_corrente_pos) * k_scambio, 3)
                    # come richiesto.
                    val_corrente_imm = float(lettura_corrente_scambio.totale_280n or 0)
                    val_successivo_imm = float(lettura_successiva_scambio.totale_280n or 0)
                    valore_calcolato_imm = round((val_successivo_imm - val_corrente_imm) * k_scambio, 3)
                except Exception:
                    valore_calcolato_scambio = ""
                    valore_calcolato_imm = ""
            reg_segnante_scambio = regsegnanti.objects.filter(
                contatore=contatore_scambio,
                anno=anno_corrente,
                mese=mese
            ).first()
            riga["autocons_campo"] = valore_calcolato_scambio if valore_calcolato_scambio != "" else ""
            riga["autocons_ed"] = reg_segnante_scambio.autocons_ed if reg_segnante_scambio and reg_segnante_scambio.autocons_ed else ""
            riga["autocons_gse"] = reg_segnante_scambio.autocons_gse if reg_segnante_scambio and reg_segnante_scambio.autocons_gse else ""
            riga["imm_campo"] = valore_calcolato_imm if valore_calcolato_imm != "" else ""
            riga["imm_ed"] = reg_segnante_scambio.imm_ed if reg_segnante_scambio and reg_segnante_scambio.imm_ed else ""
            riga["imm_gse"] = reg_segnante_scambio.imm_gse if reg_segnante_scambio and reg_segnante_scambio.imm_gse else ""
            
            # Se c'è una sostituzione, gestisci anche il contatore dismesso
            if has_sostituzione_scambio:
                # Trova il contatore di scambio dismesso nell'anno corrente
                contatore_scambio_dismesso = contatori_dismessi_anno.filter(tipologia="Scambio").first()
                if contatore_scambio_dismesso:
                    # Calcola i dati per il contatore dismesso
                    # (stessa logica del contatore principale, ma usando contatore_scambio_dismesso)
                    # Salva i risultati in campi come autocons_campo_sostituito, autocons_ed_sostituito, ecc.
                    pass
        else:
            riga["autocons_campo"] = riga["autocons_ed"] = riga["autocons_gse"] = ""
            riga["imm_campo"] = riga["imm_ed"] = riga["imm_gse"] = ""

        dati_mensili_template.append(riga)

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
    }
    
    return render(request, 'diarioenergie.html', context)
   

