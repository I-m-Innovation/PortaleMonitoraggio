 
from django.urls import path
from . import views, API_views


urlpatterns = [
	path('corrispettivi-home/', views.home, name='corrispettivi-home'),
	path('dettaglio/<str:nickname>/', views.impianto, name='dettaglio-corrispettivi'),
	path('report/<str:nickname>/', views.view_report_impianto, name='report-impianto'),
	# path('api/dati-report/<str:nickname>/', API_views.DatiReportImpianto.as_view(), name='report-impianto-dati'),
	
 	path('api/energia-kwh/<str:nickname>/<int:anno>/<int:mese>/', API_views.energiakwh, name='api-energia-kwh'),
	path('api/dati-tfo/<str:nickname>/<int:anno>/<int:mese>/', API_views.datiTFO, name='api-dati-tfo'),
	
	path('api/dati-fatturazione-tfo/<str:nickname>/<int:anno>/<int:mese>/', API_views.datiFatturazioneTFO, name='api-dati-fatturazione-tfo'),
	path('api/dati-energia-non-incentivata/<str:nickname>/<int:anno>/<int:mese>/', API_views.datiEnergiaNonIncentivata, name='api-dati-energia-non-incentivata'),

	path('api/dati-CNI/<str:nickname>/<int:anno>/<int:mese>/', API_views.datiCNI, name='api-dati-CNI'),
	

	# Alias compatibilita' per percorsi usati dal frontend (evita 404)
	path('api/dati-riepilogo-pagamenti/<str:nickname>/<int:anno>/<int:mese>/', API_views.datiRiepilogoPagamenti, name='api-dati-riepilogo-pagamenti'),
	path('api/percentuale-controllo/<str:nickname>/<int:anno>/<int:mese>/', API_views.percentualedicontrollo, name='api-percentuale-controllo'),
	# Commenti tabella corrispettivi
	path('api/salva-commento/', API_views.salva_commento_tabella, name='api-salva-commento-tabella'),
	path('api/commento/<str:nickname>/<int:anno>/<int:mese>/', API_views.get_commento_tabella, name='api-get-commento-tabella'),
	path('api/dati-PUN/<str:nickname>/<int:anno>/<int:mese>/', API_views.datiPUN, name='api-dati-PUN'),
	# Endpoint annuali ottimizzati (riduzione chiamate)
	path('api/annuale/energia-kwh/<str:nickname>/<int:anno>/', API_views.energiakwh_annuale, name='api-energia-kwh-annuale'),
	path('api/annuale/dati-tfo/<str:nickname>/<int:anno>/', API_views.datiTFO_annuale, name='api-dati-tfo-annuale'),
	path('api/annuale/dati-fatturazione-tfo/<str:nickname>/<int:anno>/', API_views.datiFatturazioneTFO_annuale, name='api-dati-fatturazione-tfo-annuale'),
	path('api/annuale/dati-energia-non-incentivata/<str:nickname>/<int:anno>/', API_views.datiEnergiaNonIncentivata_annuale, name='api-dati-energia-non-incentivata-annuale'),
	path('api/annuale/dati-CNI/<str:nickname>/<int:anno>/', API_views.datiCNI_annuale, name='api-dati-CNI-annuale'),
	path('api/annuale/dati-riepilogo-pagamenti/<str:nickname>/<int:anno>/', API_views.datiRiepilogoPagamenti_annuale, name='api-dati-riepilogo-pagamenti-annuale'),
	path('api/annuale/percentuale-controllo/<str:nickname>/<int:anno>/', API_views.percentualedicontrollo_annuale, name='api-percentuale-controllo-annuale'),
	path('api/annuale/commenti/<str:nickname>/<int:anno>/', API_views.get_commenti_annuali, name='api-commenti-annuale'),

	# Tabella misure (per tabella2)
	path('api/misure/<str:anno_nickname>/', API_views.table_misure, name='api-table-misure'),

	# Tabella consorzi (dati annuali)
	path('api/consorzi/<int:anno>/<str:nickname>/', API_views.datitabellaconsorzi, name='api-dati-tabella-consorzi'),

	
]