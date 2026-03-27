from collections import Counter

from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from PortaleZilioService.API_inverter.API_iSolarCloud import get_all_devices, login_ISC

from .models import ImpiantoAnagrafica
from .services.sync import MetricsSyncService

from .services.rows_builder import (
    build_idroelettrico_gse_rows,
    build_idroelettrico_proprieta_rows,
)
from .services.rows_builder_portale import (
    build_agrivoltaico_rows_portale,
    build_fotovoltaico_clienti_rows_portale,
    build_fotovoltaico_in_costruzione_rows_portale,
    build_fotovoltaico_ppu_rows_portale,
    build_fotovoltaico_proprieta_rows_portale,
)


def _build_home_context():
    return {
        "fv_clienti_rows": build_fotovoltaico_clienti_rows_portale(),
        "fv_proprieta_rows": build_fotovoltaico_proprieta_rows_portale(),
        "fv_agrivoltaico_rows": build_agrivoltaico_rows_portale(),
        "fv_in_costruzione_rows": build_fotovoltaico_in_costruzione_rows_portale(),
        "fv_ppu_rows": build_fotovoltaico_ppu_rows_portale(),
        "idr_gse_rows": build_idroelettrico_gse_rows(),
        "idr_proprieta_rows": build_idroelettrico_proprieta_rows(),
    }


def _build_contracts_home_context():
    impianti = ImpiantoAnagrafica.objects.select_related(
        "fotovoltaico_stato_economico",
        "fotovoltaico_metadata",
    ).filter(attivo_portale=True)

    def _fmt_contract_date(value):
        return value.strftime("%d/%m/%Y") if value else ""

    def _fmt_contract_years(data_inizio, data_fine):
        if not data_inizio or not data_fine:
            return ""
        return f"{((data_fine - data_inizio).days / 365.25):.1f}"

    def _contract_type(impianto):
        if impianto.tipo_impianto != ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO:
            return ""
        metadata = getattr(impianto, "fotovoltaico_metadata", None)
        if metadata is None:
            return ""
        if metadata.is_ppu:
            return "PPU"
        if metadata.is_oem:
            return "O&M"
        return ""

    def _contract_group(impianto):
        if impianto.tipo_impianto != ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO:
            return "other"
        metadata = getattr(impianto, "fotovoltaico_metadata", None)
        if metadata is None:
            return "fv_other"
        if metadata.is_oem and not metadata.is_ppu:
            return "fv_oem_only"
        if metadata.is_oem and metadata.is_ppu:
            return "fv_oem_ppu"
        if (not metadata.is_oem) and metadata.is_ppu:
            return "fv_ppu_only"
        return "fv_other"

    def _contract_group_label(group):
        labels = {
            "fv_oem_only": "Impianti O&M",
            "fv_oem_ppu": "Impianti sia O&M che PPU",
            "fv_ppu_only": "Impianti PPU",
            "fv_other": "Altri impianti fotovoltaici",
            "other": "Altri impianti",
        }
        return labels.get(group, "")

    def _sort_key(impianto):
        if impianto.tipo_impianto == ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO:
            group_order = {
                "fv_oem_only": 0,
                "fv_oem_ppu": 1,
                "fv_ppu_only": 2,
                "fv_other": 3,
            }
            group = _contract_group(impianto)
            return (0, group_order[group], impianto.nome_impianto or "")
        return (1, 0, impianto.nome_impianto or "")

    rows = [
        {
            "tipo_impianto": impianto.tipo_impianto,
            "contract_group": _contract_group(impianto),
            "contract_group_label": _contract_group_label(_contract_group(impianto)),
            "nome_impianto": impianto.nome_impianto or "",
            "tipo_contratto": _contract_type(impianto),
            "inizio_contratto": (
                _fmt_contract_date(data_inizio)
                if impianto.tipo_impianto == ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO
                else ""
            ),
            "fine_contratto": (
                _fmt_contract_date(data_fine)
                if impianto.tipo_impianto == ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO
                else ""
            ),
            "anni_contratto": (
                _fmt_contract_years(data_inizio, data_fine)
                if impianto.tipo_impianto == ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO
                else ""
            ),
            "importo_annuo_stimato": (
                getattr(stato_economico, "importo_stimato_contratto_annuo", "")
                if impianto.tipo_impianto == ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO
                else ""
            ),
            "importo_totale": (
                getattr(stato_economico, "totale_contratto", "")
                if impianto.tipo_impianto == ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO
                else ""
            ),
        }
        for impianto in sorted(impianti, key=_sort_key)
        for stato_economico in [getattr(impianto, "fotovoltaico_stato_economico", None)]
        for data_inizio in [getattr(stato_economico, "data_inizio_contratto", None)]
        for data_fine in [getattr(stato_economico, "data_fine_contratto", None)]
    ]
    group_counts = Counter(row["contract_group"] for row in rows)
    for index, row in enumerate(rows):
        row["contract_group_count"] = group_counts[row["contract_group"]]
        previous_group = rows[index - 1]["contract_group"] if index > 0 else None
        next_group = rows[index + 1]["contract_group"] if index + 1 < len(rows) else None
        row["is_group_start"] = row["contract_group"] != previous_group
        row["is_group_end"] = row["contract_group"] != next_group
    return {"contract_rows": rows}


def _build_tables_payload(request):
    context = _build_home_context()
    return {
        "fv_clienti": render_to_string(
            "PortaleZilioService/partials/_table_fotovoltaico_clienti.html",
            {"rows": context["fv_clienti_rows"]},
            request=request,
        ),
        "fv_proprieta": render_to_string(
            "PortaleZilioService/partials/_table_fotovoltaico_proprieta.html",
            {"rows": context["fv_proprieta_rows"]},
            request=request,
        ),
        "fv_costruzione": render_to_string(
            "PortaleZilioService/partials/_table_fotovoltaico_in_costruzione.html",
            {"rows": context["fv_in_costruzione_rows"]},
            request=request,
        ),
        "fv_agrivoltaico": render_to_string(
            "PortaleZilioService/partials/_table_fotovoltaico_agrivoltaico.html",
            {"rows": context["fv_agrivoltaico_rows"]},
            request=request,
        ),
        "fv_ppu": render_to_string(
            "PortaleZilioService/partials/_table_fotovoltaico_PPU.html",
            {"rows": context["fv_ppu_rows"]},
            request=request,
        ),
        "idr_proprieta": render_to_string(
            "PortaleZilioService/partials/_table_idroelettrico_proprieta.html",
            {"rows": context["idr_proprieta_rows"]},
            request=request,
        ),
        "idr_gse": render_to_string(
            "PortaleZilioService/partials/_table_idroelettrico_gse.html",
            {"rows": context["idr_gse_rows"]},
            request=request,
        ),
    }


def home_view(request):
    return render(request, "PortaleZilioService/home.html", _build_contracts_home_context())


def overview_view(request):
    return render(request, "PortaleZilioService/overview.html", _build_home_context())


@require_POST
def sync_isc_metrics_view(request):
    try:
        service = MetricsSyncService()
        portale_outcome = service.sync_portale_fotovoltaico_isc_metrics()
        saj_outcome = service.sync_portale_fotovoltaico_saj_metrics()
        tables = _build_tables_payload(request)
        return JsonResponse(
            {
                "ok": True,
                "message": (
                    "Aggiornamento completato. "
                    f"Nuove metriche FV ISC aggiornate: {portale_outcome.updated}. "
                    f"Nuove metriche FV SAJ aggiornate: {saj_outcome.updated}."
                ),
                "result": {
                    "portale_updated": portale_outcome.updated,
                    "portale_skipped": portale_outcome.skipped,
                    "portale_missing": portale_outcome.missing,
                    "window_start": portale_outcome.window_start.isoformat(),
                    "window_end": portale_outcome.window_end.isoformat(),
                    "saj_updated": saj_outcome.updated,
                    "saj_skipped": saj_outcome.skipped,
                    "saj_missing": saj_outcome.missing,
                },
                "tables": tables,
            }
        )
    except Exception as error:
        return JsonResponse(
            {
                "ok": False,
                "message": f"Errore durante il recupero dati ISC: {error}",
            },
            status=500,
        )


def test_view(request):
    return render(request, "PortaleZilioService/test.html")



# iSolarCloud views
def _get_data_from_isc():
    login_resp = login_ISC()
    token = login_resp.get("result_data", {}).get("token")
    if not token:
        print("Login failed: missing iSolarCloud token")
        return 2
    devices = get_all_devices(token=token)
    for device in devices:
        print(f"Device: {device.get('device_name')} (type: {device.get('device_type')})")
    
    
    
    pass


# saj - elekeeper views
def _get_data_from_saj():
    pass


# myleo views 
def _get_data_from_myleo():
    pass


