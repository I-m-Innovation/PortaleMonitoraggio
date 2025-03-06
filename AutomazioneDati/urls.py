from django.urls import path
from . import views  # Importa le tue viste

urlpatterns = [
    path('', views.home, name='automazione-dati'),
    
]
