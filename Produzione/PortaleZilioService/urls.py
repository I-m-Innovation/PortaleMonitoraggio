from django.urls import path

from .views import (
    documento_impianto_download_view,
    home_v2_view,
    home_view,
    impianto_detail_view,
    overview_view,
    sync_provider_metrics_view,
    update_fv_construction_category_view,
)

app_name = "PortaleZilioService"

urlpatterns = [
    path("", home_view, name="home"),
    path("overview/", overview_view, name="overview"),
    path("impianto/", impianto_detail_view, name="impianto-detail"),
    path("documenti/<int:documento_id>/", documento_impianto_download_view, name="documento-download"),
    path("api/sync-provider-metrics/", sync_provider_metrics_view, name="sync-provider-metrics"),
    path("api/fv-construction-category/", update_fv_construction_category_view, name="fv-construction-category"),
    # v2 - sviluppo sperimentale
    path("v2/", home_v2_view, name="home-v2"),
]
