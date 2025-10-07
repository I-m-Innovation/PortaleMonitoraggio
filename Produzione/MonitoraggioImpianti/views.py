import pandas as pd
from datetime import datetime,timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .models import *
from MonitoraggioImpianti.utils import functions as fn
from .API_OpenMeteo import get_OpenMeteoData, get_WeatherIcon


# VIEW MONITORAGGIO - HOME
@login_required
def home(request):
	# PRENDO LINK PORTALE CORRISPETTIVI (NELLA NAV-BAR)
	link_corrispettivi = linkportale.objects.filter(tag='portale-corrispettivi')[0].link

	# INTERVALLO DI REFRESH DELLA HOMEPAGE (SECONDI)
	refresh_interval = 900
	Now = datetime.now()

	# DATI IMPIANTI
	impianti = Impianto.objects.all()
	df_impianti = pd.DataFrame(impianti.values())
	nicks = list(df_impianti['nickname'])
	df_impianti = df_impianti.set_index('nickname')
	dz_impianti = df_impianti.to_dict(orient='index')

	# LAST RUN DEL MATEMATICO, CODICE DI CONTROLLO SUL MATEMATICO
	try:
		last_run = fn.read_DATA('Database_Produzione', 'lastRun.csv', 'Database_Produzione')
		last_run = pd.to_datetime(last_run['t'])
		matematico_down = Now - last_run > timedelta(minutes=30)

	except Exception as error:
		matematico_down = [True]
		print('Errore lettura last run matematico', type(error).__name__, "–", error)

	# CREAZIONE DATAFRAME OER IL MONITORAGGIO GENERALE CON I DATI SULLA SCHEDA DI OGNI IMPIANTO
	df_monitoraggio = pd.DataFrame([{nickname: None} for nickname in nicks],
								dtype='object',
								columns=['Name', 'last_power', 'last_eta', 'state', 'Energy', 'tipo', 'potenza_installata'],
								index=nicks)
	# VALORI DI DEFAULT PER TUTTI GLI IMPIANTI CON ETA = 0 E LED GRIGIO (Off)
	leds = {'O': 'led-green', 'A': 'led-red', 'W': 'led-yellow', 'OK': 'led-green'}
	df_monitoraggio['last_eta'] = 0
	df_monitoraggio['last_power'] = 0
	df_monitoraggio['Energy'] = 0
	df_monitoraggio['state'] = 'led-gray'

	# --------------------------------------------------------------------------------------------------------------#
	# OVERVIEW IMPIANTI - LETTURA "PORTALE IMPIANTI HP.CSV" CON I DATI AGGIORNATI PER LA HOMEPAGE
	# (CONTIENE SOLO DATI PER GLI IMPIANTI DI PROPRIETA)
	# CONTIENE I DATI AGGIORNATI DI: TAG,Name,last_power,last_eta,state,Energy
	try:
		DF_lastDATA_impianti = fn.read_DATA('Database_Produzione', 'Portale impianti HP.csv', 'Database_Produzione')
		DF_lastDATA_impianti = DF_lastDATA_impianti.set_index('TAG')
	except Exception as error:
		DF_lastDATA_impianti = pd.DataFrame()
		print('Errore lettura lastdata impianti', type(error).__name__, "–", error)

	# CREO df_monitoraggio CON I DATI da DF_lastDATA_impianti + I DATI DI:
	# 						led + INFO VARIE (nome_impianto, tipo_impianto, potenza_installata)
	for impianto in list(impianti):
		tag = impianto.tag
		try:
			if matematico_down[0]:
				raise ValueError('matematico down, last run: {}'.format(last_run[0]))
			# AGGIUNTA DATI DAL FILE "Portale impianti HP", PER GLI IMPIANTI CHE CI SONO NEL FILE
			if impianto.tipo == 'Idroelettrico':
				df_monitoraggio.loc[impianto.nickname] = DF_lastDATA_impianti.loc[tag]
				# APPLICO IL LED RELATIVO ALLO STATO DELL'IMPIANTO
				df_monitoraggio.loc[impianto.nickname, 'state'] = leds[df_monitoraggio.loc[impianto.nickname, 'state']]

			# INFO VARIE
			df_monitoraggio.loc[impianto.nickname, 'Name'] = impianto.nome_impianto
			df_monitoraggio.loc[impianto.nickname, 'tipo'] = impianto.tipo
			df_monitoraggio.loc[impianto.nickname, 'potenza_installata'] = impianto.potenza_installata

		except Exception as error:
			print('Errore aggiunta dati al df_monitoraggio', type(error).__name__, "–", error)
			df_monitoraggio.loc[impianto.nickname, 'Name'] = impianto.nome_impianto
			df_monitoraggio.loc[impianto.nickname, 'tipo'] = impianto.tipo
			df_monitoraggio.loc[impianto.nickname, 'potenza_installata'] = impianto.potenza_installata

		# API DATI METEO DA OPEN METEO
		try:
			[weather_code, temp] = get_OpenMeteoData(impianto.lat, impianto.lon)
			[meteo, icona] = get_WeatherIcon(int(weather_code))
			df_monitoraggio.loc[impianto.nickname, 'curr_weather_code'] = weather_code
			df_monitoraggio.loc[impianto.nickname, 'curr_meteo'] = meteo
			df_monitoraggio.loc[impianto.nickname, 'curr_temp'] = str(int(round(temp, 0)))
			df_monitoraggio.loc[impianto.nickname, 'curr_icona'] = icona
		except Exception as error:
			print('Errore lettura dati meteo', type(error).__name__, "–", error)
			df_monitoraggio.loc[impianto.nickname, 'curr_meteo'] = '-'
			df_monitoraggio.loc[impianto.nickname, 'curr_temp'] = '-'
			df_monitoraggio.loc[impianto.nickname, 'curr_icona'] = '-'

	# LED ROSSO PER SA3 MISURA IN WATT FOTVOLTAICO ZILIO_GR
	df_monitoraggio.loc['ionico_SA3', 'state'] = 'led-red'
	df_monitoraggio.loc['zilio_gr', 'Energy'] = df_monitoraggio.loc['zilio_gr', 'Energy']/1000

	# ORDINAMENTO DEL DATAFRAME IN BASE A LED E POI IN BASE A RENDIMENTO
	df_monitoraggio['state'] = pd.Categorical(df_monitoraggio['state'],
											  ['led-red', 'led-yellow', 'led-gray', 'led-green'])
	df_monitoraggio = df_monitoraggio.sort_values(by=['state', 'last_eta'])

	# DATI MONITORAGGIO
	dz_monitoraggio = df_monitoraggio.to_dict(orient="index")

	# CALCOLO INFO GENERALI, POSIZIONATE SULLA SIDEBAR
	# TOTALE ENERGIE DEGLI IMPIANTI CHE CI SONO SU "PORTALE IMPIANTI HP.CSV"
	tot_energy_idro = sum([dz_monitoraggio[key]['Energy'] for key in dz_monitoraggio.keys() if
						   dz_monitoraggio[key]['Energy'] and dz_monitoraggio[key]['tipo'] == 'Idroelettrico'])
	tot_energy_pv = sum([dz_monitoraggio[key]['Energy'] for key in dz_monitoraggio.keys() if
						 dz_monitoraggio[key]['Energy'] and dz_monitoraggio[key]['tipo'] == 'Fotovoltaico'])
	tot_energy = tot_energy_pv + tot_energy_idro
	co2_kg = tot_energy * 0.457
	# TEMPO TRASCORSO DALLA MEZZANOTTE
	tdelta = Now - datetime(Now.year, Now.month, Now.day, 0, 0, 0)
	if tdelta.total_seconds() > 0:
		alberi = int(co2_kg / (tdelta.total_seconds() / 3600) * 24 * 365 / 1000)
		case = int(tot_energy / 9.5)
		tesla_y_dual = int(tot_energy / 75.96)
	else:
		alberi = 0
		case = 0
		tesla_y_dual = 0

	# CONTEXT DATA
	context = {
		# NAV-BAR
		'link_corrispettivi': link_corrispettivi,
		# PAGINA
		'refresh': refresh_interval,
		'page_title': 'Monitoraggio Impianti',
		# DATI - PAGINA
		'alarm_matematico': matematico_down[0],
		'plants_overview': dz_monitoraggio,
		'impianti': dz_impianti,
		# SIDEBAR
		'tot_energia': tot_energy,
		'energia_idro': tot_energy_idro,
		'energia_pv': tot_energy_pv,
		'co2_kg': co2_kg,
		'alberi': alberi,
		'case': case,
		'tesla': tesla_y_dual
	}
	return render(request, 'MonitoraggioImpianti/HomePageMonitoraggio.html', context)


# VIEW MONITORAGGIO - IMPIANTO
@login_required
def impianto(request, nickname):
	# LINK PORTALE CORRISPETTIVI (NELLA NAV-BAR)
	link_corrispettivi = linkportale.objects.filter(tag='portale-corrispettivi')[0].link

	# INTERVALLO DI REFRESH DELLA PAGINA (SECONDI)
	refresh_interval = 3600

	# DATI IMPIANTO
	impianto = Impianto.objects.filter(nickname=nickname)[0]
	# if nickname == 'petilia_bf_canaletta':
	# 	return redirect('monitoraggio-home')

	# SE IMPIANTI FOTOVOLTAICI
	if impianto.tipo == 'Fotovoltaico':
		curr_anno = datetime.now().year
		impianto = impianto.__dict__
		context = {
			# PAGINA
			'link_corrispettivi': link_corrispettivi,
			'page_title': f"Monitoraggio {impianto['nome_impianto']}",
			'refresh': refresh_interval,
			# DATI
			'nickname': nickname,
			'impianto': impianto,
			'curr_anno': curr_anno
		}
		if nickname == 'zilio_gr':
			return render(request, 'MonitoraggioImpianti/monitoraggio_zilio_gr.html', context=context)
		else:
			return render(request, 'MonitoraggioImpianti/monitoraggio_fotovoltaico.html', context=context)

	elif impianto.tipo == 'Idroelettrico':
		try:
			YearStatFile = impianto.filemonitoraggio_set.filter(tipo='YearStat')[0]
			DF_stat = fn.read_DATA(YearStatFile.cartella, str(YearStatFile), nickname)
			# STATISTICHE GLOBALI CALCOLATE DA MATLAB (SALVATE NEL DB)
			StatALL = {stat.variabile: stat.valore for stat in list(impianto.infostat_set.all())}
			impianto = impianto.__dict__
			impianto.update(StatALL)

		except Exception as error:
			print(f'Errore elaborazione pagina {impianto["nome_impianto"]}',type(error).__name__, "–", error)
			impianto = impianto.__dict__
			DF_stat = pd.DataFrame()
			impianto['StatALL'] = {}

		refresh_interval = 3600
		curr_anno = datetime.now().year

		context = {
			# PAGINA
			'link_corrispettivi': link_corrispettivi,
			'page_title': f"Monitoraggio {impianto['nome_impianto']}",
			'refresh': refresh_interval,
			# DATI
			'nickname': nickname,
			'impianto': impianto,
			'curr_anno': curr_anno
		}

		if impianto['unita_misura'] == 'mc/s':
			context['QMedia_anno'] = DF_stat['QMean'][0]
		else:
			context['QMedia_anno'] = DF_stat['QMean'][0]*1000
		return render(request, 'MonitoraggioImpianti/monitoraggio_idroelettrico.html', context=context)

	else:
		return redirect('home')