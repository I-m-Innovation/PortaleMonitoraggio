from django.shortcuts import render, get_object_or_404, redirect
from MonitoraggioImpianti.models import Impianto

from django.http import  JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import datetime
from .models import Impianto, Contatore, LetturaContatore, regsegnanti
from MonitoraggioImpianti.models import Impianto as MonitoraggioImpianto
from django.contrib import messages
from django.urls.exceptions import NoReverseMatch
import re
from django.utils.dateparse import parse_datetime
from django.db import models




def home(request):
    from MonitoraggioImpianti.models import Impianto 
    # Filtriamo solo gli impianti con tipo "Idroelettrico"
    impianti = Impianto.objects.filter(tipo='Idroelettrico')
    return render(request, 'home.html', {'impianti': impianti})




def diarioenergie(request, nickname):
    impianto = get_object_or_404(Impianto, nickname=nickname)
    
    try:
        # Ottieni l'anno corrente dalla query string o usa quello attuale
        anno_corrente = request.GET.get('anno', str(datetime.date.today().year))
        
        # Recupera tutti i contatori associati all'impianto
        # ma esclude i contatori dismessi quando l'anno selezionato è successivo all'anno di dismissione
        contatori = Contatore.objects.filter(impianto_nickname=nickname).filter(
            # Condizione: O non ha data_dismissione, OPPURE anno corrente <= anno dismissione 
            models.Q(data_dismissione__isnull=True) | 
            models.Q(data_dismissione__year__gte=int(anno_corrente))
        )
        
        if contatori.exists():
            # Dizionario per memorizzare i dati per ciascun contatore
            dati_contatori = {}
            
            # Dizionario per memorizzare i totali mensili per i contatori Gesis (Produzione)
            mesi_totali = {mese: Decimal('0.0') for mese in range(1, 13)}
            
            # Loop per ogni contatore
            for contatore in contatori:
                contatore_key = contatore.id
                
                # Recupera le letture già esistenti di tipo "diarioenergie" per questo contatore
                letture_reg = LetturaContatore.objects.filter(
                    contatore=contatore,
                    anno=anno_corrente,
                    tipo_tabella='diarioenergie'
                ).order_by('mese')
                letture_reg_per_mese = {lettura.mese: lettura for lettura in letture_reg}
                
                # MODIFICA: Recupera anche i dati da regsegnanti
                regsegnanti_records = regsegnanti.objects.filter(
                    contatore=contatore,
                    anno=anno_corrente
                ).order_by('mese')
                regsegnanti_per_mese = {record.mese: record for record in regsegnanti_records}
                
                # Dizionario per memorizzare i dati per ogni mese per il contatore corrente
                dati_per_mese = {}
                
                for mese in range(1, 13):
                    lettura_reg = letture_reg_per_mese.get(mese)
                    if lettura_reg is None:
                        lettura_reg = LetturaContatore(
                            contatore=contatore,
                            anno=anno_corrente,
                            mese=mese,
                            tipo_tabella='diarioenergie'
                        )
                    
                    # MODIFICA: Recupera il record regsegnanti per questo mese
                    regsegnante = regsegnanti_per_mese.get(mese)
                    
                    # Calcolo per contatori Gesis di tipo Produzione: utilizzare totale_neg
                    if contatore.marca == 'Gesis' and contatore.tipologia == 'Produzione':
                        # Calcolo per mesi da 1 a 11 (differenza con mese successivo dello stesso anno)
                        if mese < 12:
                            libro_corrente = LetturaContatore.objects.filter(
                                contatore=contatore,
                                anno=anno_corrente,
                                mese=mese,
                                tipo_tabella='libro_energie'
                            ).first()
                            libro_successivo = LetturaContatore.objects.filter(
                                contatore=contatore,
                                anno=anno_corrente,
                                mese=mese + 1,
                                tipo_tabella='libro_energie'
                            ).first()
                            
                            # Se entrambi i dati sono presenti e contengono un valore per totale_neg
                            if (libro_corrente and libro_successivo and 
                                libro_corrente.totale_neg is not None and 
                                libro_successivo.totale_neg is not None):
                                k_decimal = Decimal(contatore.k)
                                prod_valore = (libro_successivo.totale_neg - libro_corrente.totale_neg) * k_decimal
                                lettura_reg.prod_campo = prod_valore
                                mesi_totali[mese] += prod_valore
                                print(f"Mese {mese} ({anno_corrente}): Calcolato prod_campo = {prod_valore} dalla differenza: {libro_successivo.totale_neg} - {libro_corrente.totale_neg} * {k_decimal}")
                            else:
                                print(f"Mese {mese} ({anno_corrente}): Dati insufficienti per calcolare prod_campo")
                        # Calcolo per il mese 12 (differenza con Gennaio dell'anno successivo)
                        elif mese == 12:
                            anno_successivo = int(anno_corrente) + 1
                            libro_corrente = LetturaContatore.objects.filter(
                                contatore=contatore,
                                anno=anno_corrente,
                                mese=mese,
                                tipo_tabella='libro_energie'
                            ).first()
                            libro_successivo = LetturaContatore.objects.filter(
                                contatore=contatore,
                                anno=str(anno_successivo), # Passa l'anno successivo come stringa
                                mese=1,
                                tipo_tabella='libro_energie'
                            ).first()
                            
                            # Se entrambi i dati sono presenti e contengono un valore per totale_neg
                            if (libro_corrente and libro_successivo and
                                libro_corrente.totale_neg is not None and
                                libro_successivo.totale_neg is not None):
                                k_decimal = Decimal(contatore.k)
                                prod_valore = (libro_successivo.totale_neg - libro_corrente.totale_neg) * k_decimal
                                lettura_reg.prod_campo = prod_valore
                                mesi_totali[mese] += prod_valore
                                print(f"Mese {mese} ({anno_corrente}): Calcolato prod_campo = {prod_valore} dalla differenza con Gennaio {anno_successivo}: {libro_successivo.totale_neg} - {libro_corrente.totale_neg} * {k_decimal}")
                            else:
                                print(f"Mese {mese} ({anno_corrente}): Dati insufficienti per calcolare prod_campo (richiesto Gennaio {anno_successivo})")
                    
                    # Calcolo per contatori Kaifa di tipo Scambio: utilizzare totale_pos
                    elif contatore.marca == 'Kaifa' and contatore.tipologia == 'Scambio':
                        # Calcolo per mesi da 1 a 11 (differenza con mese successivo dello stesso anno)
                        if mese < 12:
                            libro_corrente = LetturaContatore.objects.filter(
                                contatore=contatore,
                                anno=anno_corrente,
                                mese=mese,
                                tipo_tabella='libro_energie'
                            ).first()
                            libro_successivo = LetturaContatore.objects.filter(
                                contatore=contatore,
                                anno=anno_corrente,
                                mese=mese + 1,
                                tipo_tabella='libro_energie'
                            ).first()
                            
                            # Se entrambi i valori per totale_pos sono presenti
                            if (libro_corrente and libro_successivo and 
                                libro_corrente.totale_pos is not None and 
                                libro_successivo.totale_pos is not None):
                                k_decimal = Decimal(contatore.k)
                                autocons_valore = (libro_successivo.totale_pos - libro_corrente.totale_pos) * k_decimal
                                lettura_reg.autocons_campo = autocons_valore
                                print(f"Mese {mese} ({anno_corrente}): Calcolato autocons_campo = {autocons_valore} dalla differenza: {libro_successivo.totale_pos} - {libro_corrente.totale_pos} * {k_decimal}")
                            else:
                                print(f"Mese {mese} ({anno_corrente}): Dati insufficienti per calcolare autocons_campo")
                        # Calcolo per il mese 12 (differenza con Gennaio dell'anno successivo)
                        elif mese == 12:
                            anno_successivo = int(anno_corrente) + 1
                            libro_corrente = LetturaContatore.objects.filter(
                                contatore=contatore,
                                anno=anno_corrente,
                                mese=mese,
                                tipo_tabella='libro_energie'
                            ).first()
                            libro_successivo = LetturaContatore.objects.filter(
                                contatore=contatore,
                                anno=str(anno_successivo), # Passa l'anno successivo come stringa
                                mese=1,
                                tipo_tabella='libro_energie'
                            ).first()
                            
                            # Se entrambi i valori per totale_pos sono presenti
                            if (libro_corrente and libro_successivo and
                                libro_corrente.totale_pos is not None and
                                libro_successivo.totale_pos is not None):
                                k_decimal = Decimal(contatore.k)
                                autocons_valore = (libro_successivo.totale_pos - libro_corrente.totale_pos) * k_decimal
                                lettura_reg.autocons_campo = autocons_valore
                                print(f"Mese {mese} ({anno_corrente}): Calcolato autocons_campo = {autocons_valore} dalla differenza con Gennaio {anno_successivo}: {libro_successivo.totale_pos} - {libro_corrente.totale_pos} * {k_decimal}")
                            else:
                                print(f"Mese {mese} ({anno_corrente}): Dati insufficienti per calcolare autocons_campo (richiesto Gennaio {anno_successivo})")
                    
                    # MODIFICA: Se esiste un record regsegnanti, prioritizza i suoi valori
                    if regsegnante:
                        # Aggiorna i valori di prod_campo, prod_ed, prod_gse, ecc. con quelli da regsegnanti
                        # se esistono nel record regsegnante
                        campi = ['prod_campo', 'prod_ed', 'prod_gse', 
                                'prel_campo', 'prel_ed', 'prel_gse',
                                'autocons_campo', 'autocons_ed', 'autocons_gse',
                                'imm_campo', 'imm_ed', 'imm_gse']
                        
                        for campo in campi:
                            valore_regsegnante = getattr(regsegnante, campo, None)
                            if valore_regsegnante is not None:
                                setattr(lettura_reg, campo, valore_regsegnante)
                    
                    # Salva ed assegna il record della lettura per il mese
                    dati_per_mese[mese] = lettura_reg
                    if lettura_reg.id is None:
                        lettura_reg.save()
                
                # Memorizza i dati processati per il contatore corrente
                dati_contatori[contatore_key] = {
                    'contatore': contatore,
                    'dati_per_mese': dati_per_mese
                }
            
            # Assicurati che il contatore attivo sia disponibile nel contesto
            contatore_attivo = contatori.first()  # O seleziona un contatore specifico in base alla logica necessaria
            
            # Prepara il contesto per il template
            context = {
                'impianto': impianto,
                'contatori': contatori,
                'contatore': contatore_attivo,  # Aggiungi il contatore attivo al contesto
                'dati_contatori': dati_contatori,
                'num_rows': range(12),
                'anno_corrente': anno_corrente,
                'mesi_totali': mesi_totali
            }
            
            return render(request, 'diarioenergie.html', context)
        else:
            # Se non ci sono contatori, reindirizza alla pagina di creazione
            return redirect('nuovo-contatore', nickname=nickname)
    except Exception as e:
        return render(request, 'diarioenergie.html', {'impianto': impianto, 'errore': str(e)})

def nuovo_contatore(request, nickname):
    # Recupera l'oggetto Impianto in base al nickname
    impianto = get_object_or_404(Impianto, nickname=nickname)
    return render(request, 'nuovo_contatore.html', {'impianto': impianto})



@csrf_exempt
def salva_contatore(request):
    if request.method == 'POST':
        # Recupera i dati dal form
        nome = request.POST.get('nome')
        pod = request.POST.get('pod')
        tipologia = request.POST.get('tipologia')
        k = request.POST.get('k')
        marca = request.POST.get('marca')
        modello = request.POST.get('modello')
        data_installazione = request.POST.get('data_installazione')
        impianto_id = request.POST.get('impianto_id')
        
        # Usa il modello corretto per Impianto
  
        
        # Recupera l'impianto originale da MonitoraggioImpianti
        impianto_monitoraggio = get_object_or_404(Impianto, id=impianto_id)
        
        # Crea un nuovo contatore usando i dati dell'impianto
        from AutomazioneDati.models import Contatore
        contatore = Contatore(
            impianto_nickname=impianto_monitoraggio.nickname,
            nome=nome,
            pod=pod,
            tipologia=tipologia,
            k=k,
            marca=marca,
            modello=modello,
            data_installazione=data_installazione
        )
        contatore.save()
        
        # Reindirizza alla pagina di panoramica contatore invece che a diari-letture
        return redirect('panoramica-contatore', nickname=impianto_monitoraggio.nickname)
    
    # Se la richiesta non è POST, reindirizza alla home
    return redirect('automazione-dati')

def diari_letture(request, nickname):
    impianto = get_object_or_404(Impianto, nickname=nickname)
    contatore_id = request.GET.get('contatore_id')
    contatore = get_object_or_404(Contatore, id=contatore_id, impianto_nickname=nickname)
    anno_selezionato_str = request.GET.get('anno', str(datetime.date.today().year))

    try:
        anno_selezionato = int(anno_selezionato_str)
        anno_successivo = anno_selezionato + 1

        # Recupera le letture Energie per l'anno selezionato e Gennaio dell'anno successivo
        letture_libro_energie_qs = LetturaContatore.objects.filter(
            contatore=contatore,
            tipo_tabella='libro_energie',
            anno__in=[anno_selezionato, anno_successivo] # Filtra per entrambi gli anni
        ).order_by('anno', 'mese')

        # Crea un dizionario per accesso rapido: chiave=(anno, mese)
        letture_energie_per_anno_mese = {}
        for l in letture_libro_energie_qs:
            letture_energie_per_anno_mese[(l.anno, l.mese)] = l

        # Recupera i dati da regsegnanti per l'anno selezionato
        regsegnanti_records = regsegnanti.objects.filter(
            contatore=contatore,
            anno=anno_selezionato
        ).order_by('mese')
        regsegnanti_per_mese = {record.mese: record for record in regsegnanti_records}

        # Prepara la lista di dati Energie per il template (13 elementi)
        libro_energie_dati = []
        for mese_indice in range(1, 14): # Itera da 1 a 13
            anno_corrente_loop = anno_selezionato
            mese_corrente_loop = mese_indice

            # Se l'indice è 13, rappresenta Gennaio dell'anno successivo
            if mese_indice == 13:
                anno_corrente_loop = anno_successivo
                mese_corrente_loop = 1 # Il mese è 1 (Gennaio)

            # Cerca la lettura nel dizionario
            lettura = letture_energie_per_anno_mese.get((anno_corrente_loop, mese_corrente_loop))

            # Cerca il record regsegnanti e determina prod_campo
            regsegnante = None
            if anno_corrente_loop == anno_selezionato: # Solo per i mesi dell'anno selezionato
                 regsegnante = regsegnanti_per_mese.get(mese_corrente_loop)

            prod_campo_valore = None
            if regsegnante and regsegnante.prod_campo is not None:
                # Priorità al valore salvato in regsegnanti
                prod_campo_valore = regsegnante.prod_campo
            elif mese_indice < 13 and contatore.marca == 'Gesis' and contatore.tipologia == 'Produzione':
                # Calcola il valore se non c'è in regsegnanti e se è un contatore Gesis Produzione
                # Cerca la lettura del mese successivo (solo se siamo nell'anno selezionato)
                lettura_successiva = letture_energie_per_anno_mese.get((anno_corrente_loop, mese_corrente_loop + 1))
                if lettura and lettura_successiva and lettura.totale_neg is not None and lettura_successiva.totale_neg is not None:
                     try:
                         k_decimal = Decimal(contatore.k)
                         prod_campo_valore = (lettura_successiva.totale_neg - lettura.totale_neg) * k_decimal
                     except (TypeError, ValueError, InvalidOperation):
                         prod_campo_valore = None # Errore nel calcolo

            # Aggiungi i dati alla lista, includendo il mese "logico" (1-13) per il template
            # e la data/ora formattata
            if lettura:
                 libro_energie_dati.append({
                    'mese': mese_indice, # Mese logico (1-13) per l'attributo data-mese nel template
                    'anno': anno_corrente_loop, # Anno effettivo
                    'mese_effettivo': mese_corrente_loop, # Mese effettivo (1-12)
                    'data_ora_lettura': lettura.data_ora_lettura,
                    'a1_neg': lettura.a1_neg,
                    'a2_neg': lettura.a2_neg,
                    'a3_neg': lettura.a3_neg,
                    'totale_neg': lettura.totale_neg,
                    'a1_pos': lettura.a1_pos,
                    'a2_pos': lettura.a2_pos,
                    'a3_pos': lettura.a3_pos,
                    'totale_pos': lettura.totale_pos,
                    'prod_campo': prod_campo_valore,
                })
            else:
                 # Se non c'è lettura per quel mese/anno, aggiungi un placeholder
                 # con i dati minimi necessari per il template
                 libro_energie_dati.append({
                    'mese': mese_indice,
                    'anno': anno_corrente_loop,
                    'mese_effettivo': mese_corrente_loop,
                    'data_ora_lettura': None,
                    'a1_neg': None, 'a2_neg': None, 'a3_neg': None, 'totale_neg': None,
                    'a1_pos': None, 'a2_pos': None, 'a3_pos': None, 'totale_pos': None,
                    'prod_campo': prod_campo_valore,
                 })

        # Recupera le letture Kaifa per l'anno selezionato e Gennaio dell'anno successivo
        letture_libro_kaifa_qs = LetturaContatore.objects.filter(
            contatore=contatore,
            tipo_tabella='libro_kaifa',
            anno__in=[anno_selezionato, anno_successivo] # Filtra per entrambi gli anni
        ).order_by('anno', 'mese')

        # Crea un dizionario per accesso rapido: chiave=(anno, mese)
        letture_kaifa_per_anno_mese = {(l.anno, l.mese): l for l in letture_libro_kaifa_qs}

        # Prepara la lista di dati Kaifa per il template (13 elementi)
        libro_kaifa_dati = []
        for mese_indice in range(1, 14): # Itera da 1 a 13
            anno_corrente_loop = anno_selezionato
            mese_corrente_loop = mese_indice

            # Se l'indice è 13, rappresenta Gennaio dell'anno successivo
            if mese_indice == 13:
                anno_corrente_loop = anno_successivo
                mese_corrente_loop = 1 # Il mese è 1 (Gennaio)

            # Cerca la lettura Kaifa nel dizionario
            lettura_kaifa = letture_kaifa_per_anno_mese.get((anno_corrente_loop, mese_corrente_loop))

            # Se non esiste una lettura per questo mese/anno, aggiungi None alla lista
            # Il template gestirà il caso in cui l'oggetto è None
            libro_kaifa_dati.append(lettura_kaifa)


        context = {
            'impianto': impianto,
            'contatore': contatore,
            'anno_corrente': anno_selezionato_str, # Passa l'anno come stringa
            'libro_energie_dati': libro_energie_dati, # Lista con 13 elementi (dizionari)
            'libro_kaifa_dati': libro_kaifa_dati, # Lista con 13 elementi (oggetti LetturaContatore o None)
            'num_rows': range(13), # Usato per iterare 13 volte nel template Kaifa
        }
        return render(request, 'reg_segnanti.html', context)

    except Exception as e:
        print(f"Errore in diari_letture: {e}")
        import traceback
        traceback.print_exc()
        
        # Usa un template esistente invece di error.html
        return render(request, 'base_layout.html', {
            'errore': 'Si è verificato un errore nel caricamento dei dati.',
            'dettaglio': str(e)
        })

@csrf_exempt
def salva_diarioenergie(request):
    # Debug
    print(f"Metodo richiesta: {request.method}")
    print(f"Content type: {request.content_type}")
    
    if request.method == 'POST':
        try:
            # Stampa il corpo della richiesta per debug
            print(f"Body della richiesta: {request.body.decode('utf-8')[:200]}...")
            
            # Decodifica i dati JSON dalla richiesta
            data = json.loads(request.body)
            
            # Debug dei dati ricevuti
            print(f"Contatore ID: {data.get('contatore_id')}")
            print(f"Anno: {data.get('anno')}")
            print(f"Tipo tabella: {data.get('tipo_tabella')}")
            print(f"Numero righe ricevute: {len(data.get('rows', []))}")
            
            # Estrai le informazioni principali
            contatore_id = data.get('contatore_id')
            anno = data.get('anno')
            rows = data.get('rows', [])
            
            # Ottieni il contatore dal database
            contatore = get_object_or_404(Contatore, id=contatore_id)
            
            # Contatore per verificare quante righe sono state salvate
            righe_salvate = 0
            errori = []
            
            # Debug: stampa tutti i campi delle prime righe per verifica
            for idx, row in enumerate(rows[:2]):  # Stampa solo le prime 2 righe per brevità
                print(f"DEBUG - Riga {idx+1}, mese {row.get('mese')}:")
                for key, value in row.items():
                    print(f"  {key}: {value}")
            
            # Elabora ogni riga di dati
            for row_data in rows:
                mese = row_data.get('mese')
                print(f"Elaborazione mese: {mese}")
                
                try:
                    # Cerca un record regsegnanti esistente o crea uno nuovo
                    reg_segnante_obj, created = regsegnanti.objects.get_or_create(
                        contatore=contatore,
                        anno=anno,
                        mese=mese,
                        defaults={}
                    )
                    
                    print(f"Record trovato: {not created}, mese: {mese}")
                    
                    # Aggiorna i campi con i dati ricevuti
                    modificato = False
                    
                    # Elenco di tutti i campi numerici del modello regsegnanti
                    campi_numerici = [
                        'prod_campo', 'prod_ed', 'prod_gse',
                        'prel_campo', 'prel_ed', 'prel_gse',
                        'autocons_campo', 'autocons_ed', 'autocons_gse',
                        'imm_campo', 'imm_ed', 'imm_gse'
                    ]
                    
                    for field_name in campi_numerici:
                        # Ottengo il valore dal payload JSON
                        field_value = row_data.get(field_name, None)
                        
                        # Debug
                        print(f"  Campo: {field_name}, Valore ricevuto: {field_value}")
                        
                        # Se il valore è presente, procedo con la conversione
                        if field_value is not None and field_value.strip():
                            try:
                                # Pulizia del valore: rimuovo spazi e sostituisco virgole con punti
                                cleaned_value = field_value.strip().replace(',', '.')
                                
                                # Se ci sono più punti decimali, mantieni solo il primo
                                if cleaned_value.count('.') > 1:
                                    parts = cleaned_value.split('.')
                                    cleaned_value = parts[0] + '.' + ''.join(parts[1:])
                                
                                # Verifica che sia un numero valido
                                if cleaned_value and cleaned_value != '.':
                                    # Converti in Decimal per precisione numerica
                                    decimal_value = Decimal(cleaned_value)
                                    # Arrotonda a 3 decimali
                                    decimal_value = decimal_value.quantize(Decimal('0.001'), rounding='ROUND_HALF_UP')
                                    
                                    # Confronto con il valore attuale
                                    valore_attuale = getattr(reg_segnante_obj, field_name)
                                    
                                    # Aggiorno solo se diverso 
                                    if valore_attuale != decimal_value:
                                        setattr(reg_segnante_obj, field_name, decimal_value)
                                        modificato = True
                                        print(f"    Modificato {field_name}: {valore_attuale} → {decimal_value}")
                                else:
                                    # Se è un valore vuoto o solo un punto
                                    setattr(reg_segnante_obj, field_name, None)
                                    modificato = True
                            except (InvalidOperation, ValueError) as e:
                                print(f"Errore nel convertire il valore '{field_value}' per {field_name}: {e}")
                                errori.append(f"Errore nel mese {mese}, campo {field_name}: {str(e)}")
                    
                    # Salva solo se sono state effettuate modifiche
                    if modificato:
                        reg_segnante_obj.save()
                        righe_salvate += 1
                        print(f"Salvato record per mese {mese}")
                    else:
                        print(f"Nessuna modifica per mese {mese}")
                
                except Exception as e:
                    import traceback
                    print(f"Errore nell'elaborazione della riga per mese {mese}: {e}")
                    print(traceback.format_exc())
                    errori.append(f"Errore generale nel mese {mese}: {str(e)}")
            
            # Restituisci una risposta JSON di successo
            if errori:
                return JsonResponse({
                    'status': 'partial_success',
                    'message': f'Salvate {righe_salvate} righe, con {len(errori)} errori',
                    'errors': errori
                })
            else:
                return JsonResponse({
                    'status': 'success',
                    'message': f'Salvate {righe_salvate} righe di dati',
                    'tipo_tabella': 'diarioenergie',
                    'anno': anno
                })
            
        except json.JSONDecodeError as e:
            # Errore di decodifica JSON
            print(f"Errore JSON: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Errore nella decodifica JSON: {str(e)}'
            }, status=400)
        except Exception as e:
            # Altri errori
            import traceback
            print(f"Errore generico: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    # Se la richiesta non è POST, restituisci un errore
    return JsonResponse({
        'status': 'error',
        'message': 'Metodo non consentito'
    }, status=405)

@csrf_exempt
def salva_dati_letture(request):
    # Debug
    print(f"Metodo richiesta: {request.method}")
    print(f"Content type: {request.content_type}")
    
    if request.method == 'POST':
        try:
            # Stampa il corpo della richiesta per debug
            print(f"Body della richiesta: {request.body.decode('utf-8')[:200]}...")
            
            # Decodifica i dati JSON dalla richiesta
            data = json.loads(request.body)
            
            # Debug dei dati ricevuti
            print(f"Dati ricevuti: {data}")
            
            # Estrai le informazioni principali
            tipo_tabella = data.get('tipo_tabella')
            rows = data.get('rows', [])
            
            # Verifica che ci siano righe da elaborare
            if not rows:
                return JsonResponse({'status': 'error', 'message': 'Nessun dato ricevuto'}, status=400)
            
            # Prendi il contatore_id e l'anno dalla prima riga
            contatore_id = rows[0].get('contatore_id')
            anno_principale = rows[0].get('anno') # Anno selezionato nel dropdown

            if not contatore_id or not anno_principale:
                return JsonResponse({'status': 'error', 'message': 'ID contatore o anno mancante'}, status=400)
            
            # Tenta di ottenere il contatore dal database in modo sicuro
            try:
                contatore = Contatore.objects.get(id=contatore_id)
            except Contatore.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': f'Contatore {contatore_id} non trovato'}, status=404)
            
            # Contatore per verificare quante righe sono state salvate
            righe_salvate = 0
            righe_con_errore_data = []
            
            # Elabora ogni riga di dati
            dati_risposta_righe = [] # Lista per contenere i dati aggiornati da restituire
            for row_data in rows:
                mese_logico = row_data.get('mese')
                anno_effettivo = int(anno_principale)
                mese_effettivo = int(mese_logico)
                if mese_logico == 13: # Gestione Gennaio anno successivo
                    anno_effettivo += 1
                    mese_effettivo = 1

                # Cerca una lettura esistente o crea una nuova istanza
                lettura, created = LetturaContatore.objects.get_or_create(
                    contatore=contatore,
                    anno=anno_effettivo,
                    mese=mese_effettivo,
                    tipo_tabella=tipo_tabella,
                    defaults={} # Importante avere defaults vuoto o appropriato
                )

                modificato = False
                errore_in_riga = False # Flag per errori specifici della riga
                dati_riga_aggiornati = {'mese': mese_logico} # Dati da restituire per questa riga

                for field_name, field_value in row_data.items():
                    # Salta i campi non pertinenti al modello o i totali calcolati
                    if field_name in ['contatore_id', 'anno', 'mese', 'tipo_tabella'] or not hasattr(lettura, field_name):
                        continue
                    
                    # IMPORTANTE: NON saltare i campi totale_neg, totale_pos, totale_180n, totale_280n
                    # Questi devono essere salvati anche nel database, non solo calcolati lato client

                    valore_attuale = getattr(lettura, field_name, None)

                    # --- Blocco specifico per data_presa (SOLO DATA) ---
                    if field_name == 'data_presa':
                        iso_date = None
                        try:
                            field_value_str = str(field_value).strip() if field_value is not None else ""
                            if field_value_str:
                                print(f"--- DEBUG [data_presa]: Mese {mese_logico}, Ricevuto: '{field_value_str}'")
                                
                                # Prendi solo la parte della data (ignora eventuale ora qui)
                                date_str = field_value_str.split(' ')[0]
                                
                                # Converti la data
                                iso_date = convert_date_format(date_str)
                                print(f"--- DEBUG [data_presa]: Mese {mese_logico}, Data convertita in: '{iso_date}'")
                                
                                # Confronta il valore attuale della data con quello nuovo
                                valore_attuale_str = valore_attuale.strftime('%Y-%m-%d') if isinstance(valore_attuale, datetime.date) else None
                                if valore_attuale_str != iso_date:
                                    setattr(lettura, field_name, iso_date)
                                    modificato = True
                                    print(f"--- DEBUG [data_presa]: Mese {mese_logico}, Modificato: {valore_attuale_str} -> {iso_date}")
                                
                                # Aggiungi al dizionario di risposta
                                dati_riga_aggiornati[field_name] = iso_date
                               
                            else:
                                # Se il valore ricevuto è vuoto, imposta a None
                                if getattr(lettura, field_name) is not None:
                                    setattr(lettura, field_name, None)
                                    modificato = True
                                    print(f"--- DEBUG [data_presa]: Mese {mese_logico}, Impostato a None (era vuoto)")
                                
                                dati_riga_aggiornati[field_name] = None
                        except ValueError as e:
                            # Errore durante la conversione della data
                            print(f"--- ERRORE [data_presa]: Mese {mese_logico}, Valore: '{field_value}', Errore: {e}")
                            errore_in_riga = True # Segna che c'è stato un errore in questa riga
                            righe_con_errore_data.append({'mese': mese_logico, 'valore': field_value, 'errore': str(e)})
                            # Non interrompere, ma questa riga non verrà salvata se modificato=True
                            dati_riga_aggiornati[field_name] = valore_attuale.strftime('%Y-%m-%d') if isinstance(valore_attuale, datetime.date) else None # Restituisci il valore vecchio in caso di errore

                    # --- NUOVO Blocco specifico per ora_lettura ---
                    elif field_name == 'ora_lettura':
                        ora_da_salvare = None
                        try:
                            field_value_str = str(field_value).strip() if field_value is not None else ""
                            print(f"--- DEBUG [ora_lettura]: Mese {mese_logico}, Ricevuto: '{field_value_str}'")
                            
                            if field_value_str and re.match(r'^\d{1,2}:\d{2}$', field_value_str): # Verifica formato HH:MM o H:MM
                                # Normalizza a HH:MM se necessario (Django TimeField lo accetta comunque)
                                parts = field_value_str.split(':')
                                ora_normalizzata = f"{parts[0].zfill(2)}:{parts[1]}"
                                ora_da_salvare = ora_normalizzata # Django gestirà la conversione a oggetto time
                                print(f"--- DEBUG [ora_lettura]: Mese {mese_logico}, Ora valida trovata: '{ora_da_salvare}'")
                            elif field_value_str:
                                # Formato non valido ricevuto
                                print(f"--- ATTENZIONE [ora_lettura]: Mese {mese_logico}, Formato ora non valido ricevuto: '{field_value_str}'")
                                # Non impostare errore_in_riga, ma non salvare l'ora
                                ora_da_salvare = None # Non salvare un formato errato
                            
                            # Confronta il valore attuale dell'ora con quello nuovo
                            ora_attuale_str = valore_attuale.strftime('%H:%M') if isinstance(valore_attuale, datetime.time) else None
                            
                            if ora_attuale_str != ora_da_salvare:
                                setattr(lettura, field_name, ora_da_salvare) # Passa la stringa HH:MM o None
                                modificato = True
                                print(f"--- DEBUG [ora_lettura]: Mese {mese_logico}, Modificato: {ora_attuale_str} -> {ora_da_salvare}")
                            
                            # Aggiungi al dizionario di risposta (anche se None)
                            dati_riga_aggiornati[field_name] = ora_da_salvare
                            
                        except Exception as e: # Cattura eccezioni generiche per sicurezza
                             print(f"--- ERRORE [ora_lettura]: Mese {mese_logico}, Valore: '{field_value}', Errore: {e}")
                             errore_in_riga = True # Segna errore se qualcosa va storto qui
                             dati_riga_aggiornati[field_name] = valore_attuale.strftime('%H:%M') if isinstance(valore_attuale, datetime.time) else None

                    # --- Blocco migliorato per campi numerici ---
                    elif field_name in ['a1_neg', 'a2_neg', 'a3_neg', 'a1_pos', 'a2_pos', 'a3_pos', 'totale_neg', 'totale_pos', 'kaifa_180n', 'kaifa_280n', 'totale_180n', 'totale_280n']:
                        # Controlla se il valore è fornito
                        if field_value is not None and field_value != '':
                            try:
                                # Normalizza il valore: rimuovi spazi e sostituisci virgole con punti
                                valore_pulito = str(field_value).strip().replace(' ', '').replace(',', '.')
                                
                                # Stampa di debug per vedere cosa arriva
                                print(f"--- DEBUG [{field_name}]: Mese {mese_logico}, Valore originale: '{field_value}', Pulito: '{valore_pulito}'")
                                
                                # Se ci sono più punti decimali, mantieni solo il primo
                                if valore_pulito.count('.') > 1:
                                    parti = valore_pulito.split('.')
                                    valore_pulito = parti[0] + '.' + ''.join(parti[1:])
                                    print(f"--- DEBUG [{field_name}]: Corretto punti multipli: '{valore_pulito}'")
                                
                                # Controlla che il valore sia effettivamente numerico
                                if valore_pulito and valore_pulito != '.':
                                    # Converti in Decimal per precisione
                                    valore_decimal = Decimal(valore_pulito)
                                    # Arrotonda a 3 decimali
                                    valore_arrotondato = valore_decimal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                                    
                                    # Controlla se il valore è cambiato rispetto a quello attuale
                                    # Usa quantize per fare un confronto coerente tra Decimal 
                                    valore_attuale_dec = Decimal('0') if valore_attuale is None else Decimal(str(valore_attuale)).quantize(Decimal('0.001'))
                                    
                                    print(f"--- DEBUG [{field_name}]: Mese {mese_logico}, Valore attuale: {valore_attuale_dec}, Nuovo: {valore_arrotondato}")
                                    
                                    if valore_attuale_dec != valore_arrotondato:
                                        setattr(lettura, field_name, valore_arrotondato)
                                        modificato = True
                                        print(f"--- DEBUG [{field_name}]: Modificato da {valore_attuale_dec} a {valore_arrotondato}")
                                else:
                                    # Se il valore non è valido, imposta a None
                                    if getattr(lettura, field_name) is not None:
                                        setattr(lettura, field_name, None)
                                        modificato = True
                                        print(f"--- DEBUG [{field_name}]: Mese {mese_logico}, Valore non valido impostato a None")
                                
                                # Aggiungi il valore al dizionario di risposta (come stringa formattata)
                                dati_riga_aggiornati[field_name] = float(valore_arrotondato) if valore_pulito and valore_pulito != '.' else None
                                
                            except (InvalidOperation, ValueError, TypeError) as e:
                                print(f"--- ERRORE conversione {field_name} con valore '{field_value}': {e}")
                                errore_in_riga = True
                                # Aggiungi il valore attuale al dizionario di risposta
                                dati_riga_aggiornati[field_name] = float(valore_attuale) if valore_attuale is not None else None
                        else:
                            # Se il valore è vuoto o None, imposta il campo a None
                            if getattr(lettura, field_name) is not None:
                                setattr(lettura, field_name, None)
                                modificato = True
                                print(f"--- DEBUG [{field_name}]: Mese {mese_logico}, Impostato a None (era vuoto)")
                            # Aggiungi None al dizionario di risposta
                            dati_riga_aggiornati[field_name] = None

                    # --- Blocco specifico per data_ora_lettura ---
                    elif field_name == 'data_ora_lettura':
                        datetime_iso = None
                        try:
                            field_value_str = str(field_value).strip() if field_value is not None else ""
                            if field_value_str:
                                print(f"--- DEBUG [data_ora_lettura]: Mese {mese_logico}, Ricevuto: '{field_value_str}'")
                                
                                # Converti la stringa ISO in oggetto datetime
                                datetime_iso = parse_datetime(field_value_str)
                                
                                if datetime_iso:
                                    print(f"--- DEBUG [data_ora_lettura]: Mese {mese_logico}, DateTime convertito in: '{datetime_iso}'")
                                    
                                    # Confronta il valore attuale con quello nuovo
                                    if valore_attuale != datetime_iso:
                                        setattr(lettura, field_name, datetime_iso)
                                        modificato = True
                                        print(f"--- DEBUG [data_ora_lettura]: Mese {mese_logico}, Modificato: {valore_attuale} -> {datetime_iso}")
                                    
                                    # Aggiungi al dizionario di risposta
                                    dati_riga_aggiornati[field_name] = datetime_iso.strftime('%Y-%m-%d %H:%M')
                                else:
                                    print(f"--- ERRORE [data_ora_lettura]: Mese {mese_logico}, Impossibile convertire '{field_value_str}'")
                                    errore_in_riga = True
                            else:
                                # Se il valore ricevuto è vuoto, imposta a None
                                if getattr(lettura, field_name) is not None:
                                    setattr(lettura, field_name, None)
                                    modificato = True
                                    print(f"--- DEBUG [data_ora_lettura]: Mese {mese_logico}, Impostato a None (era vuoto)")
                                
                                dati_riga_aggiornati[field_name] = None
                        
                        except Exception as e:
                            print(f"--- ERRORE [data_ora_lettura]: Mese {mese_logico}, Valore: '{field_value}', Errore: {e}")
                            errore_in_riga = True
                            righe_con_errore_data.append({'mese': mese_logico, 'valore': field_value, 'errore': str(e)})
                            # Restituisci il valore vecchio in caso di errore
                            dati_riga_aggiornati[field_name] = valore_attuale.strftime('%Y-%m-%d %H:%M') if isinstance(valore_attuale, datetime.datetime) else None

                # Salva solo se sono state effettuate modifiche E non ci sono stati errori critici nella riga
                if modificato and not errore_in_riga:
                    try:
                        lettura.save()
                        righe_salvate += 1
                        print(f"--- DEBUG: Riga Mese {mese_logico} salvata.")
                        dati_risposta_righe.append(dati_riga_aggiornati) # Aggiungi i dati salvati alla risposta
                    except Exception as e:
                         print(f"--- ERRORE SALVATAGGIO: Mese {mese_logico}, Errore: {e}")
                         # Gestisci errore di salvataggio (es. errore DB)
                         # Potresti voler restituire un errore 500 qui o gestire diversamente
                         # Per ora, aggiungiamo un messaggio di errore alla risposta parziale
                         righe_con_errore_data.append({'mese': mese_logico, 'valore': 'SALVATAGGIO', 'errore': str(e)})
                         # Aggiungi comunque i dati (vecchi o parzialmente aggiornati) che si tentava di salvare
                         dati_risposta_righe.append(dati_riga_aggiornati)
                elif errore_in_riga:
                     print(f"--- DEBUG: Riga Mese {mese_logico} non salvata causa errori.")
                     # Aggiungi i dati (con i valori vecchi dove c'è stato errore) alla risposta
                     dati_risposta_righe.append(dati_riga_aggiornati)
                elif not modificato:
                     print(f"--- DEBUG: Riga Mese {mese_logico} non modificata.")
                     # Aggiungi i dati non modificati alla risposta
                     dati_risposta_righe.append(dati_riga_aggiornati)
                    
            # --- Gestione Risposta Finale ---
            # Se ci sono stati errori (es. data non valida), restituisci un successo parziale
            if righe_con_errore_data:
                return JsonResponse({
                    'status': 'partial',
                    'message': f'Salvate {righe_salvate} righe, ma con {len(righe_con_errore_data)} errori',
                    'errors': righe_con_errore_data,
                    'rows': dati_risposta_righe
                })
            else:
                return JsonResponse({
                    'status': 'success',
                    'message': f'Salvate {righe_salvate} righe di dati',
                    'rows': dati_risposta_righe
                })
            
        except json.JSONDecodeError as e:
            # Errore di decodifica JSON
            print(f"Errore JSON: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Errore nella decodifica JSON: {str(e)}'
            }, status=400)
        except Exception as e:
            # Altri errori
            import traceback
            print(f"Errore generico: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    # Se la richiesta non è POST, restituisci un errore
    return JsonResponse({
        'status': 'error',
        'message': 'Metodo non consentito'
    }, status=405)

def debug_letture(request, contatore_id=None, anno=None):
    """Vista temporanea per debug delle letture"""
    if not contatore_id:
        contatore_id = request.GET.get('contatore_id')
    if not anno:
        anno = request.GET.get('anno', '2025')
    
    try:
        contatore = Contatore.objects.get(id=contatore_id)
        letture = LetturaContatore.objects.filter(contatore=contatore, anno=anno).order_by('tipo_tabella', 'mese')
        
        letture_data = []
        for l in letture:
            letture_data.append({
                'id': l.id,
                'tipo_tabella': l.tipo_tabella,
                'mese': l.mese,
                'data_presa': l.data_presa,
                'a1_neg': l.a1_neg,
                'a2_neg': l.a2_neg,
                'a3_neg': l.a3_neg,
                'totale_neg': l.totale_neg,
                'a1_pos': l.a1_pos,
                'a2_pos': l.a2_pos,
                'a3_pos': l.a3_pos,
                'totale_pos': l.totale_pos,
            })
        
        return JsonResponse({
            'contatore': {
                'id': contatore.id,
                'nome': contatore.nome,
                'pod': contatore.pod
            },
            'letture': letture_data
        })
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)

def convert_date_format(date_str):
    """
    Converte una stringa di data in vari formati al formato ISO (YYYY-MM-DD).
    Accetta formati come DD/MM/YYYY, YYYY-MM-DD o altri formati comuni.
    
    Args:
        date_str (str): La stringa di data da convertire
        
    Returns:
        str: La data in formato ISO (YYYY-MM-DD) o None se la conversione fallisce
    """
    date_str = date_str.strip()
    
    # Prova con il formato DD/MM/YYYY
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                # Assicurati che giorno, mese e anno siano numeri validi
                day = int(day)
                month = int(month)
                year = int(year)
                # Controlla che i valori siano in intervalli validi
                if 1 <= day <= 31 and 1 <= month <= 12 and 1000 <= year <= 9999:
                    # Formatta come YYYY-MM-DD
                    return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        pass
        
    # Prova con il formato YYYY-MM-DD (già ISO)
    try:
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                year, month, day = parts
                # Assicurati che giorno, mese e anno siano numeri validi
                day = int(day)
                month = int(month)
                year = int(year)
                # Controlla che i valori siano in intervalli validi
                if 1 <= day <= 31 and 1 <= month <= 12 and 1000 <= year <= 9999:
                    # Formatta come YYYY-MM-DD
                    return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        pass
        
    # Prova con il formato DD-MM-YYYY
    try:
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                day, month, year = parts
                # Assicurati che giorno, mese e anno siano numeri validi
                day = int(day)
                month = int(month)
                year = int(year)
                # Controlla che i valori siano in intervalli validi
                if 1 <= day <= 31 and 1 <= month <= 12 and 1000 <= year <= 9999:
                    # Formatta come YYYY-MM-DD
                    return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        pass

    # Se arriviamo qui, il formato non è stato riconosciuto
    raise ValueError(f"Formato data non valido: {date_str}")

def get_kaifa_data(request):
    """Restituisce i dati relativi alle letture per un contatore, anno e opzionalmente un mese specifici."""
    try:
        contatore_id = request.GET.get('contatore_id')
        anno = request.GET.get('anno')
        mese = request.GET.get('mese')  # Nuovo parametro opzionale per il mese
        
        if not contatore_id or not anno:
            return JsonResponse({
                'status': 'error',
                'message': 'Parametri mancanti: contatore_id e anno sono obbligatori'
            }, status=400)
            
        # Ottieni il contatore
        contatore = get_object_or_404(Contatore, id=contatore_id)
        
        # Crea il filtro base
        filtro = {
            'contatore': contatore,
            'anno': anno,
            'tipo_tabella': 'libro_kaifa'
        }
        
        # Se specificato un mese, aggiungilo al filtro
        if mese:
            filtro['mese'] = mese
            
        # Ottieni le letture filtrate dal database
        letture = LetturaContatore.objects.filter(**filtro).order_by('mese')
        
        # Prepara i dati da restituire
        letture_data = []
        for lettura in letture:
            letture_data.append({
                'mese': lettura.mese,
                'kaifa_180n': float(lettura.kaifa_180n) if lettura.kaifa_180n is not None else None,
                'kaifa_280n': float(lettura.kaifa_280n) if lettura.kaifa_280n is not None else None,
                'totale_180n': float(lettura.totale_180n) if lettura.totale_180n is not None else None,
                'totale_280n': float(lettura.totale_280n) if lettura.totale_280n is not None else None
            })
        
        # Aggiungi dati del contatore nella risposta
        return JsonResponse({
            'status': 'success',
            'contatore': {
                'id': contatore.id,
                'nome': contatore.nome,
                'k': contatore.k,
                'marca': contatore.marca
            },
            'letture': letture_data,
            'filtro_applicato': {
                'anno': anno,
                'mese': mese if mese else 'tutti'
            }
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }, status=500)

def get_kaifa_totale_mapping(contatore, anno):
    """
    Recupera i valori delle colonne totale_180n e totale_280n dalla tabella LetturaContatore
    per il contatore specificato, anno e per il tipo_tabella 'libro_kaifa'.
    Filtra per mostrare solo valori positivi.
    
    Restituisce:
        dict: {mese: {'totale_180n': valore1, 'totale_280n': valore2}}
    """
    qs = LetturaContatore.objects.filter(
        contatore=contatore,
        anno=anno,
        tipo_tabella='libro_kaifa'
    ).order_by('mese')
    
    # Restituisce un dizionario con entrambi i valori (solo positivi)
    mapping = {}
    for lettura in qs:
        mapping[lettura.mese] = {
            'totale_180n': lettura.totale_180n if lettura.totale_180n and lettura.totale_180n > 0 else None,
            'totale_280n': lettura.totale_280n if lettura.totale_280n and lettura.totale_280n > 0 else None
        }
    return mapping

def sostituzione_contatore(request, nickname):
    """Vista per mostrare la pagina di sostituzione contatore."""
    try:
        impianto = get_object_or_404(MonitoraggioImpianto, nickname=nickname)

        # --- DEBUG: Stampa il tipo dell'oggetto recuperato ---
        # print(f"DEBUG: Oggetto impianto recuperato: {impianto}")
        # print(f"DEBUG: Tipo di oggetto impianto: {type(impianto)}")
        # --- FINE DEBUG ---

        if not isinstance(impianto, MonitoraggioImpianto):
             raise TypeError(f"Errore imprevisto: get_object_or_404 ha restituito {type(impianto)} invece di MonitoraggioImpianto.")

        contatori_attivi = Contatore.objects.filter(impianto_nickname=nickname, data_dismissione__isnull=True)

        context = {
            'impianto': impianto,
            'contatori_attivi': contatori_attivi,
            # Inizialmente non c'è un contatore selezionato nel contesto
        }

        # Se abbiamo un contatore selezionato in sessione, proviamo a caricarlo
        if 'contatore_selezionato_id' in request.session:
            contatore_id = request.session['contatore_selezionato_id']
            try:
                # Assicurati che il contatore esista e appartenga all'impianto corretto
                contatore_selezionato = Contatore.objects.get(id=contatore_id, impianto_nickname=nickname)
                context['contatore_selezionato'] = contatore_selezionato
                print(f"DEBUG: Contatore ID {contatore_id} trovato e aggiunto al contesto.")
            except Contatore.DoesNotExist:
                # Se il contatore non esiste o non appartiene a questo impianto,
                # rimuovi l'ID non valido dalla sessione e informa l'utente.
                print(f"DEBUG: Contatore ID {contatore_id} dalla sessione non trovato per nickname {nickname}. Rimuovo dalla sessione.")
                del request.session['contatore_selezionato_id']
                messages.warning(request, f"Il contatore precedentemente selezionato (ID: {contatore_id}) non è stato trovato o non appartiene a questo impianto.")
                # La pagina verrà comunque renderizzata, ma senza un contatore preselezionato.

        return render(request, 'sostituzione_contatore.html', context)

    except MonitoraggioImpianto.DoesNotExist:
         raise Http404(f"Impianto con nickname '{nickname}' non trovato nel modello MonitoraggioImpianti.")
    except Exception as e:
         print(f"Errore inatteso in sostituzione_contatore: {e}")
         import traceback
         traceback.print_exc()
         raise

def seleziona_contatore_sostituzione(request):
    """Funzione per selezionare un contatore da sostituire."""
    if request.method == 'POST':
        contatore_id = request.POST.get('contatore_id')
        nickname = request.POST.get('impianto_nickname')
        
        # Salviamo l'ID del contatore selezionato nella sessione
        request.session['contatore_selezionato_id'] = contatore_id
        
        # Reindirizziamo alla pagina di sostituzione contatore
        return redirect('sostituzione_contatore', nickname=nickname)
    
    # Se non è una richiesta POST, reindirizza alla home
    return redirect('automazione-dati')

def salva_contatore_sostituzione(request):
    """Funzione per salvare la sostituzione di un contatore."""
    if request.method == 'POST':
        # 1. Otteniamo i dati dal form
        nickname = request.POST.get('impianto_nickname')
        contatore_da_sostituire_id = request.POST.get('contatore_da_sostituire_id')
        data_dismissione = request.POST.get('data_dismissione')

        # 2. Aggiorniamo il contatore vecchio con la data di dismissione
        contatore_vecchio = get_object_or_404(Contatore, id=contatore_da_sostituire_id)
        contatore_vecchio.data_dismissione = data_dismissione
        contatore_vecchio.save()

        # 3. Creiamo il nuovo contatore
        # Modifica: Recupera l'impianto dal modello corretto (MonitoraggioImpianto)
        impianto_monitoraggio = get_object_or_404(MonitoraggioImpianto, nickname=nickname)
        nuovo_contatore = Contatore(
            # Rimosso: impianto=impianto, (il modello Contatore non ha questo campo)
            impianto_nickname=impianto_monitoraggio.nickname, # Usa il nickname dall'impianto corretto
            nome=request.POST.get('nome'),
            pod=request.POST.get('pod'),
            tipologia=request.POST.get('tipologia'),
            k=request.POST.get('k'),
            marca=request.POST.get('marca'),
            modello=request.POST.get('modello'),
            data_installazione=request.POST.get('data_installazione'),
        )
        nuovo_contatore.save()

        # 4. Puliamo la sessione e mostriamo un messaggio di successo
        if 'contatore_selezionato_id' in request.session:
            del request.session['contatore_selezionato_id']

        messages.success(request, f"Contatore {contatore_vecchio.nome} sostituito con successo da {nuovo_contatore.nome}!")

        # 5. Redirigiamo alla pagina di dettaglio dell'impianto (usando il namespace e pk)
        # Modifica: Usa il namespace 'monitoraggio-impianti' e 'pk' come argomento
        try:
            # Prova a reindirizzare usando il namespace e 'pk'
            return redirect('monitoraggio-impianti:dettaglio_impianto', pk=impianto_monitoraggio.id)
        except NoReverseMatch:
            # Se fallisce, potrebbe essere che l'argomento si chiami 'impianto_id'
            try:
                return redirect('monitoraggio-impianti:dettaglio_impianto', impianto_id=impianto_monitoraggio.id)
            except NoReverseMatch:
                # Se fallisce ancora, informa che l'URL non è stato trovato
                # In un'applicazione reale, potresti reindirizzare a una pagina generica o loggare l'errore
                messages.error(request, "Errore: Impossibile trovare l'URL per la pagina di dettaglio dell'impianto. Contattare l'amministratore.")
                # Reindirizza alla home dell'app come fallback
                return redirect('automazione-dati')


    # Se non è una richiesta POST, reindirizza alla home
    return redirect('automazione-dati')

@require_POST
def elimina_contatore(request, contatore_id):
    """
    Elimina un contatore specifico e le sue letture associate.
    Accetta solo richieste POST.
    """
    try:
        # 1. Trova il contatore nel database usando l'ID fornito nell'URL.
        #    get_object_or_404 restituisce l'oggetto se esiste,
        #    altrimenti genera automaticamente un errore 404 (Not Found).
        contatore = get_object_or_404(Contatore, id=contatore_id)

        # 2. Salva il nickname dell'impianto e il nome del contatore PRIMA di eliminarlo.
        #    Ci serviranno per il reindirizzamento e per il messaggio di conferma.
        nickname_impianto = contatore.impianto_nickname
        nome_contatore = contatore.nome

        # 3. Elimina l'oggetto contatore dal database.
        #    Grazie a `on_delete=models.CASCADE` nel modello LetturaContatore,
        #    Django eliminerà automaticamente anche tutte le letture associate
        #    a questo contatore.
        contatore.delete()

        # 4. Mostra un messaggio di successo all'utente.
        #    Questi messaggi vengono solitamente mostrati nel template base.
        messages.success(request, f"Il contatore '{nome_contatore}' e tutte le sue letture sono stati eliminati con successo.")

        # 5. Reindirizza l'utente alla pagina da cui probabilmente proveniva,
        #    cioè la panoramica dei contatori per quell'impianto.
        return redirect('panoramica-contatore', nickname=nickname_impianto)

    except Http404:
        # Questo blocco viene eseguito se get_object_or_404 non trova il contatore.
        messages.error(request, f"Errore: Impossibile trovare il contatore con ID {contatore_id}.")
        # Reindirizza a una pagina generica o alla home dell'app,
        # dato che non abbiamo il nickname dell'impianto se il contatore non è stato trovato.
        return redirect('automazione-dati') # O un'altra pagina di fallback appropriata

    except Exception as e:
        # Gestisce qualsiasi altro errore imprevisto durante il processo.
        messages.error(request, f"Si è verificato un errore imprevisto durante l'eliminazione del contatore: {e}")
        # Tenta di reindirizzare alla pagina dell'impianto se abbiamo il nickname,
        # altrimenti alla pagina di fallback.
        try:
            # Se l'errore è avvenuto dopo aver recuperato il nickname
            if nickname_impianto:
                 return redirect('panoramica-contatore', nickname=nickname_impianto)
            else:
                 # Se l'errore è avvenuto prima (improbabile con get_object_or_404)
                 return redirect('automazione-dati')
        except NameError: # Se nickname_impianto non è stato definito a causa dell'errore
             return redirect('automazione-dati')

