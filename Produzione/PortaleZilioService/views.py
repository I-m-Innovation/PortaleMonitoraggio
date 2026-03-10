from django.shortcuts import render

from .services.rows_builder import (
    build_fotovoltaico_clienti_rows,
    build_fotovoltaico_in_costruzione_rows,
    build_fotovoltaico_ppu_rows,
    build_fotovoltaico_proprieta_rows,
    build_idroelettrico_proprieta_rows,
)

def home_view(request):
    return render(request, "PortaleZilioService/home.html", {
        "fv_clienti_rows": build_fotovoltaico_clienti_rows(),
        "fv_proprieta_rows": build_fotovoltaico_proprieta_rows(),
        "fv_in_costruzione_rows": build_fotovoltaico_in_costruzione_rows(),
        "fv_ppu_rows": build_fotovoltaico_ppu_rows(),
        "idr_proprieta_rows": build_idroelettrico_proprieta_rows(),
    })


def test_view(request):
    return render(request, "PortaleZilioService/test.html")
