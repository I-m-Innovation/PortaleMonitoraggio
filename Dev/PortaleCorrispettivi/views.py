from django.forms import model_to_dict
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

import io
import pandas as pd
from datetime import datetime
import numpy as np

from PortaleCorrispettivi.utils import functions as fn
from PortaleCorrispettivi.utils import graphics as gf

from .models import *

# elaborazione dati api
# from PortaleCorrispettivi.API_views import energievolumi_dati as vlm
# from PortaleCorrispettivi.API_views import tabellacorrispettivi_data as tblc
# from PortaleCorrispettivi.API_views import tabellamisure_data as tblm
from PortaleCorrispettivi.API_views import get_available_years

impianti_m3s = ['ionico_foresta', 'ionico_SA3']
# leds = {'O': 'led-green', 'A': 'led-red', 'W': 'led-yellow', 'OK': 'led-green'}

max_corrispettivi = {'ionico_foresta': 40000, 'san_teodoro': 30000, 'ponte_giurino': 20000, 'petilia_bf_partitore': 20000}
max_energie = {'ionico_foresta': 157000, 'san_teodoro': 122000, 'ponte_giurino': 67000, 'petilia_bf_partitore': 37000}


@login_required(login_url='login')
def home(request):
	# Cerca il link del portale di monitoraggio in modo sicuro
	portale_results = linkportale.objects.filter(tag='portale-monitoraggio')
	if portale_results.exists():
		link_monitoraggio = portale_results[0].link
	else:
		# Gestisci il caso in cui non c'è nessun record con tag='portale-monitoraggio'
		link_monitoraggio = "#"  # Imposta un link vuoto o un valore predefinito

	# Gestione sicura per portale-analisi
	analisi_results = linkportale.objects.filter(tag='portale-analisi')
	if analisi_results.exists():
		link_analisi = analisi_results[0].link
	else:
		link_analisi = "#"  # Valore predefinito

	# PRENDO I DATI DEGLI IMPIANTI
	impianti = Impianto.objects.all().filter(tipo='Idroelettrico')
	df_impianti = pd.DataFrame(impianti.values())
	print("Colonne presenti in df_impianti:", df_impianti.columns)
	
	# Controlla se la colonna 'nickname' esiste
	if 'nickname' in df_impianti.columns:
		df_impianti = df_impianti.set_index('nickname')
	else:
		# Se esiste 'Nickname' (con la N maiuscola) la rinominiamo
		if 'Nickname' in df_impianti.columns:
			df_impianti.rename(columns={'Nickname': 'nickname'}, inplace=True)
			df_impianti = df_impianti.set_index('nickname')
		else:
			# Se la colonna non esiste, gestiamo il caso:
			# Ad esempio, impostiamo un indice numerico e logghiamo un messaggio di attenzione
			print("Attenzione: la colonna 'nickname' non esiste in df_impianti. Le colonne presenti sono:", df_impianti.columns)
			df_impianti.index = range(len(df_impianti))
	dz_impianti = df_impianti.to_dict(orient='index')

	Now = datetime.now()
	curr_anno = Now.year

	context = {
		# PAGINA
		'link_monitoraggio': link_monitoraggio,
		'link_analisi': link_analisi,
		'page_title': 'Portale Corrispettivi',
		# DATI PAGINA
		'impianti': dz_impianti,
		'curr_anno': curr_anno
	}
	return render(request, 'PortaleCorrispettivi/HomePageCorrispettivi.html', context=context)


@login_required(login_url='login')
def impianto(request, nickname):
	# Ottieni l'anno dalla query string, o usa l'anno corrente come default
	anno = request.GET.get('anno', datetime.now().year)
	
	# LINK PORTALE MONITORAGGIO (NELLA NAV-BAR)
	# link_monitoraggio = linkportale.objects.filter(tag='portale-monitoraggio')[0].link
	# link_analisi = linkportale.objects.filter(tag='portale-analisi')[0].link

	# DATI DEGLI IMPAIANTI
	impianti = Impianto.objects.all().filter(tipo='Idroelettrico')
	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
	df_impianti = pd.DataFrame(impianti.values())
	df_impianti = df_impianti.set_index('nickname')
	dz_impianti = df_impianti.to_dict(orient='index')
	dz_impianto = dz_impianti[nickname]

	# RICHIAMO I DIARI DELLE LETTURE
	diari_letture = list(impianto.diarioletture_set.all())
	dz_impianto['diari_letture'] = {str(diario.anno): diario.nome for diario in diari_letture}
	anni = list(dz_impianto['diari_letture'].keys())
	
	# Ottieni gli anni disponibili per questo impianto
	anni_disponibili = get_available_years(nickname)

	# POST METHOD --> INSERIMENTO COMMENTO MISURA
	if request.method == 'POST':
		form = AddCommentoForm(request.POST)
		# SE L'ANNO INSERITO NON NEGLI ANNI DEI DIARI
		if request.POST.get('date_input_year') not in anni:
			form.add_error('date_input', "Anno non valido")

		if form.is_valid():
			form = form.cleaned_data
			# SE ESISTE UN COMMENTO VECCHIO PER QUEL MESE/ANNO
			old_comment = impianto.commento_set.filter(mese_misura=form['date_input'])
			if old_comment.exists():
				# SE è STATO SELEZIONATA LA CHECKBOX PER L'ELIMINAZIONE DEL COMMENTO
				if form['delete']:
					old_comment.delete()
					messages.warning(request, f"{form['date_input']} - Il commento è stato eliminato")

				# ALTRIMENTI SI SOVRASCRIVE
				else:
					old_comment.update(testo=form['testo'])
					old_comment.update(stato=form['stato'])
					messages.warning(request, f"{form['date_input']} - Il precedente commento è stato scovrascritto")

			# SE NON ESISTE UN PRECEDENTE COMMENTO PER QUEL MESE/ANNO
			# CREAZIONE NUOVO COMMENTO
			else:
				if form['delete']:
					messages.warning(request, f"{form['date_input']} - Non è presente nessun comento")

				else:
					new_commento = Commento.objects.create(
						testo=form['testo'],
						impianto=form['impianto'],
						stato=form['stato'],
						mese_misura=datetime(form['date_input'].year, form['date_input'].month, 1)
					)
					new_commento.save()
					messages.success(request, f"{form['date_input']} - Commento inserito")

			# SALVATO IL COMMENTO --> RITORNO FORM VUOTO
			form = AddCommentoForm(initial={'impianto': impianto})

	# GET METHOD --> FORM VUTO (INIZIALIZZATO CON IMPIANTO)
	else:
		form = AddCommentoForm(initial={'impianto': impianto})

	# Passa l'anno al template
	context = {
		# PAGINA
		# 'link_monitoraggio': link_monitoraggio,
		# 'link_analisi': link_analisi,
		'page_title': 'Situazione corrispettivi',
		# DATI PAGINA
		'impianti': dz_impianti,
		'headtitle': 'Dettaglio impianto',
		'nickname': nickname,
		'impianto': dz_impianto,
		'diari_letture': dz_impianto['diari_letture'],
		'form': form,
		'anno': anno,
		'curr_anno': str(datetime.now().year),
		'anni_disponibili': anni_disponibili
	}
	return render(request, 'PortaleCorrispettivi/dettaglio_corrispettivi.html', context=context)


@login_required(login_url='login')
def view_report_impianto(request, nickname):
	# LINK PORTALE MONITORAGGIO (NELLA NAV-BAR)
	link_monitoraggio = linkportale.objects.filter(tag='portale-monitoraggio')[0].link
	link_analisi = linkportale.objects.filter(tag='portale-analisi')[0].link

	# DATI DEGLI IMPIANTI
	impianti = Impianto.objects.all().filter(tipo='Idroelettrico')
	df_impianti = pd.DataFrame(impianti.values())
	df_impianti = df_impianti.set_index('nickname')
	dz_impianti = df_impianti.to_dict(orient='index')
	dz_impianto = dz_impianti[nickname]

	# ANNI PER I GRAFICI E STATISTICHE
	Now = datetime.now()
	curr_anno = Now.year
	anno_prec = curr_anno-1

	context = {
		# PAGINA
		'link_monitoraggio': link_monitoraggio,
		'link_analis': link_analisi,
		# DATI PAGINA
		'nickname': nickname,
		'impianto': dz_impianto,
		'curr_anno': curr_anno,
		'anno_prec': anno_prec,
		'unita_misura': dz_impianto['unita_misura'],
		# 'max_energia': max_energie[nickname] * 1.15,
		# 'max_corrispettivi': max_corrispettivi[nickname]
	}
	return render(request, 'PortaleCorrispettivi/report.html', context=context)


@login_required(login_url='login')
def genera_reportPDF(request, nickname):
	from reportlab.pdfgen import canvas
	from reportlab.lib.units import cm
	from reportlab.platypus import Frame, Image, Paragraph, Spacer, Table, TableStyle
	from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
	from reportlab.lib import utils

	# FUNZIONE CREA TABELLA AGGREGATI
	def tabelle_aggregati(DF1, DF2, anno):
		tot_incassi = sum(list(DF1['incassi']))
		tot_fatturato = sum(list(DF1['fatturazione_tfo'] + DF['fatturazione_non_inc']))
		DF2.loc[DF2['prodotta_campo'] == '', 'prodotta_campo'] = 0
		tot_prodotta = sum(list(DF2['prodotta_campo'].astype('float64')))
		aggragati = [
			[Paragraph('<b><font color=white>Aggregati ' + anno + '</font></b>'), ''],
			['Energia prodotta', Paragraph(f'<b>{int(tot_prodotta):,}&nbsp;kWh</b>'.replace(',', '.'))],
			['Totale incassi GSE',
			 Paragraph(f'<b>{tot_incassi:,.2f}&nbsp;€</b>'.replace('.', '$$').replace(',', '.').replace('$$', ','))],
			['Totale fatturato',
			 Paragraph(f'<b>{tot_fatturato:,.2f}&nbsp;€</b>'.replace('.', '$$').replace(',', '.').replace('$$', ','))]
		]
		return aggragati

	# FUNZIONE RE-SIZE IMMAGINI
	def get_image(path, width=1 * cm, height=1 * cm):
		img = utils.ImageReader(path)
		iw, ih = img.getSize()
		if width > 1 * cm:
			aspect = ih / float(iw)
			return Image(path, width=width, height=(width * aspect)), width * aspect
		if height > 1 * cm:
			aspect = iw / float(ih)
			return Image(path, width=(height * aspect), height=height), height * aspect

	# INFO IMPIANTO
	impianto = Impianto.objects.all().filter(nickname=nickname)[0]
	dz_impianto = model_to_dict(impianto)

	# DATI DI PRODUZIONE CENTRALE
	dati_produzione = vlm(nickname)
	DF = pd.DataFrame(dati_produzione)
	DF['mesi'] = DF['mesi'].dt.strftime('%m/%y')
	max_portate = dz_impianto['portata_concessione']
	unita_misura = dz_impianto['unita_misura']

	# GRAFICO ENERGIE, VOLUMI DERIVATI E PORTATE MEDIE
	plot_andamento = gf.plot_andamento_centrale(DF, unita_misura, 8)

	# GRAFICO CON DATI CORRISPETTIVI ANNO CORRENTE
	curr_anno = str(datetime.now().year)
	dati_corrispettivi = tblc(curr_anno+"_"+nickname)
	DF = pd.DataFrame(dati_corrispettivi['TableCorrispettivi'])
	plot_corrispettivi = gf.plot_corrispettivi_centrale2(DF, unita_misura, 11, max_corrispettivi[nickname])

	# TABELLE AGGRAGATI ANNO PRECEDENTE E ANTECEDENTE
	anno_prec = str(datetime.now().year - 1)
	dati_corrispettivi = tblc(anno_prec + "_" + nickname)
	dati_misure = tblm(anno_prec + "_" + nickname)
	DF1 = pd.DataFrame(dati_corrispettivi['TableCorrispettivi'])
	DF2 = pd.DataFrame(dati_misure['TableMisure'])
	aggragati_prec = tabelle_aggregati(DF1, DF2, anno_prec)

	# NEL CASO DI TORRINO FORESTA SKIPPO IL 2022 -> DA RIMUOVERE IL PROSSIMO ANNO
	if not nickname == 'ionico_foresta':
		anno_ante = str(datetime.now().year - 2)
		dati_corrispettivi = tblc(anno_ante + "_" + nickname)
		dati_misure = tblm(anno_ante + "_" + nickname)
		DF1 = pd.DataFrame(dati_corrispettivi['TableCorrispettivi'])
		DF2 = pd.DataFrame(dati_misure['TableMisure'])
		aggragati_ante = tabelle_aggregati(DF1, DF2, anno_ante)

	# GENERAZION PDF
	buffer = io.BytesIO()
	a4_portrait = (841.89, 595.27)
	# slide_format = (1440, 810)
	width, height = a4_portrait
	x_offset = 0.5 * cm
	y_offset = 0.5 * cm
	c = canvas.Canvas(buffer, pagesize=a4_portrait)
	# fonts = c.getAvailableFonts()
	c.setFont('Times-Roman', 18)

	# PER MOSTRARE BORDI
	show_boundaries = False

	# INSERISCO LOGHI IN ALTO A DESTRA DELLA SLIDE
	logo = []
	img1, LOGO1_height = get_image('static/images/zilio_logo.png', width=4.5 * cm)
	logo.append(img1)
	x, y = width - 4.5 * cm - x_offset, height - LOGO1_height - y_offset
	w, h = 4.5 * cm, LOGO1_height
	frame_LOGO1 = Frame(x, y, w, h, showBoundary=show_boundaries, topPadding=0, bottomPadding=0)
	frame_LOGO1.addFromList(logo, c)
	logo = []
	img2, IMG2_height = get_image('static/images/logo_IM.png', width=2 * cm)
	logo.append(img2)
	x, y = width - frame_LOGO1.width - 2 * cm - 2*x_offset, height - frame_LOGO1.height - y_offset
	w, h = 2 * cm, frame_LOGO1.height
	frame_LOGO2 = Frame(x, y, w, h, showBoundary=show_boundaries)
	frame_LOGO2.addFromList(logo, c)

	# INSERISCO I GRAFICI
	images = []
	grafico_andamento, plot1_height = get_image(plot_andamento, width=width - 2 * x_offset)
	images.append(grafico_andamento)
	x, y = x_offset, y_offset
	w, h = width - 2 * x_offset, plot1_height
	frame_andamento = Frame(x, y, w, h, showBoundary=show_boundaries, topPadding=0, bottomPadding=0)
	frame_andamento.addFromList(images, c)
	images = []
	grafico_corrispettivi, plot2_width = get_image(plot_corrispettivi, height=height - frame_andamento.height - 1 * cm)
	images.append(grafico_corrispettivi)
	x, y = x_offset, frame_andamento.height
	w, h = plot2_width, height - frame_andamento.height - 0.5 * cm - y_offset
	frame_corrispettivi = Frame(x, y, w, h, showBoundary=show_boundaries, topPadding=0, bottomPadding=0)
	frame_corrispettivi.addFromList(images, c)

	ts = [
		('SPAN', (0, 0), (1, 0)),
		('BACKGROUND', (0, 1), (2, 3), '#EEEEEE'),
		('GRID', (0, 1), (2, 3), 1, '#FFFFFF'),
		('BACKGROUND', (0, 0), (1, 0), '#4088d4'),
	]

	tables = []
	t = Table(aggragati_prec, style=ts)
	t.wrap(0, 0)
	t.drawOn(c, plot2_width + 1*cm, frame_andamento.height + 2*cm + 4.5 * cm)

	# NEL CASO DI TORRINO FORESTA SKIPPO IL 2022 -> DA RIMUOVERE IL PROSSIMO ANNO
	if not nickname == 'ionico_foresta':
		tables = []
		t = Table(aggragati_ante, style=ts)
		t.wrap(0, 0)
		t.drawOn(c, plot2_width + 1*cm, frame_andamento.height + 2*cm  + 1 * cm)

	impianto = str(dz_impianto['nome_impianto'])
	text = 'Centrale&nbsp;idroelettrica&nbsp;"{impianto}", dati&nbsp;aggiornati&nbsp;{date}'.format(impianto=impianto.replace(' ','&nbsp;'), date=datetime.now().strftime('%d/%m/%y'))
	pp = Paragraph('<font color=grey>'+text+'</font>')
	tables = []
	t = Table([[pp]])
	t.wrap(0, 0)
	t.drawOn(c, plot2_width + 1*cm, frame_andamento.height + y_offset)

	c.save()
	buffer.seek(0)
	return FileResponse(buffer, as_attachment=True, filename="report_{impianto}_{data}.pdf".format(impianto=nickname, data=datetime.now().strftime('%d_%m_%y')))
