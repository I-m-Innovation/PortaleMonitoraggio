from django.contrib import admin

from .models import (
    FotovoltaicoMetadata,
    FvMetadata,
    IdroelettricoMetadata,
    ImpiantoAnagrafica,
    ImpiantoDispositivo,
    ImpiantoSorgenteDati,
)


@admin.register(FvMetadata)
class FvMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome_impianto",
        "nome_proprietario",
        "nome_cliente",
        "categoria_fv",
        "is_ppu",
        "is_in_costruzione",
        "data_inizio_contratto",
        "data_fine_contratto",
        "pr_contrattuale",
        "potenza",
        "updated_at",
    )
    list_filter = ("categoria_fv", "is_ppu", "is_in_costruzione")
    search_fields = (
        "nome_impianto",
        "nome_proprietario",
        "nome_cliente",
        "impianto__nickname",
        "impianto__nome_impianto",
        "impianto__societa",
    )
    ordering = ("nome_impianto",)
    raw_id_fields = ("impianto",)
    list_select_related = ("impianto",)
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "nome_impianto",
        "nome_proprietario",
        "nome_cliente",
        "categoria_fv",
        "is_ppu",
        "is_in_costruzione",
        "data_inizio_contratto",
        "data_fine_contratto",
        "pr_contrattuale",
        "potenza",
        "note",
        "impianto",
        "created_at",
        "updated_at",
    )


@admin.register(ImpiantoAnagrafica)
class ImpiantoAnagraficaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome_impianto",
        "tag_impianto",
        "tipo_impianto",
        "codice_impianto",
        "stato_impianto",
        "potenza_installata_kw",
        "nome_proprietario",
        "nome_cliente",
        "attivo_portale",
    )
    list_filter = ("tipo_impianto", "stato_impianto", "attivo_portale")
    search_fields = ("nome_impianto", "tag_impianto", "nome_proprietario", "nome_cliente")
    ordering = ("nome_impianto",)


@admin.register(ImpiantoSorgenteDati)
class ImpiantoSorgenteDatiAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "impianto",
        "tipo_sorgente",
        "nome_sorgente",
        "identificativo_esterno",
        "nome_riferimento_esterno",
        "attiva",
    )
    list_filter = ("tipo_sorgente", "attiva")
    search_fields = (
        "impianto__nome_impianto",
        "impianto__tag_impianto",
        "nome_sorgente",
        "identificativo_esterno",
        "nome_riferimento_esterno",
    )
    list_select_related = ("impianto",)


@admin.register(FotovoltaicoMetadata)
class FotovoltaicoMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "impianto",
        "categoria_fv",
        "is_ppu",
        "is_agrivoltaico",
        "pr_contrattuale",
    )
    list_filter = ("categoria_fv", "is_ppu", "is_agrivoltaico")
    search_fields = ("impianto__nome_impianto", "impianto__tag_impianto")
    list_select_related = ("impianto",)


@admin.register(IdroelettricoMetadata)
class IdroelettricoMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "impianto",
        "categoria_idr",
        "portata_concessione",
        "unita_misura_portata",
        "salto",
        "potenza_business_plan_kw",
    )
    list_filter = ("categoria_idr",)
    search_fields = ("impianto__nome_impianto", "impianto__tag_impianto")
    list_select_related = ("impianto",)


@admin.register(ImpiantoDispositivo)
class ImpiantoDispositivoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "impianto",
        "tipo_dispositivo",
        "codice_dispositivo",
        "attivo",
    )
    list_filter = ("tipo_dispositivo", "attivo")
    search_fields = (
        "impianto__nome_impianto",
        "impianto__tag_impianto",
        "impianto__codice_impianto",
        "codice_dispositivo",
    )
    list_select_related = ("impianto",)
