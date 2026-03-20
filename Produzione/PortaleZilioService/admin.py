from django.contrib import admin

from .models import FvMetadata


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
        "totale_contratto",
        "totale_annuo_su_mv",
        "totale_annuo",
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
        "totale_contratto",
        "totale_annuo_su_mv",
        "totale_annuo",
        "potenza",
        "note",
        "impianto",
        "created_at",
        "updated_at",
    )
