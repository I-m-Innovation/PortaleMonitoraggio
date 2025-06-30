from django.shortcuts import render, get_object_or_404, redirect
from MonitoraggioImpianti.models import Impianto

from django.http import  JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
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

def reg_segnantitrifascia(request, nickname, contatore_id=None):
    """
    View principale per la registrazione dei segnanti trifascia
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
        
        # Verifica che il contatore sia di tipo trifascio
        # Nota: i tuoi modelli usano 'tipologiafascio' per questo. Assicurati che i valori siano coerenti.
        if contatore.tipologiafascio.lower() != 'trifascio':
            messages.warning(request, f'Il contatore selezionato ({contatore.nome}) è di tipo {contatore.tipologiafascio}, non trifascio. Reindirizzamento a diario energie.')
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
        
        return render(request, 'reg_segnantitrifascia.html', context)
        
    except Exception as e:
        messages.error(request, f'Errore durante il caricamento della pagina: {str(e)}')
        return redirect('panoramica-contatore', nickname=nickname)

@require_POST
def salva_letture_trifasica(request, contatore_id):
    """
    View per salvare le letture del contatore trifasica via AJAX
    
    Questa funzione riceve i dati dal frontend JavaScript e li salva nel database.
    Gestisce anche la validazione dei dati e restituisce una risposta JSON.
    """
    try:
        # Verifica che il contatore esista
        contatore = get_object_or_404(Contatore, id=contatore_id)
        
        # Decodifica i dati JSON dal body della richiesta
        data = json.loads(request.body)
        dati_letture = data.get('dati', [])
        
        if not dati_letture:
            return JsonResponse({
                'success': False, 
                'message': 'Nessun dato ricevuto per il salvataggio.'
            })
        
        letture_salvate = []
        errori = []
        
        # Cicla attraverso tutti i dati ricevuti
        for idx, riga_dati in enumerate(dati_letture):
            try:
                mese = riga_dati.get('mese')
                anno = riga_dati.get('anno')
                
                
                
                # Cerca se esiste già una lettura per questo mese/anno
                lettura_esistente = LetturaContatore.objects.filter(
                    contatore=contatore,
                    mese=mese,
                    anno=anno
                ).first()
                
                if lettura_esistente:
                    # Aggiorna la lettura esistente
                    lettura = lettura_esistente
                else:
                    # Crea una nuova lettura
                    lettura = LetturaContatore(
                        contatore=contatore,
                        mese=mese,
                        anno=anno
                    )
                
                # Aggiorna i campi della lettura
                aggiorna_campi_lettura(lettura, riga_dati)
                
                # Valida i dati prima di salvare
                errori_validazione = valida_dati_lettura(riga_dati, mese)
                if errori_validazione:
                    errori.extend(errori_validazione)
                    continue
                
                # Salva nel database
                lettura.save()
                
                # Aggiungi alla lista delle letture salvate
                letture_salvate.append({
                    'id': lettura.id,
                    'mese': lettura.mese,
                    'anno': lettura.anno,
                    'data_ora_lettura': lettura.data_ora_lettura.isoformat() if lettura.data_ora_lettura else None,
                    'a1_neg': str(lettura.a1_neg) if lettura.a1_neg is not None else None,
                    'a2_neg': str(lettura.a2_neg) if lettura.a2_neg is not None else None,
                    'a3_neg': str(lettura.a3_neg) if lettura.a3_neg is not None else None,
                    'a1_pos': str(lettura.a1_pos) if lettura.a1_pos is not None else None,
                    'a2_pos': str(lettura.a2_pos) if lettura.a2_pos is not None else None,
                    'a3_pos': str(lettura.a3_pos) if lettura.a3_pos is not None else None,
                    'totale_neg': str(lettura.totale_neg) if lettura.totale_neg is not None else None,
                    'totale_pos': str(lettura.totale_pos) if lettura.totale_pos is not None else None,
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


def aggiorna_campi_lettura(lettura, riga_dati):
    """
    Aggiorna i campi dell'oggetto LetturaContatore con i dati ricevuti (MIGLIORATA)
    CORRETTO per gestire correttamente il timezone italiano
    """
    # Aggiorna data/ora se presente
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
    
    # Aggiorna i campi numerici con maggiore precisione
    campi_numerici = {
        'a1_neg': 'a1_neg',
        'a2_neg': 'a2_neg', 
        'a3_neg': 'a3_neg',
        'a1_pos': 'a1_pos',
        'a2_pos': 'a2_pos',
        'a3_pos': 'a3_pos',
        'totale_neg': 'totale_neg',
        'totale_pos': 'totale_pos'
    }
    
    for campo_json, campo_modello in campi_numerici.items():
        valore_str = riga_dati.get(campo_json, '').strip()
        if valore_str:  # CORRETTO: salva qualsiasi valore numerico valido, inclusi gli zeri
            try:
                # Converti virgola in punto e poi in Decimal
                valore_normalizzato = valore_str.replace(',', '.')
                # Usa quantize per controllare la precisione
                valore_decimal = Decimal(valore_normalizzato).quantize(
                    Decimal('0.000001'), 
                    rounding=ROUND_HALF_UP
                )
                setattr(lettura, campo_modello, valore_decimal)
                logger.info(f"Campo {campo_modello} impostato a: {valore_decimal}")
            except (InvalidOperation, ValueError) as e:
                logger.error(f"Errore conversione campo {campo_modello}: {valore_str} -> {e}")
                setattr(lettura, campo_modello, None)
        else:
            setattr(lettura, campo_modello, None)

def valida_dati_lettura(riga_dati, mese):
    """
    Valida i dati di una lettura e restituisce una lista di errori
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
    
    # Valida i campi numerici
    campi_numerici = ['a1_neg', 'a2_neg', 'a3_neg', 'a1_pos', 'a2_pos', 'a3_pos']
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
def test_connessione(request):
    """
    Endpoint semplice per testare che Django sia raggiungibile
    """
    return JsonResponse({
        'success': True,
        'message': 'Connessione OK',
        'timestamp': timezone.now().isoformat(),
        'debug_info': {
            'method': request.method,
            'path': request.path,
            'user_agent': request.META.get('HTTP_USER_AGENT', 'N/A')
        }
    })

@require_GET
def debug_contatore_info(request, contatore_id):
    """
    Endpoint per debug delle informazioni del contatore
    """
    try:
        contatore = get_object_or_404(Contatore, id=contatore_id)
        
        # Conta le letture per anno
        letture_per_anno = {}
        anni = LetturaContatore.objects.filter(contatore=contatore).values_list('anno', flat=True).distinct()
        
        for anno in anni:
            count = LetturaContatore.objects.filter(contatore=contatore, anno=anno).count()
            letture_per_anno[anno] = count
        
        return JsonResponse({
            'success': True,
            'contatore': {
                'id': contatore.id,
                'nome': contatore.nome,
                'tipologia': contatore.tipologia,
                'matricola': contatore.matricola,
                'pod': contatore.pod,
            },
            'impianto': {
                'id': contatore.impianto.id,
                'nome': contatore.impianto.nome_impianto,
                'nickname': contatore.impianto.nickname,
            },
            'statistiche': {
                'totale_letture': LetturaContatore.objects.filter(contatore=contatore).count(),
                'letture_per_anno': letture_per_anno,
                'primi_3_record': list(LetturaContatore.objects.filter(contatore=contatore).order_by('anno', 'mese').values('mese', 'anno', 'data_ora_lettura')[:3])
            }
        })
        
    except Exception as e:
        logger.error(f"Errore in debug_contatore_info: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_GET
def get_letture_trifasica_per_anno(request, contatore_id, anno):
    """
    API view per recuperare le letture (MIGLIORATA)
    """
    logger.info(f"DEBUG: Chiamata API con contatore_id={contatore_id}, anno={anno}")
    
    try:
        contatore = get_object_or_404(Contatore, id=contatore_id)
        anno_int = int(anno)
        
        # Recupera le letture per i 12 mesi dell'anno specificato
        letture_anno_corrente = LetturaContatore.objects.filter(
            contatore=contatore,
            anno=anno_int
        ).order_by('mese')
        
        # Recupera la lettura per gennaio dell'anno successivo
        lettura_gennaio_successivo = LetturaContatore.objects.filter(
            contatore=contatore,
            anno=anno_int + 1,
            mese=1
        ).first()

        letture_serializzate = []

        # Funzione helper per serializzare una lettura
        def serializza_lettura(lettura):
            return {
                'id': lettura.id,
                'mese': lettura.mese,
                'anno': lettura.anno,
                'data_ora_lettura': lettura.data_ora_lettura.isoformat() if lettura.data_ora_lettura else None,
                # Mantieni la precisione originale dal database
                'a1_neg': str(lettura.a1_neg) if lettura.a1_neg is not None else '',
                'a2_neg': str(lettura.a2_neg) if lettura.a2_neg is not None else '',
                'a3_neg': str(lettura.a3_neg) if lettura.a3_neg is not None else '',
                'totale_neg': str(lettura.totale_neg) if lettura.totale_neg is not None else '',
                'a1_pos': str(lettura.a1_pos) if lettura.a1_pos is not None else '',
                'a2_pos': str(lettura.a2_pos) if lettura.a2_pos is not None else '',
                'a3_pos': str(lettura.a3_pos) if lettura.a3_pos is not None else '',
                'totale_pos': str(lettura.totale_pos) if lettura.totale_pos is not None else '',
            }

        # Serializza i dati delle letture dell'anno corrente
        for lettura in letture_anno_corrente:
            letture_serializzate.append(serializza_lettura(lettura))

        # Serializza i dati della lettura di gennaio dell'anno successivo, se esiste
        if lettura_gennaio_successivo:
            letture_serializzate.append(serializza_lettura(lettura_gennaio_successivo))
        
        logger.info(f"DEBUG: Restituendo {len(letture_serializzate)} letture serializzate")
        return JsonResponse({
            'success': True, 
            'letture': letture_serializzate,
            'debug_info': {
                'contatore_id': contatore_id,
                'anno_richiesto': anno,
                'letture_anno_corrente': letture_anno_corrente.count(),
                'ha_gennaio_successivo': lettura_gennaio_successivo is not None,
                'totale_serializzate': len(letture_serializzate)
            }
        })

    except Exception as e:
        logger.error(f"DEBUG: Errore interno: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'Errore interno del server: {str(e)}'}, status=500)

def test_dati_database(request, contatore_id):
    """
    Funzione di debug per controllare che dati esistono nel database
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
            'anni_disponibili': list(anni_disponibili),
            'dati_per_anno': dati_per_anno,
            'totale_letture': LetturaContatore.objects.filter(contatore=contatore).count()
        })
        
    except Exception as e:
        return JsonResponse({'errore': str(e)})