
from MonitoraggioImpianti.models import Impianto
import numpy as np
import pandas as pd

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import models
from django.conf import settings
from django.db import connection
import os
from PortaleCorrispettivi.models import Cashflow
import pandas as pd
import os
from PortaleCorrispettivi.models import Cashflow
from datetime import datetime,timedelta
import PortaleCorrispettivi.utils.functions as fn
from .models import *
import re
from AutomazioneDati.models import regsegnanti
from django.db.models import Q
from .models import commento_tabellacorrispettivi


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated
from django.forms.models import model_to_dict

def filtroimpianto(nickname,anno,mese):
    
    return regsegnanti.objects.filter(
        anno=anno,
        mese=mese,
        contatore__impianto_nickname=nickname
    )

def energiakwh(request, nickname, anno, mese):

    energia_kwh = filtroimpianto(nickname,anno,mese).values_list('prod_campo', flat=True)


    energia_list = [float(v) if v is not None else None for v in list(energia_kwh)]
    if not energia_list:
        energia_list = [None]

    return JsonResponse({
        'success': True,
        'data': energia_list,
        'anno': anno,
        'mese': mese,
        'impianto': nickname
    })
    
    
def datiTFO(request, nickname, anno, mese):
    # Recupera i dati di produzione e immissione per l'impianto, anno e mese specificati
    dati_tfo = filtroimpianto(nickname,anno,mese).values_list('prod_campo', 'imm_campo')
    
    # Memorizza i valori di produzione e immissione in due variabili separate
    prod_values = [record[0] for record in dati_tfo if record[0] is not None]
    imm_values = [record[1] for record in dati_tfo if record[1] is not None]
    
    # Moltiplica i valori di produzione per 0,98 (coefficiente di correzione)
    prod_values_corretti = [float(value) * 0.98 for value in prod_values]
    
    # Calcola il minimo tra produzione corretta e immissione per ogni record e moltiplica per 0.21
    tfo_values = []
    for i in range(min(len(prod_values_corretti), len(imm_values))):
        valore_minimo = min(prod_values_corretti[i], imm_values[i])
        tfo_values.append(float(valore_minimo) * 0.21)
    if not tfo_values:
        tfo_values = [None]
    
    
     
    # Restituisci la risposta in formato JSON
    return JsonResponse({
        'success': True,
        'data': tfo_values,
        'anno': anno,
        'mese': mese,
        'impianto': nickname
    })
    
def datiPUN(request, nickname, anno, mese):
    """
    Connette alla tabella 'Prezzi medi mensili' e recupera la colonna 'timestamp' (tipo timestamp)
    e 'mean_puns' (tipo real), restituendo i dati filtrati per anno e mese.
    """
    # print(f"[DEBUG][datiPUN] Chiamata con nickname={nickname}, anno={anno}, mese={mese}")
    with connection.cursor() as cursor:
        query = """
            SELECT strftime('%%Y-%%m-%%d %%H:%%M:%%S', timestamp) as timestamp, mean_puns
            FROM "Prezzi medi mensili"
            WHERE strftime('%%Y', timestamp) = %s
              AND strftime('%%m', timestamp) = %s
            ORDER BY timestamp
        """
        anno_str = str(anno)
        mese_str = str(mese).zfill(2)
        # print(f"[DEBUG][datiPUN] Esegui query: {query.strip()}")
        # print(f"[DEBUG][datiPUN] Parametri query: anno_str={anno_str}, mese_str={mese_str}")
        cursor.execute(query, [anno_str, mese_str])
        rows = cursor.fetchall()
        # print(f"[DEBUG][datiPUN] Numero di righe restituite dalla query: {len(rows)}")
        # 
        # Prepara la struttura dati: lista di dizionari con 'timestamp' e 'mean_pun'
        dati = []
        for row in rows:
            # print(f"[DEBUG][datiPUN] Riga: timestamp={row[0]}, mean_puns={row[1]}")
            dati.append({
                'timestamp': row[0],         # timestamp nel formato db (stringa ISO o Unix timestamp)
                'mean_pun': float(row[1]) if row[1] is not None else None  # mean_puns come float o None
            })
        if not dati:
            # print("[DEBUG][datiPUN] Nessun dato trovato per i parametri specificati.")
            dati = []  # Restituisci lista vuota in caso non ci siano dati

    risposta = {
        'success': True,
        'data': dati,
        'anno': anno,
        'mese': mese,
        'impianto': nickname
    }
    # print(f"[DEBUG][datiPUN] Risposta restituita: {risposta}")
    return JsonResponse(risposta)
# //questa energia non è moltiplicata per 0,21 che sono soldi 
    
def datiNI(request, nickname, anno, mese):
    # Recupera i queryset per energia prodotta e immissione
    energia_prodotta = filtroimpianto(nickname,anno,mese).values_list('prod_campo', flat=True)
    immissione = filtroimpianto(nickname,anno,mese).values_list('imm_campo', flat=True)
   
    # Converte i queryset in liste per poter operare sui dati
    energia_prodotta_list = list(energia_prodotta)
    immissione_list = list(immissione)
    
    
    energia_non_incentivata = []
    
    # Itera attraverso entrambe le liste e sottrae i valori corrispondenti
    for i in range(len(energia_prodotta_list)):
        if i < len(immissione_list):
            # Verifica che entrambi i valori non siano None prima di eseguire l'operazione
            # Questo risolve l'errore "TypeError: unsupported operand type(s) for -: 'decimal.Decimal' and 'NoneType'"
            if energia_prodotta_list[i] is not None and immissione_list[i] is not None:
                # Sottrae immissione da energia prodotta per ogni elemento
                differenza = energia_prodotta_list[i] - immissione_list[i]
                energia_non_incentivata.append(differenza)
            elif energia_prodotta_list[i] is not None and immissione_list[i] is None:
                # Se l'immissione è None ma l'energia prodotta no, usa solo l'energia prodotta
                energia_non_incentivata.append(energia_prodotta_list[i])
            elif energia_prodotta_list[i] is None and immissione_list[i] is not None:
                # Se l'energia prodotta è None ma l'immissione no, il risultato è negativo dell'immissione
                energia_non_incentivata.append(-immissione_list[i])
            else:
                # Entrambi i valori sono None, aggiungi 0 o salta questo elemento
                energia_non_incentivata.append(0)
        else:
            # Se non c'è un valore di immissione corrispondente, usa solo l'energia prodotta se non è None
            if energia_prodotta_list[i] is not None:
                energia_non_incentivata.append(energia_prodotta_list[i])
            else:
                energia_non_incentivata.append(0)
        
    # print(f"[DEBUG] Energia non incentivata calcolata: {energia_non_incentivata}")
    if not energia_non_incentivata:
        return [None]
    return energia_non_incentivata
def datiCNI(request, nickname, anno, mese):
 
    
    # Calcoliamo l'energia non incentivata meno l'immissione
    # Otteniamo l'energia non incentivata come lista
    ni  = datiNI(request, nickname, anno, mese)
    
   
    
    # Query corretta per filtrare i dati CNI dalla tabella "Prezzi medi mensili"
    # usando le colonne timestamp e mean_CNIs per anno e mese specificati
    with connection.cursor() as cursor: 
        # print(f"[DEBUG] Esecuzione query CNI per anno {anno} e mese {mese}")
        cursor.execute("""
            SELECT strftime('%%Y', timestamp), strftime('%%m', timestamp), mean_puns
            FROM "Prezzi medi mensili"
            WHERE strftime('%%Y', timestamp) = %s
                AND strftime('%%m', timestamp) = %s
            ORDER BY timestamp
        """, [str(anno), str(mese).zfill(2)])
        rows = cursor.fetchall()
        # print(f"[DEBUG] Query CNI eseguita, trovati {len(rows)} record")
        
        # Estraiamo solo i valori mean_CNIs (terza colonna, non seconda) che non sono NULL
        # e convertiamo esplicitamente in float per evitare errori di tipo
        data_CNI = []
        for row in rows:
            if row[2] is not None:  # row[2] è mean_CNIs (terza colonna)
                try:
                    # Converte esplicitamente in float il valore mean_CNIs
                    CNI_value = float(row[2])
                    data_CNI.append(CNI_value)
                except (ValueError, TypeError) as e:
                    # print(f"[DEBUG] Errore conversione valore CNI {row[2]}: {e}")
                    continue
        # print(f"[DEBUG] Valori CNI filtrati e convertiti per mese {mese}: {data_CNI}")
    
    # Se abbiamo dati CNI, li moltiplichiamo per l'energia non incentivata
    if data_CNI and ni:
        # print(f"[DEBUG] Calcolo risultato CNI - data_CNI ha {len(data_CNI)} elementi")
        # Se data_CNI è una lista di valori, prendiamo la media o il primo valore
        # In questo caso prendiamo la media dei valori CNI del mese
        media_CNI = sum(data_CNI) / len(data_CNI) if data_CNI else 0
        # print(f"[DEBUG] Media CNI calcolata: {media_CNI}")
        ni_iter = ni if hasattr(ni, '__iter__') else [ni]
        ni_iter_filtrato = [float(x) for x in ni_iter if x is not None]
        risultato_CNI = [float(ni_val) * media_CNI for ni_val in ni_iter_filtrato]
        # print(f"[DEBUG] Risultato CNI prima della divisione per 1000: {risultato_CNI}")
        # Dividiamo ogni valore del risultato per 1000
        risultato_CNI = [valore / 1000 for valore in risultato_CNI]
        # print(f"[DEBUG] Risultato CNI finale dopo divisione per 1000: {risultato_CNI}")
    else:
         risultato_CNI = []
    if not risultato_CNI:
        risultato_CNI = [None]
    
    media_CNI_finale = sum(data_CNI) / len(data_CNI) if data_CNI else 0
    # print(f"[DEBUG] Preparazione risposta JSON con {len(risultato_CNI)} elementi nel risultato")
    
    return JsonResponse({
        'success': True,
        'data': risultato_CNI,
        'anno': anno,
        'mese': mese,
        'impianto': nickname,
        'media_CNI_mensile': media_CNI_finale,
        'num_record_CNI': len(data_CNI)
    })




def datiFatturazioneTFO(request, nickname, anno, mese):
    """
    Questa funzione restituisce i dati di fatturazione TFO per un impianto specifico,
    anno e mese. Il nickname viene passato come parametro URL e deve essere convertito
    per corrispondere alla tabella corretta del database.
    """
    
    # Stampa di debug per i parametri ricevuti
    # print(f"[DEBUG] datiFatturazioneTFO chiamata con parametri: nickname={nickname}, anno={anno}, mese={mese}")
    
    # Mappa di conversione dai nickname ricevuti ai nomi delle tabelle nel database
    # Il nickname ricevuto può essere diverso dal nome della tabella nel database
    # IMPORTANTE: I nickname devono corrispondere esattamente a quelli inviati dal JavaScript
    # Se arriva "ponte_giurino" dal frontend, deve essere mappato qui con lo stesso formato
    nickname_to_table = {
        "petilia_bf_partitore": "corrispettivi_energia_BA",
        "petilia_bf_partitore": "corrispettivi_energia_BA",  # Aggiunto in minuscolo per compatibilità
        
        "Ionico Foresta": "corrispettivi_energia_I1",
        "ionico_foresta": "corrispettivi_energia_I1",  # Aggiunto con underscore per compatibilità
        
        "San Teodoro": "corrispettivi_energia_PE",
        "san_teodoro": "corrispettivi_energia_PE",  # Aggiunto con underscore per compatibilità
        
        "Ponte Giurino": "corrispettivi_energia_PG",
        "ponte_giurino": "corrispettivi_energia_PG",  # Aggiunto con underscore per compatibilità - questo risolve l'errore
        
    }
    
    # print(f"[DEBUG] Nickname supportati: {list(nickname_to_table.keys())}")
    
    # Verifica che il nickname sia valido e lo converte alla tabella corrispondente
    # Ora la ricerca includerà anche le varianti con underscore e minuscole
    if nickname not in nickname_to_table:
        # print(f"[DEBUG] ERRORE: Nickname {nickname} non trovato nella mappa di conversione")
        return JsonResponse({
            'success': False,
            'error': f'Nickname {nickname} non valido. Valori accettati: {list(nickname_to_table.keys())}'
        })
    
    # Ottieni il nome della tabella corrispondente al nickname convertito
    table_name = nickname_to_table[nickname]
    # print(f"[DEBUG] Nickname '{nickname}' convertito alla tabella: {table_name}")
    
    # Esegui la query per la tabella specifica
    with connection.cursor() as cursor:
        query = f"""
            SELECT 
                CAST(strftime('%%Y', "Data di competenza") AS INTEGER) AS anno,
                CAST(strftime('%%m', "Data di competenza") AS INTEGER) AS mese,
                SUM("Omnicomprensiva") AS valore
            FROM "{table_name}"
            WHERE CAST(strftime('%%Y', "Data di competenza") AS INTEGER) = %s 
                AND CAST(strftime('%%m', "Data di competenza") AS INTEGER) = %s
            GROUP BY anno, mese
            ORDER BY anno, mese;
        """
        # print(f"[DEBUG] Esecuzione query SQL: {query}")
        # print(f"[DEBUG] Parametri query: anno={anno}, mese={mese}")
        
        cursor.execute(query, [anno, mese])
        rows = cursor.fetchall()
        
        # print(f"[DEBUG] Query eseguita, trovati {len(rows)} record")
        if rows:
            pass

    # Estrai solo i valori numerici per la risposta data (direttamente da rows)
    data_values = [float(r[2]) if r[2] is not None else None for r in rows]
    if not data_values:
        data_values = [None]
    # print(f"[DEBUG] Lista valori finali da restituire: {data_values}")
    
    return JsonResponse({
        'success': True,
        'data': data_values,  # Modificato per restituire solo i valori come le altre funzioni
        'anno': anno,
        'mese': mese,
        'impianto': nickname
    })
    
    

def datiEnergiaNonIncentivata(request, nickname, anno, mese):
   
    # Stampa di debug per i parametri ricevuti
    # print(f"[DEBUG] datiEnergiaNonIncentivata chiamata con parametri: nickname={nickname}, anno={anno}, mese={mese}")
    
   
    nickname_to_table = {
        "petilia_bf_partitore":    "corrispettivi_energia_BA",
        "petilia_bf_partitore": "corrispettivi_energia_BA",  # Aggiunto in minuscolo per compatibilità
        
        "Ionico Foresta": "corrispettivi_energia_I1",
        "ionico_foresta": "corrispettivi_energia_I1",  # Aggiunto con underscore per compatibilità
        
        "San Teodoro": "corrispettivi_energia_PE",
        "san_teodoro": "corrispettivi_energia_PE",  # Aggiunto con underscore per compatibilità
        
        "Ponte Giurino": "corrispettivi_energia_PG",
        "ponte_giurino": "corrispettivi_energia_PG",  # Aggiunto con underscore per compatibilità - questo risolve l'errore
        
    }
    
    # print(f"[DEBUG] Nickname supportati: {list(nickname_to_table.keys())}")
    
    # Verifica che il nickname sia valido e lo converte alla tabella corrispondente
    # Ora la ricerca includerà anche le varianti con underscore e minuscole
    if nickname not in nickname_to_table:
        # print(f"[DEBUG] ERRORE: Nickname {nickname} non trovato nella mappa di conversione")
        return JsonResponse({
            'success': False,
            'error': f'Nickname {nickname} non valido. Valori accettati: {list(nickname_to_table.keys())}'
        })
    
    # Ottieni il nome della tabella corrispondente al nickname convertito
    table_name = nickname_to_table[nickname]
    # print(f"[DEBUG] Nickname '{nickname}' convertito alla tabella: {table_name}")
    
    result = {}
    # Esegui la query per la tabella specifica
    with connection.cursor() as cursor:
        query = f"""
            SELECT 
                CAST(strftime('%%Y', "Data di competenza") AS INTEGER) AS anno,
                CAST(strftime('%%m', "Data di competenza") AS INTEGER) AS mese,
                SUM("Non incentivata") AS valore
            FROM "{table_name}"
            WHERE CAST(strftime('%%Y', "Data di competenza") AS INTEGER) = %s 
                AND CAST(strftime('%%m', "Data di competenza") AS INTEGER) = %s
            GROUP BY anno, mese
            ORDER BY anno, mese;
        """
        # print(f"[DEBUG] Esecuzione query SQL: {query}")
        # print(f"[DEBUG] Parametri query: anno={anno}, mese={mese}")
        
        cursor.execute(query, [anno, mese])
        rows = cursor.fetchall()
        
        # print(f"[DEBUG] Query eseguita, trovati {len(rows)} record")
        if rows:
            pass

    # Estrai solo i valori numerici per la risposta data (direttamente da rows)
    data_values = [float(r[2]) if r[2] is not None else None for r in rows]
    if not data_values:
        data_values = [None]
    # print(f"[DEBUG] Lista valori finali da restituire: {data_values}")
    
    return JsonResponse({
        'success': True,
        'data': data_values,  # Modificato per restituire solo i valori come le altre funzioni
        'anno': anno,
        'mese': mese,
        'impianto': nickname
    })
    
    
    
    
    

def datiRiepilogoPagamenti(request, nickname, anno, mese):
	"""
	Apre il file Excel associato allo specifico impianto e restituisce i valori
	del foglio 2 (indice 1) dalle colonne W (data) e X (valore), filtrati per
	anno e mese richiesti. Per i file che terminano con "Ionico Energy Uno TF.xlsx"
	utilizza le colonne Z (data) e AA (valore). Ritorna una lista di valori numerici.
	
	IMPORTANTE: I valori nelle tabelle Excel sono considerati due mesi avanti rispetto 
	all'effettivo, quindi per visualizzare i dati del mese richiesto, cerchiamo i dati 
	che sono registrati due mesi dopo nella tabella Excel.
	"""
	# print(f"[DEBUG] datiRiepilogoPagamenti - Richiesta per nickname: {nickname}, anno: {anno}, mese: {mese}")
	
	# Calcola il mese e anno da cercare nella tabella Excel (due mesi avanti)
	# Se il mese richiesto è 11 (novembre), cerco gennaio dell'anno successivo
	# Se il mese richiesto è 12 (dicembre), cerco febbraio dell'anno successivo
	mese_excel = mese + 2
	anno_excel = anno
	
	if mese_excel > 12:
		# Se superiamo dicembre, passiamo all'anno successivo
		mese_excel = mese_excel - 12
		anno_excel = anno + 1
	
	# print(f"[DEBUG] Mese richiesto: {mese}/{anno}, cercherò nella tabella Excel: {mese_excel}/{anno_excel}")
	
	# Cerca i file cashflow collegati all'impianto tramite nickname (case-insensitive)
	cashflow_qs = Cashflow.objects.filter(impianto__nickname__iexact=nickname)
	# print(f"[DEBUG] Trovati {cashflow_qs.count()} file cashflow per l'impianto '{nickname}'")
	
	if not cashflow_qs.exists():
		# print(f"[ERROR] Nessun file cashflow configurato per l'impianto '{nickname}'")
		return JsonResponse({
			'success': False,
			'error': f"Nessun file cashflow configurato per l'impianto '{nickname}'"
		})

	valori = []
	for i, cf in enumerate(cashflow_qs):
		# print(f"[DEBUG] Elaborazione file {i+1}/{cashflow_qs.count()}: {cf.percorso}")
		
		# Costruisce il percorso completo: se 'percorso' è relativo, premette l'unit
		percorso_completo = cf.percorso if os.path.isabs(cf.percorso) else os.path.join(cf.unit, cf.percorso)
		# print(f"[DEBUG] Percorso completo file: {percorso_completo}")
		
		if not os.path.exists(percorso_completo):
			# print(f"[WARNING] File non trovato: {percorso_completo}")
			continue
			
		try:
			# print(f"[DEBUG] Tentativo di lettura del file Excel...")
			
			# Determina le colonne da usare in base al nome del file
			# Per file che finiscono con "Ionico Energy Uno TF.xlsx": colonne Z e AA (indici 25 e 26)
			# Per tutti gli altri file: colonne W e X (indici 22 e 23)
			if percorso_completo.endswith("Ionico Energy Uno TF.xlsx"):
				colonne_da_leggere = [25, 26]  # Colonne Z e AA (0-based: Z=25, AA=26)
				# print(f"[DEBUG] File 'Ionico Energy Uno TF.xlsx' rilevato, utilizzo colonne Z e AA")
			else:
				colonne_da_leggere = [22, 23]  # Colonne W e X (0-based: W=22, X=23)
				# print(f"[DEBUG] File standard, utilizzo colonne W e X")
			
			# Foglio 2 -> indice 1
			df = pd.read_excel(percorso_completo, sheet_name=1, usecols=colonne_da_leggere)
			df.columns = ['data', 'valore']
			# print(f"[DEBUG] Letto DataFrame con {len(df)} righe dal foglio 2")
			
			df = df.dropna(subset=['data', 'valore'])
			# print(f"[DEBUG] Dopo rimozione righe vuote: {len(df)} righe")
			
			df['data'] = pd.to_datetime(df['data'], errors='coerce')
			df = df.dropna(subset=['data'])
			# print(f"[DEBUG] Dopo conversione date valide: {len(df)} righe")
			
			# Filtra per anno e mese calcolati (due mesi avanti rispetto alla richiesta)
			df = df[(df['data'].dt.year == int(anno_excel)) & (df['data'].dt.month == int(mese_excel))]
			# print(f"[DEBUG] Dopo filtro per anno {anno_excel} e mese {mese_excel}: {len(df)} righe")
			
			df['valore'] = pd.to_numeric(df['valore'], errors='coerce')
			df = df.dropna(subset=['valore'])
			# print(f"[DEBUG] Dopo conversione valori numerici: {len(df)} righe")
			
			valori_file = [float(v) for v in df['valore'].tolist()]
			# print(f"[DEBUG] Valori estratti dal file: {valori_file}")
			valori.extend(valori_file)
			
		except Exception as e:
			# print(f"[ERROR] Errore durante la lettura del file {percorso_completo}: {str(e)}")
			# Se un file non è leggibile, passa al successivo
			continue
	
	# print(f"[DEBUG] Totale valori raccolti da tutti i file: {len(valori)} - {valori}")
	
	if not valori:
		valori = [None]
	return JsonResponse({
		'success': True,
		'data': valori,
		'anno': anno,  # Restituiamo l'anno originariamente richiesto
		'mese': mese,  # Restituiamo il mese originariamente richiesto
		'impianto': nickname,
		'anno_excel_consultato': anno_excel,  # Info aggiuntiva per debug
		'mese_excel_consultato': mese_excel   # Info aggiuntiva per debug
	})

def percentualedicontrollo(request, nickname, anno, mese):
    # print(f"[DEBUG] Inizio calcolo percentuale di controllo per impianto: {nickname}, anno: {anno}, mese: {mese}")
   
    # # Il totale corrispettivi è dato dalla somma dei dati TFO e dei dati CNI
    # # Otteniamo i dati TFO (corrispettivi incentivo)
    # print(f"[DEBUG] Recupero dati TFO...")
    response_tfo = datiTFO(request, nickname, anno, mese)
    tfo_data = response_tfo.content.decode('utf-8')
    tfo_json = json.loads(tfo_data)
    valori_tfo = tfo_json.get('data', [])
    # print(f"[DEBUG] Dati TFO ottenuti: {valori_tfo}")
    
    # # Otteniamo i dati CNI
    # print(f"[DEBUG] Recupero dati CNI...")
    response_CNI = datiCNI(request, nickname, anno, mese)
    CNI_data = response_CNI.content.decode('utf-8')
    CNI_json = json.loads(CNI_data)
    valori_CNI = CNI_json.get('data', [])
    # print(f"[DEBUG] Dati CNI ottenuti: {valori_CNI}")
    
    # Calcoliamo la somma totale dei corrispettivi
    somma_tfo = sum(valori_tfo) if valori_tfo else 0
    somma_CNI = sum(valori_CNI) if valori_CNI else 0
    totalecorrispettivi = somma_tfo + somma_CNI
    # print(f"[DEBUG] Somma TFO: {somma_tfo}")
    # print(f"[DEBUG] Somma CNI: {somma_CNI}")
    # print(f"[DEBUG] Totale corrispettivi: {totalecorrispettivi}")
    
    
    
    # Otteniamo i dati di riepilogo pagamenti
    # print(f"[DEBUG] Recupero dati riepilogo pagamenti...")
    response_pagamenti = datiRiepilogoPagamenti(request, nickname, anno, mese)
    pagamenti_data = response_pagamenti.content.decode('utf-8')
    pagamenti_json = json.loads(pagamenti_data)
    valori_pagamenti = pagamenti_json.get('data', [])
    # print(f"[DEBUG] Dati pagamenti ottenuti: {valori_pagamenti}")
    
    # Calcoliamo la somma dei pagamenti
    somma_pagamenti = sum(valori_pagamenti) if valori_pagamenti else 0
    # print(f"[DEBUG] Somma pagamenti: {somma_pagamenti}")
    
    # Calcoliamo la percentuale: (datiRiepilogoPagamenti - totalecorrispettivi) / totalecorrispettivi * 100
    # Per evitare divisione per zero, verifichiamo che totalecorrispettivi sia diverso da 0
    if (not valori_tfo and not valori_CNI and not valori_pagamenti):
        percentuale = None
    elif totalecorrispettivi != 0:
        percentuale = (somma_pagamenti - totalecorrispettivi)
    else:
        percentuale = None
    
    # print(f"[DEBUG] Percentuale finale calcolata: {percentuale}")
    
    return JsonResponse({
        'success': True,
        'data': percentuale,
        'anno': anno,
        'mese': mese,
        'impianto': nickname
    })


@csrf_exempt
def salva_commento_tabella(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    try:
        body = request.body.decode('utf-8') if request.body else '{}'
        payload = json.loads(body)
        nickname = payload.get('nickname')
        anno = int(payload.get('anno')) if payload.get('anno') is not None else None
        mese = int(payload.get('mese')) if payload.get('mese') is not None else None
        testo = (payload.get('testo') or '').strip()
        stato = (payload.get('stato') or '')

        if not nickname or anno is None or mese is None:
            return JsonResponse({'success': False, 'error': 'Parametri mancanti'}, status=400)

        try:
            impianto = Impianto.objects.get(nickname__iexact=nickname)
        except Impianto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Impianto non trovato'}, status=404)

        obj, created = commento_tabellacorrispettivi.objects.update_or_create(
            impianto=impianto,
            anno=anno,
            mese=mese,
            defaults={'testo': testo, 'stato': stato}
        )

        return JsonResponse({'success': True, 'created': created, 'id': obj.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_commento_tabella(request, nickname, anno, mese):
    try:
        obj = commento_tabellacorrispettivi.objects.filter(
            impianto__nickname__iexact=nickname,
            anno=anno,
            mese=mese
        ).first()
        if not obj:
            return JsonResponse({'success': True, 'testo': '', 'stato': ''})
        return JsonResponse({'success': True, 'testo': obj.testo, 'stato': obj.stato})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# # =========================
# Endpoint ANNUALI (ottimizzazione performance)
# =========================

def _mesi_1_12():
    return list(range(1, 13))


def energiakwh_annuale(request, nickname, anno):
    """
    Restituisce la somma mensile (1..12) dell'energia prodotta (kWh) come mappa mese->valore.
    { "per_month": {1: numero, 2: numero, ...} }
    """
    per_month = {m: 0 for m in _mesi_1_12()}
    qs = regsegnanti.objects.filter(
        anno=anno,
        contatore__impianto_nickname=nickname,
        mese__in=_mesi_1_12()
    ).values('mese').annotate(total=models.Sum('prod_campo'))
    for row in qs:
        m = row.get('mese')
        per_month[int(m)] = float(row.get('total') or 0)
    return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})


def datiTFO_annuale(request, nickname, anno):
    """
    Somma mensile di min(prod*0.98, imm) * 0.21
    """
    # print(f"[DEBUG] datiTFO_annuale - Richiesta per nickname: {nickname}, anno: {anno}")
    
    per_month = {m: 0.0 for m in _mesi_1_12()}
    # print(f"[DEBUG] Inizializzato dizionario per_month: {per_month}")
    
    # Recupero tutti i record dell'anno e calcolo per mese
    # Recupero i dati di produzione (prod_campo) per tutti i mesi dell'anno
    records_prod = regsegnanti.objects.filter(
        anno=anno,
        contatore__impianto_nickname=nickname,
        mese__in=_mesi_1_12()
    ).values_list('mese', 'prod_campo')
    
    # Recupero i dati di immissione (imm_campo) per tutti i mesi dell'anno
    records_imm = regsegnanti.objects.filter(
        anno=anno,
        contatore__impianto_nickname=nickname,
        mese__in=_mesi_1_12()
    ).values_list('mese', 'imm_campo')
    
    # print(f"[DEBUG] Trovati {len(records_prod)} record di produzione per l'anno {anno}")
    # print(f"[DEBUG] Trovati {len(records_imm)} record di immissione per l'anno {anno}")
    
    # Creo dizionari per organizzare i dati per mese
    prod_per_mese = {}
    imm_per_mese = {}
    
    # Organizzo i dati di produzione per mese
    for mese, prod in records_prod:
        if mese not in prod_per_mese:
            prod_per_mese[mese] = []
        if prod is not None:
            prod_per_mese[mese].append(float(prod))
    
    # Organizzo i dati di immissione per mese
    for mese, imm in records_imm:
        if mese not in imm_per_mese:
            imm_per_mese[mese] = []
        if imm is not None:
            imm_per_mese[mese].append(float(imm))
    
    # Calcolo il valore TFO per ogni mese
    for mese in _mesi_1_12():
        # print(f"[DEBUG] Elaborazione mese {mese} -anno- {anno}")
        
        # Sommo tutti i valori di produzione per il mese
        prod_totale = sum(prod_per_mese.get(mese, []))
        # Sommo tutti i valori di immissione per il mese
        imm_totale = sum(imm_per_mese.get(mese, []))
        
        # print(f"[DEBUG] Mese {mese}: prod_totale={prod_totale}, imm_totale={imm_totale}")
        
        if prod_totale > 0 and imm_totale > 0:
            try:
                prod_corr = prod_totale * 0.98
                val = min(prod_corr, imm_totale) * 0.21
                per_month[mese] = val
                # print(f"[DEBUG] Calcolato per mese {mese} -anno- {anno}: prod_corr={prod_corr}, val={val}")
            except (ValueError, TypeError) as e:
                # print(f"[DEBUG] Errore conversione numerica per mese {mese}: {e}")
                continue
        else:
            # print(f"[DEBUG] Mese {mese}: dati insufficienti (prod_totale={prod_totale}, imm_totale={imm_totale})")
            pass
    
    # print(f"[DEBUG] Risultato finale per_month: {per_month}")
    return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})


def _map_nickname_to_table(nickname):
    # stessa mappa usata negli endpoint mensili
    nickname_to_table = {
        "petilia_bf_partitore": "corrispettivi_energia_BA",
        "petilia_bf_partitore": "corrispettivi_energia_BA",
        "Ionico Foresta": "corrispettivi_energia_I1",
        "ionico_foresta": "corrispettivi_energia_I1",
        "San Teodoro": "corrispettivi_energia_PE",
        "san_teodoro": "corrispettivi_energia_PE",
        "Ponte Giurino": "corrispettivi_energia_PG",
        "ponte_giurino": "corrispettivi_energia_PG",
    }
    return nickname_to_table.get(nickname)


def datiFatturazioneTFO_annuale(request, nickname, anno):
    """
    Funzione che recupera i dati di fatturazione TFO per un intero anno.
    Questa funzione esegue una query SQL per sommare i valori della colonna "Omnicomprensiva"
    raggruppati per mese per l'anno specificato.
    """
    # print(f"[DEBUG] datiFatturazioneTFO_annuale - Richiesta per nickname: {nickname}, anno: {anno}")
    
    # Ottieni il nome della tabella corrispondente al nickname
    table_name = _map_nickname_to_table(nickname)
    # print(f"[DEBUG] Nickname '{nickname}' mappato alla tabella: {table_name}")
    
    if not table_name:
        # Se non esiste una tabella mappata per l'impianto, restituisci zeri per tutti i mesi
        per_month = {m: 0.0 for m in _mesi_1_12()}
        return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})
    
    # Inizializza il dizionario per i dati mensili (tutti i mesi da 1 a 12 con valore 0)
    per_month = {m: 0.0 for m in _mesi_1_12()}
    # print(f"[DEBUG] Inizializzato dizionario per_month: {per_month}")
    
    # Esegui la query per recuperare i dati annuali raggruppati per mese
    with connection.cursor() as cursor:
        query = f"""
            SELECT 
                CAST(strftime('%%m', "Data di competenza") AS INTEGER) AS mese,
                SUM("Omnicomprensiva") AS valore
            FROM "{table_name}"
            WHERE CAST(strftime('%%Y', "Data di competenza") AS INTEGER) = %s
            GROUP BY mese
            ORDER BY mese;
        """
        # print(f"[DEBUG] Esecuzione query SQL: {query}")
        # print(f"[DEBUG] Parametro query: anno={anno}")
        
        cursor.execute(query, [anno])
        rows = cursor.fetchall()
        
        # print(f"[DEBUG] Query eseguita, trovati {len(rows)} record")
        # print(f"[DEBUG] Risultati query: {rows}")
        
        # Popola il dizionario per_month con i valori trovati
        for m, val in rows:
            valore_convertito = float(val or 0)
            per_month[int(m)] = valore_convertito
            # print(f"[DEBUG] Mese {m}: valore {val} -> convertito a {valore_convertito}")
    
    # print(f"[DEBUG] Dizionario finale per_month: {per_month}")
    
    return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})

def datiEnergiaNonIncentivata_annuale(request, nickname, anno):
    table_name = _map_nickname_to_table(nickname)
    if not table_name:
        # Se non esiste una tabella mappata per l'impianto, restituisci zeri per tutti i mesi
        per_month = {m: 0.0 for m in _mesi_1_12()}
        return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})
    per_month = {m: 0.0 for m in _mesi_1_12()}
    with connection.cursor() as cursor:
        query = f"""
            SELECT 
                CAST(strftime('%%m', "Data di competenza") AS INTEGER) AS mese,
                SUM("Non incentivata") AS valore
            FROM "{table_name}"
            WHERE CAST(strftime('%%Y', "Data di competenza") AS INTEGER) = %s
            GROUP BY mese
            ORDER BY mese;
        """
        cursor.execute(query, [anno])
        rows = cursor.fetchall()
        for m, val in rows:
            per_month[int(m)] = float(val or 0)
    return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})


def datiRiepilogoPagamenti_annuale(request, nickname, anno):
    # Ricerca file cashflow come in versione mensile
    # print(f"[DEBUG] datiRiepilogoPagamenti_annuale - Inizio per nickname: {nickname}, anno: {anno}")
    
    cashflow_qs = Cashflow.objects.filter(impianto__nickname__iexact=nickname)
    # print(f"[DEBUG] Trovati {cashflow_qs.count()} file cashflow per l'impianto '{nickname}'")
    
    if not cashflow_qs.exists():
        # print(f"[DEBUG] Nessun file cashflow trovato per l'impianto '{nickname}'")
        return JsonResponse({'success': False, 'error': f"Nessun file cashflow configurato per l'impianto '{nickname}'"})

    per_month = {m: 0.0 for m in _mesi_1_12()}
    # print(f"[DEBUG] Inizializzato dizionario per_month: {per_month}")
    
    for cf in cashflow_qs:
        percorso_completo = cf.percorso if os.path.isabs(cf.percorso) else os.path.join(cf.unit, cf.percorso)
        # print(f"[DEBUG] Elaborazione file cashflow: {percorso_completo}")
        
        if not os.path.exists(percorso_completo):
            # print(f"[DEBUG] File non trovato: {percorso_completo}")
            continue
            
        try:
            # Colonne dipendenti dal nome file
            if percorso_completo.endswith("Ionico Energy Uno TF.xlsx"):
                usecols = [25, 26]
                # print(f"[DEBUG] File Ionico Energy Uno TF.xlsx - usando colonne: {usecols}")
            else:
                usecols = [22, 23]
                # print(f"[DEBUG] File standard - usando colonne: {usecols}")
                
            df = pd.read_excel(percorso_completo, sheet_name=1, usecols=usecols)
            # print(f"[DEBUG] Letto Excel con {len(df)} righe")
            
            df.columns = ['data', 'valore']
            df = df.dropna(subset=['data', 'valore'])
            # print(f"[DEBUG] Dopo rimozione righe vuote: {len(df)} righe")
            
            df['data'] = pd.to_datetime(df['data'], format='%Y-%m-%d', errors='coerce')
            df = df.dropna(subset=['data'])
            # print(f"[DEBUG] Dopo conversione date: {len(df)} righe")
            
            df['valore'] = pd.to_numeric(df['valore'], errors='coerce')
            df = df.dropna(subset=['valore'])
            # print(f"[DEBUG] Dopo conversione valori numerici: {len(df)} righe")

            # Pre-calcolo anno/mese del file
            df['anno'] = df['data'].dt.year.astype(int)
            df['mese'] = df['data'].dt.month.astype(int)
            # print(f"[DEBUG] Aggiunto anno e mese al DataFrame")

            # Per ogni mese richiesto, cercare due mesi avanti
            for mese in _mesi_1_12():
                mese_excel = mese + 2
                anno_excel = anno
                if mese_excel > 12:
                    mese_excel -= 12
                    anno_excel = anno + 1
                    
                # print(f"[DEBUG] Mese {mese}: cercando nel file anno {anno_excel}, mese {mese_excel}")
                
                mask = (df['anno'] == int(anno_excel)) & (df['mese'] == int(mese_excel))
                righe_trovate = mask.sum()
                
                if mask.any():
                    valore_somma = float(df.loc[mask, 'valore'].sum())
                    per_month[mese] += valore_somma
                    # print(f"[DEBUG] Mese {mese}: trovate {righe_trovate} righe, somma: {valore_somma}, totale mese: {per_month[mese]}")
                else:
                    print(f"[DEBUG] Mese {mese}: nessuna riga trovata per anno {anno_excel}, mese {mese_excel}")
                    
        except Exception as e:
            # print(f"[DEBUG] Errore durante elaborazione file {percorso_completo}: {str(e)}")
            continue

    # print(f"[DEBUG] Dizionario finale per_month: {per_month}")
    return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})


def datiCNI_annuale(request, nickname, anno):
    """
    Calcolo mensile del CNI: somma_i( (prod-imm, con gestione None) * media_PUN_mensile / 1000 )
    """
    # Preleva tutti i record dell'anno
    records = regsegnanti.objects.filter(
        anno=anno,
        contatore__impianto_nickname=nickname,
        mese__in=_mesi_1_12()
    ).values_list('mese', 'prod_campo', 'imm_campo')

    # Calcolo energia non incentivata per mese (somma delle differenze gestendo None come in datiNI)
    ni_per_month_list = {m: [] for m in _mesi_1_12()}
    for mese, prod, imm in records:
        mese = int(mese)
        if prod is not None and imm is not None:
            ni_val = float(prod) - float(imm)
        elif prod is not None and imm is None:
            ni_val = float(prod)
        elif prod is None and imm is not None:
            ni_val = -float(imm)
        else:
            ni_val = 0.0
        ni_per_month_list[mese].append(ni_val)

    # Preleva media_puns per ciascun mese dell'anno richiesto
    media_pun_per_month = {m: 0.0 for m in _mesi_1_12()}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CAST(strftime('%%m', timestamp) AS INTEGER) AS mese, mean_puns
            FROM "Prezzi medi mensili"
            WHERE strftime('%%Y', timestamp) = %s
            ORDER BY timestamp
            """,
            [str(anno)]
        )
        rows = cursor.fetchall()
        # possono esserci più righe per mese, calcoliamo media per sicurezza
        temp = {}
        for mese, val in rows:
            mese = int(mese)
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            temp.setdefault(mese, []).append(v)
        for m, vals in temp.items():
            media_pun_per_month[m] = sum(vals) / len(vals) if vals else 0.0

    # Calcolo finale per mese
    per_month = {m: 0.0 for m in _mesi_1_12()}
    for m in _mesi_1_12():
        media = media_pun_per_month.get(m, 0.0) or 0.0
        totale = sum(ni_val * media / 1000.0 for ni_val in ni_per_month_list[m])
        per_month[m] = float(totale)

    return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})


def percentualedicontrollo_annuale(request, nickname, anno):
    """
    Differenza mensile: incassi - (TFO + CNI). Restituisce mappa mese->valore.
    """
    # Riutilizzo funzioni annuali interne per evitare I/O multiplo
    tfo = json.loads(datiTFO_annuale(request, nickname, anno).content.decode('utf-8')).get('per_month', {})
    cni = json.loads(datiCNI_annuale(request, nickname, anno).content.decode('utf-8')).get('per_month', {})
    inc = json.loads(datiRiepilogoPagamenti_annuale(request, nickname, anno).content.decode('utf-8')).get('per_month', {})

    per_month = {m: 0.0 for m in _mesi_1_12()}
    for m in _mesi_1_12():
        somma_corr = float(tfo.get(str(m), tfo.get(m, 0))) + float(cni.get(str(m), cni.get(m, 0)))
        somma_inc = float(inc.get(str(m), inc.get(m, 0)))
        per_month[m] = somma_inc - somma_corr

    return JsonResponse({'success': True, 'per_month': per_month, 'anno': anno, 'impianto': nickname})


def get_commenti_annuali(request, nickname, anno):
    """
    Restituisce tutti i commenti per l'anno: { mese: {testo, stato} }
    Se la tabella dei commenti non esiste ancora, restituisce struttura vuota.
    """
    comments = {m: {'testo': '', 'stato': ''} for m in _mesi_1_12()}
    try:
        items = commento_tabellacorrispettivi.objects.filter(
            impianto__nickname__iexact=nickname,
            anno=anno
        )
        for it in items:
            try:
                comments[int(it.mese)] = {'testo': it.testo or '', 'stato': it.stato or ''}
            except Exception:
                continue
    except Exception:
        # Tabella mancante o altro errore DB: ritorna struttura vuota per non interrompere il frontend
        pass
    return JsonResponse({'success': True, 'comments_by_month': comments, 'anno': anno, 'impianto': nickname})





# tabella misure 
def table_misure(request, anno_nickname):
	"""
	Endpoint: /corrispettivi/api/misure/<anno>_<nickname>/
	Restituisce i dati mensili (1..12) aggregati per impianto come array "TableMisure".
	Ogni elemento contiene: mese, prod_campo, imm_campo, prel_campo, prod_ed, imm_ed, prel_ed, prod_gse, imm_gse
	"""
	try:
		sep_idx = anno_nickname.find('_')
		if sep_idx == -1:
			return JsonResponse({'success': False, 'error': "Formato non valido. Usa '<anno>_<nickname>'"}, status=400)
		anno_str = anno_nickname[:sep_idx]
		nickname = anno_nickname[sep_idx + 1:]
		anno = int(anno_str)
	except Exception:
		return JsonResponse({'success': False, 'error': 'Parametri non validi'}, status=400)

	mesi = list(range(1, 13))

	# Struttura base con zeri
	per_mese = {
		m: {
			'mese': m,
			'prod_campo': 0.0,
			'imm_campo': 0.0,
			'prel_campo': 0.0,
			'prod_ed': 0.0,
			'imm_ed': 0.0,
			'prel_ed': 0.0,
			'prod_gse': 0.0,
			'imm_gse': 0.0,
		}
		for m in mesi
	}

	# Aggregazione per mese su tutti i contatori dell'impianto
	qs = (
		regsegnanti.objects
			.filter(anno=anno, contatore__impianto_nickname=nickname, mese__in=mesi)
			.values('mese')
			.annotate(
				prod_campo=models.Sum('prod_campo'),
				imm_campo=models.Sum('imm_campo'),
				prel_campo=models.Sum('prel_campo'),
				prod_ed=models.Sum('prod_ed'),
				imm_ed=models.Sum('imm_ed'),
				prel_ed=models.Sum('prel_ed'),
				prod_gse=models.Sum('prod_gse'),
				imm_gse=models.Sum('imm_gse'),
			)
	)

	for row in qs:
		m = int(row.get('mese'))
		if m in per_mese:
			per_mese[m]['prod_campo'] = float(row.get('prod_campo') or 0)
			per_mese[m]['imm_campo'] = float(row.get('imm_campo') or 0)
			per_mese[m]['prel_campo'] = float(row.get('prel_campo') or 0)
			per_mese[m]['prod_ed'] = float(row.get('prod_ed') or 0)
			per_mese[m]['imm_ed'] = float(row.get('imm_ed') or 0)
			per_mese[m]['prel_ed'] = float(row.get('prel_ed') or 0)
			per_mese[m]['prod_gse'] = float(row.get('prod_gse') or 0)
			per_mese[m]['imm_gse'] = float(row.get('imm_gse') or 0)

	# Ordina per mese 1..12
	items = [per_mese[m] for m in mesi]
	return JsonResponse({'success': True, 'TableMisure': items, 'anno': anno, 'impianto': nickname})





#funzioni per i consorzi
def datitabellaconsorzi(request, anno, nickname):
    """
    Restituisce i dati per le tabelle dei consorzi per TUTTI gli anni disponibili.
    Utilizza filtroimpianto per recuperare i dati di energia prodotta dal database.
    
    Per ogni anno (2021-2025), costruisce:
    
    Table1 (Periodo ottobre-marzo): 
        - Ottobre, Novembre, Dicembre dell'anno PRECEDENTE (anno-1)
        - Gennaio, Febbraio, Marzo dell'anno CORRENTE (anno)
    
    Table2 (Periodo aprile-settembre):
        - Aprile, Maggio, Giugno, Luglio, Agosto, Settembre dell'anno CORRENTE (anno)
    
    Ogni riga contiene: i (indice), mese, incassi, canone (11% degli incassi), prodotta_def (energia)
    
    Restituisce un dizionario con i dati organizzati per anno.
    """
    # print(f"[DEBUG] datitabellaconsorzi - nickname: {nickname}")
    
    # Lista degli anni da elaborare
    anni_da_elaborare = [2021, 2022, 2023, 2024, 2025]
    
    # Nomi dei mesi in italiano
    nomi_mesi = [
        'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
    ]
    
    # Dizionario che conterrà i dati per tutti gli anni
    data_per_anno = {}
    
    # ===== CICLA SU TUTTI GLI ANNI =====
    for anno_corrente in anni_da_elaborare:
        # print(f"[DEBUG] Elaborazione anno {anno_corrente}")
        
        anno_precedente = anno_corrente - 1
        
        # Recupera i dati di incassi per l'anno CORRENTE (dai file Excel)
        response_incassi_corrente = datiRiepilogoPagamenti_annuale(request, nickname, anno_corrente)
        incassi_data_corrente = json.loads(response_incassi_corrente.content.decode('utf-8'))
        incassi_per_mese_corrente = incassi_data_corrente.get('per_month', {})
        
        # Recupera i dati di incassi per l'anno PRECEDENTE (dai file Excel)
        response_incassi_precedente = datiRiepilogoPagamenti_annuale(request, nickname, anno_precedente)
        incassi_data_precedente = json.loads(response_incassi_precedente.content.decode('utf-8'))
        incassi_per_mese_precedente = incassi_data_precedente.get('per_month', {})
        
        # Recupera i dati di energia prodotta per l'anno CORRENTE usando filtroimpianto
        energia_per_mese_corrente = {}
        for mese in range(1, 13):
            qs = filtroimpianto(nickname, anno_corrente, mese)
            energia_totale = sum(float(record.prod_campo) for record in qs if record.prod_campo is not None)
            energia_per_mese_corrente[mese] = energia_totale
        
        # Recupera i dati di energia prodotta per l'anno PRECEDENTE usando filtroimpianto
        energia_per_mese_precedente = {}
        for mese in range(1, 13):
            qs = filtroimpianto(nickname, anno_precedente, mese)
            energia_totale = sum(float(record.prod_campo) for record in qs if record.prod_campo is not None)
            energia_per_mese_precedente[mese] = energia_totale
        
        # ===== TABLE 1: Ottobre-Marzo (anno fiscale) =====
        # IMPORTANTE: Gli incassi vengono registrati 2 mesi dopo la produzione
        # Quindi per visualizzare il mese X, devo prendere gli incassi di (X-2 mesi)
        
        table1 = []
        totale_incassi_t1 = 0
        totale_canone_t1 = 0
        totale_energia_t1 = 0
        
        # Ottobre, Novembre, Dicembre dell'anno PRECEDENTE (mesi 10, 11, 12)
        # Per questi mesi, devo prendere gli incassi di 2 mesi prima (Ago, Set, Ott dell'anno precedente)
        for mese_num in [10, 11, 12]:
            # Calcola il mese di incasso (2 mesi prima)
            mese_incasso = mese_num - 2
            anno_incasso = anno_precedente
            if mese_incasso <= 0:
                mese_incasso += 12
                anno_incasso = anno_precedente - 1
            
            # Prende gli incassi dal mese di incasso, ma l'energia dal mese di produzione
            if anno_incasso == anno_precedente - 1:
                # Per agosto e settembre, prendi dall'anno precedente-1
                response_incassi_anno_meno2 = datiRiepilogoPagamenti_annuale(request, nickname, anno_precedente - 1)
                incassi_data_anno_meno2 = json.loads(response_incassi_anno_meno2.content.decode('utf-8'))
                incassi_per_mese_anno_meno2 = incassi_data_anno_meno2.get('per_month', {})
                incassi = float(incassi_per_mese_anno_meno2.get(mese_incasso, incassi_per_mese_anno_meno2.get(str(mese_incasso), 0)))
            else:
                incassi = float(incassi_per_mese_precedente.get(mese_incasso, incassi_per_mese_precedente.get(str(mese_incasso), 0)))
            
            energia = float(energia_per_mese_precedente.get(mese_num, energia_per_mese_precedente.get(str(mese_num), 0)))
            canone = incassi * 0.11
            
            totale_incassi_t1 += incassi
            totale_canone_t1 += canone
            totale_energia_t1 += energia
            
            table1.append({
                'i': mese_num,
                'mese': f"{nomi_mesi[mese_num-1]} {anno_precedente}",  # Es: "Ottobre 2023"    
                'incassi': incassi,
                'canone': canone,
                'prodotta_def': energia
            })
        
        # Gennaio, Febbraio, Marzo dell'anno CORRENTE (mesi 1, 2, 3)
        # Per questi mesi, devo prendere gli incassi di 2 mesi prima (Nov, Dic dell'anno precedente, Gen dell'anno corrente)
        for mese_num in [1, 2, 3]:
            # Calcola il mese di incasso (2 mesi prima)
            mese_incasso = mese_num - 2
            anno_incasso = anno_corrente
            if mese_incasso <= 0:
                mese_incasso += 12
                anno_incasso = anno_precedente
            
            # Prende gli incassi dal mese di incasso, ma l'energia dal mese di produzione
            if anno_incasso == anno_precedente:
                incassi = float(incassi_per_mese_precedente.get(mese_incasso, incassi_per_mese_precedente.get(str(mese_incasso), 0)))
            else:
                incassi = float(incassi_per_mese_corrente.get(mese_incasso, incassi_per_mese_corrente.get(str(mese_incasso), 0)))
            
            energia = float(energia_per_mese_corrente.get(mese_num, energia_per_mese_corrente.get(str(mese_num), 0)))
            canone = incassi * 0.11
            
            totale_incassi_t1 += incassi
            totale_canone_t1 += canone
            totale_energia_t1 += energia
            
            table1.append({
                'i': mese_num,
                'mese': f"{nomi_mesi[mese_num-1]} {anno_corrente}",  # Es: "Gennaio 2024"
                'incassi': incassi,
                'canone': canone,
                'prodotta_def': energia
            })
        
        # Aggiunge riga totale per table1
        table1.append({
            'i': 13,
            'mese': 'Totale Periodo',
            'incassi': totale_incassi_t1,
            'canone': totale_canone_t1,
            'prodotta_def': totale_energia_t1
        })
        
        # ===== TABLE 2: Aprile-Settembre dell'anno CORRENTE =====
        # IMPORTANTE: Gli incassi vengono registrati 2 mesi dopo la produzione
        # Quindi per visualizzare il mese X, devo prendere gli incassi di (X-2 mesi)
        
        table2 = []
        totale_incassi_t2 = 0
        totale_canone_t2 = 0
        totale_energia_t2 = 0
        
        # Aprile, Maggio, Giugno, Luglio, Agosto, Settembre (mesi 4-9)
        # Per questi mesi, devo prendere gli incassi di 2 mesi prima (Feb, Mar, Apr, Mag, Giu, Lug dell'anno corrente)
        for mese_num in [4, 5, 6, 7, 8, 9]:
            # Calcola il mese di incasso (2 mesi prima)
            mese_incasso = mese_num - 2
            anno_incasso = anno_corrente
            if mese_incasso <= 0:
                mese_incasso += 12
                anno_incasso = anno_precedente
            
            # Prende gli incassi dal mese di incasso, ma l'energia dal mese di produzione
            if anno_incasso == anno_precedente:
                incassi = float(incassi_per_mese_precedente.get(mese_incasso, incassi_per_mese_precedente.get(str(mese_incasso), 0)))
            else:
                incassi = float(incassi_per_mese_corrente.get(mese_incasso, incassi_per_mese_corrente.get(str(mese_incasso), 0)))
            
            energia = float(energia_per_mese_corrente.get(mese_num, energia_per_mese_corrente.get(str(mese_num), 0)))
            canone = incassi * 0.11
            
            totale_incassi_t2 += incassi
            totale_canone_t2 += canone
            totale_energia_t2 += energia
            
            table2.append({
                'i': mese_num,
                'mese': f"{nomi_mesi[mese_num-1]} {anno_corrente}",  # Es: "Aprile 2024"
                'incassi': incassi,
                'canone': canone,
                'prodotta_def': energia
            })
        
        # Aggiunge riga totale per table2
        table2.append({
            'i': 14,
            'mese': 'Totale Periodo',
            'incassi': totale_incassi_t2,
            'canone': totale_canone_t2,
            'prodotta_def': totale_energia_t2
        })
        
        # Memorizza i dati per questo anno nel dizionario principale
        data_per_anno[str(anno_corrente)] = {
            'table1': table1,  # Ottobre-Marzo (anno fiscale)
            'table2': table2,  # Aprile-Settembre
            'anno': anno_corrente,
            'anno_precedente': anno_precedente
        }
        
        # print(f"[DEBUG] Anno {anno_corrente}: table1={len(table1)} righe, table2={len(table2)} righe")
    
    # print(f"[DEBUG] Totale anni elaborati: {len(data_per_anno)}")
    
    return JsonResponse({
        'success': True,
        'data_per_anno': data_per_anno,  # Dizionario con chiavi '2021', '2022', '2023', '2024', '2025'
        'anni_disponibili': anni_da_elaborare,
        'impianto': nickname
    })
