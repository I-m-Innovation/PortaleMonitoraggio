from django.contrib import admin
from django.urls import path,include
from . import views
from . import APIViews

urlpatterns = [
	path('', views.home, name='analisi-home'),
	path('view/<str:nickname>/', views.impianto, name='analisi-impianto'),
	path('api/analisi/<str:nickname>/', APIViews.ChartData.as_view(), name='api-analisi-impianto'),
]