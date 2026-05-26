from collections import Counter
from datetime import date
from decimal import Decimal
import logging

from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from PortaleZilioService.API_inverter.API_iSolarCloud import get_all_devices, login_ISC

from .models import DocumentoImpianto, FotovoltaicoMetadata, ImpiantoAnagrafica
from .services.fatturato import (
    get_canoni_incassati_oem_per_impianto,
    get_costo_straordinario_totale_per_impianto,
    get_fatturato_ordinario_anno_corrente_per_impianto,
    get_fatturato_straordinario_totale_per_impianto,
    get_numero_fatture_straordinarie_anno_corrente_per_impianto,
    get_numero_fatture_straordinarie_totali_per_impianto,
)
from .services.sync import MetricsSyncService

from .services.rows_builder_idroelettrico import (
    build_idroelettrico_gse_rows,
    build_idroelettrico_proprieta_rows,
)
from .services.rows_builder_fotovoltaico import (
    build_agrivoltaico_rows_portale,
    build_fotovoltaico_clienti_rows_portale,
    build_fotovoltaico_in_costruzione_rows_portale,
    build_fotovoltaico_ppu_rows_portale,
    build_fotovoltaico_proprieta_rows_portale,
)

logger = logging.getLogger(__name__)
ENDPOINT_ERROR_LABEL = "API ERR"


def _fmt_date(value):
    return value.strftime("%d/%m/%Y") if value else "--"


def _fmt_decimal(value, suffix=""):
    if value in (None, ""):
        return "--"
    number = Decimal(str(value))
    formatted = f"{number:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{formatted}{suffix}"


def _fmt_decimal_var(value, decimals=2, suffix=""):
    if value in (None, ""):
        return "--"
    number = float(value)
    formatted = f"{number:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{formatted}{suffix}"


def _fmt_bool(value):
    return "Si" if value else "No"


def _join_values(values):
    cleaned = [value for value in values if value]
    return ", ".join(cleaned) if cleaned else "--"


def _normalize_plant_name(value):
    if value is None:
        return ""
    return " ".join(value.strip().split()).casefold()


def _normalize_plant_tag(value):
    if value is None:
        return ""
    return str(value).strip().casefold()


def _resolve_mapping_value(impianto, fallback_value, values_by_impianto, endpoint_name):
    if values_by_impianto:
        normalized_tag = _normalize_plant_tag(impianto.tag_impianto)
        by_tag = getattr(values_by_impianto, "by_tag", None)
        if by_tag and normalized_tag in by_tag:
            return by_tag[normalized_tag]
    return None


def _resolve_incassato_mapping_value(impianto, values_by_impianto):
    if not values_by_impianto or not getattr(values_by_impianto, "is_available", False):
        return None

    normalized_tag = _normalize_plant_tag(impianto.tag_impianto)
    by_tag = getattr(values_by_impianto, "by_tag", None) or {}
    if normalized_tag in by_tag:
        return by_tag[normalized_tag]
    return Decimal("0")


def _format_log_sample(values, *, limit=8):
    if not values:
        return "-"
    sample = values[:limit]
    rendered = ", ".join(sample)
    if len(values) > limit:
        return f"{rendered} ..."
    return rendered


def _log_overview_alignment_summary(endpoint_name, values_by_impianto, impianti):
    by_tag = getattr(values_by_impianto, "by_tag", None) or {}
    endpoint_tags = sorted(by_tag.keys())

    local_entries = []
    for impianto in impianti:
        normalized_tag = _normalize_plant_tag(impianto.tag_impianto)
        if not normalized_tag:
            continue
        local_entries.append((impianto.nome_impianto, normalized_tag))

    missing_local = [
        f"{nome}[{tag}]"
        for nome, tag in local_entries
        if tag not in by_tag
    ]
    local_tags = {tag for _, tag in local_entries}
    extra_endpoint_tags = [tag for tag in endpoint_tags if tag not in local_tags]
    matched_count = len(local_entries) - len(missing_local)

    logger.info(
        "[overview-tag-summary] endpoint=%s | local_plants=%s | matched=%s | missing_local_count=%s | missing_local_sample=%s | endpoint_tags_count=%s | extra_endpoint_tags_count=%s | extra_endpoint_tags_sample=%s",
        endpoint_name,
        len(local_entries),
        matched_count,
        len(missing_local),
        _format_log_sample(missing_local),
        len(endpoint_tags),
        len(extra_endpoint_tags),
        _format_log_sample(extra_endpoint_tags),
    )


def _contract_type_label(impianto):
    metadata = getattr(impianto, "fotovoltaico_metadata", None)
    if metadata is None:
        return "--"
    labels = []
    if metadata.is_oem:
        labels.append("O&M")
    if metadata.is_ppu:
        labels.append("PPU")
    if metadata.is_agrivoltaico:
        labels.append("Agrivoltaico")
    if not labels:
        return "--"
    return " / ".join(labels)


def _maturato_value(stato_economico):
    if stato_economico is None:
        return None

    data_inizio = getattr(stato_economico, "data_inizio_contratto", None)
    periodicita_mesi = getattr(stato_economico, "periodicita_canone_mesi", None)
    importo_canone_periodico = getattr(
        stato_economico,
        "compute_importo_canone_periodico",
        lambda: None,
    )()
    if importo_canone_periodico is None:
        importo_canone_periodico = getattr(stato_economico, "importo_canone_periodico", None)

    if not data_inizio or periodicita_mesi in (None, 0) or importo_canone_periodico is None:
        return None

    today = date.today()
    if data_inizio > today:
        return Decimal("0")

    data_fine = getattr(stato_economico, "data_fine_contratto", None)
    effective_end = min(today, data_fine) if data_fine else today
    if effective_end < data_inizio:
        return Decimal("0")

    elapsed_months = (
        (effective_end.year - data_inizio.year) * 12
        + (effective_end.month - data_inizio.month)
    )
    if effective_end.day < data_inizio.day:
        elapsed_months -= 1

    if elapsed_months < periodicita_mesi:
        return Decimal("0")

    numero_canoni_maturati = elapsed_months // periodicita_mesi
    return Decimal(numero_canoni_maturati) * Decimal(str(importo_canone_periodico))


def _anni_contratto_value(stato_economico):
    if stato_economico is None:
        return None

    data_inizio = getattr(stato_economico, "data_inizio_contratto", None)
    data_fine = getattr(stato_economico, "data_fine_contratto", None)
    if not data_inizio or not data_fine:
        return None

    return Decimal(str((data_fine - data_inizio).days / 365.25)).quantize(Decimal("0.1"))


def _build_impianto_detail_context(
    impianto,
    *,
    fatturato_by_impianto=None,
    incassato_by_impianto=None,
    fatturato_straordinario_by_impianto=None,
    costo_straordinario_by_impianto=None,
    fatture_straordinarie_annuo_by_impianto=None,
    fatture_straordinarie_totali_by_impianto=None,
):
    stato_economico = getattr(impianto, "fotovoltaico_stato_economico", None)
    metriche = getattr(impianto, "fotovoltaico_metriche_tecniche", None)
    metadata_fv = getattr(impianto, "fotovoltaico_metadata", None)
    metadata_idr = getattr(impianto, "idroelettrico_metadata", None)
    sorgenti_dati = list(impianto.sorgenti_dati.all())
    dispositivi = list(impianto.dispositivi.all())
    commesse = list(impianto.commesse.all())
    documenti = list(impianto.documenti.all())

    counts_by_device_type = Counter(
        dispositivo.get_tipo_dispositivo_display() for dispositivo in dispositivi
    )
    device_counts_summary = _join_values(
        [f"{count} {label}" for label, count in counts_by_device_type.items()]
    )
    sources_summary = _join_values(
        [
            f"{sorgente.nome_sorgente} ({sorgente.get_tipo_sorgente_display()})"
            for sorgente in sorgenti_dati
        ]
    )
    fatturato_ordinario_value = _resolve_mapping_value(
        impianto,
        getattr(stato_economico, "fatturato", None),
        fatturato_by_impianto,
        "fatturato_ordinario_anno_corrente_per_impianto",
    )
    incassato_value = _resolve_incassato_mapping_value(impianto, incassato_by_impianto)
    costo_straordinario_value = _resolve_mapping_value(
        impianto,
        getattr(stato_economico, "costo_sostenuto_straordinario", None),
        costo_straordinario_by_impianto,
        "costo_straordinario_totale_per_impianto",
    )
    fatturato_straordinario_value = _resolve_mapping_value(
        impianto,
        getattr(stato_economico, "totale_fatturato_straordinario", None),
        fatturato_straordinario_by_impianto,
        "fatturato_straordinario_totale_per_impianto",
    )
    fatture_straordinarie_annuo_value = _resolve_mapping_value(
        impianto,
        getattr(stato_economico, "numero_fatture_straordinarie_annuo", None),
        fatture_straordinarie_annuo_by_impianto,
        "numero_fatture_straordinarie_anno_corrente_per_impianto",
    )
    fatture_straordinarie_totali_value = _resolve_mapping_value(
        impianto,
        getattr(stato_economico, "numero_fatture_straordinarie_totali", None),
        fatture_straordinarie_totali_by_impianto,
        "numero_fatture_straordinarie_totali_per_impianto",
    )
    margine_straordinario_value = None
    if costo_straordinario_value is not None and fatturato_straordinario_value is not None:
        margine_straordinario_value = Decimal(str(fatturato_straordinario_value)) - Decimal(
            str(costo_straordinario_value)
        )

    return {
        "impianto": impianto,
        "is_fotovoltaico": impianto.tipo_impianto == ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
        "is_idroelettrico": impianto.tipo_impianto == ImpiantoAnagrafica.TipoImpianto.IDROELETTRICO,
        "anagrafica_impianto_items": [
            ("Tipo impianto", impianto.get_tipo_impianto_display()),
            ("Stato impianto", impianto.get_stato_impianto_display()),
            ("Tag impianto", impianto.tag_impianto or "--"),
            ("Cliente", impianto.nome_cliente or "--"),
            ("Proprietario", impianto.nome_proprietario or "--"),
            ("Entrata in esercizio", _fmt_date(impianto.data_entrata_esercizio)),
        ],
        "anagrafica_tecnica_items": [
            ("Potenza installata", _fmt_decimal_var(impianto.potenza_installata_kw, decimals=3, suffix=" kW")),
            ("Potenza contratto", _fmt_decimal_var(getattr(metadata_fv, "potenza_contratto_kw", None), decimals=3, suffix=" kW")),
        ],
        "anagrafica_geografica_items": [
            ("Localita", impianto.localita or "--"),
            ("Provincia", impianto.provincia or "--"),
            ("Regione", impianto.regione or "--"),
            ("Indirizzo", impianto.indirizzo or "--"),
        ],
        "latitudine": impianto.latitudine,
        "longitudine": impianto.longitudine,
        "anagrafica_idroelettrico_items": [
            ("Categoria IDR", getattr(metadata_idr, "get_categoria_idr_display", lambda: "--")()),
            ("Portata concessione", _fmt_decimal_var(getattr(metadata_idr, "portata_concessione", None), decimals=3)),
            ("Unita misura portata", getattr(metadata_idr, "unita_misura_portata", None) or "--"),
            ("Salto", _fmt_decimal_var(getattr(metadata_idr, "salto", None), decimals=3, suffix=" m")),
            ("Potenza business plan", _fmt_decimal_var(getattr(metadata_idr, "potenza_business_plan_kw", None), decimals=3, suffix=" kW")),
        ],
        "economico_contratto_items": [
            ("Tipologia contratto", _contract_type_label(impianto)),
            ("Inizio contratto", _fmt_date(getattr(stato_economico, "data_inizio_contratto", None))),
            ("Fine contratto", _fmt_date(getattr(stato_economico, "data_fine_contratto", None))),
            ("Anni contratto", _fmt_decimal(_anni_contratto_value(stato_economico))),
            ("Totale contratto", _fmt_decimal(getattr(stato_economico, "totale_contratto", None), " EUR")),
            ("Totale annuo", _fmt_decimal(getattr(stato_economico, "totale_annuo", None), " EUR")),
            ("Totale annuale su MW", _fmt_decimal(getattr(stato_economico, "totale_annuale_su_mw", None), " EUR")),
            ("Periodicita canone", getattr(stato_economico, "periodicita_canone_mesi", None) or "--"),
            ("Importo canone periodico", _fmt_decimal(getattr(stato_economico, "importo_canone_periodico", None), " EUR")),
            ("Prossima fattura", _fmt_date(getattr(stato_economico, "data_prossima_fattura", None))),
            ("Importo prossima fattura", _fmt_decimal(getattr(stato_economico, "importo_prossima_fattura", None), " EUR")),
        ],
        "economico_ordinario_items": [
            ("Maturato", _fmt_decimal(_maturato_value(stato_economico), " EUR")),
            ("Fatturato", _fmt_decimal(fatturato_ordinario_value, " EUR") if fatturato_ordinario_value is not None else ENDPOINT_ERROR_LABEL),
            ("Incassato", _fmt_decimal(incassato_value, " EUR") if incassato_value is not None else ENDPOINT_ERROR_LABEL),
        ],
        "economico_straordinario_items": [
            ("Costo sostenuto", _fmt_decimal(costo_straordinario_value, " EUR") if costo_straordinario_value is not None else ENDPOINT_ERROR_LABEL),
            ("Totale fatturato straordinario", _fmt_decimal(fatturato_straordinario_value, " EUR") if fatturato_straordinario_value is not None else ENDPOINT_ERROR_LABEL),
            ("Margine", _fmt_decimal(margine_straordinario_value, " EUR") if margine_straordinario_value is not None else ENDPOINT_ERROR_LABEL),
            ("Fatture straordinarie annuo", fatture_straordinarie_annuo_value if fatture_straordinarie_annuo_value is not None else ENDPOINT_ERROR_LABEL),
            ("Fatture straordinarie totali", fatture_straordinarie_totali_value if fatture_straordinarie_totali_value is not None else ENDPOINT_ERROR_LABEL),
        ],
        "monitoraggio_tecnico_items": [
            ("Sorgenti dati", sources_summary),
            ("Dispositivi", device_counts_summary),
            ("PR contrattuale", _fmt_decimal_var(getattr(metadata_fv, "pr_contrattuale", None), suffix=" %")),
            ("PR ultimi 12 mesi", _fmt_decimal_var((getattr(metriche, "pr_ultimi_12_mesi", None) or 0) * 100, suffix=" %") if getattr(metriche, "pr_ultimi_12_mesi", None) is not None else "--"),
            ("Mancata produzione", _fmt_decimal(getattr(metriche, "mancata_produzione", None), " kWh")),
            ("Ore equivalenti ultimi 12 mesi", _fmt_decimal(getattr(metriche, "ore_equivalenti_ultimi_12_mesi", None), " h")),
            ("Stato operativo", getattr(metriche, "get_stato_operativo_display", lambda: "--")()),
        ],
        "commesse": commesse,
        "documenti": documenti,
        "note_impianto": impianto.note or "",
    }


def _build_home_context():
    impianti_overview = list(
        ImpiantoAnagrafica.objects.filter(
            tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
        ).only("id", "nome_impianto", "tag_impianto")
    )
    fatturato_by_impianto = get_fatturato_ordinario_anno_corrente_per_impianto()
    incassato_by_impianto = get_canoni_incassati_oem_per_impianto()
    fatturato_straordinario_by_impianto = get_fatturato_straordinario_totale_per_impianto()
    costo_straordinario_by_impianto = get_costo_straordinario_totale_per_impianto()
    fatture_straordinarie_annuo_by_impianto = (
        get_numero_fatture_straordinarie_anno_corrente_per_impianto()
    )
    fatture_straordinarie_totali_by_impianto = (
        get_numero_fatture_straordinarie_totali_per_impianto()
    )

    _log_overview_alignment_summary(
        "fatturato_ordinario_anno_corrente",
        fatturato_by_impianto,
        impianti_overview,
    )
    _log_overview_alignment_summary(
        "canoni_incassati_oem",
        incassato_by_impianto,
        impianti_overview,
    )
    _log_overview_alignment_summary(
        "fatturato_straordinario_totale",
        fatturato_straordinario_by_impianto,
        impianti_overview,
    )
    _log_overview_alignment_summary(
        "costo_straordinario_totale",
        costo_straordinario_by_impianto,
        impianti_overview,
    )
    _log_overview_alignment_summary(
        "fatture_straordinarie_annuo",
        fatture_straordinarie_annuo_by_impianto,
        impianti_overview,
    )
    _log_overview_alignment_summary(
        "fatture_straordinarie_totali",
        fatture_straordinarie_totali_by_impianto,
        impianti_overview,
    )

    return {
        "fv_clienti_rows": build_fotovoltaico_clienti_rows_portale(
            fatturato_by_impianto,
            incassato_by_impianto,
            fatturato_straordinario_by_impianto,
            costo_straordinario_by_impianto,
            fatture_straordinarie_annuo_by_impianto,
            fatture_straordinarie_totali_by_impianto,
        ),
        "fv_proprieta_rows": build_fotovoltaico_proprieta_rows_portale(
            fatturato_by_impianto,
            incassato_by_impianto,
            fatturato_straordinario_by_impianto,
            costo_straordinario_by_impianto,
            fatture_straordinarie_annuo_by_impianto,
            fatture_straordinarie_totali_by_impianto,
        ),
        "fv_agrivoltaico_rows": build_agrivoltaico_rows_portale(
            fatturato_by_impianto,
            incassato_by_impianto,
            fatturato_straordinario_by_impianto,
            costo_straordinario_by_impianto,
            fatture_straordinarie_annuo_by_impianto,
            fatture_straordinarie_totali_by_impianto,
        ),
        "fv_in_costruzione_rows": build_fotovoltaico_in_costruzione_rows_portale(
            fatturato_by_impianto,
            incassato_by_impianto,
            fatturato_straordinario_by_impianto,
            costo_straordinario_by_impianto,
            fatture_straordinarie_annuo_by_impianto,
            fatture_straordinarie_totali_by_impianto,
        ),
        "year": date.today().year,
        "fv_ppu_rows": build_fotovoltaico_ppu_rows_portale(),
        "idr_gse_rows": build_idroelettrico_gse_rows(),
        "idr_proprieta_rows": build_idroelettrico_proprieta_rows(),
    }


def _build_contracts_home_context():
    impianti = ImpiantoAnagrafica.objects.select_related(
        "fotovoltaico_stato_economico",
        "fotovoltaico_metadata",
    )

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
            {"rows": context["fv_ppu_rows"], "year": context["year"]},
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


def impianto_detail_view(request):
    nome_impianto = (request.GET.get("nome") or "").strip()
    if not nome_impianto:
        raise Http404("Parametro nome mancante")

    impianto = (
        ImpiantoAnagrafica.objects.select_related(
            "fotovoltaico_metadata",
            "fotovoltaico_stato_economico",
            "fotovoltaico_metriche_tecniche",
            "idroelettrico_metadata",
        )
        .prefetch_related("commesse", "sorgenti_dati", "dispositivi", "documenti")
        .filter(nome_impianto=nome_impianto)
        .order_by("id")
        .first()
    )
    if impianto is None:
        raise Http404("Impianto non trovato")
    fatturato_by_impianto = get_fatturato_ordinario_anno_corrente_per_impianto()
    incassato_by_impianto = get_canoni_incassati_oem_per_impianto()
    fatturato_straordinario_by_impianto = get_fatturato_straordinario_totale_per_impianto()
    costo_straordinario_by_impianto = get_costo_straordinario_totale_per_impianto()
    fatture_straordinarie_annuo_by_impianto = (
        get_numero_fatture_straordinarie_anno_corrente_per_impianto()
    )
    fatture_straordinarie_totali_by_impianto = (
        get_numero_fatture_straordinarie_totali_per_impianto()
    )
    return render(
        request,
        "PortaleZilioService/impianto_detail.html",
        _build_impianto_detail_context(
            impianto,
            fatturato_by_impianto=fatturato_by_impianto,
            incassato_by_impianto=incassato_by_impianto,
            fatturato_straordinario_by_impianto=fatturato_straordinario_by_impianto,
            costo_straordinario_by_impianto=costo_straordinario_by_impianto,
            fatture_straordinarie_annuo_by_impianto=fatture_straordinarie_annuo_by_impianto,
            fatture_straordinarie_totali_by_impianto=fatture_straordinarie_totali_by_impianto,
        ),
    )


def documento_impianto_download_view(request, documento_id):
    documento = (
        DocumentoImpianto.objects.select_related("impianto")
        .filter(pk=documento_id)
        .first()
    )
    if documento is None:
        raise Http404("Documento non trovato")

    file_field = documento.file
    if not file_field:
        raise Http404("File documento non disponibile")

    return FileResponse(file_field.open("rb"), as_attachment=False, filename=file_field.name.rsplit("/", 1)[-1])


@require_POST
def sync_provider_metrics_view(request):
    try:
        service = MetricsSyncService()
        portale_outcome = service.sync_portale_fotovoltaico_isc_metrics()
        saj_outcome = service.sync_portale_fotovoltaico_saj_metrics()
        saj_annual_energy_outcome = service.sync_portale_fotovoltaico_saj_annual_produced_energy()
        tables = _build_tables_payload(request)
        return JsonResponse(
            {
                "ok": True,
                "message": (
                    "Aggiornamento completato. "
                    f"Nuove metriche FV ISC aggiornate: {portale_outcome.updated}. "
                    f"Nuove metriche FV SAJ aggiornate: {saj_outcome.updated}. "
                    f"Energia PPU SAJ aggiornata: {saj_annual_energy_outcome.updated}."
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
                    "saj_annual_energy_updated": saj_annual_energy_outcome.updated,
                    "saj_annual_energy_skipped": saj_annual_energy_outcome.skipped,
                    "saj_annual_energy_missing": saj_annual_energy_outcome.missing,
                },
                "tables": tables,
            }
        )
    except Exception as error:
        return JsonResponse(
            {
                "ok": False,
                "message": f"Errore durante la sincronizzazione delle metriche provider: {error}",
            },
            status=500,
        )


@require_POST
def update_fv_construction_category_view(request):
    impianto_id = request.POST.get("impianto_id")
    categoria_fv = request.POST.get("categoria_fv")

    valid_categories = {
        FotovoltaicoMetadata.CategoriaFV.CLIENTE,
        FotovoltaicoMetadata.CategoriaFV.PROPRIETA,
    }
    if categoria_fv not in valid_categories:
        return JsonResponse(
            {"ok": False, "message": "Categoria fotovoltaico non valida."},
            status=400,
        )

    impianto = (
        ImpiantoAnagrafica.objects.filter(
            pk=impianto_id,
            tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
            stato_impianto=ImpiantoAnagrafica.StatoImpianto.IN_COSTRUZIONE,
        )
        .first()
    )
    if impianto is None:
        return JsonResponse(
            {"ok": False, "message": "Impianto fotovoltaico in costruzione non trovato."},
            status=404,
        )

    metadata, _ = FotovoltaicoMetadata.objects.get_or_create(
        impianto=impianto,
        defaults={"categoria_fv": categoria_fv},
    )
    if metadata.categoria_fv != categoria_fv:
        metadata.categoria_fv = categoria_fv
        metadata.save(update_fields=["categoria_fv"])

    return JsonResponse(
        {
            "ok": True,
            "message": "Categoria fotovoltaico aggiornata.",
            "impianto_id": impianto.id,
            "categoria_fv": metadata.categoria_fv,
        }
    )


def home_v2_view(request):
    impianti_fotovoltaici = ImpiantoAnagrafica.objects.select_related("fotovoltaico_stato_economico", "fotovoltaico_metadata").filter(tipo_impianto=ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO)
    impianti_idroelettrici = ImpiantoAnagrafica.objects.select_related("idroelettrico_metadata").filter(tipo_impianto=ImpiantoAnagrafica.TipoImpianto.IDROELETTRICO)
    
    if not impianti_fotovoltaici.exists() or impianti_fotovoltaici.count() < 1:
        print("Nessun impianto fotovoltaico trovato. Verifica la presenza di impianti di tipo FOTOVOLTAICO nel database.")
    if not impianti_idroelettrici.exists() or impianti_idroelettrici.count() < 1:
        print("Nessun impianto idroelettrico trovato. Verifica la presenza di impianti di tipo IDROELETTRICO nel database.")
    
    context = {
            "impianti_fotovoltaici": impianti_fotovoltaici,
            "impianti_idroelettrici": impianti_idroelettrici,
    }
    
    
    return render(request, "PortaleZilioService/v2/home.html", context)

