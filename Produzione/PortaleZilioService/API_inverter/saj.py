"""
Script per interrogare l'API SAJ Elekeeper e calcolare il Performance Ratio (PR)
degli impianti fotovoltaici negli ultimi 12 mesi.

Documentazione API: https://developer.saj-electric.com/fileApi/portFile
URL base produzione: https://developer.saj-electric.com/prod-api
"""

import datetime

import openmeteo_requests
import requests
import requests_cache
from retry_requests import retry


# ─────────────────────────────────────────────────────────────────────────────
# CREDENZIALI
# ─────────────────────────────────────────────────────────────────────────────

APP_ID     = "VH_rQtUpniM"
APP_SECRET = "hiDHa5riPzzTl2vixkVCWh4kpniM6ZrJZxkjunfShyuVrQtUFmPCbKu6oUaw7WAi"
BASE_URL   = "https://developer.saj-electric.com/prod-api"


# ─────────────────────────────────────────────────────────────────────────────
# DATI IMPIANTI (aggiornare manualmente se cambiano)
# ─────────────────────────────────────────────────────────────────────────────

# Potenza di picco installata per impianto (kWp)
PLANTS_PEAK_POWER = {
    "Zilio Group":      490,    # kWp — verificare con documentazione impianto
    "Col Roigo 50 kWp": 49.74,  # kWp — dal nome impianto
}

# Mappa impianti → dispositivi noti (serial number)
# Tipo dispositivo: C6 = inverter, S12 = sistema di accumulo
PLANTS_INFO = {
    "Zilio Group": {
        "plantId": "24031286133",
        "devices": [
            "C6T9104J2314E00560",  # C6 - inverter
            "C6T9104J2315E00670",  # C6 - inverter
            "C6V9104G2424E00228",  # C6 - inverter
            "C6V9104J2421E01334",  # C6 - inverter
            "CSV6503J2416E00023",  # S12 - accumulo (nessun dato disponibile)
            "CSV6503J2416E00036",  # S12 - accumulo
            "CSV6503J2416E00047",  # S12 - accumulo (nessun dato disponibile)
        ]
    },
    "Col Roigo 50 kWp": {
        "plantId": "24110165619",
        "devices": [
            "CSV6503J2416E00004",  # S12 - accumulo
        ]
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNZIONI DI SUPPORTO
# ─────────────────────────────────────────────────────────────────────────────

def get_token():
    """
    Recupera il token di accesso dall'API SAJ.
    Restituisce il token come stringa, oppure None in caso di errore.
    """
    url = f"{BASE_URL}/open/api/access_token?appId={APP_ID}&appSecret={APP_SECRET}"
    token = requests.get(url).json().get("data", {}).get("access_token")
    if not token:
        print("ERRORE: impossibile ottenere il token di accesso.")
    return token


def build_headers(token):
    """Costruisce gli header HTTP richiesti dall'API SAJ."""
    return {
        "accessToken":      token,
        "clientSecret":     APP_SECRET,
        "content-language": "en_US",
    }


def get_snapshot_energia(device_sn, at_time, headers):
    """
    Restituisce il valore cumulativo di totalPvEnergy (kWh) del dispositivo
    nella finestra di 24 ore che termina a 'at_time'.

    L'API historyDataCommon accetta finestre massime di 24 ore.
    totalPvEnergy è un contatore cumulativo lifetime: sottraendo il valore
    di inizio periodo da quello di fine periodo si ottiene la produzione del periodo.

    Restituisce None se non ci sono dati per quella finestra.
    """
    window_start = (at_time - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    window_end   = at_time.strftime("%Y-%m-%d %H:%M:%S")
    resp = requests.get(
        f"{BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn":  device_sn,
            "startTime": window_start,
            "endTime":   window_end,
        }
    )
    records = resp.json().get("data", [])
    if records:
        return float(records[-1].get("totalPvEnergy", 0) or 0)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# FUNZIONE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def main():

    # ── Autenticazione ────────────────────────────────────────────────────────
    token = get_token()
    if not token:
        return
    print(f"Token di accesso: {token}")
    headers = build_headers(token)

    # ── Elenco impianti ───────────────────────────────────────────────────────
    # Endpoint: GET /open/api/developer/plant/page
    # Risposta esempio:
    #   { "rows": [ {"plantId": "24031286133", "plantName": "Zilio Group"}, ... ] }
    print("\n=== Impianti ===")
    plants_url = f"{BASE_URL}/open/api/developer/plant/page?appId={APP_ID}&pageSize=20&pageNum=1"
    plants = requests.get(plants_url, headers=headers).json().get("rows", [])
    for plant in plants:
        print(f"  ID: {plant['plantId']}  Nome: {plant['plantName']}")

    # ── Elenco dispositivi per impianto ──────────────────────────────────────
    # Endpoint: GET /open/api/developer/device/page
    # Campi principali nella risposta:
    #   deviceSn   → numero di serie univoco del dispositivo
    #   deviceType → modello (C6 = inverter, S12 = accumulo)
    #   plantId    → impianto di appartenenza
    #   isOnline   → 1 online, 0 offline
    #   isAlarm    → 1 allarme attivo, 0 nessun allarme
    print("\n=== Dispositivi ===")
    for plant in plants:
        plant_id   = plant['plantId']
        plant_name = plant['plantName']
        devices_url = (
            f"{BASE_URL}/open/api/developer/device/page"
            f"?appId={APP_ID}&plantId={plant_id}&pageSize=20&pageNum=1"
        )
        devices = requests.get(devices_url, headers=headers).json().get("rows", [])
        print(f"\n  {plant_name}:")
        for device in devices:
            print(f"    SN: {device['deviceSn']}  Tipo: {device.get('deviceType', 'N/A')}")

    # ── Produzione ultimi 12 mesi per impianto ────────────────────────────────
    # Strategia snapshot: poiché historyDataCommon accetta max 24 ore per richiesta
    # e totalPvEnergy è un contatore cumulativo lifetime (kWh), si leggono due
    # snapshot (inizio e fine periodo) e si calcola la differenza.
    # Formato timestamp richiesto dall'API: "yyyy-MM-dd HH:mm:ss"
    print("\n=== Produzione ultimi 12 mesi ===")
    now          = datetime.datetime.now()
    period_end   = now
    period_start = now - datetime.timedelta(days=365)

    plants_production = {name: 0.0 for name in PLANTS_INFO}

    for plant_name, plant_data in PLANTS_INFO.items():
        plant_total_kwh = 0.0
        for device_sn in plant_data["devices"]:
            pv_inizio = get_snapshot_energia(device_sn, period_start, headers)
            pv_fine   = get_snapshot_energia(device_sn, period_end,   headers)
            if pv_inizio is not None and pv_fine is not None:
                device_kwh = pv_fine - pv_inizio
            else:
                device_kwh = 0.0
                print(f"  ATTENZIONE {device_sn}: nessun dato — inizio={pv_inizio}, fine={pv_fine}")
            print(f"  {device_sn}: {device_kwh:.2f} kWh  (inizio={pv_inizio}, fine={pv_fine})")
            plant_total_kwh += device_kwh
        plants_production[plant_name] = plant_total_kwh
        print(f"\n  {plant_name} — totale ultimi 12 mesi: {plant_total_kwh:.2f} kWh\n")

    # ── Coordinate geografiche degli impianti ─────────────────────────────────
    # Endpoint: GET /open/api/plant/details
    # Restituisce tra gli altri i campi 'latitude' e 'longitude'
    print("=== Coordinate impianti ===")
    plants_coordinates = {}
    for plant_name, plant_data in PLANTS_INFO.items():
        plant_id    = plant_data["plantId"]
        details_url = f"{BASE_URL}/open/api/plant/details?appId={APP_ID}&plantId={plant_id}"
        data        = requests.get(details_url, headers=headers).json().get("data", {})
        lat = data.get("latitude")
        lon = data.get("longitude")
        if lat is not None and lon is not None:
            plants_coordinates[plant_name] = (lat, lon)
            print(f"  {plant_name} — lat: {lat}, lon: {lon}")
        else:
            print(f"  ATTENZIONE: coordinate non disponibili per {plant_name}")

    # ── Irradiazione solare (GHI) da Open-Meteo ──────────────────────────────
    # API gratuita per dati meteorologici storici: https://archive-api.open-meteo.com/v1/archive
    # Campo 'shortwave_radiation': irradianza globale orizzontale GHI (W/m², media oraria)
    # Somma oraria W/m² → Wh/m² → diviso 1000 → kWh/m²
    #
    # Nota: GHI misura la radiazione su superficie orizzontale.
    # Per un calcolo più preciso usare GTI (Global Tilted Irradiance) con
    # i parametri 'tilt' (inclinazione pannelli in gradi) e 'azimuth'
    # (orientamento: 0=Sud) non appena noti.
    cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo     = openmeteo_requests.Client(session=retry_session)

    meteo_url      = "https://archive-api.open-meteo.com/v1/archive"
    start_date_str = period_start.strftime("%Y-%m-%d")
    end_date_str   = period_end.strftime("%Y-%m-%d")

    # ── Calcolo Performance Ratio (PR) ───────────────────────────────────────
    # PR (%) = E_reale / E_attesa × 100
    # E_attesa (kWh) = Potenza_picco (kWp) × GHI_annuo (kWh/m²)
    # Produzione mancata (kWh) = E_attesa − E_reale
    print("\n=== Performance Ratio (ultimi 12 mesi) ===")
    for plant_name, coords in plants_coordinates.items():
        lat, lon = coords
        meteo_resp = openmeteo.weather_api(meteo_url, params={
            "latitude":   lat,
            "longitude":  lon,
            "start_date": start_date_str,
            "end_date":   end_date_str,
            "hourly":     "shortwave_radiation",
        })[0]
        ghi_values  = meteo_resp.Hourly().Variables(0).ValuesAsNumpy()
        ghi_sum_kwh = float(ghi_values.sum()) / 1000.0  # kWh/m²

        e_reale     = plants_production[plant_name]
        potenza_pic = PLANTS_PEAK_POWER.get(plant_name)

        print(f"\n  {plant_name}:")
        print(f"    GHI ultimi 12 mesi  : {ghi_sum_kwh:.1f} kWh/m²")
        print(f"    Energia prodotta    : {e_reale:.1f} kWh")
        if potenza_pic:
            e_attesa           = potenza_pic * ghi_sum_kwh
            pr                 = (e_reale / e_attesa) * 100 if e_attesa > 0 else 0
            produzione_mancata = e_attesa - e_reale
            print(f"    Potenza di picco    : {potenza_pic:.1f} kWp")
            print(f"    Energia attesa      : {e_attesa:.1f} kWh")
            print(f"    Performance Ratio   : {pr:.1f}%")
            print(f"    Produzione mancata  : {produzione_mancata:.1f} kWh")
        else:
            print(f"    Performance Ratio   : N/D (potenza di picco non impostata)")


if __name__ == "__main__":
    main()

