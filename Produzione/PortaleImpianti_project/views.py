from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from MonitoraggioImpianti.models import *


from django.contrib.auth.decorators import login_required # Importiamo il decoratore necessario

@login_required(login_url='login') 
def HomePage(request):
	# Questa riga verrà eseguita solo se l'utente ha superato il controllo del `@login_required`,
	# ovvero se è già loggato.
	return render(request, 'HomePage.html')


def loadingPageMonitoraggio(request):
	return render(request, 'loading_gif/loading_1.html')


def loadingPageAnalisi(request):
	return render(request, 'loading_gif/loading_2.html')


def loadingPage(request):
	link_corrispettivi = linkportale.objects.filter(tag='portale-corrispettivi')[0].link
	return render(request, 'loading_gif/loading_3.html', {'link_corrispettivi': link_corrispettivi})


def loadingPageCorrispettivi(request):
	link_corrispettivi = linkportale.objects.filter(tag='portale-corrispettivi')[0].link
	return render(request, 'loading_gif/loading_3.html', {'link_corrispettivi': link_corrispettivi})
