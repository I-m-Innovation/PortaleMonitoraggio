from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from PortaleZilioService.API_inverter.API_iSolarCloud import get_all_devices, login_ISC

from .services.sync import MetricsSyncService

from .services.rows_builder import (
    build_fotovoltaico_clienti_rows,
    build_fotovoltaico_in_costruzione_rows,
    build_fotovoltaico_ppu_rows,
    build_fotovoltaico_proprieta_rows,
    build_idroelettrico_gse_rows,
    build_idroelettrico_proprieta_rows,
)
from .services.rows_builder_portale import (
    build_fotovoltaico_clienti_rows_portale,
    build_fotovoltaico_proprieta_rows_portale,
)


def _build_home_context():
    return {
        "fv_clienti_rows": build_fotovoltaico_clienti_rows_portale(),
        "fv_proprieta_rows": build_fotovoltaico_proprieta_rows_portale(),
        "fv_in_costruzione_rows": build_fotovoltaico_in_costruzione_rows(),
        "fv_ppu_rows": build_fotovoltaico_ppu_rows(),
        "idr_gse_rows": build_idroelettrico_gse_rows(),
        "idr_proprieta_rows": build_idroelettrico_proprieta_rows(),
    }


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
    return render(request, "PortaleZilioService/home.html", _build_home_context())


def fotovoltaico_clienti_portale_test_view(request):
    return render(
        request,
        "PortaleZilioService/fotovoltaico_clienti_portale_test.html",
        {"fv_clienti_portale_rows": build_fotovoltaico_clienti_rows_portale()},
    )


def fotovoltaico_proprieta_portale_test_view(request):
    return render(
        request,
        "PortaleZilioService/fotovoltaico_proprieta_portale_test.html",
        {"fv_proprieta_portale_rows": build_fotovoltaico_proprieta_rows_portale()},
    )


@require_POST
def sync_isc_metrics_view(request):
    try:
        service = MetricsSyncService()
        legacy_outcome = service.sync_api_isc_impianti()
        portale_outcome = service.sync_portale_fotovoltaico_isc_metrics()
        saj_outcome = service.sync_portale_fotovoltaico_saj_metrics()
        tables = _build_tables_payload(request)
        return JsonResponse(
            {
                "ok": True,
                "message": (
                    "Aggiornamento completato. "
                    f"Legacy aggiornati: {legacy_outcome.updated}. "
                    f"Nuove metriche FV ISC aggiornate: {portale_outcome.updated}. "
                    f"Nuove metriche FV SAJ aggiornate: {saj_outcome.updated}."
                ),
                "result": {
                    "updated": legacy_outcome.updated,
                    "skipped": legacy_outcome.skipped,
                    "missing": legacy_outcome.missing,
                    "window_start": legacy_outcome.window_start.isoformat(),
                    "window_end": legacy_outcome.window_end.isoformat(),
                    "portale_updated": portale_outcome.updated,
                    "portale_skipped": portale_outcome.skipped,
                    "portale_missing": portale_outcome.missing,
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


