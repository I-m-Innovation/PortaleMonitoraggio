from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .services.sync import MetricsSyncService

from .services.rows_builder import (
    build_fotovoltaico_clienti_rows,
    build_fotovoltaico_in_costruzione_rows,
    build_fotovoltaico_ppu_rows,
    build_fotovoltaico_proprieta_rows,
    build_idroelettrico_gse_rows,
    build_idroelettrico_proprieta_rows,
)


def _build_home_context():
    return {
        "fv_clienti_rows": build_fotovoltaico_clienti_rows(),
        "fv_proprieta_rows": build_fotovoltaico_proprieta_rows(),
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


@require_POST
def sync_isc_metrics_view(request):
    try:
        outcome = MetricsSyncService().sync_api_isc_impianti()
        tables = _build_tables_payload(request)
        return JsonResponse(
            {
                "ok": True,
                "message": f"Aggiornamento completato. Impianti aggiornati: {outcome.updated}.",
                "result": {
                    "updated": outcome.updated,
                    "skipped": outcome.skipped,
                    "missing": outcome.missing,
                    "window_start": outcome.window_start.isoformat(),
                    "window_end": outcome.window_end.isoformat(),
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
