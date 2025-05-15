from django.urls import path
from . import views  # Importa le tue viste
from django.views.decorators.http import require_POST

urlpatterns = [
    path('', views.home, name='automazione-dati'),
    path('panoramica/<str:nickname>/', views.diarioenergie, name='panoramica-contatore'),
    path('diari-letture/<str:nickname>/', views.diari_letture, name='diari-letture'),
    path('nuovo-contatore/<str:nickname>/', views.nuovo_contatore, name='nuovo-contatore'),
    path('sostituzione-contatore/<str:nickname>/', views.sostituzione_contatore, name='sostituzione-contatore'),
    path('salva-contatore/', views.salva_contatore, name='salva_contatore'),
    path('salva-reg-segnanti/', views.salva_diarioenergie, name='salva-reg-segnanti'),
    path('salva-dati-letture/', views.salva_dati_letture, name='salva-dati-letture'),
    path('get-kaifa-data/', views.get_kaifa_data, name='get-kaifa-data'),
    path('impianto/<str:nickname>/sostituzione-contatore/', views.sostituzione_contatore, name='sostituzione_contatore'),
    path('seleziona-contatore-sostituzione/', views.seleziona_contatore_sostituzione, name='seleziona_contatore_sostituzione'),
    path('salva-contatore-sostituzione/', views.salva_contatore_sostituzione, name='salva_contatore_sostituzione'),
    path('elimina-contatore/<int:contatore_id>/', views.elimina_contatore, name='elimina_contatore'),
    
]
