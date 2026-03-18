from django.urls import path

from .views import (
    home_view,
    sync_isc_metrics_view,
    test_view,
)

app_name = "PortaleZilioService"

urlpatterns = [
    path("", home_view, name="home"),
    path("api/sync-isc/", sync_isc_metrics_view, name="sync-isc"),
    path("test/", test_view, name="test-view"),
]
