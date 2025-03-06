from django.shortcuts import render
from MonitoraggioImpianti.models import Impianto  # Supponiamo che il modello si chiami "Impianto"

def home(request):
    # Filtriamo solo gli impianti con tipo "Idroelettrico"
    impianti = Impianto.objects.filter(tipo='Idroelettrico')
    return render(request, 'home.html', {'impianti': impianti})