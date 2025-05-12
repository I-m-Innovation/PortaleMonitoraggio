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
from .models import DatiMensiliTabella, ValoriPUN
import json
from django.db import models
from django.conf import settings
from PortaleCorrispettivi.APIgme import scarica_dati_pun_mensili, GME_FTP_USERNAME, GME_FTP_PASSWORD

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


# # FUNZIONE LETTURA DATI FILE CASHFLOW
# def load_cashflow(diario_cashflow, sheet):
# 	# CARICO FILE DI CASH-FLOW (contiene i dati di tutti gli anni)
# 	df = pd.read_excel(diario_cashflow, sheet, index_col=None, header=[2, 3], na_values=[np.nan])
# 	df = df.dropna(axis=1, how='all')
# 	# NOME COLONNE NEL FILE EXCEL
# 	x = ['Fatturazione TFO', 'Fatturazione Energia non incentivata', 'Riepilogo pagamenti']

# 	# SISTEMAZIONE DATAFRAME IN BASE ALLA FORMATTAZIONE DELLA TABELLA EXCEL

# 	# il dataframe df2 contiene 2 righe di headers:
# 	# _____________________________________________________________________________________________________________________________________________________________________
# 	# |Fatturazione TFO | Fatturazione TFO       | Fatturazione Energia non incentivata | Fatturazione Energia non incentivata | Riepilogo pagamenti | Riepilogo pagamenti |
# 	# |Periodo          | Energia di competenza  | Periodo                              | Energia di competenza                | Periodo             | Incasso/pagamento   |
# 	# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 	# LISTA DI LISTE BOOLEANE CHE INDICANO IN df2 LA POSIZIONE DELLE COLONNE DATE IN x
# 	ll = [list(df.columns.get_level_values(0).str.contains(z)) for z in x]
# 	# LISTA BOOLEANA CHE INDICA LA POSIZIONE DI TUTTE LE COLONNE DATE IN x
# 	ll = list(map(any, zip(*ll)))

# 	# FORMATTAZIONE IN DATETIME DELLA SOTTOCOLONNA 'Periodo' RELATIVA ALLE COLONNE IN x
# 	df = df.loc[:, ll]
# 	for s in x:
# 		df[(s, 'Periodo')] = pd.to_datetime(df[(s, 'Periodo')], errors='coerce')
# 	df = df.dropna(subset=[('Fatturazione TFO', 'Periodo')])
# 	return df


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
		# OTTIENI DATI DAL MODELLO LetturaContatore INVECE DEL FILE EXCEL
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


# def tabellamisure_data(anno_nickname):
# 	# DA URL ESTRAPOLO ANNO E NICKNAME
# 	anno = int(anno_nickname.split('_', 1)[0])
# 	nickname = anno_nickname.split('_', 1)[1]

# 	# ESTRAPOLO DATI IMPIANTO DAL DATABASE
# 	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
# 	dz_impianto = model_to_dict(impianto)

# 	# DEFINIZIONE MESE CORRENTE, PRECEDENTE E ANTECEDENTE
# 	Now = datetime.now()
# 	curr_mese = datetime(Now.year, Now.month, 1)
# 	last_mese = curr_mese - timedelta(days=1)
# 	last_mese = last_mese.replace(day=1)
# 	last_last_mese = last_mese - timedelta(days=1)
# 	last_last_mese = last_last_mese.replace(day=1)

# 	# PERCORSO DEL DIARIO DELLE LETTURE PER L'ANNO RICHIESTO
# 	diari_letture = list(impianto.diarioletture_set.all())
# 	letture_sheet = '07. Portale'

# 	if anno == Now.year:
# 		diari_letture = [str(diario) for diario in diari_letture if diario.anno >= anno - 1]
# 	else:
# 		diari_letture = [str(diario) for diario in diari_letture if diario.anno == anno]

# 	try:
# 		df1 = load_diariletture(diari_letture, letture_sheet)
# 		df1['i'] = df1.index
		
# 		# NUOVA FORMULA PER CALCOLARE L'ENERGIA INCENTIVATA
# 		# Calcolo il 98% dell'energia prodotta dal campo
# 		energia_prodotta_98 = df1['prodotta_campo'] * 0.98
# 		# Utilizzo il minimo tra 98% energia prodotta e 100% energia immessa
# 		df1['E_incentivata'] = np.minimum(energia_prodotta_98, df1['immessa_campo'])
		
# 		# Stampa di debug
# 		print(f"Calcolo energia incentivata per impianto {nickname}, anno {anno}:")
# 		print(f"98% energia prodotta: {energia_prodotta_98}")
# 		print(f"100% energia immessa: {df1['immessa_campo']}")
# 		print(f"Energia incentivata calcolata: {df1['E_incentivata']}")

# 		# CODICE DI CONTROLLO SULLE MISURE DI ENERGIA - TABELLA 2
# 		df1['check_misure'] = ''

# 		# CALCOLO DELTA PERCENTUALI DI PRODUZIONE TRA: CAMPO/e-D e CAMPO/GSE
# 		delta_prod_ed = (df1['prodotta_campo'] - df1['prodotta_ed']).abs() / df1['prodotta_campo'] * 100
# 		delta_prod_gse = (df1['prodotta_campo'] - df1['prodotta_gse']).abs() / df1['prodotta_campo'] * 100

# 		# CALCOLO DELTA PERCENTUALI DI IMMISSIONE TRA: CAMPO/e-D e CAMPO/GSE
# 		delta_imm_ed = (df1['immessa_campo'] - df1['immessa_ed']).abs() / df1['immessa_campo'] * 100
# 		delta_imm_gse = (df1['immessa_campo'] - df1['immessa_gse']).abs() / df1['immessa_campo'] * 100

# 		# ARROTONDAMENTO A DUE CIFRE DECIMALI VALORI
# 		delta_prod_ed = delta_prod_ed.round(decimals=2)
# 		delta_prod_gse = delta_prod_gse.round(decimals=2)
# 		delta_imm_ed = delta_imm_ed.round(decimals=2)
# 		delta_imm_gse = delta_imm_gse.round(decimals=2)

# 		# SOSITTUZIONE VALORI "inf" e TRASFORMAZIONE IN STRRINGHE
# 		delta_prod_ed = delta_prod_ed.replace([-np.inf, np.inf], '-').astype("string")
# 		delta_prod_gse = delta_prod_gse.replace([-np.inf, np.inf], '-').astype("string")
# 		delta_imm_ed = delta_imm_ed.replace([-np.inf, np.inf], '-').astype("string")
# 		delta_imm_gse = delta_imm_gse.replace([-np.inf, np.inf, ], '-').astype("string")

# 		# DEFINIZIONE COLONNA CON DELTA PERCENTUALI CHE VENGONO SEPARATI E ELABORATI NEL FRONT-END
# 		df1['check_misure'] = df1.check_misure.add(delta_prod_gse, fill_value='') + '_' + df1.check_misure.add(
# 			delta_prod_ed, fill_value='') + '_' + df1.check_misure.add(delta_imm_gse,
# 		                                                             fill_value='') + '_' + df1.check_misure.add(
# 			delta_imm_ed, fill_value='')

# 		# CHECK FINALE DI INSERIMENTO MISURE PER ULTIMI DUE MESI
# 		if anno == Now.year:
# 			if df1[last_last_mese == df1['mese']].iloc[0]['prodotta_campo'] == 0 or df1[last_last_mese == df1['mese']].iloc[0]['prodotta_gse'] == 0:
# 				index = df1[last_last_mese == df1['mese']].iloc[0]['i']
# 				df1.loc[index, 'check_misure'] = 'misure'

# 			if df1[last_last_mese < df1['mese']].iloc[0]['prodotta_campo'] == 0 or df1[last_last_mese < df1['mese']].iloc[0][
# 				'prodotta_gse'] == 0:
# 				index = df1[last_last_mese < df1['mese']].iloc[0]['i']
# 				df1.loc[index, 'check_misure'] = 'misure'

# 			# SLICE SU DATI ANNO CORRENTE
# 			df1 = df1[df1['mese'].dt.year == anno]

# 		# CODICE DI GESTIONE DEI COMMENTI SULLE MISURE
# 		# comments = impianto.Commento.objects.filter(impianto=nickname)
# 		comments = impianto.commento_set.all()
# 		comments = list(comments.values())
# 		comments = [comment for comment in comments if comment['mese_misura'].year == anno]

# 		df1['comments'] = ''

# 		for comment in comments:
# 			df1.loc[df1.index[comment['mese_misura'].month - 1], 'comments'] = comment['testo'] + '&' + comment['stato']

# 		df1['mese'] = df1['mese'].dt.month_name(locale='it_IT.utf8')
# 		df1.replace(0, np.nan, inplace=True)
# 		df1 = df1.fillna('')

# 		dict2 = df1[
# 			['i', 'mese', 'prodotta_campo', 'immessa_campo', 'prelevata_campo', 'prodotta_ed', 'immessa_ed', 'prelevata_ed',
# 			 'prodotta_gse', 'immessa_gse', 'check_misure', 'comments', 'prodotta_def']].to_dict('records')

# 	except Exception as error:
# 		print(f'Errore elaborazione Tabella Misure', type(error).__name__, "–", error)
# 		dict2 = {}

# 	table_data = {
# 		'anno': anno,
# 		'TableMisure': dict2,
# 		'info': dz_impianto,
# 	}
# 	return table_data


# def energievolumi_dati(nickname):
# 	# ESTRAPOLO DATI IMPIANTO DAL DATABASE
# 	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
# 	dz_impianto = model_to_dict(impianto)

# 	dati_mensili = str(impianto.datimensili_set.all()[0])
# 	df_dati_mensili = pd.read_excel(dati_mensili, 'Foglio1', parse_dates=False)

# 	if nickname == 'ionico_foresta':
# 		df_dati_mensili = df_dati_mensili.loc[:df_dati_mensili.MESE.isnull().idxmax() - 1, ['MESE', 'Prodotta', 'Portata DN800', 'Volume derivato']]
# 		df_dati_mensili = df_dati_mensili.rename(columns={'MESE': 'mesi', 'Portata DN800': 'Portata media'})
# 		df_dati_mensili = df_dati_mensili.iloc[-24:].reset_index(drop=True).copy()
# 		df_dati_mensili = df_dati_mensili.fillna('')

# 	else:
# 		df_dati_mensili = df_dati_mensili.rename(columns={df_dati_mensili.columns[0]: 'mesi'})
# 		df_dati_mensili = df_dati_mensili[['mesi', 'Portata media', 'Volume derivato', 'Prodotta']].copy()
# 		df_dati_mensili = df_dati_mensili.dropna(how='all')
# 		df_dati_mensili = df_dati_mensili.iloc[-24:].reset_index(drop=True).copy()
# 		df_dati_mensili = df_dati_mensili.fillna('')

# 	data = {
# 		'mesi': df_dati_mensili['mesi'],
# 		'volumi': df_dati_mensili['Volume derivato'],
# 		'energie': df_dati_mensili['Prodotta'],
# 		'portate_medie': df_dati_mensili['Portata media'],
# 	}
# 	return data


# # ----------------------------------------------------------------------------------------------------------------------
# # 1. VIEW CHE GESTISCE LA VISIONE DEI DATI RELATIVI ALLA TABELLA "CONSORZI"
# class TableConsorzi(APIView):
# 	renderer_classes = [JSONRenderer]
# 	permission_classes = (IsAuthenticated,)

# 	def get(self, request, anno_nickname, format=None):
# 		table_data = tabellaconsorzi_data(anno_nickname)
# 		return Response(table_data)


# 2. VIEW CHE GESTISCE LA VISIONE DEI DATI RELATIVI ALLA TABELLA "CORRISPETTIVI"
class TableCorrispettivi(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)

	def get(self, request, anno_nickname, format=None):
		table_data = tabellacorrispettivi_data(anno_nickname)
		return Response(table_data)


# # 3. VIEW CHE GESTISCE LA VISIONE DEI DATI RELATIVI ALLA TABELLA "MISURE"
# class TableMisure(APIView):
# 	renderer_classes = [JSONRenderer]
# 	permission_classes = (IsAuthenticated,)

# 	def get(self, request, anno_nickname, format=None):
# 		table_data = tabellamisure_data(anno_nickname)
# 		return Response(table_data)


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
    
    # Prova a trovare un contatore associato all'impianto
    try:
        contatore_obj = Contatore.objects.filter(
            Q(impianto_nickname=nickname) | 
            Q(impianto__nickname=nickname)
        ).first()
        
        if contatore_obj:
            # Se abbiamo trovato un contatore, usa il suo ID per filtrare regsegnanti
            anni = list(regsegnanti.objects.filter(contatore=contatore_obj.id)
                                      .values_list('anno', flat=True)
                                      .distinct()
                                      .order_by('anno'))
        else:
            # Se non troviamo un contatore, proviamo a cercare direttamente per nickname
            # Questo presuppone che esista un campo contatore che potrebbe contenere il nickname
            anni = list(regsegnanti.objects.filter(contatore=nickname)
                                      .values_list('anno', flat=True)
                                      .distinct()
                                      .order_by('anno'))
            
            # Se ancora non troviamo nulla, restituiamo una lista vuota o degli anni di default
            if not anni:
                print(f"Nessun anno trovato per l'impianto {nickname}")
                # Restituisci anni di default o una lista vuota
                anni = []
        
        return anni
    
    except Exception as e:
        print(f"Errore nel recupero degli anni disponibili per {nickname}: {str(e)}")
        # Restituisci una lista vuota in caso di errore
        return []

# Aggiungiamo una nuova API view per esporre questi anni
class AvailableYears(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)
	
	def get(self, request, nickname, format=None):
		years = get_available_years(nickname)
		return Response({'years': years})


def ottieni_valore_pun(anno, mese):
    """
    Funzione di utilità per ottenere il valore PUN dal DB o scaricarlo se non presente
    """
    try:
        # Prima verifica se esiste già nel db
        pun_esistente = ValoriPUN.objects.filter(anno=int(anno), mese=int(mese)).first()
        
        if pun_esistente:
            # Se esiste già nel db, usa quel valore
            print(f"PUN per {mese}/{anno} caricato dal database: {pun_esistente.valore_medio}")
            return pun_esistente.valore_medio
        else:
            # Altrimenti, scarica i dati e poi salva nel db
            media_pun_mensile = scarica_dati_pun_mensili(
                int(anno), 
                int(mese), 
                GME_FTP_USERNAME, 
                GME_FTP_PASSWORD, 
                stampare_media_dettaglio=False
            )
            
            # Se il download è andato a buon fine, salva nel db
            if media_pun_mensile is not None:
                ValoriPUN.objects.create(
                    anno=int(anno),
                    mese=int(mese),
                    valore_medio=media_pun_mensile
                )
                print(f"PUN per {mese}/{anno} calcolato e salvato: {media_pun_mensile}")
            return media_pun_mensile
    except Exception as e:
        print(f"Errore nell'ottenimento del PUN per {mese}/{anno}: {e}")
        return None

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
            
            # Cerca contatore sia per impianto che per nickname
            contatore_obj = Contatore.objects.filter(
                models.Q(impianto=impianto_obj.id) | 
                models.Q(impianto_nickname=impianto_obj.nickname)
            ).first()
            
            data_response = [] # Rinomino la variabile per chiarezza

            if not contatore_obj:
                print(f"Nessun contatore trovato per l'impianto {impianto_obj.nome_impianto}")
                
                # Cerca direttamente letture per questo impianto usando regsegnanti
                try:
                    # Usa direttamente regsegnanti invece di DatiMensiliTabella
                    dati_reg = regsegnanti.objects.filter(anno=int(anno_richiesto))
                    
                    # Se il modello regsegnanti non ha un campo impianto ma ha impianto_nickname
                    if hasattr(regsegnanti, 'impianto_nickname'):
                        dati_reg = dati_reg.filter(impianto_nickname=impianto_obj.nickname)
                    
                    print(f"Dati trovati (fallback regsegnanti): {dati_reg.count()} record")
                    
                    for dato in dati_reg:
                        media_pun_mensile = ottieni_valore_pun(anno_richiesto, dato.mese)
                        try:
                            # Usa direttamente le credenziali dal modulo APIgme
                            media_pun_mensile = scarica_dati_pun_mensili(
                                int(anno_richiesto), 
                                dato.mese, 
                                GME_FTP_USERNAME, 
                                GME_FTP_PASSWORD, 
                                stampare_media_dettaglio=False
                            )
                        except Exception as e_pun:
                            print(f"Errore scaricamento PUN per {dato.mese}/{anno_richiesto} (fallback): {e_pun}")
                        
                        # Verifica che prod_campo non sia None e lo converte a float
                        if dato.prod_campo is not None:
                            # Converti Decimal a float prima di moltiplicare
                            prod_campo_float = float(dato.prod_campo)
                            prod_campo_98 = prod_campo_float * 0.98
                            
                            # Verifica anche che imm_campo non sia None
                            if dato.imm_campo is not None:
                                imm_campo_float = float(dato.imm_campo)
                                energia_incentivata = min(prod_campo_98, imm_campo_float)
                            else:
                                energia_incentivata = prod_campo_98
                        else:
                            # Se prod_campo è None, imposta energia_incentivata a 0 o None
                            energia_incentivata = 0
                            prod_campo_float = 0  # Assicurati che sia 0 anche qui
                        
                        data_response.append({
                            'mese': dato.mese,
                            'energia_kwh': energia_incentivata,
                            'corrispettivo_incentivo': None,
                            'corrispettivo_altro': None,
                            'fatturazione_tfo': None,
                            'fatturazione_altro': None,
                            'incassi': None,
                            'controllo_scarto': None,
                            'controllo_percentuale': None,
                            'media_pun_mensile': media_pun_mensile, # Aggiunto valore media PUN
                            'prod_campo_originale': prod_campo_float  # Aggiungiamo il valore originale di prod_campo
                        })
                    
                    return JsonResponse({'success': True, 'data': data_response})
                    
                except Exception as inner_e:
                    print(f"Errore nel tentativo di usare regsegnanti (fallback): {str(inner_e)}")
                
                return JsonResponse({'success': True, 'data': []}) # Risposta vuota se fallback fallisce
            
            print(f"Contatore trovato: ID {contatore_obj.id}")
            
            dati_reg = regsegnanti.objects.filter(contatore=contatore_obj, anno=int(anno_richiesto))
            print(f"Dati trovati (regsegnanti con contatore): {dati_reg.count()} record")
            
            for dato in dati_reg:
                media_pun_mensile = ottieni_valore_pun(anno_richiesto, dato.mese)
                try:
                    # Usa direttamente le credenziali dal modulo APIgme
                    media_pun_mensile = scarica_dati_pun_mensili(
                        int(anno_richiesto), 
                        dato.mese, 
                        GME_FTP_USERNAME, 
                        GME_FTP_PASSWORD, 
                        stampare_media_dettaglio=False
                    )
                except Exception as e_pun:
                    print(f"Errore scaricamento PUN per {dato.mese}/{anno_richiesto}: {e_pun}")
                    media_pun_mensile = None

                # Verifica che prod_campo non sia None e lo converte a float
                if dato.prod_campo is not None:
                    # Converti Decimal a float prima di moltiplicare
                    prod_campo_float = float(dato.prod_campo)
                    prod_campo_98 = prod_campo_float * 0.98
                    
                    # Verifica anche che imm_campo non sia None
                    if dato.imm_campo is not None:
                        imm_campo_float = float(dato.imm_campo)
                        energia_incentivata = min(prod_campo_98, imm_campo_float)
                    else:
                        energia_incentivata = prod_campo_98
                else:
                    # Se prod_campo è None, imposta energia_incentivata a 0 o None
                    energia_incentivata = 0
                    prod_campo_float = 0  # Assicurati che sia 0 anche qui
                
                data_response.append({
                    'mese': dato.mese,
                    'energia_kwh': energia_incentivata,
                    'corrispettivo_incentivo': None,
                    'corrispettivo_altro': None,
                    'fatturazione_tfo': None,
                    'fatturazione_altro': None,
                    'incassi': None,
                    'controllo_scarto': None,
                    'controllo_percentuale': None,
                    'media_pun_mensile': media_pun_mensile, # Aggiunto valore media PUN
                    'prod_campo_originale': prod_campo_float  # Aggiungiamo il valore originale di prod_campo
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


