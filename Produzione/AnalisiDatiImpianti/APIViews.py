from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

from MonitoraggioImpianti.utils import functions as fn
from MonitoraggioImpianti.models import *

import pandas as pd
import numpy as np
from datetime import datetime


class ChartData(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)

	def get(self, request, nickname, format=None):
		print(f"[DEBUG] ChartData API chiamata per impianto: {nickname}")
		
		impianto = Impianto.objects.filter(nickname=nickname)[0]
		print(f"[DEBUG] Impianto trovato: {impianto.nome_impianto}")
		
		time_series_year_file = impianto.filemonitoraggio_set.filter(tipo='YearTL')[0]
		print(f"[DEBUG] File YearTL: {time_series_year_file}")
		
		try:
			print(f"[DEBUG] Tentativo lettura dati da: {time_series_year_file.cartella}/{str(time_series_year_file)}")
			df_TS = fn.read_DATA(time_series_year_file.cartella, str(time_series_year_file), nickname)
			print(f"[DEBUG] Dati letti con successo. Shape: {df_TS.shape}")
			print(f"[DEBUG] Colonne disponibili: {df_TS.columns.tolist()}")
			
			df_TS['t'] = pd.to_datetime(df_TS.t)
			print(f"[DEBUG] Conversione timestamp completata")

		except Exception as e:
			print(f"[DEBUG] Errore nella lettura dati: {e}")
			return

		Now = datetime.now()
		print(f"[DEBUG] Timestamp corrente: {Now}")
		
		today = datetime(Now.year, Now.month, Now.day,0,0,0)
		current_month = datetime(today.year, today.month, 1)
		print(f"[DEBUG] Oggi (00:00): {today}")
		print(f"[DEBUG] Inizio mese corrente: {current_month}")
		
		today_indexes = np.where(df_TS['t']>=today)[0]
		today_max = df_TS.P[today_indexes].max()
		print(f"[DEBUG] Massimo potenza oggi: {today_max} (su {len(today_indexes)} record)")
		
		current_month_indexes = np.where(df_TS['t'] >= current_month)[0]
		month_max = df_TS.P[current_month_indexes].max()
		print(f"[DEBUG] Massimo potenza mese: {month_max} (su {len(current_month_indexes)} record)")
		
		year_max = df_TS.P.max()
		print(f"[DEBUG] Massimo potenza anno: {year_max}")

		df_TS['t'] = df_TS['t'].dt.strftime('%d/%m/%Y %H:%M')
		df_TS['Eta'] = df_TS['Eta'] * 100
		print(f"[DEBUG] Formattazione timestamp e rendimento completata")

		# Aggiungi il timestamp corrente come ultimo punto
		current_timestamp = Now.strftime('%d/%m/%Y %H:%M')
		print(f"[DEBUG] Aggiungendo timestamp corrente: {current_timestamp}")
		
		# Funzione per convertire NaN in None (che diventa null in JSON)
		def nan_to_none(value):
			if pd.isna(value) or np.isnan(value):
				return None
			return value

		Chart_data = {
			'time': df_TS.t.tolist() + [current_timestamp],
			'pot': [nan_to_none(x) for x in df_TS.P.tolist()] + [None],
			'eta': [nan_to_none(x) for x in df_TS.Eta.tolist()] + [None],
			'today_max': nan_to_none(today_max),
			'month_max': nan_to_none(month_max),
			'year_max': nan_to_none(year_max)
		}

		if impianto.unita_misura == 'l/s':
			print(f"[DEBUG] Conversione portata da m³/s a l/s")
			df_TS['Q'] = df_TS['Q'] * 1000

		Chart_data['port'] = [nan_to_none(x) for x in df_TS.Q.tolist()] + [None]
		Chart_data['pres'] = [nan_to_none(x) for x in df_TS.Bar.tolist()] + [None]
		
		print(f"[DEBUG] Dati preparati per risposta. Numero record: {len(df_TS)}")
		print(f"[DEBUG] Unità di misura impianto: {impianto.unita_misura}")
		
		return Response(Chart_data)
