import time
from datetime import datetime, timedelta
import random
from time import sleep
import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

from .models import *

import numpy as np
import pandas as pd

from . import API_ISC as ISC
from . import API_HIGECO as HIGECO
from . import API_MyLeo as LEO
from MonitoraggioImpianti.utils import functions as fn


# calcolo energia e info varie
def info_energy(df, delta):
	energy = np.mean(df['P']) * delta
	co2_kg = energy * 0.457
	Now = datetime.now()
	tdelta = Now - datetime(Now.year, Now.month, Now.day, 0, 0, 0)
	if tdelta.total_seconds() > 0:
		alberi = int(co2_kg / (tdelta.total_seconds() / 3600) * 24 * 365 / 1000)
		case = int(energy / 9.5)
	else:
		alberi = 0
		case = 0
	return energy, alberi, case, co2_kg


class DayChartData(APIView):
	renderer_classes = [JSONRenderer]

	def get(self, request, nickname, format=None):
		print(f"DEBUG: Starting DayChartData.get for nickname: {nickname}")
		impianto = Impianto.objects.filter(nickname=nickname)[0]
		print(f"DEBUG: Found impianto: {impianto.nome_impianto}")
		Now = datetime.now()
		print(f"DEBUG: Current time: {Now}")
		# ---------------------------------------- FTP ---------------------------------------------------
		if impianto.lettura_dati == 'ftp':
			print("DEBUG: Using FTP data reading method")
			# NOME FILE "last24hTL"
			time_series_day_file = impianto.filemonitoraggio_set.filter(tipo='last24hTL')[0]
			print(f"DEBUG: Time series file: {time_series_day_file}")

			# PRIMO PASSAGGIO: LETTURA DATI DAI FILE CSV
			try:
				print("DEBUG: Starting CSV data reading")
				df_time_series = fn.read_DATA(time_series_day_file.cartella, str(time_series_day_file), nickname)
				print(f"DEBUG: Read {len(df_time_series)} rows from CSV")

				# COMPLETO LA TimeSeries CON VALORI VUOTI FINO A MEZZANOTTE,
				# CON INTERVALLI DI 15 MIN (CON LA LIBRERIA DA FRONT-END NON RIESCO)
				df_time_series, k_last, t_last, delta = fn.fillTL(df_time_series, '15min')
				print(f"DEBUG: After fillTL - k_last: {k_last}, t_last: {t_last}, delta: {delta}")

				# TRASFORMO IN "ORE:MINUTI"
				df_time_series['t'] = df_time_series['t'].dt.strftime('%H:%M')
				print("DEBUG: Converted timestamps to HH:MM format")

				# RENDIMENTO
				df_time_series['Eta'] = df_time_series['Eta'] * 100
				print("DEBUG: Converted efficiency to percentage")
				# PORTATA
				if impianto.unita_misura == 'l/s':
					df_time_series['Q'] = df_time_series['Q'] * 1000
					print("DEBUG: Converted flow rate from l/s to ml/s")

			except Exception as error:
				print(f"DEBUG: Exception in CSV processing: {type(error).__name__} - {error}")
				df_time_series = pd.DataFrame({'t': [], 'P': [], 'Q': []})
				k_last = t_last = delta = None
				print(f'Errore elaborazione {time_series_day_file}', type(error).__name__, "–", error)

			# SECONDO PASSAGGIO: DATI RELATIVI AI GAUGE (ultimo valore, media e deviazione standard)
			try:
				print("DEBUG: Starting gauge data processing")
				# LETTURA DATI DEI GAUGE
				dict_gauge = fn.Gauges(impianto)
				print(f"DEBUG: Gauge data processed: {dict_gauge.keys()}")

			except Exception as error:
				print(f"DEBUG: Exception in gauge processing: {type(error).__name__} - {error}")
				dict_gauge = {'Power': [], 'Eta': [], 'colors': [], 'Var2': [], 'Var3': [], 'leds': []}
				print(f'Errore elaborazione dati Gauge {impianto.nome_impianto}', type(error).__name__, "–", error)

			# TERZO PASSAGGIO LETTURA STATO CENTRALE
			try:
				print("DEBUG: Starting alarm state reading")
				# DIZIONARIO LEDS MONITORAGGIO
				leds = {'O': 'led-green', 'A': 'led-red', 'W': 'led-yellow', 'OK': 'led-green'}
				dfAlarms = fn.read_DATA('Database_Produzione', 'AlarmStatesBeta.csv', 'Database_Produzione')
				print(f"DEBUG: Read alarm states, tag: {impianto.tag}")
				# LED IN BASE ALLO STATO
				led = leds[dfAlarms[impianto.tag][0]]
				print(f"DEBUG: LED status: {led}")
			except Exception as error:
				print(f"DEBUG: Exception in alarm state reading: {type(error).__name__} - {error}")
				led = 'led-gray'
				print(f'Errore lettura stato {impianto.nome_impianto}', type(error).__name__, "–", error)

			# fillna sulle celle vuote
			df_time_series[['t', 'P', 'Q']] = df_time_series[['t', 'P', 'Q']].fillna('')
			print("DEBUG: Filled NaN values in dataframe")

			chart_data = {
				'timestamps': df_time_series.t,
				'potenza': df_time_series.P,
				'portata': df_time_series.Q,
				'last_index': k_last,
				'last_timestamp': t_last,
				'gauges': dict_gauge,
				'led': led
			}
			print(f"DEBUG: Prepared chart_data with {len(df_time_series)} data points")
			return Response(chart_data)

		# ---------------------------------------- ISolarCloud ---------------------------------------------------
		elif impianto.lettura_dati == 'API_ISC':
			nome_impianto = impianto.nome_impianto
			# NOME FILE TEMPORANEO CON I DATI DI MONITORAGGIO
			file_path = f'temporary/{nickname}/{nickname}.csv'
			# CONTROLLO CHE CI SIA LA CARTELLA
			os.makedirs(f'temporary/{nickname}', exist_ok=True)
			t_start = datetime(Now.year, Now.month, Now.day, 0, 0, 0)
			# SE ESISTE FILE TEMPORANEO
			if os.path.isfile(file_path):
				df_time_series_old = pd.read_csv(file_path)
				if not df_time_series_old.empty:
					df_time_series_old['t'] = pd.to_datetime(df_time_series_old['t'])
					t_last = df_time_series_old['t'].iloc[-1]
				else:
					t_last = datetime(Now.year, Now.month, Now.day, 0, 0, 0)

				# SE CONTIENE DATI RILEVANTI DELLA GIORNATA
				if t_last > datetime(Now.year, Now.month, Now.day, 0, 30, 0):
					try:
						# SCARICO I DATI A PARTIRE DALL'ULTIMO TIMESTAMP
						df_time_series, df_status = ISC.getDATA(nome_impianto, start=t_last, end=Now)
						# AGGREGO I DATI
						df_time_series = pd.concat([df_time_series_old.iloc[:-1], df_time_series],
												   ignore_index=True)
						if not df_time_series.empty:
							df_time_series.to_csv(file_path, index=False)
					except Exception as error:
						# RITORNO GLI ULTIMI DATI SALVATI
						df_status = pd.DataFrame({'dev_fault_status': []})
						df_time_series = df_time_series_old
						print(f'aggiunta dati - Errore getDATA {nome_impianto}', type(error).__name__, "–", error)

				# SE NON CONTIENE DATI DELLA GIORNATA
				else:
					try:
						# SCARICO I DATI A PARTIRE DALLA MEZZANOTTE
						df_time_series, df_status = ISC.getDATA(nome_impianto, start=t_start, end=Now)
						if not df_time_series.empty:
							df_time_series.to_csv(file_path, index=False)
					except Exception as error:
						df_status = pd.DataFrame({'dev_fault_status': []})
						df_time_series = pd.DataFrame({'t': [], 'Total': []})
						print(f'nuovi dati - Errore getDATA {nome_impianto}', type(error).__name__, "–", error)
			# SE NON ESISTE FILE TEMPORANEO
			else:
				try:
					# SCARICO I DATI A PARTIRE DALLA MEZZANOTTE
					df_time_series, df_status = ISC.getDATA(nome_impianto, start=t_start, end=Now)
					if not df_time_series.empty:
						df_time_series.to_csv(file_path, index=False)
				except Exception as error:
					df_status = pd.DataFrame({'dev_fault_status': []})
					df_time_series = pd.DataFrame({'t': [], 'Total': []})
					print(f'nuovi dati - Errore getDATA {nome_impianto}', type(error).__name__, "–", error)

			try:
				# RIEMPIO DATASET CON DATI NULLI FINO ALLA MEZZANOTTE
				df_time_series, k_last, t_last, delta = fn.fillTL(df_time_series, '5min')
				df_time_series['P'] = df_time_series['Total']

			except Exception as error:
				k_last = t_last = delta = None
				print(f'Errore fillNA {nome_impianto}', type(error).__name__, "–", error)

			try:
				# CALCOLO ENERGIA TOTALE GIORNATA, + ALTRE INFO VARIE
				energy, alberi, case, co2_kg = info_energy(df_time_series, delta)
				# df_status contiene i dati stati degli inverter
				# in base alla documentazion ISC se presenti 2 o 1 come valori, è presente qualche problema
				if 2 in list(df_status.dev_fault_status):
					led = 'led-yellow'
				elif 2 in list(df_status.dev_fault_status) and 1 in list(df_status.dev_fault_status):
					led = 'led-red'
				elif 1 in list(df_status.dev_fault_status):
					led = 'led-red'
				else:
					led = 'led-green'

				if df_status.empty:
					led = 'led-on'

			except Exception as error:
				led = 'led-gray'
				energy = alberi = case = co2_kg = None
				print(f'Mancato ultimo passaggio dati {nome_impianto}')

			df_time_series['t'] = df_time_series['t'].dt.strftime('%H:%M')
			df_time_series['P'] = df_time_series['Total'].fillna('')

			# CONTEXT
			chart_data = {
				'time': df_time_series.t,
				'pot': df_time_series.P,
				'k_last': k_last,
				't_last': t_last,
				'PLast': round(df_time_series.P[k_last], 2),
				'led': led,
				'info': {'co2': co2_kg, 'case': case, 'alberi': alberi, 'energy': round(energy, 2),}
			}
			return Response(chart_data)

		# ---------------------------------------- MyLeonardo ---------------------------------------------------
		elif impianto.lettura_dati == 'API_LEO':
			nome_impianto = impianto.nome_impianto

			# CONTROLLO CHE CI SIA LA CARTELLA
			file_path = f'temporary/{nickname}/{nickname}.csv'
			os.makedirs(f'temporary/{nickname}', exist_ok=True)
			t_start = datetime(Now.year, Now.month, Now.day, 0, 0, 0)
			# SE C'è FILE TEMPORANEO
			if os.path.isfile(file_path):
				df_time_series_old = pd.read_csv(file_path)
				if not df_time_series_old.empty:
					df_time_series_old['t'] = pd.to_datetime(df_time_series_old['t'])
					t_last = df_time_series_old['t'].iloc[-1]
				else:
					t_last = datetime(Now.year, Now.month, Now.day, 0, 0, 0)

				# SE CONTIENE DATI RILEVANTI DELLA GIORNATA
				if t_last > datetime(Now.year, Now.month, Now.day, 0, 30, 0):
					try:
						# SCARICO I DATI A PARTIRE DALL'ULTIMO TIMESTAMP
						df_time_series = LEO.get_leo_data(t_start=t_last, t_end=Now)
						# AGGREGO I DATI
						df_time_series = pd.concat([df_time_series_old[:-1], df_time_series], ignore_index=True)
						df_time_series.to_csv(file_path, index=False)
						dfAlarms = fn.read_DATA('Database_Produzione', 'AlarmStatesBeta.csv', 'Database_Produzione')
						leds = {'O': 'led-green', 'A': 'led-red', 'W': 'led-yellow', 'OK': 'led-green'}
						led = leds[dfAlarms["ZG"][0]]
						print(led)
					except Exception as error:
						# RITORNO GLI ULTIMI DATI SALVATI
						df_time_series = df_time_series_old
						led = 'led-on'
						print(f'Aggiunta nuovi dati - Errore get_leo_data {nome_impianto}',
							  type(error).__name__, "–", error)
				else:
					try:
						# SCARICO I DATI A PARTIRE DALL'ULTIMO TIMESTAMP
						df_time_series = LEO.get_leo_data(t_start=t_start, t_end=Now)
						if not df_time_series.empty:
							df_time_series.to_csv(file_path, index=False)
					except Exception as error:
						# RITORNO GLI ULTIMI DATI SALVATI
						dfAlarms = fn.read_DATA('Database_Produzione', 'AlarmStatesBeta.csv', 'Database_Produzione')
						leds = {'O': 'led-green', 'A': 'led-red', 'W': 'led-yellow', 'OK': 'led-green'}
						led = leds[dfAlarms["ZG"][0]]
						print(led)
						df_time_series = pd.DataFrame({'t': [], 'P': [], 'BESS': [], 'PacHome': [], 'SoC': []})
						print(f'Aggiunta nuovi dati - Errore get_leo_data {nome_impianto}',
							  type(error).__name__, "–", error)
			else:
				try:
					# SCARICO I DATI A PARTIRE DALLA MEZZANOTTE
					df_time_series = LEO.get_leo_data(t_start=t_start, t_end=Now)
					if not df_time_series.empty:
						df_time_series.to_csv(file_path, index=False)
				except Exception as error:
					led = 'led-gray'
					print(f'nuovo file - Errore get_leo_data {nome_impianto}', type(error).__name__, "–", error)
					df_time_series = pd.DataFrame({'t': [], 'P': [], 'BESS': [], 'PacHome': [], 'SoC': []})

			try:
				df_time_series, k_last, t_last, delta = fn.fillTL(df_time_series, '5min')
				# TRASFORMO IN kW (su MyLeo sono in WATT)
				df_time_series['P'] = df_time_series['PacPV'] / 1000
				# POTENZA BATTERIA
				df_time_series['BESS'] = df_time_series['Pbat'] / 1000
				# CONSUMI
				df_time_series['PacHome'] = df_time_series['PacHome'] / 1000
				# RETE
				df_time_series['PacGrid'] = df_time_series['PacGrid'] / 1000
				# BESS %
				df_time_series['SoC'] = df_time_series['SoC']

			except Exception as error:
				k_last = t_last = delta = None
				print(f'Errore fillNA {nome_impianto}', type(error).__name__, "–", error)

			try:
				# CALCOLO ENERGIA TOTALE GIORNATA, + ALTRE INFO VARIE
				energy, alberi, case, co2_kg = info_energy(df_time_series, delta)
				df_time_series['t'] = df_time_series['t'].dt.strftime('%H:%M')
				df_time_series = df_time_series.fillna('')

			except Exception as error:
				energy = alberi = case = co2_kg = None
				print(f'Errore ultimo passaggio dati {nome_impianto}', type(error).__name__, "–", error)

			# CONTEXT
			chart_data = {
				'time': df_time_series.t,
				'pot': df_time_series.P,
				'bess': df_time_series.BESS,
				'consumi': df_time_series.PacHome,
				'rete': df_time_series.PacGrid,
				'k_last': k_last,
				't_last': t_last,
				'led': led,
				'PLast': round(df_time_series.P[k_last], 2),
				'ConsumoLast': round(df_time_series.PacHome[k_last], 2),
				'GridLast': round(df_time_series.PacGrid[k_last], 2),
				'BESSLast': round(df_time_series.BESS[k_last], 2),
				'BESSSoC': round(df_time_series.SoC[k_last], 2),
				'info': {'co2': co2_kg, 'case': case, 'alberi': alberi, 'energy': round(energy, 2), }
			}
			return Response(chart_data)
