from django.shortcuts import redirect, render

from .forms import (
    FvClientiForm,
    FvInCostruzioneForm,
    FvPpuForm,
    FvProprietaForm,
)

from .services.rows_builder import (
    build_fotovoltaico_clienti_rows,
    build_fotovoltaico_in_costruzione_rows,
    build_fotovoltaico_ppu_rows,
    build_fotovoltaico_proprieta_rows,
    build_idroelettrico_proprieta_rows,
)


FV_FORM_SPECS = {
    "fv_clienti": (FvClientiForm, "Nuovo Record FV Clienti"),
    "fv_proprieta": (FvProprietaForm, "Nuovo Record FV Proprieta"),
    "fv_in_costruzione": (FvInCostruzioneForm, "Nuovo Record FV In Costruzione"),
    "fv_ppu": (FvPpuForm, "Nuovo Record FV PPU"),
}


def _build_home_context(active_form_type=None, form_instances=None):
    forms = {
        key: (form_instances[key] if form_instances and key in form_instances else spec[0]())
        for key, spec in FV_FORM_SPECS.items()
    }
    return {
        "fv_clienti_rows": build_fotovoltaico_clienti_rows(),
        "fv_proprieta_rows": build_fotovoltaico_proprieta_rows(),
        "fv_in_costruzione_rows": build_fotovoltaico_in_costruzione_rows(),
        "fv_ppu_rows": build_fotovoltaico_ppu_rows(),
        "idr_proprieta_rows": build_idroelettrico_proprieta_rows(),
        "fv_forms": forms,
        "active_form_type": active_form_type or "",
    }


def home_view(request):
    if request.method == "POST":
        form_type = request.POST.get("form_type", "")
        spec = FV_FORM_SPECS.get(form_type)
        if spec is not None:
            form_class, _ = spec
            form = form_class(request.POST)
            if form.is_valid():
                form.save()
                return redirect("PortaleZilioService:home")
            return render(
                request,
                "PortaleZilioService/home.html",
                _build_home_context(active_form_type=form_type, form_instances={form_type: form}),
            )

    return render(request, "PortaleZilioService/home.html", _build_home_context())


def test_view(request):
    return render(request, "PortaleZilioService/test.html")


def _fv_form_view(request, form_class, page_title):
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect("PortaleZilioService:home")
    else:
        form = form_class()

    return render(
        request,
        "PortaleZilioService/forms/fv_metadata_form.html",
        {"form": form, "page_title": page_title},
    )


def fv_clienti_create_view(request):
    return _fv_form_view(request, FvClientiForm, "Nuovo Record FV Clienti")


def fv_proprieta_create_view(request):
    return _fv_form_view(request, FvProprietaForm, "Nuovo Record FV Proprieta")


def fv_in_costruzione_create_view(request):
    return _fv_form_view(request, FvInCostruzioneForm, "Nuovo Record FV In Costruzione")


def fv_ppu_create_view(request):
    return _fv_form_view(request, FvPpuForm, "Nuovo Record FV PPU")
