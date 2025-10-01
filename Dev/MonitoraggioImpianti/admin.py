from django.contrib import admin
from .models import *


@admin.register(Impianto)
class ImpiantoAdmin(admin.ModelAdmin):
	list_filter = ['tipo', 'proprieta']
	list_display = [field.name for field in Impianto._meta.fields]
	form = ImpiantoForm


@admin.register(FileMonitoraggio)
class FileMonitoraggioAdmin(admin.ModelAdmin):
	list_filter = ['impianto']
	list_display = [field.name for field in FileMonitoraggio._meta.fields]

	form = FileMonitoraggioForm


@admin.register(InfoStat)
class InfoStatAdmin(admin.ModelAdmin):
	list_filter = ['impianto']
	list_display = [field.name for field in InfoStat._meta.fields]
	form = InfoStatForm


@admin.register(linkportale)
class linkportaleAdmin(admin.ModelAdmin):
	list_display = [field.name for field in linkportale._meta.fields]
	form = linkportaleForm


