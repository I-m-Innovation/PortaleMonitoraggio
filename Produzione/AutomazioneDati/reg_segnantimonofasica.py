from django.shortcuts import render, get_object_or_404, redirect
from MonitoraggioImpianti.models import Impianto

from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import datetime
from AutomazioneDati.models import Contatore, LetturaContatore, regsegnanti
from MonitoraggioImpianti.models import Impianto as MonitoraggioImpianto
from django.contrib import messages
from django.urls.exceptions import NoReverseMatch
import re
from django.utils.dateparse import parse_datetime
from django.db import models
from django.utils import timezone
import logging
import shutil
import os
from django.conf import settings

# Configura il logging per debug
logger = logging.getLogger(__name__)

def crea_backup_database():
    """
    Crea una copia di backup del database SQLite nella cartella ownCloud
    (sovrascrive sempre lo stesso file)
    """
    try:
        # Percorso del database corrente
        db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        
        # Percorso di destinazione per il backup
        backup_dir = r"C:\Users\Sviluppo_Software_ZG\ownCloud\LettureImpianti"
        
        # Verifica che la cartella di destinazione esista
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
        
        # Nome fisso del file di backup (sempre lo stesso, verrà sovrascritto)
        backup_filename = "db_backup.sqlite3"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Verifica se il file esiste già e loggalo
        file_exists = os.path.exists(backup_path)
        if file_exists:
            logger.info(f"Sovrascrittura backup esistente: {backup_path}")
        
        # Copia il file (sovrascrive se esiste)
        shutil.copy2(db_path, backup_path)
        
        # Genera timestamp per il messaggio informativo
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y alle %H:%M:%S")
        
        if file_exists:
            message = f"Backup sovrascritto il {timestamp}"
            logger.info(f"Backup database sovrascritto con successo: {backup_path}")
        else:
            message = f"Backup creato il {timestamp}"
            logger.info(f"Backup database creato con successo: {backup_path}")
        
        return True, message
        
    except Exception as e:
        logger.error(f"Errore durante la creazione del backup: {str(e)}")
        return False, f"Errore backup: {str(e)}"

def reg_segnantimonofasica(request, nickname, contatore_id=None):
    """
    View principale per la registrazione dei segnanti monofasica
    """
    try:
        # Ottieni l'impianto dal nickname
        impianto = get_object_or_404(MonitoraggioImpianto, nickname=nickname)
        
        # Cerca il contatore specifico usando l'ID passato nell'URL
        if contatore_id:
            contatore = get_object_or_404(Contatore, id=contatore_id, impianto_nickname=nickname)
        else:
            # Se per qualche motivo l'ID non è stato passato, cerca il più recente (fallback)
            contatore = Contatore.objects.filter(
                impianto_nickname=nickname
            ).order_by('-data_installazione', '-id').first()
        
        if not contatore:
            messages.error(request, 'Nessun contatore trovato per questo impianto. Aggiungi prima un contatore.')
            # Reindirizza alla panoramica contatori con un messaggio esplicito
            return redirect('panoramica-contatore', nickname=nickname)
        
        # Verifica che il contatore sia di tipo monofascio
        # Nota: i tuoi modelli usano 'tipologiafascio' per questo. Assicurati che i valori siano coerenti.
        if contatore.tipologiafascio.lower() != 'monofascio':
            messages.warning(request, f'Il contatore selezionato ({contatore.nome}) è di tipo {contatore.tipologiafascio}, non monofascio. Reindirizzamento a diario energie.')
            return redirect('panoramica-contatore', nickname=nickname)
        
        # Anno corrente o selezionato
        anno_corrente = request.GET.get('anno', str(timezone.now().year))
        
        # Debug: stampa le informazioni per verificare
        print(f"Debug - Impianto: {impianto.id}, Contatore: {contatore.id if contatore else 'None'}")
        
        context = {
            'impianto': impianto,
            'contatore': contatore,
            'contatore_selezionato': contatore,
            'anno_corrente': anno_corrente,
        }
        
        return render(request, 'reg_segnantimonofascia.html', context)
        
    except Exception as e:
        messages.error(request, f'Errore durante il caricamento della pagina: {str(e)}')
        return redirect('panoramica-contatore', nickname=nickname)

@csrf_exempt
@require_POST
def salva_letture_monofasica(request, contatore_id):
    """
    Salva le letture del contatore monofasica
    """
    try:
        # Verifica che il contatore esista
        contatore = get_object_or_404(Contatore, id=contatore_id)
        
        # Decodifica i dati JSON dalla richiesta
        data = json.loads(request.body.decode('utf-8'))
        letture_data = data.get('letture', [])
        anno = data.get('anno')
        
        logger.info(f"DEBUG: Inizio salvataggio per contatore {contatore_id}, anno {anno}")
        logger.info(f"DEBUG: Ricevute {len(letture_data)} righe di dati")
        
        letture_salvate = []
        errori = []
        
        for idx, riga_dati in enumerate(letture_data):
            try:
                mese = riga_dati.get('mese')
                anno_riga = riga_dati.get('anno', anno)
                
                logger.info(f"DEBUG: Processando riga {idx + 1} - Mese: {mese}, Anno: {anno_riga}")
                logger.info(f"DEBUG: Dati riga: {riga_dati}")
                
                # Salta le righe vuote (senza dati significativi)
                if not ha_dati_significativi_monofasica(riga_dati):
                    logger.info(f"DEBUG: Riga {idx + 1} saltata - nessun dato significativo")
                    continue
                
                # Valida i dati prima del salvataggio
                errori_validazione = valida_dati_lettura_monofasica(riga_dati, mese)
                if errori_validazione:
                    errori.extend(errori_validazione)
                    continue
                
                # Cerca una lettura esistente o crea una nuova
                lettura, created = LetturaContatore.objects.get_or_create(
                    contatore=contatore,
                    mese=mese,
                    anno=anno_riga,
                    defaults={
                        'data_ora_lettura': None,
                        'kaifa_180n': None,
                        'totale_180n': None,
                        'kaifa_280n': None,
                        'totale_280n': None,
                    }
                )
                
                # Aggiorna i campi con i nuovi dati
                aggiorna_campi_lettura_monofasica(lettura, riga_dati)
                
                # Salva nel database
                lettura.save()
                
                logger.info(f"DEBUG: Lettura salvata - ID: {lettura.id}, Creata: {created}")
                
                # Aggiungi alla lista delle letture salvate
                letture_salvate.append({
                    'id': lettura.id,
                    'mese': lettura.mese,
                    'anno': lettura.anno,
                    'data_ora_lettura': lettura.data_ora_lettura.isoformat() if lettura.data_ora_lettura else None,
                    'kaifa_180n': str(lettura.kaifa_180n) if lettura.kaifa_180n is not None else None,
                    'totale_180n': str(lettura.totale_180n) if lettura.totale_180n is not None else None,
                    'kaifa_280n': str(lettura.kaifa_280n) if lettura.kaifa_280n is not None else None,
                    'totale_kaifa_280n': str(lettura.totale_280n) if lettura.totale_280n is not None else None,
                })
                
            except Exception as e:
                errori.append(f'Errore nel salvataggio della riga {idx + 1}: {str(e)}')
        
        # Crea il backup del database dopo il salvataggio
        backup_success = False
        backup_message = ""
        if letture_salvate:  # Solo se ci sono state effettivamente delle letture salvate
            backup_success, backup_message = crea_backup_database()
        
        # Prepara la risposta
        if errori:
            response_data = {
                'success': False,
                'message': 'Alcuni dati non sono stati salvati a causa di errori.',
                'errori': errori,
                'letture_salvate': letture_salvate
            }
        else:
            response_data = {
                'success': True,
                'message': f'Salvate con successo {len(letture_salvate)} letture.',
                'letture_salvate': letture_salvate
            }
        
        # Aggiungi informazioni sul backup
        if letture_salvate:
            response_data['backup'] = {
                'success': backup_success,
                'message': backup_message
            }
        
        return JsonResponse(response_data)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Errore nella decodifica dei dati JSON.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Errore interno del server: {str(e)}'
        })

def ha_dati_significativi_monofasica(riga_dati):
    """
    Controlla se una riga ha almeno un dato significativo inserito per sistema monofasica
    """
    campi_numerici = ['kaifa_180n', 'kaifa_280n']
    
    # Controlla se c'è una data/ora
    if riga_dati.get('data_ora_lettura'):
        return True
    
    # Controlla se c'è almeno un valore numerico
    for campo in campi_numerici:
        valore = riga_dati.get(campo, '').strip()
        if valore:
            return True
    
    return False

def aggiorna_campi_lettura_monofasica(lettura, riga_dati):
    """
    Aggiorna i campi della lettura con i dati ricevuti per sistema monofasica
    CORRETTO per gestire correttamente il timezone italiano
    """
    # Aggiorna la data/ora se presente
    data_ora_str = riga_dati.get('data_ora_lettura')
    if data_ora_str:
        try:
            # Importa timezone per gestire correttamente l'ora italiana
            from django.utils import timezone as django_timezone
            import pytz
            
            # Parse la datetime come naive (senza timezone)
            dt_naive = parse_datetime(data_ora_str)
            if dt_naive:
                # Tratta la data come ora locale italiana, non UTC
                italian_tz = pytz.timezone('Europe/Rome')
                # Se la datetime è naive, rendila aware nel timezone italiano
                if dt_naive.tzinfo is None:
                    dt_aware = italian_tz.localize(dt_naive)
                else:
                    dt_aware = dt_naive
                lettura.data_ora_lettura = dt_aware
            else:
                lettura.data_ora_lettura = None
        except Exception as e:
            logger.error(f"Errore nel parsing della data/ora: {data_ora_str} -> {e}")
            lettura.data_ora_lettura = None
    
    # Aggiorna i campi numerici per sistema monofasica
    campi_numerici = {
        'kaifa_180n': 'kaifa_180n',
        'totale_180n': 'totale_180n', 
        'kaifa_280n': 'kaifa_280n',
        'totale_kaifa_280n': 'totale_280n'
    }
    
    for campo_json, campo_modello in campi_numerici.items():
        valore_str = riga_dati.get(campo_json, '').strip()
        if valore_str:
            try:
                # Converti virgola in punto e poi in Decimal
                valore_normalizzato = valore_str.replace(',', '.')
                valore_decimal = Decimal(valore_normalizzato)
                setattr(lettura, campo_modello, valore_decimal)
            except (InvalidOperation, ValueError):
                # Se la conversione fallisce, imposta None
                setattr(lettura, campo_modello, None)
        else:
            setattr(lettura, campo_modello, None)

def valida_dati_lettura_monofasica(riga_dati, mese):
    """
    Valida i dati di una lettura e restituisce una lista di errori per sistema monofasica
    """
    errori = []
    
    # Valida la data/ora se presente
    data_ora_str = riga_dati.get('data_ora_lettura')
    if data_ora_str:
        try:
            data_ora = parse_datetime(data_ora_str)
            if not data_ora:
                errori.append(f'Formato data/ora non valido per il mese {mese}')
        except:
            errori.append(f'Errore nel parsing della data/ora per il mese {mese}')
    
    # Valida i campi numerici per sistema monofasica
    campi_numerici = ['kaifa_180n', 'kaifa_280n']
    for campo in campi_numerici:
        valore_str = riga_dati.get(campo, '').strip()
        if valore_str:
            try:
                valore_normalizzato = valore_str.replace(',', '.')
                Decimal(valore_normalizzato)
            except (InvalidOperation, ValueError):
                errori.append(f'Valore numerico non valido nel campo {campo} per il mese {mese}')
    
    return errori

@require_GET
def test_connessione_monofasica(request):
    """
    Endpoint semplice per testare che Django sia raggiungibile per sistema monofasica
    """
    return JsonResponse({
        'success': True,
        'message': 'Connessione OK - Sistema Monofasica',
        'timestamp': timezone.now().isoformat(),
        'debug_info': {
            'method': request.method,
            'path': request.path,
            'user_agent': request.META.get('HTTP_USER_AGENT', 'N/A')
        }
    })

@require_GET
def get_letture_monofasica_per_anno(request, contatore_id, anno):
    """
    Recupera tutte le letture per un contatore in un determinato anno per sistema monofasica
    """
    try:
        # Valida l'anno
        try:
            anno_int = int(anno)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Anno non valido.'}, status=400)
        
        # Verifica che il contatore esista
        contatore = get_object_or_404(Contatore, id=contatore_id)
        
        logger.info(f"DEBUG: Recupero letture monofasica per contatore {contatore_id}, anno {anno_int}")
        
        # Recupera le letture per l'anno specificato
        letture = LetturaContatore.objects.filter(
            contatore=contatore,
            anno=anno_int
        ).order_by('mese')
        
        # Aggiungi anche il gennaio dell'anno successivo (mese 1 dell'anno successivo)
        letture_anno_successivo = LetturaContatore.objects.filter(
            contatore=contatore,
            anno=anno_int + 1,
            mese=1
        )
        
        # Combina i QuerySet
        from itertools import chain
        tutte_letture = list(chain(letture, letture_anno_successivo))
        
        logger.info(f"DEBUG: Trovate {len(tutte_letture)} letture")
        
        # Converti in formato JSON
        letture_json = []
        for lettura in tutte_letture:
            lettura_dict = {
                'id': lettura.id,
                'mese': lettura.mese,
                'anno': lettura.anno,
                'data_ora_lettura': lettura.data_ora_lettura.isoformat() if lettura.data_ora_lettura else None,
                'kaifa_180n': str(lettura.kaifa_180n) if lettura.kaifa_180n is not None else None,
                'totale_180n': str(lettura.totale_180n) if lettura.totale_180n is not None else None,
                'kaifa_280n': str(lettura.kaifa_280n) if lettura.kaifa_280n is not None else None,
                'totale_kaifa_280n': str(lettura.totale_280n) if lettura.totale_280n is not None else None,
            }
            letture_json.append(lettura_dict)
            logger.info(f"DEBUG: Lettura {lettura.id} - Mese: {lettura.mese}, Anno: {lettura.anno}")
        
        return JsonResponse({
            'success': True,
            'letture': letture_json,
            'anno': anno_int,
            'contatore': contatore.nome
        })
        
    except Contatore.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contatore non trovato.'}, status=404)
    except ValueError as e:
        logger.error(f"DEBUG: Anno non valido: {anno} - {str(e)}")
        return JsonResponse({'success': False, 'message': 'Anno non valido.'}, status=400)
    except Exception as e:
        logger.error(f"DEBUG: Errore interno: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'Errore interno del server: {str(e)}'}, status=500)

@require_GET
def test_dati_database_monofasica(request, contatore_id):
    """
    Funzione di debug per controllare che dati esistono nel database per sistema monofasica
    """
    try:
        contatore = get_object_or_404(Contatore, id=contatore_id)
        
        # Controlla tutti gli anni disponibili per questo contatore
        anni_disponibili = LetturaContatore.objects.filter(
            contatore=contatore
        ).values_list('anno', flat=True).distinct().order_by('anno')
        
        # Per ogni anno, controlla i mesi disponibili
        dati_per_anno = {}
        for anno in anni_disponibili:
            mesi = LetturaContatore.objects.filter(
                contatore=contatore,
                anno=anno
            ).values_list('mese', flat=True).order_by('mese')
            dati_per_anno[anno] = list(mesi)
        
        return JsonResponse({
            'contatore': contatore.nome,
            'tipologia': contatore.tipologia,
            'anni_disponibili': list(anni_disponibili),
            'dati_per_anno': dati_per_anno,
            'totale_letture': LetturaContatore.objects.filter(contatore=contatore).count()
        })
        
    except Exception as e:
        return JsonResponse({'errore': str(e)}) 