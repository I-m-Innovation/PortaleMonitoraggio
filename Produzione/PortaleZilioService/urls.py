from django.urls import path

from .views import (
    fv_clienti_create_view,
    fv_in_costruzione_create_view,
    fv_ppu_create_view,
    fv_proprieta_create_view,
    home_view,
    test_view,
)

app_name = "PortaleZilioService"

urlpatterns = [
    path("", home_view, name="home"),
    path("fv/new/clienti/", fv_clienti_create_view, name="fv-clienti-create"),
    path("fv/new/proprieta/", fv_proprieta_create_view, name="fv-proprieta-create"),
    path("fv/new/in-costruzione/",fv_in_costruzione_create_view,name="fv-in-costruzione-create",),
    path("fv/new/ppu/", fv_ppu_create_view, name="fv-ppu-create"),
    path("test/", test_view, name="test-view"),
]
