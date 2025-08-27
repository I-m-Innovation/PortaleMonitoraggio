from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated
from django.forms.models import model_to_dict
from AutomazioneDati.models import LetturaContatore, regsegnanti, Contatore
from MonitoraggioImpianti.models import Impianto
import numpy as np
import pandas as pd
from datetime import datetime,timedelta
from django.db.models import Max, Min
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import DatiMensiliTabella
import json
from django.db import models
from django.conf import settings
from PortaleCorrispettivi.APIgme import scarica_dati_pun_mensili, GME_FTP_USERNAME, GME_FTP_PASSWORD
import threading
from django.utils import timezone
import os
from PortaleCorrispettivi.models import Cashflow

import PortaleCorrispettivi.utils.functions as fn
from .models import *


# # FUNZIONE LETTURA DATI DIARI LETTURE
# def load_diariletture(diari_letture, sheet_letture):
# 	# CARICAMENTO DATI DIARI DELLE LETTURE
# 	df = pd.concat([pd.read_excel(diario, sheet_letture, parse_dates=False) for diario in diari_letture])
# 	# RIMOZIONE COLONNE VUOTE
# 	df = df.dropna(axis=1, how='all')
# 	# FORMATTAZIONE DATAFRAME IN NUMERI
# 	df.iloc[:, 1:] = df.iloc[:, 1:].apply(pd.to_numeric, errors='coerce')
# 	df = df.astype('float64', errors='ignore')

# 	df.reset_index(drop=True, inplace=True)
# 	df['mese'] = pd.to_datetime(df['mese'])
# 	df.reset_index(drop=True, inplace=True)
# 	return df


# FUNZIONE LETTURA DATI FILE CASHFLOW
def load_cashflow(diario_cashflow, sheet):
	# CARICO FILE DI CASH-FLOW (contiene i dati di tutti gli anni)
	df = pd.read_excel(diario_cashflow, sheet, index_col=None, header=[2, 3], na_values=[np.nan])
	df = df.dropna(axis=1, how='all')
	# NOME COLONNE NEL FILE EXCEL
	x = ['Fatturazione TFO', 'Fatturazione Energia non incentivata', 'Riepilogo pagamenti']

	# SISTEMAZIONE DATAFRAME IN BASE ALLA FORMATTAZIONE DELLA TABELLA EXCEL

	# il dataframe df2 contiene 2 righe di headers:
	# _____________________________________________________________________________________________________________________________________________________________________
	# |Fatturazione TFO | Fatturazione TFO       | Fatturazione Energia non incentivata | Fatturazione Energia non incentivata | Riepilogo pagamenti | Riepilogo pagamenti |
	# |Periodo          | Energia di competenza  | Periodo                              | Energia di competenza                | Periodo             | Incasso/pagamento   |
	# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

	# LISTA DI LISTE BOOLEANE CHE INDICANO IN df2 LA POSIZIONE DELLE COLONNE DATE IN x
	ll = [list(df.columns.get_level_values(0).str.contains(z)) for z in x]
	# LISTA BOOLEANA CHE INDICA LA POSIZIONE DI TUTTE LE COLONNE DATE IN x
	ll = list(map(any, zip(*ll)))

	# FORMATTAZIONE IN DATETIME DELLA SOTTOCOLONNA 'Periodo' RELATIVA ALLE COLONNE IN x
	df = df.loc[:, ll]
	for s in x:
		df[(s, 'Periodo')] = pd.to_datetime(df[(s, 'Periodo')], errors='coerce')
	df = df.dropna(subset=[('Fatturazione TFO', 'Periodo')])
	return df


# def tabellaconsorzi_data(anno_nickname):
# 	# DA URL ESTRAPOLO ANNO E NICKNAME DELLA REQUEST
# 	anno = int(anno_nickname.split('_', 1)[0])
# 	nickname = anno_nickname.split('_', 1)[1]

# 	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
# 	dz_impianto = model_to_dict(impianto)

# 	# EMPTY DATA PER IMPIANTI CHE NON SONO PONTE GIURINO
# 	if nickname != 'ponte_giurino':
# 		dict1 = {}
# 		dict2 = {}

# 		table_data = {
# 			'anno': anno,
# 			'table1': dict1,
# 			'table2': dict2,
# 			'info': dz_impianto,
# 		}
# 		return Response(table_data)

# 	# MESI-INTERVALLO DI PONTE GIURINO
# 	aprile = datetime(anno, 4, 1)
# 	settembre = datetime(anno, 9, 1)
# 	ottobre = datetime(anno - 1, 10, 1)

# 	# PERCORSO DEL DIARIO DELLE LETTURE PER L'ANNO RICHIESTO
# 	diari_letture = list(impianto.diarioletture_set.all())
# 	diari_letture = [str(diario) for diario in diari_letture if diario.anno >= anno - 1]
# 	letture_sheet = '07. Portale'

# 	# PERCORSO FILE DI CASH FLOW
# 	diario_cashflow = str(impianto.cashflow_set.all()[0])
# 	cash_sheet = 'Incassi GSE'

# 	try:
# 		DF1 = load_diariletture(diari_letture, letture_sheet)
# 		# CALCOLO ENERGIA INCENTIVATA DAL CORRISPETTIVO
# 		DF1['E_incentivata'] = DF1['aspettata_inc'] / 0.21

# 		DF2 = load_cashflow(diario_cashflow, cash_sheet)

# 		# SELEZIONE ANNO RICHIESTO DATI CASH FLOW
# 		DF2 = DF2[DF2[('Fatturazione TFO', 'Periodo')].dt.year >= anno - 1]
# 		DF2.reset_index(drop=True, inplace=True)

# 		# AGGIUNGO DATI DI CASH FLOW AL DATAFRAME PRINCIPALE
# 		DF1['fatturazione_tfo'] = DF2[('Fatturazione TFO', 'Energia di competenza')]
# 		DF1['fatturazione_non_inc'] = DF2[('Fatturazione Energia non incentivata', 'Energia di competenza')]
# 		DF1['incassi'] = DF2[('Riepilogo pagamenti', 'Incasso/pagamento')]

# 		DF1['canone'] = DF1['incassi'] * 0.11
# 		DF1 = DF1[['mese', 'prodotta_def', 'incassi', 'canone']]
# 		DF1_before = DF1[(DF1['mese'] < aprile) & (DF1['mese'] >= ottobre)].copy()
# 		DF1_after = DF1[(DF1['mese'] >= aprile) & (DF1['mese'] <= settembre)].copy()
# 		DF1_before.reset_index(drop=True, inplace=True)
# 		DF1_after.reset_index(drop=True, inplace=True)

# 		DF1_before['mese'] = DF1_before['mese'].dt.month_name(locale='it_IT.utf8') + '-' + DF1_before['mese'].dt.year.astype('string')
# 		DF1_before.loc['total'] = DF1_before.sum(numeric_only=True,)
# 		DF1_before.fillna({'mese':'Totale Periodo'},inplace=True)
# 		DF1_before.fillna('',inplace=True)

# 		DF1_after['mese'] = DF1_after['mese'].dt.month_name(locale='it_IT.utf8')  + '-' + DF1_after['mese'].dt.year.astype('string')
# 		DF1_after.loc['total'] = DF1_after.sum(numeric_only=True,)
# 		DF1_after.fillna({'mese':'Totale Periodo'},inplace=True)
# 		DF1_after.fillna('', inplace=True)

# 		dict1 = DF1_before.to_dict('records')
# 		dict2 = DF1_after.to_dict('records')
		

# 	except Exception as error:
# 		print(error)
# 		dict1 = {}
# 		dict2 = {}

# 	table_data = {
# 		'anno': anno,
# 		'table1': dict1,
# 		'table2': dict2,
# 		'info': dz_impianto,
# 	}

# 	print(table_data)
# 	return table_data


def tabellacorrispettivi_data(anno_nickname):
	# DA URL ESTRAPOLO ANNO E NICKNAME
	anno = int(anno_nickname.split('_', 1)[0])
	nickname = anno_nickname.split('_', 1)[1]

	# print(f"DEBUG: Richiesta per anno={anno}, nickname={nickname}")

	# MASSIMALI EURO E ENERGIE PER LA VISUALIZZAZIONE
	max_corrispettivi = {'ionico_foresta': 40000, 'san_teodoro': 30000, 'ponte_giurino': 20000, 'petilia_bf_partitore': 20000}
	max_energie = {'ionico_foresta': 157000, 'san_teodoro': 122000, 'ponte_giurino': 67000, 'petilia_bf_partitore': 37000}

	# ESTRAPOLO DATI IMPIANTO DAL DATABASE
	impianto = Impianto.objects.all().filter(nickname=nickname).first()
	
	if not impianto:
		print(f"DEBUG: Impianto con nickname '{nickname}' non trovato.")
		return {
			'anno': anno,
			'TableCorrispettivi': {},
			'info': {},
			'max_energia': 0,
			'max_corrispettivi': 0
		}

	dz_impianto = model_to_dict(impianto)
	print(f"DEBUG: Impianto trovato: {impianto.nome_impianto}")

	# DEFINIZIONE MESE CORRENTE, PRECEDENTE E ANTECEDENTE
	Now = datetime.now()
	curr_mese = datetime(Now.year, Now.month, 1)
	last_mese = curr_mese - timedelta(days=1)
	last_mese = last_mese.replace(day=1)
	last_last_mese = last_mese - timedelta(days=1)
	last_last_mese = last_last_mese.replace(day=1)

	# PERCORSO FILE DI CASH FLOW
	cashflow_set = impianto.cashflow_set.all()
	if not cashflow_set.exists():
		print(f"DEBUG: Nessun cashflow associato all'impianto '{nickname}'.")
		return {
			'anno': anno,
			'TableCorrispettivi': {},
			'info': dz_impianto,
			'max_energia': 0,
			'max_corrispettivi': 0
		}

	diario_cashflow = str(cashflow_set[0])
	cash_sheet = 'Incassi GSE'

	if nickname == 'petilia_bf_partitore':
		cash_sheet = 'Incassi GSE Partitore'

	print(f"DEBUG: Diario cashflow: {diario_cashflow}, Sheet: {cash_sheet}")


	# CODICE DI ELEABORAZIONE DEI DATI NEI DIARI DELLE LETTURE E CASH FLOW
	try:
		# OTTIENI DATI DAL MODELLO LetturaContatore INSTEAD DEL FILE EXCEL
		letture = LetturaContatore.objects.filter(
			contatore__impianto=impianto,
			mese__year=anno
		).order_by('mese')
		
		print(f"DEBUG: Query LetturaContatore eseguita. Trovate {letture.count()} letture.")
		
		# CREA DATAFRAME PANDAS DAI DATI DEL DATABASE
		data = []
		for i, lettura in enumerate(letture):
			# Calcola energia incentivata usando la formula min(98% prod_campo, 100% imm_campo)
			prod_campo_98 = lettura.prodotta_campo * 0.98
			energia_incentivata = min(prod_campo_98, lettura.immessa_campo)
			
			# Verifico quale dei due valori è il minimo 
			if prod_campo_98 <= lettura.immessa_campo:
				# Se il minimo è prod_campo*0.98, confermiamo che stiamo usando il 98% dell'energia prodotta
				energia_incentivata = prod_campo_98
			else:
				# Se il minimo è imm_campo, usiamo il valore dell'energia immessa
				energia_incentivata = lettura.immessa_campo
			
			print(f"DEBUG: Mese {lettura.mese.strftime('%Y-%m')}: prodotta_campo={lettura.prodotta_campo}, immessa_campo={lettura.immessa_campo}, prod_campo_98={prod_campo_98}, energia_incentivata={energia_incentivata}")
			
			data.append({
				'i': i,
				'mese': lettura.mese,
				'prodotta_campo': lettura.prodotta_campo,
				'immessa_campo': lettura.immessa_campo,
				'E_incentivata': energia_incentivata,
				'aspettata_inc': lettura.aspettata_inc,
				'aspettata_non_inc': lettura.aspettata_non_inc,
				'aspettata_tot': lettura.aspettata_inc + lettura.aspettata_non_inc
			})
		
		print(f"DEBUG: Lista 'data' creata con {len(data)} elementi.")
		
		df1 = pd.DataFrame(data)
		
		print(f"DEBUG: DataFrame df1 creato. Dimensioni: {df1.shape}")
		# print(df1.head()) # Puoi anche stampare le prime righe per vedere i dati

		# SE NON CI SONO DATI, CREA UN DATAFRAME VUOTO
		if len(df1) == 0:
			raise Exception("Nessun dato trovato per l'anno selezionato")

		df2 = load_cashflow(diario_cashflow, cash_sheet)
		print(f"DEBUG: DataFrame df2 (cashflow) creato. Dimensioni: {df2.shape}")
		# print(df2.head()) # Puoi anche stampare le prime righe

		# SELEZIONE ANNO RICHIESTO DATI CASH FLOW
		if Now.year == anno:
			df2 = df2[df2[('Fatturazione TFO', 'Periodo')].dt.year >= anno - 1]
		else:
			df2 = df2[df2[('Fatturazione TFO', 'Periodo')].dt.year == anno]
		df2.reset_index(drop=True, inplace=True)
		print(f"DEBUG: DataFrame df2 filtrato per anno. Dimensioni: {df2.shape}")

		# AGGIUNGO DATI DI CASH FLOW AL DATAFRAME PRINCIPALE
		# Assicurati che df1 e df2 abbiano lo stesso numero di righe o che l'allineamento per mese funzioni
		# Questo passaggio potrebbe fallire se i mesi in df1 e df2 non corrispondono
		try:
			df1['fatturazione_tfo'] = df2[('Fatturazione TFO','Energia di competenza')]
			df1['fatturazione_non_inc'] = df2[('Fatturazione Energia non incentivata', 'Energia di competenza')]
			df1['incassi'] = df2[('Riepilogo pagamenti', 'Incasso/pagamento')]
			print("DEBUG: Dati cashflow aggiunti a df1.")
		except Exception as merge_error:
			print(f"DEBUG: Errore durante l'aggiunta dati cashflow a df1: {type(merge_error).__name__} – {merge_error}")
			print("DEBUG: df1 prima dell'unione:")
			# print(df1[['mese', 'E_incentivata']].head()) # Stampa per debug
			print("DEBUG: df2 prima dell'unione:")
			# print(df2[[('Fatturazione TFO', 'Periodo'), ('Fatturazione TFO','Energia di competenza')]].head()) # Stampa per debug
			# Potresti voler sollevare l'errore o gestire diversamente
			raise merge_error

		# CODICE DI CONTROLLO STIME-FATTURAZIONE - TABELLA 1
		# CALCOLO VARIAZIONE TRA STIME E FATTURAZIONE EFFETTIVA, VISUALIZZAZIONE DELLE VARIAZIONI IN EURO (delta_eur) E PERCENTUALE (ratio_eur)
		df1['comments'] = ''
		# Assicurati che le colonne esistano prima di usarle
		if 'fatturazione_tfo' in df1.columns and 'fatturazione_non_inc' in df1.columns and 'aspettata_tot' in df1.columns:
			df1.loc[df1.fatturazione_tfo != 0, 'delta_eur'] = (df1['aspettata_tot'] - (df1['fatturazione_tfo'] + df1['fatturazione_non_inc']))
			df1.loc[df1.fatturazione_tfo != 0, 'ratio_eur'] = (df1['aspettata_tot'] - (df1['fatturazione_tfo'] + df1['fatturazione_non_inc'])) / df1['aspettata_tot'] * 100
			df1['ratio_eur'] = df1['ratio_eur'].replace([-np.inf, np.inf], 100)
			print("DEBUG: Calcolo delta/ratio eseguito.")
		else:
			print("DEBUG: Colonne necessarie per calcolo delta/ratio non trovate in df1.")


		# CONTROLLO FINALE SU INSERIMENTO FATTURE DEGLI ULTIMI DUE MESI
		# Questo controllo si basa sugli indici iloc[0] che potrebbero fallire se il DataFrame è vuoto o ha meno di 2 righe
		if anno == Now.year and not df1.empty and len(df1) >= 2:
			try:
				if df1[last_last_mese == df1['mese']].iloc[0]['fatturazione_tfo'] == 0:
					index = df1[last_last_mese == df1['mese']].iloc[0]['i']
					df1.loc[index, 'comments'] = 'fattura'
					print(f"DEBUG: Commento 'fattura' aggiunto per {last_last_mese.strftime('%Y-%m')}")

				# Questo controllo sembra problematico: df1[last_last_mese<df1['mese']].iloc[0]
				# Se ci sono più mesi successivi a last_last_mese, .iloc[0] prende solo il primo.
				# Forse intendevi controllare il mese corrente (curr_mese)?
				# Se vuoi controllare il mese corrente:
				# if not df1[curr_mese == df1['mese']].empty and df1[curr_mese == df1['mese']].iloc[0]['fatturazione_tfo'] == 0:
				# 	index = df1[curr_mese == df1['mese']].iloc[0]['i']
				# 	df1.loc[index, 'comments'] = 'fattura'
				# 	print(f"DEBUG: Commento 'fattura' aggiunto per {curr_mese.strftime('%Y-%m')}")

				# Se vuoi controllare l'ultimo mese presente nel DataFrame:
				if not df1.empty:
					ultimo_mese_df1 = df1['mese'].max()
					if ultimo_mese_df1 > last_last_mese and df1[df1['mese'] == ultimo_mese_df1].iloc[0]['fatturazione_tfo'] == 0:
						index = df1[df1['mese'] == ultimo_mese_df1].iloc[0]['i']
						df1.loc[index, 'comments'] = 'fattura'
						print(f"DEBUG: Commento 'fattura' aggiunto per l'ultimo mese nel df ({ultimo_mese_df1.strftime('%Y-%m')})")


			except Exception as date_check_error:
				print(f"DEBUG: Errore durante il controllo date/fatture: {type(date_check_error).__name__} – {date_check_error}")
				# Continua l'esecuzione anche se questo controllo fallisce

		df1['mese'] = df1['mese'].dt.month_name(locale='it_IT.utf8')

		# df1.replace(0, np.nan, inplace=True)
		df1 = df1.fillna('')

		# Assicurati che tutte le colonne richieste esistano in df1 prima di convertirlo in dict
		required_cols = ['i', 'mese', 'E_incentivata', 'aspettata_inc', 'aspettata_non_inc', 'fatturazione_tfo', 'fatturazione_non_inc', 'incassi', 'ratio_eur','delta_eur','comments']
		missing_cols = [col for col in required_cols if col not in df1.columns]
		if missing_cols:
			print(f"DEBUG: Colonne mancanti in df1 prima della conversione in dict: {missing_cols}")
			# Potresti voler aggiungere le colonne mancanti con valori di default (es. '')
			for col in missing_cols:
				df1[col] = '' # Aggiunge la colonna mancante con valori vuoti
			print(f"DEBUG: Aggiunte colonne mancanti: {missing_cols}")


		dict1 = df1[required_cols].to_dict('records')
		print(f"DEBUG: dict1 creato con {len(dict1)} record.")


	except Exception as error:
		print(f'Errore elaborazione Tabella Corrispettivi', type(error).__name__, "–", error)
		dict1 = {}
		# Potresti voler restituire un indicatore di errore anche nel JSON di risposta
		table_data = {
			'anno': anno,
			'TableCorrispettivi': dict1,
			'info': dz_impianto,
			'max_energia': max_energie.get(nickname, 0)*1.15,
			'max_corrispettivi': max_corrispettivi.get(nickname, 0),
			'error': f'Errore elaborazione dati: {type(error).__name__} – {error}'
		}
		print("DEBUG: Restituito dict vuoto a causa di un errore.")
		return table_data

	table_data = {
		'anno': anno,
		'TableCorrispettivi': dict1,
		'info': dz_impianto,
		'max_energia': max_energie.get(nickname, 0)*1.15,
		'max_corrispettivi': max_corrispettivi.get(nickname, 0)
	}
	print("DEBUG: Dati finali preparati per la risposta.")
	# print(table_data) # Puoi stampare l'intero dict finale se non è troppo grande
	return table_data


# 3. VIEW CHE GESTISCE LA VISIONE DEI DATI RELATIVI ALLA TABELLA "MISURE"
class TableMisure(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)

	def get(self, request, anno_nickname, format=None):
		table_data = tabellamisure_data(anno_nickname)
		return Response(table_data)


# class DatiReportImpianto(APIView):
# 	renderer_classes = [JSONRenderer]
# 	permission_classes = (IsAuthenticated,)

# 	def get(self, request, nickname, format=None):
# 		data = energievolumi_dati(nickname)
# 		return Response(data)


# Aggiungiamo una nuova funzione per ottenere gli anni disponibili per un impianto
def get_available_years(nickname):
    from AutomazioneDati.models import regsegnanti
    from django.db.models import Q
    
    try:
        # Recupero di TUTTI i contatori legati all'impianto (tramite relazione o nickname)
        contatori_qs = Contatore.objects.filter(
            Q(impianto__nickname=nickname) | Q(impianto_nickname=nickname)
        )

        if contatori_qs.exists():
            # Se esistono più contatori, recupero gli anni presenti in regsegnanti per TUTTI
            anni = list(
                regsegnanti.objects.filter(contatore__in=contatori_qs)
                .values_list('anno', flat=True)
                .distinct()
                .order_by('anno')
            )
        else:
            # Fallback: nessun contatore trovato, provo comunque a filtrare i registri
            anni = list(
                regsegnanti.objects.filter(contatore__isnull=True)  # forza lista vuota se non troviamo corrispondenze
                .values_list('anno', flat=True)
                .distinct()
                .order_by('anno')
            )

        if not anni:
            print(f"Nessun anno trovato per l'impianto {nickname}")

        return anni

    except Exception as e:
        print(f"Errore nel recupero degli anni disponibili per {nickname}: {str(e)}")
        # In caso di errore, restituisco lista vuota per evitare crash lato client
        return []

# Aggiungiamo una nuova API view per esporre questi anni
class AvailableYears(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)
	
	def get(self, request, nickname, format=None):
		years = get_available_years(nickname)
		return Response({'years': years})


def carica_dati_da_excel(impianto_obj, anno, mese):
    """
    Carica i dati dai file Excel per un determinato impianto, anno e mese.
    Restituisce un dizionario con i dati caricati.
    """
    import pandas as pd
    import os
    from PortaleCorrispettivi.models import Cashflow
    import traceback
    
    # Inizializza il dizionario dei risultati
    risultati = {
        'fatturazione_tfo': None,
        'fatturazione_altro': None,
        'incassi': None,
        'debug_info': []  # Array per raccogliere info di debug
    }
    
    try:
        # Cerca i record di Cashflow per questo impianto
        cashflow_records = Cashflow.objects.filter(impianto=impianto_obj)
        debug_msg = f"Trovati {cashflow_records.count()} record Cashflow per l'impianto {impianto_obj.nome_impianto}"
        print(debug_msg)
        risultati['debug_info'].append(debug_msg)
        
        if not cashflow_records.exists():
            debug_msg = f"Nessun file Cashflow trovato per l'impianto {impianto_obj.nome_impianto}"
            print(debug_msg)
            risultati['debug_info'].append(debug_msg)
            return risultati
            
        for cashflow in cashflow_records:
            # Costruisci il percorso completo del file
            percorso_completo = os.path.join(cashflow.unit, cashflow.percorso)
            debug_msg = f"Percorso file completo: {percorso_completo}"
            print(debug_msg)
            risultati['debug_info'].append(debug_msg)
            
            # Verifica se il file esiste
            if not os.path.exists(percorso_completo):
                debug_msg = f"File non trovato: {percorso_completo}"
                print(debug_msg)
                risultati['debug_info'].append(debug_msg)
                continue
                
            try:
                # Leggi il file Excel
                debug_msg = f"Tentativo di lettura del file: {percorso_completo}"
                print(debug_msg)
                risultati['debug_info'].append(debug_msg)
                
                # Carica il file Excel con pandas
                xls = pd.ExcelFile(percorso_completo)
                
                # Debug: mostra tutti i fogli disponibili
                debug_msg = f"Fogli disponibili nel file: {', '.join(xls.sheet_names)}"
                print(debug_msg)
                risultati['debug_info'].append(debug_msg)
                
                # Identifica il formato del file e cerca i dati richiesti
                # Prima verifica se è il formato con due livelli di intestazione
                try:
                    # Tenta di leggere con il formato Cashflow standard (header multilivello)
                    debug_msg = "Tentativo lettura con formato cashflow standard (header multilivello)"
                    print(debug_msg)
                    risultati['debug_info'].append(debug_msg)
                    
                    # Leggi il foglio principale che potrebbe contenere tutti i dati
                    sheet_name = 'Incassi GSE' if 'Incassi GSE' in xls.sheet_names else xls.sheet_names[0]
                    df = pd.read_excel(xls, sheet_name, index_col=None, header=[2, 3], na_values=[pd.NA])
                    df = df.dropna(axis=1, how='all')
                    
                    # Mostra le colonne trovate
                    debug_msg = f"Colonne trovate nel foglio {sheet_name} (multilivello): {list(df.columns.values)}"
                    print(debug_msg)
                    risultati['debug_info'].append(debug_msg)
                    
                    # Cerca le colonne 'Fatturazione TFO', 'Fatturazione Energia non incentivata', 'Riepilogo pagamenti'
                    headers = ['Fatturazione TFO', 'Fatturazione Energia non incentivata', 'Riepilogo pagamenti']
                    
                    # Lista di liste booleane che indicano la posizione delle colonne date in headers
                    ll = [list(df.columns.get_level_values(0).str.contains(z)) for z in headers]
                    
                    # Lista booleana che indica la posizione di tutte le colonne date in headers
                    ll = list(map(any, zip(*ll)))
                    
                    # Filtra le colonne pertinenti
                    df_filtered = df.loc[:, ll]
                    
                    # Converti le date in formato datetime
                    for s in headers:
                        if (s, 'Periodo') in df_filtered.columns:
                            df_filtered[(s, 'Periodo')] = pd.to_datetime(df_filtered[(s, 'Periodo')], errors='coerce')
                    
                    # Ora filtra per l'anno e il mese specifici
                    # Assumiamo che la data sia nella colonna 'Periodo' di ogni header
                    for s in headers:
                        if (s, 'Periodo') in df_filtered.columns:
                            mask = (df_filtered[(s, 'Periodo')].dt.year == anno) & (df_filtered[(s, 'Periodo')].dt.month == mese)
                            df_periodo = df_filtered.loc[mask]
                            
                            debug_msg = f"Dati trovati per {s}, {anno}/{mese}: {len(df_periodo)} righe"
                            print(debug_msg)
                            risultati['debug_info'].append(debug_msg)
                            
                            # Estrai i dati specifici a seconda dell'intestazione
                            if s == 'Fatturazione TFO' and (s, 'Energia di competenza') in df_periodo.columns:
                                risultati['fatturazione_tfo'] = float(df_periodo[(s, 'Energia di competenza')].sum())
                                debug_msg = f"Fatturazione TFO: {risultati['fatturazione_tfo']}"
                                print(debug_msg)
                                risultati['debug_info'].append(debug_msg)
                                
                            elif s == 'Fatturazione Energia non incentivata' and (s, 'Energia di competenza') in df_periodo.columns:
                                risultati['fatturazione_altro'] = float(df_periodo[(s, 'Energia di competenza')].sum())
                                debug_msg = f"Fatturazione altro: {risultati['fatturazione_altro']}"
                                print(debug_msg)
                                risultati['debug_info'].append(debug_msg)
                                
                            elif s == 'Riepilogo pagamenti' and (s, 'Incasso/pagamento') in df_periodo.columns:
                                risultati['incassi'] = float(df_periodo[(s, 'Incasso/pagamento')].sum())
                                debug_msg = f"Incassi: {risultati['incassi']}"
                                print(debug_msg)
                                risultati['debug_info'].append(debug_msg)
                
                except Exception as e:
                    debug_msg = f"Errore nel formato multilivello: {str(e)}"
                    print(debug_msg)
                    risultati['debug_info'].append(debug_msg)
                    traceback.print_exc()
                    
                    # Prova formato alternativo con fogli separati
                    debug_msg = "Tentativo lettura con formato alternativo (fogli separati)"
                    print(debug_msg)
                    risultati['debug_info'].append(debug_msg)
                    
                    if 'Fatturazione' in xls.sheet_names:
                        try:
                            # Estrai i dati di fatturazione
                            df_fatturazione = pd.read_excel(xls, 'Fatturazione')
                            
                            # Debug: mostra le colonne disponibili
                            debug_msg = f"Colonne nel foglio Fatturazione: {list(df_fatturazione.columns)}"
                            print(debug_msg)
                            risultati['debug_info'].append(debug_msg)
                            
                            # Cerca dati per l'anno e mese specifici
                            if 'Anno' in df_fatturazione.columns and 'Mese' in df_fatturazione.columns:
                                maschera = (df_fatturazione['Anno'] == anno) & (df_fatturazione['Mese'] == mese)
                                dati_periodo = df_fatturazione[maschera]
                                
                                debug_msg = f"Dati trovati in Fatturazione per {anno}/{mese}: {len(dati_periodo)} righe"
                                print(debug_msg)
                                risultati['debug_info'].append(debug_msg)
                                
                                if not dati_periodo.empty:
                                    # Assumiamo che ci siano colonne per TFO e Non Incentivata
                                    if 'Fatturazione TFO' in dati_periodo.columns:
                                        risultati['fatturazione_tfo'] = float(dati_periodo['Fatturazione TFO'].sum())
                                        debug_msg = f"Fatturazione TFO: {risultati['fatturazione_tfo']}"
                                        print(debug_msg)
                                        risultati['debug_info'].append(debug_msg)
                                        
                                    if 'Fatturazione Non Incentivata' in dati_periodo.columns:
                                        risultati['fatturazione_altro'] = float(dati_periodo['Fatturazione Non Incentivata'].sum())
                                        debug_msg = f"Fatturazione altro: {risultati['fatturazione_altro']}"
                                        print(debug_msg)
                                        risultati['debug_info'].append(debug_msg)
                        except Exception as e_fatt:
                            debug_msg = f"Errore nella lettura del foglio Fatturazione: {str(e_fatt)}"
                            print(debug_msg)
                            risultati['debug_info'].append(debug_msg)
                            traceback.print_exc()
                    
                    if 'Incassi' in xls.sheet_names:
                        try:
                            # Estrai i dati degli incassi
                            df_incassi = pd.read_excel(xls, 'Incassi')
                            
                            # Debug: mostra le colonne disponibili
                            debug_msg = f"Colonne nel foglio Incassi: {list(df_incassi.columns)}"
                            print(debug_msg)
                            risultati['debug_info'].append(debug_msg)
                            
                            # Cerca dati per l'anno e mese specifici
                            if 'Anno' in df_incassi.columns and 'Mese' in df_incassi.columns:
                                maschera = (df_incassi['Anno'] == anno) & (df_incassi['Mese'] == mese)
                                dati_incassi = df_incassi[maschera]
                                
                                debug_msg = f"Dati trovati in Incassi per {anno}/{mese}: {len(dati_incassi)} righe"
                                print(debug_msg)
                                risultati['debug_info'].append(debug_msg)
                                
                                if not dati_incassi.empty and 'Importo' in dati_incassi.columns:
                                    risultati['incassi'] = float(dati_incassi['Importo'].sum())
                                    debug_msg = f"Incassi: {risultati['incassi']}"
                                    print(debug_msg)
                                    risultati['debug_info'].append(debug_msg)
                        except Exception as e_inc:
                            debug_msg = f"Errore nella lettura del foglio Incassi: {str(e_inc)}"
                            print(debug_msg)
                            risultati['debug_info'].append(debug_msg)
                            traceback.print_exc()
                
            except Exception as e:
                debug_msg = f"Errore nella lettura del file Excel {percorso_completo}: {str(e)}"
                print(debug_msg)
                risultati['debug_info'].append(debug_msg)
                traceback.print_exc()
                continue
                
        return risultati
        
    except Exception as e:
        debug_msg = f"Errore generale nel caricamento dei dati Excel: {str(e)}"
        print(debug_msg)
        risultati['debug_info'].append(debug_msg)
        traceback.print_exc()
        return risultati


@csrf_exempt
def dati_mensili_tabella_api(request):
    """API per gestire i dati mensili della tabella"""
    
    print(f"API chiamata: {request.method}, params: {request.GET if request.method == 'GET' else request.POST}")
    
    # GET: Ottieni i dati mensili
    if request.method == 'GET':
        nickname = request.GET.get('impianto')
        anno_richiesto = request.GET.get('anno')
        
        print(f"Parametri ricevuti: impianto={nickname}, anno={anno_richiesto}")
        
        if not nickname or not anno_richiesto:
            return JsonResponse({'success': False, 'error': 'Parametri mancanti'})
        
        try:
            # Assicuriamoci di ottenere l'oggetto Impianto corretto
            impianto_obj = Impianto.objects.filter(nickname=nickname).first()
            if not impianto_obj:
                print(f"Impianto non trovato: {nickname}")
                return JsonResponse({'success': False, 'error': 'Impianto non trovato'})
                
            print(f"Impianto trovato: {impianto_obj.nome_impianto}, ID: {impianto_obj.id}")

            # Recupera le credenziali FTP direttamente dal modulo APIgme
            # Non c'è bisogno di cercare nelle impostazioni di Django
            
            # Recupero di TUTTI i contatori collegati all'impianto (potrebbero esserne presenti più di uno)
            contatori_qs = Contatore.objects.filter(
                models.Q(impianto=impianto_obj.id) |
                models.Q(impianto_nickname=impianto_obj.nickname)
            )

            data_response = []  # Lista finale che verrà restituita

            if not contatori_qs.exists():
                print(f"Nessun contatore trovato per l'impianto {impianto_obj.nome_impianto}")
                
                # Cerca direttamente letture per questo impianto usando regsegnanti
                try:
                    # Usa direttamente regsegnanti come fallback
                    dati_reg = regsegnanti.objects.filter(anno=int(anno_richiesto))

                    # Se in passato esisteva il campo impianto_nickname, filtra anche per quello
                    if hasattr(regsegnanti, 'impianto_nickname'):
                        dati_reg = dati_reg.filter(impianto_nickname=impianto_obj.nickname)
                    
                    print(f"Dati trovati (fallback regsegnanti): {dati_reg.count()} record")
                    
                    # Aggregazione per mese del fallback
                    monthly_tmp = {}
                    for dato in dati_reg:
                        mese_key = dato.mese

                        # Calcola energia incentivata per la riga attuale
                        if dato.prod_campo is not None:
                            prod_campo_float = float(dato.prod_campo)
                            prod_campo_98 = prod_campo_float * 0.98
                            imm_campo_float = float(dato.imm_campo) if dato.imm_campo else 0
                            energia_incentivata = min(prod_campo_98, imm_campo_float) if imm_campo_float else prod_campo_98
                        else:
                            prod_campo_float = 0
                            imm_campo_float = 0
                            energia_incentivata = 0

                        if mese_key not in monthly_tmp:
                            monthly_tmp[mese_key] = {
                                'energia_kwh': 0,
                                'prod_campo_originale': 0,
                                'imm_campo': 0
                            }

                        monthly_tmp[mese_key]['energia_kwh'] += energia_incentivata
                        monthly_tmp[mese_key]['prod_campo_originale'] += prod_campo_float
                        monthly_tmp[mese_key]['imm_campo'] += imm_campo_float
                    
                    # Una volta aggregato, crea le righe di risposta definitive
                    for mese, valori in monthly_tmp.items():
                        media_pun_mensile = scarica_dati_pun_mensili(
                            int(anno_richiesto),
                            mese,
                            GME_FTP_USERNAME,
                            GME_FTP_PASSWORD,
                            stampare_media_dettaglio=False,
                        )

                        dati_excel = carica_dati_da_excel(impianto_obj, int(anno_richiesto), mese)

                        data_response.append({
                            'mese': mese,
                            'energia_kwh': valori['energia_kwh'],
                            'corrispettivo_incentivo': None,
                            'corrispettivo_altro': None,
                            'fatturazione_tfo': dati_excel['fatturazione_tfo'],
                            'fatturazione_altro': dati_excel['fatturazione_altro'],
                            'incassi': dati_excel['incassi'],
                            'controllo_scarto': None,
                            'controllo_percentuale': None,
                            'media_pun_mensile': media_pun_mensile,
                            'prod_campo_originale': valori['prod_campo_originale'],
                            'imm_campo': valori['imm_campo'],
                            'debug_info': dati_excel.get('debug_info', []),
                        })
                    
                    return JsonResponse({'success': True, 'data': data_response})
                    
                except Exception as inner_e:
                    print(f"Errore nel tentativo di usare regsegnanti (fallback): {str(inner_e)}")
                
                return JsonResponse({'success': True, 'data': []}) # Risposta vuota se fallback fallisce
            
            # --- SE SONO PRESENTI UNO O PIÙ CONTATORI ---

            dati_reg = regsegnanti.objects.filter(contatore__in=contatori_qs, anno=int(anno_richiesto))

            print(f"Dati trovati (regsegnanti con contatore): {dati_reg.count()} record distribuiti su {contatori_qs.count()} contatori")

            # Aggrego i dati per mese, sommando l'energia (e altri valori se necessario)
            monthly_data = {}

            for dato in dati_reg:
                # Scarica direttamente i dati PUN dal server FTP
                mese_key = dato.mese

                # Calcolo dell'energia incentivata per la singola riga
                if dato.prod_campo is not None:
                    prod_campo_float = float(dato.prod_campo)
                    prod_campo_98 = prod_campo_float * 0.98
                    imm_campo_float = float(dato.imm_campo) if dato.imm_campo else 0
                    energia_incentivata = min(prod_campo_98, imm_campo_float) if imm_campo_float else prod_campo_98
                else:
                    prod_campo_float = 0
                    imm_campo_float = 0
                    energia_incentivata = 0

                if mese_key not in monthly_data:
                    monthly_data[mese_key] = {
                        'energia_kwh': 0,
                        'prod_campo_originale': 0,
                        'imm_campo': 0,
                    }

                monthly_data[mese_key]['energia_kwh'] += energia_incentivata
                monthly_data[mese_key]['prod_campo_originale'] += prod_campo_float
                monthly_data[mese_key]['imm_campo'] += imm_campo_float

            # Dopo il ciclo, costruisco la risposta finale per ciascun mese
            for mese, valori in monthly_data.items():
                media_pun_mensile = scarica_dati_pun_mensili(
                    int(anno_richiesto),
                    mese,
                    GME_FTP_USERNAME,
                    GME_FTP_PASSWORD,
                    stampare_media_dettaglio=False,
                )

                dati_excel = carica_dati_da_excel(impianto_obj, int(anno_richiesto), mese)

                data_response.append({
                    'mese': mese,
                    'energia_kwh': valori['energia_kwh'],
                    'corrispettivo_incentivo': None,
                    'corrispettivo_altro': None,
                    'fatturazione_tfo': dati_excel['fatturazione_tfo'],
                    'fatturazione_altro': dati_excel['fatturazione_altro'],
                    'incassi': dati_excel['incassi'],
                    'controllo_scarto': None,
                    'controllo_percentuale': None,
                    'media_pun_mensile': media_pun_mensile,
                    'prod_campo_originale': valori['prod_campo_originale'],
                    'imm_campo': valori['imm_campo'],
                    'debug_info': dati_excel.get('debug_info', []),
                })
 
            return JsonResponse({'success': True, 'data': data_response})
            
        except Exception as e:
            print(f"Errore: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})
    
    # POST: Salva o aggiorna i dati mensili
    elif request.method == 'POST':
        nickname = request.POST.get('impianto')
        anno = request.POST.get('anno')
        dati_json = request.POST.get('dati')
        
        print(f"POST Parametri ricevuti: impianto={nickname}, anno={anno}")
        print(f"Dati JSON ricevuti: {dati_json[:100]}...")
        
        if not nickname or not anno or not dati_json:
            print("Errore: parametri mancanti")
            return JsonResponse({'success': False, 'error': 'Parametri mancanti'})
        
        try:
            # Assicuriamoci di ottenere l'oggetto Impianto corretto
            impianto_obj = Impianto.objects.filter(nickname=nickname).first()
            if not impianto_obj:
                print(f"Impianto non trovato: {nickname}")
                return JsonResponse({'success': False, 'error': 'Impianto non trovato'})
                
            print(f"Impianto trovato: {impianto_obj.nome_impianto}, ID: {impianto_obj.id}")
            
            # Cerca contatore sia per impianto che per nickname
            contatore_obj = Contatore.objects.filter(
                models.Q(impianto=impianto_obj.id) | 
                models.Q(impianto_nickname=impianto_obj.nickname)
            ).first()
            
            if not contatore_obj:
                print(f"Nessun contatore trovato per l'impianto {impianto_obj.nome_impianto}")
                # Crea un nuovo contatore per questo impianto
                contatore_obj = Contatore.objects.create(
                    impianto=impianto_obj,
                    impianto_nickname=impianto_obj.nickname,
                    nome=f"Contatore {impianto_obj.nome_impianto}",
                    pod="AUTO-GENERATO",
                    tipologia="Produzione",
                    k=1,
                    marca="Kaifa",
                    modello="AUTO-GENERATO",
                    data_installazione=models.functions.Now()
                )
                print(f"Creato nuovo contatore: ID {contatore_obj.id}")
            else:
                print(f"Contatore trovato: ID {contatore_obj.id}")
            
            dati = json.loads(dati_json)
            print(f"Dati JSON decodificati: {len(dati)} record")
            
            for dato in dati:
                mese = dato.get('mese')
                print(f"Elaborazione mese {mese}")
                
                # Salva i dati in regsegnanti invece che in DatiMensiliTabella
                obj, created = regsegnanti.objects.update_or_create(
                    contatore=contatore_obj,
                    anno=int(anno),
                    mese=mese,
                    defaults={
                        'prod_campo': dato.get('energia_kwh'),
                        # Gli altri campi di regsegnanti (prod_ed, prod_gse, etc.) sono impostati a None
                    }
                )
                print(f"Record {'creato' if created else 'aggiornato'} per il mese {mese}")
            
            print("Salvataggio dati completato con successo")
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Errore generico durante il salvataggio: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Metodo non supportato'})



# Funzione per recuperare i dati delle misure
def tabellamisure_data(anno_nickname):
    parts = anno_nickname.split('_', 1)
    
    if len(parts) != 2:
        return {"error": "Formato anno_nickname non valido"}
        
    anno = parts[0]
    nickname = parts[1]
    
    try:
        # Ottieni l'impianto
        impianto_obj = Impianto.objects.filter(nickname=nickname).first()
        if not impianto_obj:
            return {"error": "Impianto non trovato", "TableMisure": []}
            
        # Cerca tutti i contatori associati all'impianto
        contatori_qs = Contatore.objects.filter(
            models.Q(impianto=impianto_obj.id) |
            models.Q(impianto_nickname=impianto_obj.nickname)
        )

        misure_data = []

        # Se esistono contatori, recupera tutti i registri per tali contatori
        if contatori_qs.exists():
            dati_reg = regsegnanti.objects.filter(contatore__in=contatori_qs, anno=int(anno))
        else:
            # Fallback: cerca direttamente per impianto_nickname (compatibilità con vecchi dati)
            dati_reg = regsegnanti.objects.filter(anno=int(anno))
            if hasattr(regsegnanti, 'impianto_nickname'):
                dati_reg = dati_reg.filter(impianto_nickname=impianto_obj.nickname)
        
        # Prepara i dati per ogni mese
        for dato in dati_reg:
            misure_data.append({
                'mese': dato.mese,
                'prod_campo': float(dato.prod_campo) if dato.prod_campo else None,
                'imm_campo': float(dato.imm_campo) if dato.imm_campo else None,
                'prel_campo': float(dato.prel_campo) if dato.prel_campo else None,
                'prod_ed': float(dato.prod_ed) if dato.prod_ed else None,
                'imm_ed': float(dato.imm_ed) if dato.imm_ed else None,
                'prel_ed': float(dato.prel_ed) if dato.prel_ed else None,
                'prod_gse': float(dato.prod_gse) if dato.prod_gse else None,
                'imm_gse': float(dato.imm_gse) if dato.imm_gse else None
            })
        
        return {"TableMisure": misure_data}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "TableMisure": []}


class DatiAggregatiCentrali(APIView):
	"""API per ottenere i dati aggregati di tutte le centrali per il grafico principale"""
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)
	
	def get(self, request, anno, format=None):
		try:
			anno = int(anno)
			
			# Ottieni tutti gli impianti
			impianti = Impianto.objects.all()
			
			# Dizionario per aggregare i dati per mese
			dati_aggregati = {}
			
			for mese in range(1, 13):  # Da gennaio a dicembre
				dati_aggregati[mese] = {
					'mese': mese,
					'energia_kwh': 0,
					'corrispettivi_tfo': 0,
					'fatturazione_tfo': 0,
					'incassi': 0
				}
			
			# Per ogni impianto, aggrega i dati
			for impianto in impianti:
				print(f"Elaborando impianto: {impianto.nome_impianto}")
				
				# Cerca tutti i contatori associati all'impianto
				contatori_qs = Contatore.objects.filter(
					models.Q(impianto=impianto.id) |
					models.Q(impianto_nickname=impianto.nickname)
				)

				if contatori_qs.exists():
					# Ottieni i dati dal modello regsegnanti per tutti i contatori
					dati_reg = regsegnanti.objects.filter(contatore__in=contatori_qs, anno=anno)
				else:
					# Fallback: cerca direttamente per impianto_nickname se il campo esiste
					dati_reg = regsegnanti.objects.filter(anno=anno)
					if hasattr(regsegnanti, 'impianto_nickname'):
						dati_reg = dati_reg.filter(impianto_nickname=impianto.nickname)
					else:
						continue  # Salta questo impianto se non trovato
				
				# Carica dati dai file Excel per questo impianto
				for dato_reg in dati_reg:
					mese = dato_reg.mese
					
					# Calcola energia incentivata
					if dato_reg.prod_campo is not None:
						prod_campo_float = float(dato_reg.prod_campo)
						prod_campo_98 = prod_campo_float * 0.98
						
						if dato_reg.imm_campo is not None:
							imm_campo_float = float(dato_reg.imm_campo)
							energia_incentivata = min(prod_campo_98, imm_campo_float)
						else:
							energia_incentivata = prod_campo_98
					else:
						energia_incentivata = 0
					
					# Carica dati dai file Excel per questo mese e impianto
					dati_excel = carica_dati_da_excel(impianto, anno, mese)
					
					# Aggrega i dati
					dati_aggregati[mese]['energia_kwh'] += energia_incentivata
					
					# Calcola corrispettivi TFO (assumo 0.21 €/kWh come nell'altro codice)
					corrispettivi_incentivati = energia_incentivata * 0.21
					dati_aggregati[mese]['corrispettivi_tfo'] += corrispettivi_incentivati
					
					# Aggiungi fatturazione e incassi se disponibili
					if dati_excel['fatturazione_tfo'] is not None:
						dati_aggregati[mese]['fatturazione_tfo'] += dati_excel['fatturazione_tfo']
					
					if dati_excel['incassi'] is not None:
						dati_aggregati[mese]['incassi'] += dati_excel['incassi']
			
			# Converti il dizionario in lista ordinata per mese
			dati_lista = [dati_aggregati[mese] for mese in range(1, 13)]
			
			return Response({
				'success': True,
				'anno': anno,
				'dati': dati_lista
			})
			
		except Exception as e:
			print(f"Errore nell'elaborazione dati aggregati: {str(e)}")
			import traceback
			traceback.print_exc()
			return Response({
				'success': False,
				'error': str(e)
			})


