from datetime import datetime
import random
from time import sleep

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

from .models import *

import numpy as np
import pandas as pd

from . import API_ISC_dataQuery as ISC
from . import API_HIGECO_dataQuery as HIGECO
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
			print(nickname)
			return Response(chart_data)

		# ISolarCloud
		elif impianto.lettura_dati == 'API_ISC':

			nome_impianto = impianto.nome_impianto
			# QUANDO FACCIO LA CHIAMATA PER IL SINGOLO IMPIANTO, METTO UN QUERY PARAMETER
			# E SALTO IL DELAY
			if not request.query_params:
				delay = (impianto.id-9)*20
				print(f"delay: {delay}s")
				sleep(delay)

			# PRENDO I DATI DALL'API DI iSolarCloud
			try:
				df_time_series, df_status = ISC.getDATA(nome_impianto)

			except Exception as error:
				df_time_series = pd.DataFrame({'t': [], 'P': []})
				df_status = pd.DataFrame({'inv_key': [], 'dev_fault_status': [], 'dev_status': []})
				print(f'Errore getDATA {nome_impianto}', type(error).__name__, "–", error)

			try:
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


		elif impianto.lettura_dati == 'API_HIGECO':
			nome_impianto = impianto.nome_impianto

			plants = {'zilio_gr': 1, 'dual_im': 0}

			try:
				df_time_series = HIGECO.getDataHIGECO(plants[nickname])

			except:
				df_time_series = pd.DataFrame({'t': [], 'P': []})
				print('Mancata lettura TL {}'.format(nome_impianto))

			try:
				df_time_series, k_last, t_last, delta = fn.fillTL(df_time_series, '5min')

			except:
				k_last = None
				t_last = None
				delta = None
				print('Mancato fillNA {}'.format(nome_impianto))

			try:
				# CALCOLO ENERGIA TOTALE GIORNATA, + ALTRE INFO VARIE
				energy, alberi, case, co2_kg = info_energy(df_time_series, delta)
				df_time_series['t'] = df_time_series['t'].dt.strftime('%H:%M')
				df_time_series['P'] = df_time_series['P'].fillna('')
				led = 'led-green'

				chart_data = {
					'time': df_time_series.t,
					'pot': df_time_series.P,
					'k_last': k_last,
					't_last': t_last,
					'PLast': round(df_time_series.P[k_last], 1),
					'irg': [],
					'led': led,
					'info': {'co2': co2_kg, 'case': case, 'alberi': alberi, 'energy': round(energy, 2)}
				}
				return Response(chart_data, )

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
				}
			return Response(chart_data, )