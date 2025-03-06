from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from MonitoraggioImpianti.models import *


def HomePage(request):
	return render(request, 'HomePage.html')


def loadingPageMonitoraggio(request):
	return render(request, 'loading_gif/loading_1.html')


def loadingPageAnalisi(request):
	return render(request, 'loading_gif/loading_2.html')


def loadingPage(request):
	link_corrispettivi = linkportale.objects.filter(tag='portale-corrispettivi')[0].link
	return render(request, 'loading_gif/loading_3.html', {'link_corrispettivi': link_corrispettivi})


def loadingPageCorrispettivi(request):
    """
    Gestisce la redirezione alla pagina di caricamento dei corrispettivi.
    Assicurati che il percorso del template (ad esempio 'loading/corrispettivi.html') sia corretto.
    """
    return render(request, 'loading/corrispettivi.html', {})
