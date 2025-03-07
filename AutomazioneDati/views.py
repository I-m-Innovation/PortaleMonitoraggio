from django.shortcuts import render, get_object_or_404
from MonitoraggioImpianti.models import Impianto  # Supponiamo che il modello si chiami "Impianto"

def home(request):
    # Filtriamo solo gli impianti con tipo "Idroelettrico"
    impianti = Impianto.objects.filter(tipo='Idroelettrico')
    return render(request, 'home.html', {'impianti': impianti})

def diariLetture(request):
    return render(request, 'diariLetture.html')

def diari_letture(request, nickname):
    # Recupera l'oggetto Impianto in base al nickname passato nell'URL
    impianto = get_object_or_404(Impianto, nickname=nickname)
    context = {
        'impianto': impianto,
        'num_rows': range(12),  # Genera 12 iterazioni (da 0 a 11)
    }
    return render(request, 'diariLetture.html', context) 
