import pandas as pd
import os
from ftplib import FTP
from datetime import datetime, timedelta
import numpy as np


def GET_SAVE_DATA_FTP(folder, filename, nick):
	ftp = FTP("192.168.10.211", timeout=120)
	ftp.login('ftpdaticentzilio', 'Sd2PqAS.We8zBK')
	ftp.cwd('/dati/' + folder)
	gFile = open('temporary/' + nick + '/' + filename, "wb")
	ftp.retrbinary("RETR " + filename, gFile.write)
	gFile.close()
	ftp.close()
	return


def read_DATA(folder, filename, nick):
	file_path = 'temporary/' + nick
	os.makedirs(file_path, exist_ok=True)
	GET_SAVE_DATA_FTP(folder, filename, nick)
	df = pd.read_csv('temporary/' + nick + '/' + filename)
	df.replace([np.inf, -np.inf], np.nan, inplace=True)
	return df


def fillTL(df, interval):
	Now = datetime.now()
	t_start = datetime(Now.year, Now.month, Now.day, 0, 0, 0)
	tt_start = datetime(Now.year, Now.month, Now.day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
	t_end = datetime(Now.year, Now.month, Now.day, 23, 59, 59).strftime('%Y-%m-%d %H:%M:%S')
	df['t'] = pd.to_datetime(df.t)
	t_last = df.t.iloc[-1]
	dfTL = df[df['t'] >= tt_start]
	k_last = len(dfTL) - 1
	forward = pd.DataFrame({'t': pd.date_range(start=t_last, end=t_end, freq=interval)})
	df = pd.concat([dfTL, forward.iloc[1:]], ignore_index=True)
	delta = t_last - t_start
	delta = delta.total_seconds() / 3600
	t_last = t_last.strftime('%Y-%m-%d %H:%M:%S')
	return df, k_last, t_last, delta


def Gauges(impianto):
	# FILE GAUGE IMPIANTO
	FileGauge = impianto.filemonitoraggio_set.filter(tipo='_dati_gauge')[0]

	# LETTURA FILE GAUGE IMPIANTO
	dfGauge = read_DATA(FileGauge.cartella, str(FileGauge), impianto.nickname)
	# ESEMPIO:
	#           , Power  , Var2 , Var3, Eta
	# last_value, 50.8923, 0.020, 30.7, 0.7871017489603646
	# MaxScala  , 248.0  , 0.08 , 50.0, 100.0
	# Media     , 51.226 , 0.012, 31.5, 0.792273080602281
	# Dev       , 2.588  , 0.015, 0.9 , 0.04003722205526605

	# RINOMINO PRIMA COLONNA E IMPOSTO COME INDICE
	dfGauge.columns.values[0] = "keys"
	dfGauge.set_index("keys", inplace=True)

	# COLORE DEL TESTO NEL RISPETTIVO GAUGE
	colors = {}
	# LED NEL RISPETTIVO GAUGE
	leds = {}

	# CICLO CHE ITERA SUI VALORI DI OGNI COLONNA
	for col in dfGauge.columns:
		# SE VALORE O o NON PRESENTE o minore di MEDIA-DEV
		if dfGauge[col].loc['last_value'] < dfGauge[col].loc['Media'] - dfGauge[col].loc['Dev'] or dfGauge[col].loc['last_value'] == 0 or np.isnan(dfGauge[col].loc['last_value']):
			colors[col] = 'rgb(209,65,36)'
			leds[col] = 'led-red'
		# SE COMPRESO tra MEDIA-DEV e MEDIA+DEV
		elif dfGauge[col].loc['last_value'] < dfGauge[col].loc['Media'] + dfGauge[col].loc['Dev']:
			colors[col] = '#3d3d3d'
			leds[col] = 'led-on'
		# SE VALORE maggiore di MEDIA+DEV
		elif dfGauge[col].loc['last_value'] > dfGauge[col].loc['Media'] + dfGauge[col].loc['Dev']:
			colors[col] = 'rgb(31,160,64)'
			leds[col] = 'led-green'

	if impianto.tipo == 'Idroelettrico' and impianto.unita_misura != 'mc/s':
		dfGauge['Var2'] = dfGauge['Var2'] * 1000

	# ULTIMO STEP: MEDIA E DEVIAZIONE STANDARD VANNO PASSATI AL FRONT-END IN PERCENTUALE
	x = dfGauge.iloc[[0, 1]]
	dfGauge[['Power', 'Var2', 'Var3']] = dfGauge[['Power', 'Var2', 'Var3']].div(
		dfGauge[['Power', 'Var2', 'Var3']].iloc[1], axis='columns')
	dfGauge.iloc[[0, 1]] = x

	dfGauge = dfGauge.fillna('')
	dict_gauge = dfGauge.to_dict()
	dict_gauge.update({'colors': colors, 'leds': leds})
	return dict_gauge
