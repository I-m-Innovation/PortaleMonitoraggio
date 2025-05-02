from django.contrib import admin
from .models import *


@admin.action(description="Cambia periferica --> Y:/")
def cambia_periferica_Y(modeladmin, request, queryset):
	queryset.update(unit='Y:/')

@admin.action(description="Cambia periferica --> X:/")
def cambia_periferica_X(modeladmin, request, queryset):
	queryset.update(unit='X:/')

@admin.action(description="Cambia periferica --> Z:/")
def cambia_periferica_Z(modeladmin, request, queryset):
	queryset.update(unit='Z:/')


@admin.register(Impianto)
class ImpiantoAdmin(admin.ModelAdmin):
	list_filter = ['tipo', 'proprieta']
	list_display = [field.name for field in Impianto._meta.fields]
	form = ImpiantoForm


@admin.register(Commento)
class CommentoAdmin(admin.ModelAdmin):
	list_filter = ['impianto']
	list_display = [field.name for field in Commento._meta.fields]
	form = AddCommentoForm


@admin.register(DiarioLetture)
class DiarioLettureAdmin(admin.ModelAdmin):
	list_filter = ['impianto', 'anno']
	list_display = [field.name for field in DiarioLetture._meta.fields]
	form = AddDiarioLettureForm
	actions = [cambia_periferica_X, cambia_periferica_Y, cambia_periferica_Z]


@admin.register(Cashflow)
class CashflowAdmin(admin.ModelAdmin):
	list_filter = ['impianto']
	list_display = [field.name for field in Cashflow._meta.fields]
	form = AddCashflowForm
	actions = [cambia_periferica_X, cambia_periferica_Y, cambia_periferica_Z]


@admin.register(DatiMensili)
class DatiMensiliAdmin(admin.ModelAdmin):
	list_filter = ['impianto']
	list_display = [field.name for field in DatiMensili._meta.fields]
	form = AddDatiMensiliForm
	actions = [cambia_periferica_X, cambia_periferica_Y, cambia_periferica_Z]


@admin.register(linkportale)
class linkportaleAdmin(admin.ModelAdmin):
	list_display = [field.name for field in linkportale._meta.fields]
	form = linkportaleForm
