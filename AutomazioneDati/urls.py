from django.urls import path
from . import views  # Importa le tue viste

urlpatterns = [
    path('', views.home, name='automazione-dati'),
    path('panoramica/<str:nickname>/', views.reg_segnanti, name='panoramica-contatore'),
    path('diari-letture/<str:nickname>/', views.diari_letture, name='diari-letture'),
    path('nuovo-contatore/<str:nickname>/', views.nuovo_contatore, name='nuovo-contatore'),
    path('salva-contatore/', views.salva_contatore, name='salva_contatore'),
    path('salva-reg-segnanti/', views.salva_reg_segnanti, name='salva-reg-segnanti'),
    path('salva-dati-letture/', views.salva_dati_letture, name='salva-dati-letture'),
    path('get-kaifa-data/', views.get_kaifa_data, name='get-kaifa-data'),
]
