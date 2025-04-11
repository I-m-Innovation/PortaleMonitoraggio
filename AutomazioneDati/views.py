from django.shortcuts import render, get_object_or_404, redirect
from MonitoraggioImpianti.models import Impianto
# from .models import Contatore, LetturaContatore
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import datetime
from .models import Contatore, LetturaContatore
from AutomazioneDati.models import Impianto as AutomazioneImpianto
from MonitoraggioImpianti.models import Impianto as MonitoraggioImpianto
from django.utils.formats import date_format



def home(request):
    # Filtriamo solo gli impianti con tipo "Idroelettrico"
    impianti = Impianto.objects.filter(tipo='Idroelettrico')
    return render(request, 'home.html', {'impianti': impianti})


def reg_segnanti(request, nickname):
    impianto = get_object_or_404(Impianto, nickname=nickname)
    
    try:
        # Ottieni tutti i contatori dell'impianto
        contatori = Contatore.objects.filter(impianto_nickname=nickname)
        
        if contatori.exists():
            # Ottieni l'anno corrente dalla query string o usa quello attuale
            anno_corrente = request.GET.get('anno', str(datetime.date.today().year))
            
            # Trova i contatori Gesis e Kaifa (se esistono)
            contatore_gesis = contatori.filter(marca='Gesis', tipologia='Produzione').first()
            contatore_kaifa = contatori.filter(marca='Kaifa', tipologia='Scambio').first()
            
            # Dizionario per memorizzare i dati per ogni tipo di contatore
            dati_contatori = {}
            
            # Se esiste un contatore Gesis, elabora i suoi dati
            if contatore_gesis:
                # Recupera le letture per reg_segnanti
                letture_reg_gesis = LetturaContatore.objects.filter(
                    contatore=contatore_gesis,
                    anno=anno_corrente,
                    tipo_tabella='reg_segnanti'
                ).order_by('mese')
                letture_reg_gesis_per_mese = {lettura.mese: lettura for lettura in letture_reg_gesis}
                
                # Recupera le letture da libro_energie per Gesis/Produzione
                letture_libro_energie_qs = LetturaContatore.objects.filter(
                    contatore=contatore_gesis,
                    anno=anno_corrente,
                    tipo_tabella='libro_energie'
                ).order_by('mese')
                letture_libro_energie_per_mese = {lettura.mese: lettura for lettura in letture_libro_energie_qs}
                
                # Elabora i dati per ogni mese
                dati_gesis_per_mese = {}
                for mese in range(1, 13):
                    lettura_reg = letture_reg_gesis_per_mese.get(mese)
                    if lettura_reg is None:
                        lettura_reg = LetturaContatore(
                            contatore=contatore_gesis,
                            anno=anno_corrente,
                            mese=mese,
                            tipo_tabella='reg_segnanti'
                        )
                    
                    # Importa dati da libro_energie se disponibili
                    lettura_libro = letture_libro_energie_per_mese.get(mese)
                    if lettura_libro:
                        if lettura_libro.totale_neg is not None and lettura_libro.totale_neg > 0:
                            try:
                                valore_con_decimali = lettura_libro.totale_neg * Decimal(str(contatore_gesis.k))
                                valore_arrotondato = valore_con_decimali.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                                lettura_reg.prod_campo = valore_arrotondato
                            except (TypeError, InvalidOperation) as e:
                                print(f"Errore durante calcolo prod_campo per Gesis, mese {mese}: {e}")
                        
                        if lettura_libro.totale_pos is not None and lettura_libro.totale_pos > 0:
                            try:
                                valore_importato_pos = lettura_libro.totale_pos * Decimal(str(contatore_gesis.k))
                                lettura_reg.prel_campo = valore_importato_pos.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                            except (TypeError, InvalidOperation) as e:
                                print(f"Errore durante calcolo prel_campo per Gesis, mese {mese}: {e}")
                    
                    dati_gesis_per_mese[mese] = lettura_reg
                
                dati_contatori['gesis'] = {
                    'contatore': contatore_gesis,
                    'dati_per_mese': dati_gesis_per_mese
                }
            
            # Se esiste un contatore Kaifa, elabora i suoi dati
            if contatore_kaifa:
                # Recupera le letture per reg_segnanti
                letture_reg_kaifa = LetturaContatore.objects.filter(
                    contatore=contatore_kaifa,
                    anno=anno_corrente,
                    tipo_tabella='reg_segnanti'
                ).order_by('mese')
                letture_reg_kaifa_per_mese = {lettura.mese: lettura for lettura in letture_reg_kaifa}
                
                # Recupera i dati da libro_kaifa
                letture_libro_kaifa_qs = LetturaContatore.objects.filter(
                    contatore=contatore_kaifa,
                    anno=anno_corrente,
                    tipo_tabella='libro_kaifa'
                ).order_by('mese')
                letture_libro_kaifa_per_mese = {lettura.mese: lettura for lettura in letture_libro_kaifa_qs}
                
                # Ottieni mapping dei valori totale_180n e totale_280n
                kaifa_mapping = get_kaifa_totale_mapping(contatore_kaifa, anno_corrente)
                
                # Elabora i dati per ogni mese
                dati_kaifa_per_mese = {}
                for mese in range(1, 13):
                    lettura_reg = letture_reg_kaifa_per_mese.get(mese)
                    if lettura_reg is None:
                        lettura_reg = LetturaContatore(
                            contatore=contatore_kaifa,
                            anno=anno_corrente,
                            mese=mese,
                            tipo_tabella='reg_segnanti'
                        )
                    
                    # Imposta i campi usando i valori da totale_180n e totale_280n (solo positivi)
                    if mese in kaifa_mapping:
                        # Imposta imm_campo con totale_180n (solo se positivo)
                        if kaifa_mapping[mese]['totale_180n'] is not None:
                            valore_180n = kaifa_mapping[mese]['totale_180n'] * contatore_kaifa.k
                            if valore_180n > 0 and lettura_reg.imm_campo is None:
                                lettura_reg.imm_campo = valore_180n
                        
                        # Imposta scambio_prelevata_campo con totale_280n (solo se positivo)
                        if kaifa_mapping[mese]['totale_280n'] is not None:
                            valore_280n = kaifa_mapping[mese]['totale_280n'] * contatore_kaifa.k
                            if valore_280n > 0 and lettura_reg.scambio_prelevata_campo is None:
                                lettura_reg.scambio_prelevata_campo = valore_280n
                    
                    dati_kaifa_per_mese[mese] = lettura_reg
                
                dati_contatori['kaifa'] = {
                    'contatore': contatore_kaifa,
                    'dati_per_mese': dati_kaifa_per_mese
                }
            
            # Prepara il contesto combinato
            context = {
                'impianto': impianto,
                'contatori': contatori,
                'dati_contatori': dati_contatori,
                'num_rows': range(12),
                'anno_corrente': anno_corrente,
                'visualizza_pulsante_importazione': bool(contatore_kaifa)
            }
            
            return render(request, 'reg_segnanti.html', context)
        else:
            # Se non ci sono contatori, reindirizza alla pagina di creazione
            return redirect('nuovo-contatore', nickname=nickname)
    except Exception as e:
        return render(request, 'reg_segnanti.html', {'impianto': impianto, 'errore': str(e)})

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
        from MonitoraggioImpianti.models import Impianto as MonitoraggioImpianto
        
        # Recupera l'impianto originale da MonitoraggioImpianti
        impianto_monitoraggio = get_object_or_404(MonitoraggioImpianto, id=impianto_id)
        
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
    anno_selezionato_str = request.GET.get('anno', str(datetime.date.today().year)) # Usa l'anno corrente come default

    try:
        anno_selezionato = int(anno_selezionato_str)
        anno_successivo = anno_selezionato + 1

        # Recupera le letture per l'anno selezionato e per Gennaio dell'anno successivo
        letture_libro_energie_qs = LetturaContatore.objects.filter(
            contatore=contatore,
            tipo_tabella='libro_energie',
            anno__in=[anno_selezionato, anno_successivo] # Filtra per entrambi gli anni
        ).order_by('anno', 'mese')

        # Crea un dizionario per accesso rapido: chiave=(anno, mese)
        letture_energie_per_anno_mese = {(l.anno, l.mese): l for l in letture_libro_energie_qs}

        # Prepara la lista di dati per il template (13 elementi)
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

            # Se non esiste, crea un oggetto temporaneo
            if lettura is None:
                lettura = LetturaContatore(
                    contatore=contatore,
                    anno=anno_corrente_loop,
                    mese=mese_corrente_loop, # Mese effettivo (1-12)
                    tipo_tabella='libro_energie'
                )
                data_presa_display = "" # Nessuna data da mostrare
            else:
                # Formatta la data per la visualizzazione se esiste
                data_presa_display = date_format(lettura.data_presa, "d/m/Y") if lettura.data_presa else "" # Formato GG/MM/AAAA

            # Aggiungi i dati alla lista, includendo il mese "logico" (1-13) per il template
            # e la data formattata
            libro_energie_dati.append({
                'mese': mese_indice, # Mese logico (1-13) per l'attributo data-mese nel template
                'anno': anno_corrente_loop, # Anno effettivo
                'mese_effettivo': mese_corrente_loop, # Mese effettivo (1-12)
                'data_presa': lettura.data_presa, # Data grezza per data-rawvalue
                'data_presa_display': data_presa_display, # Data formattata per la visualizzazione
                'a1_neg': lettura.a1_neg,
                'a2_neg': lettura.a2_neg,
                'a3_neg': lettura.a3_neg,
                'totale_neg': lettura.totale_neg, # Questo viene calcolato da JS, ma lo passiamo se esiste
                'a1_pos': lettura.a1_pos,
                'a2_pos': lettura.a2_pos,
                'a3_pos': lettura.a3_pos,
                'totale_pos': lettura.totale_pos, # Questo viene calcolato da JS, ma lo passiamo se esiste
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
            'libro_energie_dati': libro_energie_dati, # Lista con 13 elementi
            'libro_kaifa_dati': libro_kaifa_dati, # Lista con 13 elementi (oggetti LetturaContatore o None)
            'num_rows': range(13), # Usato per iterare 13 volte nel template Kaifa
        }
        return render(request, 'diariLetture.html', context)

    except ValueError:
        # Gestisci il caso in cui l'anno non sia un numero valido
        # Potresti reindirizzare a una pagina di errore o usare un anno di default
        # Per ora, ritorniamo un errore semplice o reindirizziamo
        # (Questa parte dipende da come vuoi gestire l'errore)
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("Anno non valido.")
    except Exception as e:
        # Log dell'errore per debug
        print(f"Errore in diari_letture: {e}")
        import traceback
        traceback.print_exc()
        # Mostra una pagina di errore generica o gestisci diversamente
        # (Questa parte dipende dalla gestione errori della tua applicazione)
        # Potresti voler rendere una pagina di errore specifica
        return render(request, 'error.html', {'message': 'Si è verificato un errore nel caricamento dei dati.'})

@csrf_exempt
def salva_reg_segnanti(request):
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
            tipo_tabella = data.get('tipo_tabella')
            rows = data.get('rows', [])
            
            # Ottieni il contatore dal database
            contatore = get_object_or_404(Contatore, id=contatore_id)
            
            # Contatore per verificare quante righe sono state salvate
            righe_salvate = 0
            
            # Funzione per convertire la data dal formato italiano a ISO
            def convert_date_format(date_str):
                # Funzione semplificata che non modifica il formato della data
                if not date_str or not date_str.strip():
                    return None
                
                # Restituisci la data così com'è, senza conversioni
                return date_str.strip()
            
            # Elabora ogni riga di dati
            for row_data in rows:
                mese = row_data.get('mese')
                print(f"Elaborazione mese: {mese}")
                
                # Cerca una lettura esistente o crea una nuova
                lettura, created = LetturaContatore.objects.get_or_create(
                    contatore=contatore,
                    anno=anno,
                    mese=mese,
                    tipo_tabella=tipo_tabella,
                    defaults={}
                )
                
                # Aggiorna i campi della lettura con i dati ricevuti
                modificato = False
                
                for field_name, field_value in row_data.items():
                    # Ignora i campi che non sono nel modello o sono id/chiavi
                    if field_name in ['contatore_id', 'anno', 'mese', 'tipo_tabella']:
                        continue
                    
                    # Gestisci la conversione in base al tipo di campo
                    if field_name == 'data_presa':
                        if field_value and field_value.strip():
                            # Converti la data dal formato italiano a ISO
                            iso_date = convert_date_format(field_value)
                            if iso_date:
                                setattr(lettura, field_name, iso_date)
                                modificato = True
                                print(f"Data convertita: {field_value} -> {iso_date}")
                    else:
                        # Per i campi numerici, convertiamo in Decimal se non vuoto
                        if field_name in ['a1_neg', 'a2_neg', 'a3_neg', 'a1_pos', 'a2_pos', 'a3_pos', 'totale_neg', 'totale_pos', 'kaifa_180n', 'kaifa_280n', 'totale_180n', 'totale_280n']:
                            if field_value and field_value.strip():
                                try:
                                    # Rimuovi tutti gli spazi
                                    cleaned_value = field_value.strip().replace(' ', '')
                                    # Sostituisci la virgola con il punto per la conversione
                                    cleaned_value = cleaned_value.replace(',', '.')
                                    
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
                                        setattr(lettura, field_name, decimal_value)
                                        modificato = True
                                    else:
                                        setattr(lettura, field_name, None)
                                        modificato = True
                                except (InvalidOperation, ValueError) as e:
                                    print(f"Errore nel convertire il valore '{field_value}' per {field_name}: {e}")
                                    return JsonResponse({
                                        'status': 'error',
                                        'message': f"Valore non valido '{field_value}' nel campo {field_name}"
                                    }, status=400)
                            else:
                                setattr(lettura, field_name, None)
                                modificato = True
                
                # Salva solo se sono state effettuate modifiche
                if modificato:
                    lettura.save()
                    righe_salvate += 1
            
            # Restituisci una risposta JSON di successo
            return JsonResponse({
                'status': 'success',
                'message': f'Salvate {righe_salvate} righe di dati',
                'tipo_tabella': tipo_tabella,
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

                    # --- Blocco specifico per data_presa ---
                    if field_name == 'data_presa':
                        iso_date = None # Inizializza a None
                        try:
                            field_value_str = str(field_value).strip() if field_value is not None else ""
                            if field_value_str: # Se c'è un valore non vuoto dopo strip
                                print(f"--- DEBUG [data_presa]: Mese {mese_logico}, Ricevuto: '{field_value_str}'")
                                iso_date = convert_date_format(field_value_str)
                                print(f"--- DEBUG [data_presa]: Mese {mese_logico}, Convertito in: '{iso_date}'")
                            else:
                                # Se il valore ricevuto è None, vuoto o solo spazi
                                iso_date = None
                                print(f"--- DEBUG [data_presa]: Mese {mese_logico}, Ricevuto vuoto/None, impostato a None")

                            # Confronta il valore attuale (come stringa YYYY-MM-DD o None) con quello nuovo
                            valore_attuale_str = valore_attuale.strftime('%Y-%m-%d') if isinstance(valore_attuale, datetime.date) else None
                            if valore_attuale_str != iso_date:
                                setattr(lettura, field_name, iso_date)
                                modificato = True
                                print(f"--- DEBUG [data_presa]: Mese {mese_logico}, Modificato: {valore_attuale_str} -> {iso_date}")
                            dati_riga_aggiornati[field_name] = iso_date # Aggiungi al dizionario di risposta

                        except ValueError as e:
                            # Errore durante la conversione della data
                            print(f"--- ERRORE [data_presa]: Mese {mese_logico}, Valore: '{field_value}', Errore: {e}")
                            errore_in_riga = True # Segna che c'è stato un errore in questa riga
                            righe_con_errore_data.append({'mese': mese_logico, 'valore': field_value, 'errore': str(e)})
                            # Non interrompere, ma questa riga non verrà salvata se modificato=True
                            dati_riga_aggiornati[field_name] = valore_attuale_str # Restituisci il valore vecchio in caso di errore


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

