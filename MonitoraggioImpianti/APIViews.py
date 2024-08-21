from datetime import datetime
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

	def get(self, request, nickname, format = None):
		impianto = Impianto.objects.filter(nickname=nickname)[0]
		if impianto.lettura_dati == 'ftp':
			# NOME FILE "last24hTL"
			time_series_day_file = impianto.filemonitoraggio_set.filter(tipo='last24hTL')[0]

			# PRIMO PASSAGGIO: LETTURA DATI DAI FILE CSV
			try:
				df_time_series = fn.read_DATA(time_series_day_file.cartella, str(time_series_day_file), nickname)

				# COMPLETO LA TimeSeries CON VALORI VUOTI FINO A MEZZANOTTE,
				# CON INTERVALLI DI 15 MIN (CON LA LIBRERIA DA FRONT-END NON RIESCO)
				df_time_series, k_last, t_last, delta = fn.fillTL(df_time_series, '15min')

				# TRASFORMO IN "ORE:MINUTI"
				df_time_series['t'] = df_time_series['t'].dt.strftime('%H:%M')

				# RENDIMENTO
				df_time_series['Eta'] = df_time_series['Eta'] * 100
				# PORTATA
				if impianto.unita_misura == 'l/s':
					df_time_series['Q'] = df_time_series['Q'] * 1000

			except Exception as error:
				df_time_series = pd.DataFrame({'t': [], 'P': [], 'Q': []})
				k_last = t_last = delta = None
				print(f'Errore elaborazione {time_series_day_file}', type(error).__name__, "–", error)

			# SECONDO PASSAGGIO: DATI RELATIVI AI GAUGE (ultimo valore, media e deviazione standard)
			try:
				# LETTURA DATI DEI GAUGE
				dict_gauge = fn.Gauges(impianto)

			except Exception as error:
				dict_gauge = {'Power': [], 'Eta': [], 'colors': [], 'Var2': [], 'Var3': [], 'leds': []}
				print(f'Errore elaborazione dati Gauge {impianto.nome_impianto}', type(error).__name__, "–", error)

			# TERZO PASSAGGIO LETTURA STATO CENTRALE
			try:
				# DIZIONARIO LEDS MONITORAGGIO
				leds = {'O': 'led-green', 'A': 'led-red', 'W': 'led-yellow', 'OK': 'led-green'}
				dfAlarms = fn.read_DATA('Database_Produzione', 'AlarmStatesBeta.csv', 'Database_Produzione')
				# LED IN BASE ALLO STATO
				led = leds[dfAlarms[impianto.tag][0]]
			except Exception as error:
				led = 'led-gray'
				print(f'Errore lettura stato {impianto.nome_impianto}', type(error).__name__, "–", error)

			# fillna sulle celle vuote
			df_time_series[['t', 'P', 'Q']] = df_time_series[['t', 'P', 'Q']].fillna('')

			chart_data = {
				'timestamps': df_time_series.t,
				'potenza': df_time_series.P,
				'portata': df_time_series.Q,
				'last_index': k_last,
				'last_timestamp': t_last,
				'gauges': dict_gauge,
				'led': led
			}
			return Response(chart_data)

		# ISolarCloud
		elif impianto.lettura_dati == 'API_ISC':
			Now = datetime.now()
			nome_impianto = impianto.nome_impianto
			# QUANDO FACCIO LA CHIAMATA PER IL SINGOLO IMPIANTO, METTO UN QUERY PARAMETER
			# E SALTO IL DELAY
			if not request.query_params:
				delay = (impianto.id-9)*10
				print(f"delay: {delay}s")
				sleep(delay)

			# PRENDO I DATI DALL'API DI iSolarCloud
			try:
				# NOME FILE TEMPORANEO CON I DATI DI MONITORAGGIO
				file_path = f'temporary/{nickname}/{nickname}.csv'
				# CONTROLLO CHE CI SIA LA CARTELLA
				os.makedirs(f'temporary/{nickname}', exist_ok=True)
				# SE ESISTE FILE TEMPORANEO
				if os.path.isfile(file_path):
					# CARICO CSV TEMPORANEO
					df_time_series_old = pd.read_csv(file_path)[['t', 'Total']]
					df_time_series_old['t'] = pd.to_datetime(df_time_series_old['t'])
					t_last = df_time_series_old['t'].iloc[-5]
					# CONTROLLO L'ULTIMO TIMESTAMP
					# SE IL TIMESTAMP è DEL GIORNO CORRENTE
					if t_last > datetime(Now.year, Now.month, Now.day, 0, 0, 0):
						# SCARICO I DATI A PARTIRE DALL'ULTIMO TIMESTAMP
						df_time_series, df_status = ISC.getDATA(nome_impianto, start=t_last, end=Now)
						# AGGREGO I DATI
						df_time_series = pd.concat([df_time_series_old.iloc[:-5], df_time_series[['t','Total']]], ignore_index=True)
					# SE IL TIMESTAMP NON è DELLA GIORNATA CORRENTE
					else:
						t_start = datetime(Now.year, Now.month, Now.day, 0, 0, 0)
						df_time_series, df_status = ISC.getDATA(nome_impianto, start=t_start, end=Now)
				# SE NON ESISTE IL FILE TEMPORANEO
				else:
					# SCARICO I FILE DA MEZZANOTTE
					t_start = datetime(Now.year, Now.month, Now.day, 0, 0, 0)
					df_time_series, df_status = ISC.getDATA(nome_impianto, start=t_start, end=Now)
				# SALVO I DATI SU CSV TEMPORANEO
				df_time_series.to_csv(file_path, index=False)

			except Exception as error:
				df_time_series = pd.DataFrame({'t': [], 'P': []})
				df_status = pd.DataFrame({'inv_key': [], 'dev_fault_status': [], 'dev_status': []})
				print(f'Errore getDATA {nome_impianto}', type(error).__name__, "–", error)

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

			except:
				print(f'Mancato ultimo passaggio dati {nome_impianto}')

				chart_data = {
					'time': [],
					'pot': [],
					'k_last': None,
					't_last': None,
					'PLast': None,
					'irg': [],
					'led': 'led-gray',
					'info': {},
				}
			return Response(chart_data)

		elif impianto.lettura_dati == 'API_LEO':
			Now = datetime.now()
			nome_impianto = impianto.nome_impianto

			# PRENDO I DATI DALL'API DI LEONARDO E APPLICO STESSA LOGICA DEI DATI PRESI DA ISOLCLOUD
			try:
				file_path = f'temporary/{nickname}/{nickname}.csv'
				if os.path.isfile(file_path):
					df_time_series_old = pd.read_csv(file_path)
					df_time_series_old['t'] = pd.to_datetime(df_time_series_old['t'])
					t_last = df_time_series_old['t'].iloc[-5]
					if t_last > datetime(Now.year, Now.month, Now.day, 0, 0, 0):
						df_time_series = LEO.get_leo_data(t_start=t_last, t_end=Now)
						df_time_series = pd.concat([df_time_series_old.iloc[:-5], df_time_series], ignore_index=True)
					else:
						t_start = datetime(Now.year, Now.month, Now.day, 0, 0, 0)
						df_time_series = LEO.get_leo_data(t_start=t_start, t_end=Now)
				else:
					t_start = datetime(Now.year, Now.month, Now.day, 0, 0, 0)
					df_time_series = LEO.get_leo_data(t_start=t_start, t_end=Now)
				os.makedirs(f'temporary/{nickname}', exist_ok=True)
				df_time_series.to_csv(file_path, index=False)

			except Exception as error:
				df_time_series = pd.DataFrame({'t': [], 'P': [], 'BESS': [], 'PacHome': [], 'SoC': []})
				print(f'Errore get_leo_data {nome_impianto}', type(error).__name__, "–", error)

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
				led = 'led-green'

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
					'BESSLast': round(df_time_series.BESS[k_last], 2),
					'BESSSoC': round(df_time_series.SoC[k_last], 2),
					'info': {'co2': co2_kg, 'case': case, 'alberi': alberi, 'energy': round(energy, 2), }
				}

			except Exception as error:
				print(f'Errore ultimo passaggio dati {nome_impianto}', type(error).__name__, "–", error)

				chart_data = {
					'time': [],
					'pot': [],
					'bess': [],
					'consumi': [],
					'k_last': None,
					't_last': None,
					'PLast': None,
					'irg': [],
					'led': 'led-gray',
					'info': {},
				}
			return Response(chart_data)