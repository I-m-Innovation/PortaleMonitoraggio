from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse

from MonitoraggioImpianti.utils import functions as fn
from AnalisiDatiImpianti.utils import report as report
from MonitoraggioImpianti.models import *

from .forms import GeneraReportForm

import pandas as pd
from datetime import datetime, timedelta


@login_required(login_url='login')
def home(request):
	from MonitoraggioImpianti.utils.graphics import createMap
	dz_impianti = Impianto.objects.all().values()
	df_impianti = pd.DataFrame(dz_impianti)
	map = createMap(df_impianti, True, 6)

	# FILTRO IMPIANTI IDROELETTRICI
	dz_impianti = {v['nickname']: v for v in dz_impianti if v['tipo'] == 'Idroelettrico'}
	context = {
		'headtitle': 'Archivio dati',
		'impianti': dz_impianti,
		'map': map
	}
	# context['map'] = context['map'].replace('<div style="width:100%;">','<div>')
	context['map'] = context['map'].replace('<div style="position:relative;width:100%;height:0;padding-bottom:60%;">','<div style="position:relative;height:0;padding-bottom:85%;">')
	return render(request, 'AnalisiDatiImpianti/HomePageAnalisi.html', context=context)


@login_required(login_url='login')
def impianto(request, nickname):
	if nickname == 'petilia_bf_canaletta':
		return redirect('analisi-home')

	dz_impianti = Impianto.objects.all().values()
	impianto = Impianto.objects.filter(nickname=nickname)[0]
	Now = datetime.now()

	# POST METHOD PER GENERARE IL REPORT DI ANALISI DELL'IMPIANTO
	if request.method == 'POST':
		print(request.POST)
		form = GeneraReportForm(request.POST)

		if datetime.strptime(request.POST.get('datetime_start'),'%Y-%m-%dT%H:%M') > Now:
			form.add_error('datetime_start', "Inserire una data precedente a oggi")

		if datetime.strptime(request.POST.get('datetime_end'),'%Y-%m-%dT%H:%M') > Now:
			form.add_error('datetime_end', "Inserire una data precedente a oggi")

		if datetime.strptime(request.POST.get('datetime_start'),'%Y-%m-%dT%H:%M') > datetime.strptime(request.POST.get('datetime_end'),'%Y-%m-%dT%H:%M'):
			form.add_error('datetime_start', "Intervallo non valido (data inizio > data fine)")

		if form.is_valid():
			from MonitoraggioImpianti.utils.graphics import plot_analisi_dati_impianto
			form = form.cleaned_data
			start = form['datetime_start'].replace(tzinfo=None)
			end = form['datetime_end'].replace(tzinfo=None)
			if end.hour == 0:
				end = end - timedelta(minutes=1)

			time_series_year_file = impianto.filemonitoraggio_set.filter(tipo='YearTL')[0]
			df_TS = fn.read_DATA(time_series_year_file.cartella, str(time_series_year_file), nickname)
			if impianto.unita_misura == 'l/s':
				df_TS['Q'] = df_TS['Q'] * 1000

			chart, df_misure, df_BP, df_target_portata = plot_analisi_dati_impianto(df_TS, start, end, impianto)
			PDF = report.generaPDF_datiTecnici(impianto.__dict__, df_misure, df_target_portata, df_BP,  start, end, chart)
			return FileResponse(PDF, as_attachment=True, filename="report_{impianto}_{data}.pdf".format(impianto=nickname, data=datetime.now().strftime('%d_%m_%y')))

	elif request.method == 'GET':
		# INSERISCO FORM NEL CONTESTO
		form = GeneraReportForm(initial={'impianto': nickname})

	# FILTRO IMPIANTI IDROELETTRICI
	dz_impianti = {v['nickname']: v for v in dz_impianti if v['tipo'] == 'Idroelettrico'}

	Now = datetime.now()
	tdelta_day = (Now - datetime(Now.year, Now.month, Now.day, 0, 0, 0)).total_seconds()
	tdelta_month = (Now - datetime(Now.year, Now.month, 1, 0, 0, 0)).total_seconds()
	tdelta_year = (Now - datetime(Now.year, 1, 1, 0, 0, 0)).total_seconds()
	mese = pd.Series(Now).dt.month_name(locale='it_IT.utf8')[0]
	anno = Now.year
	oggi = Now.strftime('%d/%m/%Y %H:%M')

	DayStatFile = impianto.filemonitoraggio_set.filter(tipo='DayStat')[0]
	MonthStatFile = impianto.filemonitoraggio_set.filter(tipo='MonthStat')[0]
	YearStatFile = impianto.filemonitoraggio_set.filter(tipo='YearStat')[0]

	dz_daystat = fn.read_DATA(DayStatFile.cartella, str(DayStatFile), nickname).to_dict('records')[0]
	dz_monthstat = fn.read_DATA(MonthStatFile.cartella, str(MonthStatFile), nickname).to_dict('records')[0]
	dz_yearstat = fn.read_DATA(YearStatFile.cartella, str(YearStatFile), nickname).to_dict('records')[0]

	dz_daystat['Vol_deriv'] = dz_daystat['QMean'] * tdelta_day
	dz_monthstat['Vol_deriv'] = dz_monthstat['QMean'] * tdelta_month
	dz_yearstat['Vol_deriv'] = dz_yearstat['QMean'] * tdelta_year

	if impianto.unita_misura != 'mc/s':
		dz_daystat['QMean'] = dz_daystat['QMean']*1000
		dz_monthstat['QMean'] = dz_monthstat['QMean'] * 1000
		dz_yearstat['QMean'] = dz_yearstat['QMean'] * 1000

	context = {
		'headtitle': 'Dettaglio impianto',
		'nickname': nickname,
		'impianto': impianto.__dict__,
		'impianti': dz_impianti,
		'oggi': oggi,
		'curr_mese': mese,
		'curr_anno': anno,
		'daystat': dz_daystat,
		'monthstat': dz_monthstat,
		'yearstat': dz_yearstat,
		'form': form
	}

	StatALL = {stat.variabile: stat.valore for stat in list(impianto.infostat_set.all())}
	impianto = impianto.__dict__
	impianto.update(StatALL)

	# PAGINA ATTIVA, EVIDENZIARE LA PAGINA ATTIVA NEL MENU A LATO
	context['impianto']['active'] = True

	return render(request, 'AnalisiDatiImpianti/dettaglio_idroelettrico.html', context=context)


