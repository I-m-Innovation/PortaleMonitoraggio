from django.shortcuts import render, get_object_or_404, redirect
from MonitoraggioImpianti.models import Impianto

from django.http import  JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import datetime
from AutomazioneDati.models import  Contatore, LetturaContatore, regsegnanti
from MonitoraggioImpianti.models import Impianto as MonitoraggioImpianto
from django.contrib import messages
from django.urls.exceptions import NoReverseMatch
import re
from django.utils.dateparse import parse_datetime
from django.db import models
from django.utils import timezone


def elenco_contatori(request, nickname):
    
    # Recuperiamo l'ID del contatore dall'URL (parametro GET)
    contatore_id = request.GET.get('contatore_id')
    
    # Se è stato selezionato un contatore specifico, reindirizza alla vista diarioenergie
    # passando il contatore_id come parametro GET
    if contatore_id:
        try:
            # Verifica che il contatore esista e appartenga all'impianto
            contatore_selezionato = Contatore.objects.get(id=contatore_id, impianto_nickname=nickname)
            
            # Reindirizza in base al tipo di fascio del contatore
            tipologia_fascio_lower = contatore_selezionato.tipologiafascio.lower()
            if tipologia_fascio_lower == "trifascio":
                return redirect('reg_segnantitrifascia', nickname=nickname, contatore_id=contatore_id)
            elif tipologia_fascio_lower == "monofascio":
                return redirect('reg_segnantimonofasica', nickname=nickname, contatore_id=contatore_id)
            else:
                # Comportamento di default se la tipologia fascio non è riconosciuta
                return redirect(f'/automazione-dati/diario-energie/{nickname}/?contatore_id={contatore_id}')
        except Contatore.DoesNotExist:
            # Se il contatore non esiste, mostra la pagina senza contatore selezionato
            pass
    
    # Se non c'è un contatore selezionato, mostra la vista diarioenergie normale
    return redirect(f'/automazione-dati/diario-energie/{nickname}/')



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
        tipologiafascio = request.POST.get('tipologiafascio')
        matricola = request.POST.get('matricola')
        k = request.POST.get('k')
        marca = request.POST.get('marca')
        # Se la marca selezionata è 'Altro', usa il valore di 'marca_altro'
        if marca == 'Altro':
            marca = request.POST.get('marca_altro')
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
            tipologiafascio=tipologiafascio,
            matricola=matricola,
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
        
        # Gestione della marca del nuovo contatore
        nuova_marca = request.POST.get('marca')
        if nuova_marca == 'Altro':
            nuova_marca = request.POST.get('marca_altro')

        nuovo_contatore = Contatore(
            # Rimosso: impianto=impianto, (il modello Contatore non ha questo campo)
            impianto_nickname=impianto_monitoraggio.nickname, # Usa il nickname dall'impianto corretto
            nome=request.POST.get('nome'),
            pod=request.POST.get('pod'),
            tipologia=request.POST.get('tipologia'),
            tipologiafascio=request.POST.get('tipologiafascio'),
            matricola=request.POST.get('matricola'),
            k=request.POST.get('k'),
            marca=nuova_marca,
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

def modifica_contatore(request, contatore_id):
    contatore = get_object_or_404(Contatore, id=contatore_id)
    if request.method == 'POST':
        # Aggiorna i campi del contatore con i dati del POST
        contatore.nome = request.POST.get('nome')
        contatore.pod = request.POST.get('pod')
        contatore.tipologia = request.POST.get('tipologia')
        contatore.tipologiafascio = request.POST.get('tipologiafascio')
        contatore.matricola = request.POST.get('matricola')
        contatore.k = request.POST.get('k')
        marca = request.POST.get('marca')
        if marca == 'Altro':
            marca = request.POST.get('marca_altro')
        contatore.marca = marca
        contatore.modello = request.POST.get('modello')
        contatore.data_installazione = request.POST.get('data_installazione')
        contatore.save()
        messages.success(request, "Dati contatore aggiornati con successo!")
        return redirect('panoramica-contatore', nickname=contatore.impianto_nickname)
    
    # Per richieste GET, mostra il form precompilato
    context = {
        'contatore': contatore,
        'impianto': contatore.impianto, # Assicurati che l'impianto sia disponibile per il template
    }
    return render(request, 'modifica_contatore.html', context)

