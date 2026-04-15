from django.contrib import admin

from .models import (
    DocumentoImpianto,
    FotovoltaicoMetadata,
    FotovoltaicoMetricheTecniche,
    FotovoltaicoStatoEconomico,
    IdroelettricoMetadata,
    ImpiantoAnagrafica,
    ImpiantoCommessa,
    ImpiantoDispositivo,
    ImpiantoSorgenteDati,
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
    )
    list_filter = ("tipo_impianto", "stato_impianto")
    search_fields = ("nome_impianto", "tag_impianto", "nome_proprietario", "nome_cliente")
    ordering = ("nome_impianto",)
    fields = (
        "nome_impianto",
        "tag_impianto",
        "codice_impianto",
        "tipo_impianto",
        "stato_impianto",
        "potenza_installata_kw",
        "data_entrata_esercizio",
        "latitudine",
        "longitudine",
        "indirizzo",
        "localita",
        "provincia",
        "regione",
        "nome_proprietario",
        "nome_cliente",
        "note",
    )


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
        "potenza_contratto_kw",
        "is_oem",
        "is_ppu",
        "is_agrivoltaico",
        "pr_contrattuale",
    )
    list_filter = ("categoria_fv", "is_oem", "is_ppu", "is_agrivoltaico")
    search_fields = ("impianto__nome_impianto", "impianto__tag_impianto")
    list_select_related = ("impianto",)
    readonly_fields = ("potenza_installata_kw_readonly",)
    fields = (
        "impianto",
        "categoria_fv",
        "potenza_contratto_kw",
        "potenza_installata_kw_readonly",
        "is_oem",
        "is_ppu",
        "is_agrivoltaico",
        "pr_contrattuale",
        "note_fotovoltaico",
    )

    @admin.display(description="Potenza installata (kW)")
    def potenza_installata_kw_readonly(self, obj):
        if not obj or not obj.impianto:
            return "--"
        value = getattr(obj.impianto, "potenza_installata_kw", None)
        return value if value is not None else "--"


@admin.register(FotovoltaicoStatoEconomico)
class FotovoltaicoStatoEconomicoAdmin(admin.ModelAdmin):
    list_display = (
        "impianto_nome",
        "impianto",
        "data_inizio_contratto",
        "data_fine_contratto",
        "importo_stimato_contratto_annuo",
        "totale_contratto",
        "anni_contratto",
        "totale_annuale_su_mw",
        "totale_annuo",
        "periodicita_canone_mesi",
        "importo_canone_periodico",
        "maturato",
        "fatturato",
        "incassato",
        "data_prossima_fattura",
        "importo_prossima_fattura",
        "costo_sostenuto_straordinario",
        "totale_fatturato_straordinario",
        "margine_straordinario",
        "numero_fatture_straordinarie_annuo",
        "numero_fatture_straordinarie_totali",
        "api_sync_status",
        "api_sync_note",
        "last_api_sync_at",
        "updated_at",
        "created_at",
    )
    list_filter = ("api_sync_status",)
    search_fields = (
        "impianto__nome_impianto",
        "impianto__tag_impianto",
        "impianto__codice_impianto",
    )
    list_select_related = ("impianto",)
    ordering = ("impianto__nome_impianto",)
    readonly_fields = (
        "last_api_sync_at",
        "api_sync_status",
        "api_sync_note",
        "created_at",
        "updated_at",
    )
    fields = (
        "impianto",
        "data_inizio_contratto",
        "data_fine_contratto",
        "importo_stimato_contratto_annuo",
        "totale_contratto",
        "anni_contratto",
        "totale_annuale_su_mw",
        "totale_annuo",
        "periodicita_canone_mesi",
        "importo_canone_periodico",
        "maturato",
        "fatturato",
        "incassato",
        "data_prossima_fattura",
        "importo_prossima_fattura",
        "costo_sostenuto_straordinario",
        "totale_fatturato_straordinario",
        "margine_straordinario",
        "numero_fatture_straordinarie_annuo",
        "numero_fatture_straordinarie_totali",
        "last_api_sync_at",
        "api_sync_status",
        "api_sync_note",
        "note",
        "created_at",
        "updated_at",
    )

    @admin.display(ordering="impianto__nome_impianto", description="Nome impianto")
    def impianto_nome(self, obj):
        return obj.impianto.nome_impianto


@admin.register(FotovoltaicoMetricheTecniche)
class FotovoltaicoMetricheTecnicheAdmin(admin.ModelAdmin):
    list_display = (
        "impianto_nome",
        "impianto",
        "pr_ultimi_12_mesi",
        "mancata_produzione",
        "ore_equivalenti_ultimi_12_mesi",
        "sync_status",
        "last_sync_at",
        "updated_at",
    )
    list_filter = ("sync_status",)
    search_fields = (
        "impianto__nome_impianto",
        "impianto__tag_impianto",
        "impianto__codice_impianto",
    )
    list_select_related = ("impianto",)
    ordering = ("impianto__nome_impianto",)
    readonly_fields = (
        "pr_ultimi_12_mesi",
        "mancata_produzione",
        "ore_equivalenti_ultimi_12_mesi",
        "last_sync_at",
        "sync_status",
        "sync_note",
        "created_at",
        "updated_at",
    )
    fields = (
        "impianto",
        "pr_ultimi_12_mesi",
        "mancata_produzione",
        "ore_equivalenti_ultimi_12_mesi",
        "last_sync_at",
        "sync_status",
        "sync_note",
        "note",
        "created_at",
        "updated_at",
    )

    @admin.display(ordering="impianto__nome_impianto", description="Nome impianto")
    def impianto_nome(self, obj):
        return obj.impianto.nome_impianto


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


@admin.register(ImpiantoCommessa)
class ImpiantoCommessaAdmin(admin.ModelAdmin):
    autocomplete_fields = ("impianto",)
    list_display = (
        "id",
        "impianto",
        "tipo_commessa",
        "codice_commessa",
    )
    list_filter = ("tipo_commessa",)
    search_fields = (
        "impianto__nome_impianto",
        "impianto__tag_impianto",
        "impianto__codice_impianto",
        "codice_commessa",
    )
    list_select_related = ("impianto",)
    ordering = ("impianto__nome_impianto", "tipo_commessa")


@admin.register(DocumentoImpianto)
class DocumentoImpiantoAdmin(admin.ModelAdmin):
    autocomplete_fields = ("impianto",)
    list_display = (
        "id",
        "impianto",
        "file",
        "descrizione",
    )
    search_fields = (
        "impianto__nome_impianto",
        "impianto__tag_impianto",
        "impianto__codice_impianto",
        "descrizione",
        "file",
    )
    list_select_related = ("impianto",)
    ordering = ("impianto__nome_impianto", "descrizione", "id")
