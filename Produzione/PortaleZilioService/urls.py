from django.urls import path

from .views import (
    home_view,
    overview_view,
    sync_provider_metrics_view,
    test_view,
)

app_name = "PortaleZilioService"

urlpatterns = [
    path("", home_view, name="home"),
    path("overview/", overview_view, name="overview"),
    path("api/sync-provider-metrics/", sync_provider_metrics_view, name="sync-provider-metrics"),
    path("test/", test_view, name="test-view"),
]
