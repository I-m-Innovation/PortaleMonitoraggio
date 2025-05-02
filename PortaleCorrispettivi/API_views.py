from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated
from django.forms.models import model_to_dict

import numpy as np
import pandas as pd
from datetime import datetime,timedelta

import PortaleCorrispettivi.utils.functions as fn
from .models import *


# FUNZIONE LETTURA DATI DIARI LETTURE
def load_diariletture(diari_letture, sheet_letture):
	# CARICAMENTO DATI DIARI DELLE LETTURE
	df = pd.concat([pd.read_excel(diario, sheet_letture, parse_dates=False) for diario in diari_letture])
	# RIMOZIONE COLONNE VUOTE
	df = df.dropna(axis=1, how='all')
	# FORMATTAZIONE DATAFRAME IN NUMERI
	df.iloc[:, 1:] = df.iloc[:, 1:].apply(pd.to_numeric, errors='coerce')
	df = df.astype('float64', errors='ignore')

	df.reset_index(drop=True, inplace=True)
	df['mese'] = pd.to_datetime(df['mese'])
	df.reset_index(drop=True, inplace=True)
	return df


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


def tabellaconsorzi_data(anno_nickname):
	# DA URL ESTRAPOLO ANNO E NICKNAME DELLA REQUEST
	anno = int(anno_nickname.split('_', 1)[0])
	nickname = anno_nickname.split('_', 1)[1]

	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
	dz_impianto = model_to_dict(impianto)

	# EMPTY DATA PER IMPIANTI CHE NON SONO PONTE GIURINO
	if nickname != 'ponte_giurino':
		dict1 = {}
		dict2 = {}

		table_data = {
			'anno': anno,
			'table1': dict1,
			'table2': dict2,
			'info': dz_impianto,
		}
		return Response(table_data)

	# MESI-INTERVALLO DI PONTE GIURINO
	aprile = datetime(anno, 4, 1)
	settembre = datetime(anno, 9, 1)
	ottobre = datetime(anno - 1, 10, 1)

	# PERCORSO DEL DIARIO DELLE LETTURE PER L'ANNO RICHIESTO
	diari_letture = list(impianto.diarioletture_set.all())
	diari_letture = [str(diario) for diario in diari_letture if diario.anno >= anno - 1]
	letture_sheet = '07. Portale'

	# PERCORSO FILE DI CASH FLOW
	diario_cashflow = str(impianto.cashflow_set.all()[0])
	cash_sheet = 'Incassi GSE'

	try:
		DF1 = load_diariletture(diari_letture, letture_sheet)
		# CALCOLO ENERGIA INCENTIVATA DAL CORRISPETTIVO
		DF1['E_incentivata'] = DF1['aspettata_inc'] / 0.21

		DF2 = load_cashflow(diario_cashflow, cash_sheet)

		# SELEZIONE ANNO RICHIESTO DATI CASH FLOW
		DF2 = DF2[DF2[('Fatturazione TFO', 'Periodo')].dt.year >= anno - 1]
		DF2.reset_index(drop=True, inplace=True)

		# AGGIUNGO DATI DI CASH FLOW AL DATAFRAME PRINCIPALE
		DF1['fatturazione_tfo'] = DF2[('Fatturazione TFO', 'Energia di competenza')]
		DF1['fatturazione_non_inc'] = DF2[('Fatturazione Energia non incentivata', 'Energia di competenza')]
		DF1['incassi'] = DF2[('Riepilogo pagamenti', 'Incasso/pagamento')]

		DF1['canone'] = DF1['incassi'] * 0.11
		DF1 = DF1[['mese', 'prodotta_def', 'incassi', 'canone']]
		DF1_before = DF1[(DF1['mese'] < aprile) & (DF1['mese'] >= ottobre)].copy()
		DF1_after = DF1[(DF1['mese'] >= aprile) & (DF1['mese'] <= settembre)].copy()
		DF1_before.reset_index(drop=True, inplace=True)
		DF1_after.reset_index(drop=True, inplace=True)

		DF1_before['mese'] = DF1_before['mese'].dt.month_name(locale='it_IT.utf8') + '-' + DF1_before['mese'].dt.year.astype('string')
		DF1_before.loc['total'] = DF1_before.sum(numeric_only=True,)
		DF1_before.fillna({'mese':'Totale Periodo'},inplace=True)
		DF1_before.fillna('',inplace=True)

		DF1_after['mese'] = DF1_after['mese'].dt.month_name(locale='it_IT.utf8')  + '-' + DF1_after['mese'].dt.year.astype('string')
		DF1_after.loc['total'] = DF1_after.sum(numeric_only=True,)
		DF1_after.fillna({'mese':'Totale Periodo'},inplace=True)
		DF1_after.fillna('', inplace=True)

		dict1 = DF1_before.to_dict('records')
		dict2 = DF1_after.to_dict('records')
		

	except Exception as error:
		print(error)
		dict1 = {}
		dict2 = {}

	table_data = {
		'anno': anno,
		'table1': dict1,
		'table2': dict2,
		'info': dz_impianto,
	}

	print(table_data)
	return table_data


def tabellacorrispettivi_data(anno_nickname):
	# DA URL ESTRAPOLO ANNO E NICKNAME
	anno = int(anno_nickname.split('_', 1)[0])
	nickname = anno_nickname.split('_', 1)[1]

	# MASSIMALI EURO E ENERGIE PER LA VISUALIZZAZIONE
	max_corrispettivi = {'ionico_foresta': 40000, 'san_teodoro': 30000, 'ponte_giurino': 20000, 'petilia_bf_partitore': 20000}
	max_energie = {'ionico_foresta': 157000, 'san_teodoro': 122000, 'ponte_giurino': 67000, 'petilia_bf_partitore': 37000}

	# ESTRAPOLO DATI IMPIANTO DAL DATABASE
	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
	dz_impianto = model_to_dict(impianto)

	# DEFINIZIONE MESE CORRENTE, PRECEDENTE E ANTECEDENTE
	Now = datetime.now()
	curr_mese = datetime(Now.year, Now.month, 1)
	last_mese = curr_mese - timedelta(days=1)
	last_mese = last_mese.replace(day=1)
	last_last_mese = last_mese - timedelta(days=1)
	last_last_mese = last_last_mese.replace(day=1)

	# PERCORSO DEL DIARIO DELLE LETTURE PER L'ANNO RICHIESTO
	diari_letture = list(impianto.diarioletture_set.all())
	letture_sheet = '07. Portale'

	if anno == Now.year:
		diari_letture = [str(diario) for diario in diari_letture if diario.anno >= anno - 1]
	else:
		diari_letture = [str(diario) for diario in diari_letture if diario.anno == anno]

	# PERCORSO FILE DI CASH FLOW
	diario_cashflow = str(impianto.cashflow_set.all()[0])
	cash_sheet = 'Incassi GSE'

	if nickname == 'petilia_bf_partitore':
		cash_sheet = 'Incassi GSE Partitore'

	# CODICE DI ELEABORAZIONE DEI DATI NEI DIARI DELLE LETTURE E CASH FLOW
	try:
		# CARICAMENTO DATI DIARI DELLE LETTURE
		df1 = load_diariletture(diari_letture, letture_sheet)
		df1['i'] = df1.index
		# CALCOLO ENERGIA INCENTIVATA DAL CORRISPETTIVO
		df1['E_incentivata'] = df1['aspettata_inc'] / 0.21

		df2 = load_cashflow(diario_cashflow, cash_sheet)
		# SELEZIONE ANNO RICHIESTO DATI CASH FLOW
		if Now.year == anno:
			df2 = df2[df2[('Fatturazione TFO', 'Periodo')].dt.year >= anno - 1]
		else:
			df2 = df2[df2[('Fatturazione TFO', 'Periodo')].dt.year == anno]
		df2.reset_index(drop=True, inplace=True)

		# AGGIUNGO DATI DI CASH FLOW AL DATAFRAME PRINCIPALE
		df1['fatturazione_tfo'] = df2[('Fatturazione TFO','Energia di competenza')]
		df1['fatturazione_non_inc'] = df2[('Fatturazione Energia non incentivata', 'Energia di competenza')]
		df1['incassi'] = df2[('Riepilogo pagamenti', 'Incasso/pagamento')]

		# CODICE DI CONTROLLO STIME-FATTURAZIONE - TABELLA 1
		# CALCOLO VARIAZIONE TRA STIME E FATTURAZIONE EFFETTIVA, VISUALIZZAZIONE DELLE VARIAZIONI IN EURO (delta_eur) E PERCENTUALE (ratio_eur)
		df1['comments'] = ''
		df1.loc[df1.fatturazione_tfo != 0, 'delta_eur'] = (df1['aspettata_tot'] - (df1['fatturazione_tfo'] + df1['fatturazione_non_inc']))
		df1.loc[df1.fatturazione_tfo != 0, 'ratio_eur'] = (df1['aspettata_tot'] - (df1['fatturazione_tfo'] + df1['fatturazione_non_inc'])) / df1['aspettata_tot'] * 100
		df1['ratio_eur'] = df1['ratio_eur'].replace([-np.inf, np.inf], 100)

		# CONTROLLO FINALE SU INSERIMENTO FATTURE DEGLI ULTIMI DUE MESI
		if anno == Now.year:
			if df1[last_last_mese == df1['mese']].iloc[0]['fatturazione_tfo'] == 0:
				index = df1[last_last_mese == df1['mese']].iloc[0]['i']
				df1.loc[index, 'comments'] = 'fattura'

			if df1[last_last_mese<df1['mese']].iloc[0]['fatturazione_tfo'] == 0:
				index = df1[last_last_mese < df1['mese']].iloc[0]['i']
				df1.loc[index, 'comments'] = 'fattura'

			# SLICE DATI ANNO CORRENTE
			df1 = df1[df1['mese'].dt.year == anno]

		df1['mese'] = df1['mese'].dt.month_name(locale='it_IT.utf8')

		# df1.replace(0, np.nan, inplace=True)
		df1 = df1.fillna('')

		dict1 = df1[['i', 'mese', 'E_incentivata', 'aspettata_inc', 'aspettata_non_inc', 'fatturazione_tfo', 'fatturazione_non_inc', 'incassi', 'ratio_eur','delta_eur','comments']].to_dict('records')

	except Exception as error:
		print(f'Errore elaborazione Tabella Corrispettivi', type(error).__name__, "–", error)
		dict1 = {}

	table_data = {
		'anno': anno,
		'TableCorrispettivi': dict1,
		'info': dz_impianto,
		'max_energia': max_energie[nickname]*1.15,
		'max_corrispettivi': max_corrispettivi[nickname]
	}
	return table_data


def tabellamisure_data(anno_nickname):
	# DA URL ESTRAPOLO ANNO E NICKNAME
	anno = int(anno_nickname.split('_', 1)[0])
	nickname = anno_nickname.split('_', 1)[1]

	# ESTRAPOLO DATI IMPIANTO DAL DATABASE
	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
	dz_impianto = model_to_dict(impianto)

	# DEFINIZIONE MESE CORRENTE, PRECEDENTE E ANTECEDENTE
	Now = datetime.now()
	curr_mese = datetime(Now.year, Now.month, 1)
	last_mese = curr_mese - timedelta(days=1)
	last_mese = last_mese.replace(day=1)
	last_last_mese = last_mese - timedelta(days=1)
	last_last_mese = last_last_mese.replace(day=1)

	# PERCORSO DEL DIARIO DELLE LETTURE PER L'ANNO RICHIESTO
	diari_letture = list(impianto.diarioletture_set.all())
	letture_sheet = '07. Portale'

	if anno == Now.year:
		diari_letture = [str(diario) for diario in diari_letture if diario.anno >= anno - 1]
	else:
		diari_letture = [str(diario) for diario in diari_letture if diario.anno == anno]

	try:
		df1 = load_diariletture(diari_letture, letture_sheet)
		df1['i'] = df1.index
		# CALCOLO ENERGIA INCENTIVATA DAL CORRISPETTIVO
		df1['E_incentivata'] = df1['aspettata_inc'] / 0.21

		# CODICE DI CONTROLLO SULLE MISURE DI ENERGIA - TABELLA 2
		df1['check_misure'] = ''

		# CALCOLO DELTA PERCENTUALI DI PRODUZIONE TRA: CAMPO/e-D e CAMPO/GSE
		delta_prod_ed = (df1['prodotta_campo'] - df1['prodotta_ed']).abs() / df1['prodotta_campo'] * 100
		delta_prod_gse = (df1['prodotta_campo'] - df1['prodotta_gse']).abs() / df1['prodotta_campo'] * 100

		# CALCOLO DELTA PERCENTUALI DI IMMISSIONE TRA: CAMPO/e-D e CAMPO/GSE
		delta_imm_ed = (df1['immessa_campo'] - df1['immessa_ed']).abs() / df1['immessa_campo'] * 100
		delta_imm_gse = (df1['immessa_campo'] - df1['immessa_gse']).abs() / df1['immessa_campo'] * 100

		# ARROTONDAMENTO A DUE CIFRE DECIMALI VALORI
		delta_prod_ed = delta_prod_ed.round(decimals=2)
		delta_prod_gse = delta_prod_gse.round(decimals=2)
		delta_imm_ed = delta_imm_ed.round(decimals=2)
		delta_imm_gse = delta_imm_gse.round(decimals=2)

		# SOSITTUZIONE VALORI "inf" e TRASFORMAZIONE IN STRRINGHE
		delta_prod_ed = delta_prod_ed.replace([-np.inf, np.inf], '-').astype("string")
		delta_prod_gse = delta_prod_gse.replace([-np.inf, np.inf], '-').astype("string")
		delta_imm_ed = delta_imm_ed.replace([-np.inf, np.inf], '-').astype("string")
		delta_imm_gse = delta_imm_gse.replace([-np.inf, np.inf, ], '-').astype("string")

		# DEFINIZIONE COLONNA CON DELTA PERCENTUALI CHE VENGONO SEPARATI E ELABORATI NEL FRONT-END
		df1['check_misure'] = df1.check_misure.add(delta_prod_gse, fill_value='') + '_' + df1.check_misure.add(
			delta_prod_ed, fill_value='') + '_' + df1.check_misure.add(delta_imm_gse,
		                                                             fill_value='') + '_' + df1.check_misure.add(
			delta_imm_ed, fill_value='')

		# CHECK FINALE DI INSERIMENTO MISURE PER ULTIMI DUE MESI
		if anno == Now.year:
			if df1[last_last_mese == df1['mese']].iloc[0]['prodotta_campo'] == 0 or df1[last_last_mese == df1['mese']].iloc[0]['prodotta_gse'] == 0:
				index = df1[last_last_mese == df1['mese']].iloc[0]['i']
				df1.loc[index, 'check_misure'] = 'misure'

			if df1[last_last_mese < df1['mese']].iloc[0]['prodotta_campo'] == 0 or df1[last_last_mese < df1['mese']].iloc[0][
				'prodotta_gse'] == 0:
				index = df1[last_last_mese < df1['mese']].iloc[0]['i']
				df1.loc[index, 'check_misure'] = 'misure'

			# SLICE SU DATI ANNO CORRENTE
			df1 = df1[df1['mese'].dt.year == anno]

		# CODICE DI GESTIONE DEI COMMENTI SULLE MISURE
		# comments = impianto.Commento.objects.filter(impianto=nickname)
		comments = impianto.commento_set.all()
		comments = list(comments.values())
		comments = [comment for comment in comments if comment['mese_misura'].year == anno]

		df1['comments'] = ''

		for comment in comments:
			df1.loc[df1.index[comment['mese_misura'].month - 1], 'comments'] = comment['testo'] + '&' + comment['stato']

		df1['mese'] = df1['mese'].dt.month_name(locale='it_IT.utf8')
		df1.replace(0, np.nan, inplace=True)
		df1 = df1.fillna('')

		dict2 = df1[
			['i', 'mese', 'prodotta_campo', 'immessa_campo', 'prelevata_campo', 'prodotta_ed', 'immessa_ed', 'prelevata_ed',
			 'prodotta_gse', 'immessa_gse', 'check_misure', 'comments', 'prodotta_def']].to_dict('records')

	except Exception as error:
		print(f'Errore elaborazione Tabella Misure', type(error).__name__, "–", error)
		dict2 = {}

	table_data = {
		'anno': anno,
		'TableMisure': dict2,
		'info': dz_impianto,
	}
	return table_data


def energievolumi_dati(nickname):
	# ESTRAPOLO DATI IMPIANTO DAL DATABASE
	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
	dz_impianto = model_to_dict(impianto)

	dati_mensili = str(impianto.datimensili_set.all()[0])
	df_dati_mensili = pd.read_excel(dati_mensili, 'Foglio1', parse_dates=False)

	if nickname == 'ionico_foresta':
		df_dati_mensili = df_dati_mensili.loc[:df_dati_mensili.MESE.isnull().idxmax() - 1, ['MESE', 'Prodotta', 'Portata DN800', 'Volume derivato']]
		df_dati_mensili = df_dati_mensili.rename(columns={'MESE': 'mesi', 'Portata DN800': 'Portata media'})
		df_dati_mensili = df_dati_mensili.iloc[-24:].reset_index(drop=True).copy()
		df_dati_mensili = df_dati_mensili.fillna('')

	else:
		df_dati_mensili = df_dati_mensili.rename(columns={df_dati_mensili.columns[0]: 'mesi'})
		df_dati_mensili = df_dati_mensili[['mesi', 'Portata media', 'Volume derivato', 'Prodotta']].copy()
		df_dati_mensili = df_dati_mensili.dropna(how='all')
		df_dati_mensili = df_dati_mensili.iloc[-24:].reset_index(drop=True).copy()
		df_dati_mensili = df_dati_mensili.fillna('')

	data = {
		'mesi': df_dati_mensili['mesi'],
		'volumi': df_dati_mensili['Volume derivato'],
		'energie': df_dati_mensili['Prodotta'],
		'portate_medie': df_dati_mensili['Portata media'],
	}
	return data


# ----------------------------------------------------------------------------------------------------------------------
# 1. VIEW CHE GESTISCE LA VISIONE DEI DATI RELATIVI ALLA TABELLA "CONSORZI"
class TableConsorzi(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)

	def get(self, request, anno_nickname, format=None):
		table_data = tabellaconsorzi_data(anno_nickname)
		return Response(table_data)


# 2. VIEW CHE GESTISCE LA VISIONE DEI DATI RELATIVI ALLA TABELLA "CORRISPETTIVI"
class TableCorrispettivi(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)

	def get(self, request, anno_nickname, format=None):
		table_data = tabellacorrispettivi_data(anno_nickname)
		return Response(table_data)


# 3. VIEW CHE GESTISCE LA VISIONE DEI DATI RELATIVI ALLA TABELLA "MISURE"
class TableMisure(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)

	def get(self, request, anno_nickname, format=None):
		table_data = tabellamisure_data(anno_nickname)
		return Response(table_data)


class DatiReportImpianto(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)

	def get(self, request, nickname, format=None):
		data = energievolumi_dati(nickname)
		return Response(data)
