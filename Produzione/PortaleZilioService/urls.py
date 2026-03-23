from django.urls import path

from .views import (
    fotovoltaico_clienti_portale_test_view,
    fotovoltaico_proprieta_portale_test_view,
    home_view,
    sync_isc_metrics_view,
    test_view,
)

app_name = "PortaleZilioService"

urlpatterns = [
    path("", home_view, name="home"),
    path("test/fv-clienti-portale/", fotovoltaico_clienti_portale_test_view, name="test-fv-clienti-portale"),
    path("test/fv-proprieta-portale/", fotovoltaico_proprieta_portale_test_view, name="test-fv-proprieta-portale"),
    path("api/sync-isc/", sync_isc_metrics_view, name="sync-isc"),
    path("test/", test_view, name="test-view"),
]
