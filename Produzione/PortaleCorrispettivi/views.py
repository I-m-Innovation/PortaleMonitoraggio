from django.forms import model_to_dict
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
import json
import io
import pandas as pd
from datetime import datetime
import numpy as np

from PortaleCorrispettivi.utils import functions as fn
from PortaleCorrispettivi.utils import graphics as gf

from .models import *

from .models import DiarioLetture


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
	print
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

	# Scegli un nickname di default per la pagina home (o da query string)
	nickname = request.GET.get('nickname')
	if not nickname:
		# Se non specificato, prendi il primo disponibile
		first_imp = impianti.first()
		nickname = getattr(first_imp, 'nickname', '') if first_imp else ''

	# Crea lista dei nickname per sommare tutti gli impianti nel grafico
	impianti_list = [imp.nickname for imp in impianti if imp.nickname]
	impianti_json = json.dumps(impianti_list)  # Converte in JSON per il template

	context = {
		# PAGINA
		'link_monitoraggio': link_monitoraggio,
		'link_analisi': link_analisi,
		'page_title': 'Portale Corrispettivi',
		# DATI PAGINA
		'impianti': dz_impianti,
		'curr_anno': curr_anno,
		'nickname': nickname,
		'impianti_json': impianti_json  # Lista JSON di tutti i nickname per il grafico
	}
	return render(request, 'PortaleCorrispettivi/HomePageCorrispettivi.html', context=context)


@login_required(login_url='login')
def impianto(request, nickname):
    # Ottieni l'anno dalla query string, o usa l'anno corrente come default
    anno = request.GET.get('anno', datetime.now().year)
    
    # DATI DEGLI IMPAIANTI
    impianti = Impianto.objects.all().filter(tipo='Idroelettrico')
    impianto = Impianto.objects.all().filter(nickname=nickname)[0]
    df_impianti = pd.DataFrame(impianti.values())
    df_impianti = df_impianti.set_index('nickname')
    dz_impianti = df_impianti.to_dict(orient='index')
    dz_impianto = dz_impianti[nickname]

    # Ottieni gli anni disponibili per questo impianto
    anni_disponibili = list(DiarioLetture.objects.filter(impianto=impianto).values_list('anno', flat=True).distinct())
    print(anni_disponibili)
    
    # Passa l'anno al template
    context = {
        # PAGINA
        'page_title': 'Situazione corrispettivi',
        # DATI PAGINA
        'impianti': dz_impianti,
        'headtitle': 'Dettaglio impianto',
        'nickname': nickname,
        'impianto': dz_impianto,
        
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

