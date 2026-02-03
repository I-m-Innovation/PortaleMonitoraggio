from django.contrib import admin
from django.urls import path, include

from . import views, APIViews

urlpatterns = [
    path("", views.home, name="monitoraggio-home"),
    path('view/<str:nickname>/', views.impianto, name='monitoraggio-impianto'),
    path('api/monitoraggio/<str:nickname>/', APIViews.DayChartData.as_view(), name='api-monitoraggio-impianto'),
]