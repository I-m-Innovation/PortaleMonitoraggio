from django.urls import path
from . import views, defconatori, reg_segnantitrifascia, reg_segnantimonofasica
from .reg_segnantitrifascia import salva_letture_trifasica, get_letture_trifasica_per_anno, test_connessione, test_dati_database
from .reg_segnantimonofasica import salva_letture_monofasica, get_letture_monofasica_per_anno, test_dati_database_monofasica


urlpatterns = [
    path('', views.home, name='automazione-dati'),
    path('diario-energie/<str:nickname>/', views.diarioenergie, name='panoramica-contatore'),
    path('elenco-contatori/<str:nickname>/', defconatori.elenco_contatori, name='elenco-contatori'),
    path('nuovo-contatore/<str:nickname>/', defconatori.nuovo_contatore, name='nuovo-contatore'),
    path('sostituzione-contatore/<str:nickname>/', defconatori.sostituzione_contatore, name='sostituzione-contatore'),
    path('salva-contatore/', defconatori.salva_contatore, name='salva_contatore'),
    path('impianto/<str:nickname>/reg_segnantitrifascia/<int:contatore_id>/', reg_segnantitrifascia.reg_segnantitrifascia, name='reg_segnantitrifascia'),
    path('impianto/<str:nickname>/sostituzione-contatore/', defconatori.sostituzione_contatore, name='sostituzione_contatore'),
    path('seleziona-contatore-sostituzione/', defconatori.seleziona_contatore_sostituzione, name='seleziona_contatore_sostituzione'),
    path('salva-contatore-sostituzione/', defconatori.salva_contatore_sostituzione, name='salva_contatore_sostituzione'),
    path('elimina-contatore/<int:contatore_id>/', defconatori.elimina_contatore, name='elimina_contatore'),
    path('salva-letture-trifasica/<int:contatore_id>/', salva_letture_trifasica, name='salva-letture-trifasica'),
    path('api/letture-trifasica/<int:contatore_id>/<int:anno>/',  get_letture_trifasica_per_anno,  name='api_get_letture_trifasica_anno'),
    path('automazione/api/letture-trifasica/<int:contatore_id>/<int:anno>/', get_letture_trifasica_per_anno,   name='api_get_letture_trifasica_anno_alt'),
    path('impianto/<str:nickname>/reg_segnantimonofasica/<int:contatore_id>/', reg_segnantimonofasica.reg_segnantimonofasica, name='reg_segnantimonofasica'),
    path('salva-letture-monofasica/<int:contatore_id>/', salva_letture_monofasica, name='salva-letture-monofasica'),
    path('api/letture-monofasica/<int:contatore_id>/<int:anno>/', get_letture_monofasica_per_anno, name='api_get_letture_monofasica_anno'),
    path('automazione/api/letture-monofasica/<int:contatore_id>/<int:anno>/', get_letture_monofasica_per_anno, name='api_get_letture_monofasica_anno_alt'),
    path('api/test-dati-monofasica/<int:contatore_id>/', test_dati_database_monofasica, name='api_test_dati_monofasica'),
    path('api/salva_diario_energie/', views.salva_diario_energie, name='salva_diario_energie'),
    path('modifica-contatore/<int:contatore_id>/', defconatori.modifica_contatore, name='modifica_contatore'),
    path('api/test-connessione/', test_connessione, name='api_test_connessione'),
    path('api/test-dati-trifasica/<int:contatore_id>/', test_dati_database, name='api_test_dati_trifasica'),
]