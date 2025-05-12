from django.contrib import admin
from django.urls import path,include
from . import views, API_views
from .API_views import dati_mensili_tabella_api


urlpatterns = [
	path('corrispettivi-home/', views.home, name='corrispettivi-home'),
	path('dettaglio/<str:nickname>/', views.impianto, name='dettaglio-corrispettivi'),
	path('report/<str:nickname>/', views.view_report_impianto, name='report-impianto'),
	# path('api/dati-report/<str:nickname>/', API_views.DatiReportImpianto.as_view(), name='report-impianto-dati'),
	path('api/corrispettivi/<str:anno_nickname>/', API_views.TableCorrispettivi.as_view(), name='api-table-corrispettivi'),
	# path('api/misure/<str:anno_nickname>/', API_views.TableMisure.as_view(), name='api-table-misure'),
	# path('api/consorzi/<str:anno_nickname>/', API_views.TableConsorzi.as_view(), name='api-table-consorzi'),
	path('report/<str:nickname>/reportpfd/', views.genera_reportPDF, name='genera-report-pdf'),
	path('api/dati-mensili-tabella/', API_views.dati_mensili_tabella_api, name='dati_mensili_tabella_api'),
]