# Analisi Dettagliata: PortaleZilioService & Provider (ISC/SAJ)

**Data**: Maggio 2026  
**Versione**: Architettura refactored con zilio_monitoring package  
**Branch**: feature/portale-zilio-service-app

---

## 📊 Indice

1. [Visione d'Insieme](#visione-dinsieme)
2. [Architettura Stratificata](#architettura-stratificata)
3. [Modelli di Dati](#modelli-di-dati)
4. [Provider ISC (iSolarCloud)](#provider-isc-isolarcloud)
5. [Provider SAJ (Elekeeper)](#provider-saj-elekeeper)
6. [Flusso di Sincronizzazione](#flusso-di-sincronizzazione)
7. [Calcolo Metriche](#calcolo-metriche)
8. [Persistenza Dati](#persistenza-dati)
9. [Problemi & Limitazioni](#problemi--limitazioni)
10. [Roadmap & Recommendations](#roadmap--recommendations)

---

## Visione d'Insieme

**PortaleZilioService** è il nucleo della nuova architettura che aggrega dati da **due provider cloud** distinti:

```
┌─────────────────────────────────────────────────────────────────┐
│ PortaleZilioService (Django App)                                │
│                                                                  │
│ ├─ ImpiantoAnagrafica (Modello centrale)                        │
│ ├─ ImpiantoSorgenteDati (Mapping → Provider)                    │
│ ├─ ImpiantoDispositivo (Device-level detail)                    │
│ ├─ FotovoltaicoMetadata (FV specifics)                          │
│ └─ FotovoltaicoStatoEconomico (Dati economici)                  │
│                                                                  │
│ Services:                                                        │
│ ├─ MetricsSyncService (Coordinamento sync)                      │
│ ├─ persist_metrics_to_impianto() (ORM write)                    │
│ └─ rows_builder_* (Tabelle per UI)                              │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│ zilio_monitoring Package (Reusable Library)                     │
│                                                                  │
│ ├─ ProviderRegistry (Router → IscMetricsProvider / SajMetrics)  │
│ ├─ MetricsCollector (Network I/O orchestration)                 │
│ ├─ DefaultMetricsCalculator (PR, Eq.Hrs, Missed Prod.)          │
│ └─ ProviderPlantSnapshot DTO                                    │
└─────────────────────────────────────────────────────────────────┘
              ↓                           ↓
        ┌──────────────────┐      ┌──────────────────┐
        │ IscMetricsProvider   │ SajMetricsProvider      │
        │                  │      │                  │
        │ - login_ISC()    │      │ - get_token()    │
        │ - find_plant()   │      │ - get_plants()   │
        │ - fetch energy   │      │ - get_devices()  │
        │ - fetch irrad.   │      │ - fetch energy   │
        └──────────────────┘      └──────────────────┘
              ↓                           ↓
        ┌──────────────────┐      ┌──────────────────┐
        │ iSolarCloud API  │      │ SAJ Elekeeper    │
        │ gateway.isolarc. │      │ developer.saj-   │
        │ eu/openapi       │      │ electric.com     │
        └──────────────────┘      └──────────────────┘
```

---

## Architettura Stratificata

### Layer 1: Client HTTP

#### **IscMetricsProvider / isolarcloud.py**
```python
# Logica
def login_ISC() → token
def get_all_plants(token, size=500) → List[Dict]
def get_all_devices(token, plant_id, size=100) → List[Dict]
def get_device_list_paginated(token, plant_id) → Dict with pageList

# Struttura risposta
Plant: {
    "ps_id": 5488121,          # Plant ID
    "ps_name": "RCT",          # Plant name
    "ps_status": 1,            # 1=online, 0=offline
    "installed_power": 250,    # kW
    "daily_power": 123.45,     # kWh
    ...
}

Device: {
    "ps_key": "5488121_1_1_5", # Identificativo univoco
    "device_name": "Inverter 1",
    "device_type": "5",        # 5=inverter, X=weather station
    "device_sn": "SN123456",
    ...
}
```

#### **SajMetricsProvider / saj.py**
```python
# Logica
def get_token() → access_token
def get_plants(headers) → List[Dict]
def get_devices(headers, plant_id) → List[Dict]
def get_device_energy_snapshot(headers, device_sn, at_time) → float (kWh)

# Struttura risposta
Plant: {
    "plantId": "P001",
    "plantName": "Centrale SA3",
    ...
}

Device: {
    "deviceSn": "SAJ001",
    "deviceType": "1",         # 1=inverter, 2=storage, etc
    "deviceStatus": 1,
    ...
}
```

### Layer 2: Provider Adapters

#### **IscMetricsProvider (zilio_monitoring/providers/isc.py)**

**Metodi Pubblici**:
```python
fetch_snapshot(impianto, window: MetricsWindow) → ProviderPlantSnapshot
fetch_portale_snapshot(impianto, sorgente, window) → ProviderPlantSnapshot
```

**Logica Interna**:

1. **Plant Matching**
   - Normalizza candidate names/tags: `impianto.nome_impianto`, `impianto.tag_impianto`, `impianto.codice_impianto`
   - Confronta con `api_plant.ps_name` e `ps_id` normalizzati
   - Ritorna primo match trovato

2. **Device Selection**
   ```python
   # Esclude weather station (device_type == "5")
   inverter_keys = [d["ps_key"] for d in devices if d["device_type"] != WEATHER_STATION]
   
   # Per portale: applica filtri per source (3F Ferro vs 3F Plastica)
   ```

3. **Energy Fetching**
   - Chunking 100 giorni per volta (limiti API ISC)
   - Query: `data_type=2` (energy), `ps_key_list=inverters`, `data_point=p1` (total)
   - Somma energia su tutti gli inverter

4. **Irradiation Fetching**
   - Richiede weather station ID
   - Special case: 3F Ferro/Plastica condividono stazione meteo di Ferro
   - Query: `data_type=2`, `ps_key=weather_station`, `data_point=p2`

5. **Special Cases (Portale)**
   ```python
   SPECIAL_PORTALE_PEAK_POWER_BY_SOURCE = {
       ("3F - Ferro e Plastica", "5079244"): 300.25,  # Ferro
       ("3F - Ferro e Plastica", "5079150"): 351.0,   # Plastica
   }
   # Override potenza nominale per fonte specifica
   
   SPECIAL_PORTALE_IRRADIATION_SOURCE_BY_SOURCE = {
       ("3F - Ferro e Plastica", "5079244"): "3F - Ferro",
       ("3F - Ferro e Plastica", "5079150"): "3F - Ferro",
   }
   # Entrambi leggono irraggiamento da Ferro
   ```

#### **SajMetricsProvider (zilio_monitoring/providers/saj.py)**

**Metodi Pubblici**:
```python
fetch_portale_snapshot(impianto, sorgente, window) → ProviderPlantSnapshot
```

**Logica Interna**:

1. **Device Selection**
   ```python
   # Priority 1: inverter
   inverter_devices = [d for d in impianto.dispositivi if type(d) == "inverter"]
   
   # Priority 2: fallback storage_inverter
   storage_devices = [d for d in impianto.dispositivi if type(d) == "storage_inverter"]
   
   # Se nessuno → NotImplementedError
   ```

2. **Device Matching**
   - Estrae `codice_dispositivo` da impianto.dispositivi
   - Confronta con remote devices da API SAJ
   - Raccoglie matched_serials

3. **Energy Computation**
   - Per ogni device_sn in matched_serials:
     - `start_value = get_energy_snapshot(device_sn, window.start_date 00:00)`
     - `end_value = get_energy_snapshot(device_sn, window.end_date 23:59)`
     - `energy = max(0, end_value - start_value)`
   - Somma su tutti i device

4. **Coverage Calculation**
   ```python
   coverage = devices_with_data / len(matched_serials)
   # Se coverage < 1.0 → alcuni device non hanno dati
   ```

### Layer 3: DTO & Calculator

#### **ProviderPlantSnapshot (Data Transfer Object)**
```python
@dataclass
class ProviderPlantSnapshot:
    source_name: str                      # "iSolarCloud" o "Saj - Elekeeper"
    plant_key: str                        # Plant ID da API
    plant_name: str                       # Nome impianto
    window_start: date                    # Data inizio periodo
    window_end: date                      # Data fine periodo
    peak_power_kw: float | None           # Potenza nominale
    status: str | None                    # "online"/"offline"/None
    window_energy_kwh: float | None       # Energia prodotta nel periodo
    window_irradiation_kwh_m2: float | None  # Irraggiamento (solo ISC)
    contractual_pr: float | None          # PR contrattuale
    has_weather_station: bool | None
    inverters_count: int | None           # Numero inverter totali
    inverters_ok: int | None              # Inverter con dati validi
    coverage: float | None                # inverters_ok / inverters_count
    missing_inverters: List[str]          # Serial dei device senza dati
```

#### **ComputedPlantMetrics (Metriche Calcolate)**
```python
@dataclass
class ComputedPlantMetrics:
    energy_kwh: float | None              # Energia window
    equivalent_hours: float | None        # energy_kwh / peak_power_kw
    daily_equivalent_hours: float | None  # media giornaliera (ISC)
    irradiation_kwh_m2: float | None      # Irraggiamento (ISC)
    performance_ratio: float | None       # energy / (power * irradiation)
    missed_production_kwh: float | None   # Produzione mancata vs PR contrat.
```

#### **DefaultMetricsCalculator**
```python
def compute(snapshot: ProviderPlantSnapshot, window: MetricsWindow) → ComputedPlantMetrics:
    # Ore equivalenti
    eq_hrs = snapshot.window_energy_kwh / snapshot.peak_power_kw
    
    # Performance Ratio
    pr = snapshot.window_energy_kwh / (
        snapshot.peak_power_kw * snapshot.window_irradiation_kwh_m2
    )
    
    # Mancata produzione (vs PR contrattuale)
    if snapshot.contractual_pr > 0:
        expected = snapshot.peak_power_kw * snapshot.window_irradiation_kwh_m2 * snapshot.contractual_pr
        missed = expected - snapshot.window_energy_kwh
```

### Layer 4: Registry & Collector

#### **ProviderRegistry**
```python
class ProviderRegistry:
    _providers = {
        "API_ISC": IscMetricsProvider(),
        "iSolarCloud": IscMetricsProvider(),
        "Saj - Elekeeper": SajMetricsProvider(),
        "---": FallbackMetricsProvider(),
        None: FallbackMetricsProvider(),
    }
    
    def get_provider(source_name: str | None) → Provider
```

**Mapping**:
- `ImpiantoSorgenteDati.nome_sorgente = "iSolarCloud"` → IscMetricsProvider
- `ImpiantoSorgenteDati.nome_sorgente = "Saj - Elekeeper"` → SajMetricsProvider

#### **MetricsCollector / MetricsSyncService**
```python
class MetricsCollector:
    def collect_portale_snapshots(pairs, source_name, window):
        # Itera su (impianto, sorgente) tuple
        for impianto, sorgente in pairs:
            provider = registry.get_provider(source_name)
            snapshot = provider.fetch_portale_snapshot(impianto, sorgente, window)
            metrics = calculator.compute(snapshot, window)
            yield impianto, sorgente, snapshot, metrics
    
    def collect_portale_with_outcome(pairs, source_name, window):
        # Raccogli con error handling
        results = []
        missing = []
        for impianto, sorgente in pairs:
            try:
                snapshot = provider.fetch_portale_snapshot(...)
                results.append((impianto, sorgente, snapshot, metrics))
            except NotImplementedError:
                missing.append(impianto.nome_impianto)
        return results, SyncOutcome(updated, skipped, missing, ...)
```

---

## Modelli di Dati

### **ImpiantoAnagrafica** (Centro di Gravità)
```python
class ImpiantoAnagrafica(models.Model):
    # Identificativi
    nome_impianto: CharField        # "RCT", "Alessi", "3F - Ferro"
    tag_impianto: CharField         # Abbreviazione unica
    codice_impianto: CharField      # Codice esterno (opzionale)
    
    # Tipo e Stato
    tipo_impianto: Choice           # "fotovoltaico" / "idroelettrico"
    stato_impianto: Choice          # "attivo" / "in_costruzione" / "sospeso" / "dismesso"
    
    # Localizzazione
    latitudine, longitudine: Decimal
    indirizzo, localita, provincia, regione: CharField
    
    # Caratteristiche Tecniche
    potenza_installata_kw: DecimalField
    data_entrata_esercizio: DateField
    
    # Anagrafici
    nome_proprietario, nome_cliente: CharField
```

### **ImpiantoSorgenteDati** (Mapping → Provider)
```python
class ImpiantoSorgenteDati(models.Model):
    impianto: FK(ImpiantoAnagrafica)
    
    # Provider specifico
    tipo_sorgente: Choice           # "monitoraggio_tecnico"
    nome_sorgente: CharField        # "iSolarCloud" o "Saj - Elekeeper"
    
    # Identificativi esterni
    identificativo_esterno: CharField  # Plant ID / Code da API
    nome_riferimento_esterno: CharField # Nome alternativo
    
    attiva: Boolean
```

**Esempio RCT**:
```
ImpiantoAnagrafica
├─ nome_impianto = "RCT"
├─ tag_impianto = "RCT"
├─ potenza_installata_kw = 250
└─ sorgenti_dati
   ├─ ImpiantoSorgenteDati
   │  ├─ nome_sorgente = "iSolarCloud"
   │  ├─ identificativo_esterno = "5488121"
   │  └─ attiva = True
   └─ ImpiantoSorgenteDati
      ├─ nome_sorgente = "Saj - Elekeeper"
      ├─ identificativo_esterno = "RCT_SAJ"
      └─ attiva = False  (al momento)
```

### **ImpiantoDispositivo** (Device-level Detail)
```python
class ImpiantoDispositivo(models.Model):
    impianto: FK(ImpiantoAnagrafica)
    
    tipo_dispositivo: CharField     # "inverter", "storage_inverter"
    codice_dispositivo: CharField   # Serial number / ps_key / SN
    attivo: Boolean
```

### **FotovoltaicoMetadata** (Specifiche FV)
```python
class FotovoltaicoMetadata(models.Model):
    impianto: OneToOne(ImpiantoAnagrafica)
    
    categoria_fv: Choice            # "cliente" / "proprieta"
    potenza_contratto_kw: Decimal
    
    # Flag speciali
    is_oem, is_ppu, is_agrivoltaico: Boolean
    
    # Contratto
    pr_contrattuale: Decimal        # Expected Performance Ratio (%)
```

### **FotovoltaicoStatoEconomico** (Dati Economici)
```python
class FotovoltaicoStatoEconomico(models.Model):
    impianto: OneToOne(ImpiantoAnagrafica)
    
    # Contratto
    data_inizio_contratto, data_fine_contratto: DateField
    tariffa_ppu_mwh: Decimal
    strumento_contabilizzazione_ppu: CharField
    
    # Scadenziario
    mese_primo_versamento: ChoiceField
    durata_versamenti_mesi: IntegerField
    importo_versamento_euro: Decimal
    
    # Stato sync
    api_sync_status: Choice         # "never", "ok", "partial", "error"
```

### **FotovoltaicoMetricheTecniche** (Output Sync)
```python
class FotovoltaicoMetricheTecniche(models.Model):
    impianto: OneToOne(ImpiantoAnagrafica)
    sorgente: FK(ImpiantoSorgenteDati)
    
    # Finestra temporale
    data_inizio_periodo: DateField
    data_fine_periodo: DateField
    
    # Metriche
    energia_prodotta_kwh: Decimal
    ore_equivalenti: Decimal
    irraggiamento_kwh_m2: Decimal
    performance_ratio: Decimal
    mancata_produzione_kwh: Decimal
    
    # Stato device
    numero_inverter_totali: IntegerField
    numero_inverter_funzionanti: IntegerField
    copertura_device: Decimal  # 0.0 - 1.0
    
    # Timestamp
    data_update: DateTimeField
```

---

## Provider ISC (iSolarCloud)

### Configurazione Credenziali

**Environment variables** (non hardcodare!):
```env
ISC_API_KEY=<API_KEY>
ISC_APPKEY=<APPKEY_FROM_ISC_DASHBOARD>
ISC_USER_ACCOUNT=<EMAIL_UTENTE>
ISC_USER_PASSWORD=<PASSWORD>
ISC_BASE_URL=https://gateway.isolarcloud.eu/openapi
```

### Flusso Login & Plant Fetch
```
1. login_ISC()
   POST /openapi/login.json
   body: {appkey, email, password, ...}
   response: {result_code, result_data: {token: "ABC123XYZ"}}

2. get_all_plants(token)
   POST /openapi/plant/list.json
   body: {appkey, token, curPage=1, size=500}
   response: {result_data: {rowCount, pageList: [{ps_id, ps_name, ps_status, ...}]}}

3. get_all_devices(token, plant_id=5488121)
   POST /openapi/device/list.json
   body: {appkey, token, ps_id, curPage=1, size=100}
   response: {result_data: {pageList: [{ps_key, device_name, device_type, ...}]}}
```

### Identificativi Gerarchia

**ps_key Structure** (Power Station Key):
```
5488121 _ 1 _ 1 _ 5
│       │ │ │ │
│       │ │ │ └─ Device Type (5=inverter)
│       │ │ └─── Device Number (1st or 2nd inverter)
│       │ └───── Circuit/String (usually 1)
│       └─────── Plant ID (5488121 = RCT)
└────────────── Foundation of ISC hierarchy
```

RCT Example:
```
Plant: 5488121 (RCT, 250 kW)
├─ Inverter 1: ps_key = "5488121_1_1_5"
├─ Inverter 2: ps_key = "5488121_1_2_5"
└─ Weather Stn: ps_key = "5488121_1_100_1" (device_type="5" per ISC)
```

### Energy Query

```python
def _fetch_energy_kwh(self, token, inverter_keys, plant_id, window):
    # Chunking: ISC limita a 100 giorni per query
    for chunk_start, chunk_end in _date_chunks(start, end, max_days=100):
        payload = {
            "appkey": LOGIN_PARAMS["appkey"],
            "token": token,
            "query_type": "1",       # 1=interval query
            "data_type": "2",        # 2=energy data
            "ps_key_list": inverter_keys,  # es. ["5488121_1_1_5", "5488121_1_2_5"]
            "data_point": "p1",      # p1=total, p2=dc, etc.
            "start_time": "20260501",
            "end_time": "20260630",
            "order": 0,              # Ascending
        }
        response = _post("getDeviceAllDataWithoutOracle", payload)
        # Process response and sum energy
        total_wh += sum(...)
```

**Response Structure**:
```json
{
  "result_code": "1",
  "result_data": {
    "ps_key": "5488121_1_1_5",
    "data": [
      {"date": "20260501", "day_energy": 4567.89},  // in Wh
      {"date": "20260502", "day_energy": 5123.45},
      ...
    ]
  }
}
```

### Irradiation Query

```python
def _fetch_irradiation_kwh_m2(self, token, weather_station, window):
    # Weather station ps_key
    ws_key = weather_station.get("ps_key")
    
    payload = {
        "query_type": "1",
        "data_type": "2",           # irradiation data
        "ps_key_list": [ws_key],
        "data_point": "p2",         # p2=irradiation
        "start_time": start.strftime("%Y%m%d"),
        "end_time": end.strftime("%Y%m%d"),
    }
    response = _post("getDeviceAllDataWithoutOracle", payload)
    # Sum irradiation over all days
```

### Special Cases

#### **3F Ferro e Plastica**
```python
IRRADIATION_ALIAS_BY_PLANT_NAME = {
    "3F - Plastica": "3F - Ferro",  # Plastica legge irraggiamento da Ferro
}

SPECIAL_PORTALE_PEAK_POWER_BY_SOURCE = {
    ("3F - Ferro e Plastica", "5079244"): 300.25,  # Ferro è 300.25 kW
    ("3F - Ferro e Plastica", "5079150"): 351.0,   # Plastica è 351 kW
}

SPECIAL_PORTALE_IRRADIATION_SOURCE_BY_SOURCE = {
    ("3F - Ferro e Plastica", "5079244"): "3F - Ferro",
    ("3F - Ferro e Plastica", "5079150"): "3F - Ferro",
}
```

**Logica**:
- 3F Ferro ha plant_id=5079244, Plastica ha plant_id=5079150
- Entrambi leggono irraggiamento da plant "3F - Ferro"
- Potenza nominale è diversa (300.25 vs 351)

#### **Multiple Sorgenti per Impianto**
Un impianto può avere due sorgenti ISC:
```
ImpiantoAnagrafica (3F - Ferro)
├─ sorgenti_dati[0]
│  ├─ nome_sorgente = "iSolarCloud"
│  ├─ identificativo_esterno = "5079244"  # Plant ID ISC
│  └─ inverters = 3 device
└─ sorgenti_dati[1]
   ├─ nome_sorgente = "iSolarCloud"
   ├─ identificativo_esterno = "alternativo"  # Altro plant?
   └─ inverters = 2 device

// Nel portale: traccia separatamente
FotovoltaicoMetricheTecniche(impianto, sorgente[0]) → Ferro metrics
FotovoltaicoMetricheTecniche(impianto, sorgente[1]) → Plastica metrics
```

---

## Provider SAJ (Elekeeper)

### Configurazione Credenziali

**Environment variables**:
```env
SAJ_APP_ID=<APP_ID_DA_DASHBOARD_SAJ>
SAJ_APP_SECRET=<SECRET>
SAJ_BASE_URL=https://developer.saj-electric.com/prod-api
```

### Flusso Token & Plant Fetch

```
1. get_token()
   GET /open/api/access_token?appId=...&appSecret=...
   response: {data: {access_token: "TOKEN123"}}

2. get_plants(headers)
   GET /open/api/developer/plant/page?appId=...&pageSize=100&pageNum=1
   headers: {accessToken, clientSecret, content-language}
   response: {rows: [{plantId, plantName, ...}]}

3. get_devices(headers, plant_id)
   GET /open/api/developer/device/page?plantId=...&pageSize=100
   response: {rows: [{deviceSn, deviceType, ...}]}
```

### Device Type Classification

```python
def device_type(device):
    """Return 'inverter', 'storage_inverter', or 'other'"""
    tipo = device.get("deviceType")
    if tipo == "1":
        return "inverter"
    elif tipo == "2":
        return "storage_inverter"
    else:
        return "other"
```

**Selezione Device**:
```python
def _select_energy_devices(local_devices):
    # Priority 1: inverter
    inverters = [d for d in local_devices if device_type(d) == "inverter"]
    if inverters:
        return inverters, "inverter"
    
    # Priority 2: storage_inverter (fallback)
    storage = [d for d in local_devices if device_type(d) == "storage_inverter"]
    if storage:
        return storage, "storage_inverter_fallback"
    
    # No valid device
    raise NotImplementedError("No usable SAJ devices found")
```

### Energy Snapshot Pattern

**SAJ non offre energia aggregata su range**: deve interrogare punto-punto.

```python
def get_device_energy_snapshot(headers, device_sn, at_time: datetime) -> float:
    # Query storico 24h prima di at_time
    response = requests.get(
        "/open/api/device/historyDataCommon",
        params={
            "deviceSn": device_sn,
            "startTime": (at_time - 24h).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": at_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    records = response.json().get("data", [])
    if not records:
        return None
    # Estrai energia totale dall'ultimo record
    return float(records[-1].get("totalPvEnergy", 0))
```

### Window Energy Computation

```python
def _compute_window_energy_kwh(headers, selected_serials, window):
    start_dt = datetime.combine(window.start_date, time(0, 0, 0))
    end_dt = datetime.combine(window.end_date, time(23, 59, 59))
    
    total_energy_kwh = 0.0
    devices_with_data = 0
    missing_serials = []
    
    for device_sn in selected_serials:
        start_value = get_device_energy_snapshot(headers, device_sn, start_dt)
        end_value = get_device_energy_snapshot(headers, device_sn, end_dt)
        
        if start_value is None or end_value is None:
            missing_serials.append(device_sn)
            continue
        
        energy = max(0.0, end_value - start_value)
        total_energy_kwh += energy
        devices_with_data += 1
    
    coverage = devices_with_data / len(selected_serials) if selected_serials else None
    return total_energy_kwh, devices_with_data, missing_serials
```

### Coverage & Reliability

```python
# Nel ProviderPlantSnapshot
coverage = round(devices_with_data / len(matched_serials), 4)

# Se coverage < 1.0 → alcuni device sono offline o non hanno dati
# Il portale deve indicare "X device su Y funzionanti"
```

---

## Flusso di Sincronizzazione

### MetricsSyncService Workflow

```python
class MetricsSyncService:
    def sync_portale_fotovoltaico_isc_metrics(self, window=None):
        # 1. Recupera queryset di impianti ISC
        queryset = self._get_portale_isc_queryset()
        
        # 2. Itera e raccoglie snapshot
        results = []
        missing = []
        for impianto in queryset.prefetch_related("sorgenti_dati", "dispositivi"):
            sorgenti = impianto.sorgenti_dati.filter(
                attiva=True,
                nome_sorgente="iSolarCloud"
            )
            
            for sorgente in sorgenti:
                try:
                    provider = registry.get_provider("iSolarCloud")
                    snapshot = provider.fetch_portale_snapshot(
                        impianto, sorgente, window
                    )
                    metrics = calculator.compute(snapshot, window)
                    results.append((impianto, sorgente, snapshot, metrics))
                except NotImplementedError as e:
                    logger.warning(f"[ISC] Skipped {impianto.nome_impianto}: {e}")
                    missing.append(impianto.nome_impianto)
        
        # 3. Atomic write to DB
        with transaction.atomic():
            for impianto, sorgente, snapshot, metrics in results:
                metriche_obj, created = FotovoltaicoMetricheTecniche.objects.update_or_create(
                    impianto=impianto,
                    sorgente=sorgente,
                    defaults={
                        "data_inizio_periodo": window.start_date,
                        "data_fine_periodo": window.end_date,
                        "energia_prodotta_kwh": metrics.energy_kwh,
                        "ore_equivalenti": metrics.equivalent_hours,
                        "irraggiamento_kwh_m2": metrics.irradiation_kwh_m2,
                        "performance_ratio": metrics.performance_ratio,
                        "mancata_produzione_kwh": metrics.missed_production_kwh,
                        ...
                    }
                )
        
        return SyncOutcome(updated=len(results), skipped=0, missing=missing, ...)
```

### Phase Separation

**Critica**: Network I/O e DB write sono separati per evitare lock su SQLite.

```
Phase 1: Network I/O (fuori transaction)
├─ Chiama provider.fetch_snapshot() per ogni impianto
├─ Riceve ProviderPlantSnapshot
└─ No database locks

Phase 2: Persistence (in transaction atomica)
├─ Single transaction.atomic() block
├─ Scrive tutti i risultati in una sola operazione
└─ SQLite locked for minimum time
```

---

## Calcolo Metriche

### Performance Ratio (PR)

```
PR = Energia Prodotta / (Potenza Nominale × Irraggiamento)
   = E [kWh] / (P [kW] × H [kWh/m²])
```

- **ISC**: Ha stazione meteo → calcola PR effettivo
- **SAJ**: No irraggiamento → PR = None

### Ore Equivalenti

```
Ore Equivalenti = Energia Prodotta / Potenza Nominale
                = E [kWh] / P [kW]
```

Rappresenta il numero di ore "equivalenti" a potenza nominale.

### Mancata Produzione

```
Se PR contrattuale è definito:
   Energia Attesa = P [kW] × H [kWh/m²] × PR_contrattuale
   Mancata = Energia Attesa - Energia Effettiva
   
Se PR_contrattuale = 0.8 e Energia Attesa = 1000 kWh
   Energia Effettiva = 950 kWh
   Mancata = 50 kWh
```

---

## Persistenza Dati

### ORM Models Update

```python
# PortaleZilioService/services/persistence.py

def persist_metrics_to_impianto(impianto, metrics: ComputedPlantMetrics):
    """Save computed metrics to Impianto model."""
    impianto.ultimo_aggiornamento = now()
    impianto.energia_kwh_ultimi_12_mesi = metrics.energy_kwh
    impianto.ore_equivalenti_ultimi_12_mesi = metrics.equivalent_hours
    impianto.pr_ultimi_12_mesi = metrics.performance_ratio
    impianto.save(update_fields=[...])

def persist_metrics_to_fotovoltaico_metriche_tecniche(impianto, sorgente, metrics):
    """Save to detailed metrics table."""
    obj, created = FotovoltaicoMetricheTecniche.objects.update_or_create(
        impianto=impianto,
        sorgente=sorgente,
        defaults={
            "data_inizio_periodo": metrics.window_start,
            "data_fine_periodo": metrics.window_end,
            "energia_prodotta_kwh": metrics.energy_kwh,
            "ore_equivalenti": metrics.equivalent_hours,
            "irraggiamento_kwh_m2": metrics.irradiation_kwh_m2,
            "performance_ratio": metrics.performance_ratio,
            "mancata_produzione_kwh": metrics.missed_production_kwh,
            "numero_inverter_totali": metrics.inverters_count,
            "numero_inverter_funzionanti": metrics.inverters_ok,
            "copertura_device": metrics.coverage,
            "data_update": now(),
        }
    )
    return obj, created
```

---

## Problemi & Limitazioni

### 1. ⚠️ **Credenziali Hardcoded**
- **Luogo**: `zilio_monitoring/clients/api_config.py`, probabilmente
- **Impatto**: Security risk
- **Fix**: Migrare a environment variables (`.env` + `python-dotenv`)

### 2. ⚠️ **Duck Typing senza Validazione**
Provider assume che impianto/sorgente/dispositivo abbiano certi attributi:
```python
# In isc.py
plant_name = api_plant.get("ps_name") or getattr(impianto, "nome_impianto", "")
```
Se attributo non esiste → valore falsy, comportamento silenzioso.

### 3. ⚠️ **Nessun Caching**
Ogni sync = query API fresca. Per finestre lunghe (12 mesi) con tanti impianti:
- **ISC**: 100 giorni × 12 impianti = 12 query (acceptable)
- **SAJ**: 365 giorni × 365 punti × 12 impianti = molto lento

**Soluzione futura**: Redis cache con TTL 24h

### 4. ⚠️ **Errori di Matching Plant**
```python
def _find_matching_plant(self, token, impianto):
    candidates = {normalize(getattr(impianto, "nome_impianto", None)), ...}
    for plant in plants:
        plant_keys = {normalize(plant.get("ps_name")), normalize(str(plant.get("ps_id")))}
        if candidates & plant_keys:
            return plant
    return None
```
Se plant non trovato → **NotImplementedError** (skip silenzioso in sync)

### 5. ⚠️ **SAJ: No Irradiation Data**
SAJ Elekeeper non espone dati meteo → Performance Ratio non calcolabile.

### 6. ⚠️ **3F Special Cases Hardcoded**
Se si aggiungono nuovi impianti con comportamento speciale → modifica codice.

### 7. ⚠️ **Coverage < 1.0 Non Bloccante**
Se solo 1 su 3 device ha dati:
```python
coverage = 0.33
# Il sync continua comunque e salva energy parziale
# L'utente potrebbe non accorgersi
```

### 8. 📊 **Metriche Incomplete per SAJ**
```python
# SAJ snapshot
ProviderPlantSnapshot(
    window_energy_kwh=3000,        # ✅ OK
    window_irradiation_kwh_m2=None,  # ❌ Missing
    status=None,                    # ❌ Missing
    daily_equivalent_hours=None,    # ❌ Missing
)
```

---

## Roadmap & Recommendations

### Urgente (Sprint 1)

1. **Security**: Migrare credenziali a `.env`
   ```python
   # zilio_monitoring/clients/config.py
   def require_env(var_name):
       value = os.getenv(var_name)
       if not value:
           raise ValueError(f"Missing {var_name} in environment")
       return value
   ```

2. **Logging**: Aggiungere log dettagliati nelle fasi di matching/fetch
   ```python
   logger.info(f"[ISC] Matching plant for {impianto.nome_impianto}")
   logger.debug(f"[ISC] Candidates: {candidates}")
   logger.warning(f"[ISC] Plant not found, skipping")
   ```

3. **Model Validation**: Aggiungere docstring ai metodi provider
   ```python
   def fetch_snapshot(self, impianto, window: MetricsWindow) -> ProviderPlantSnapshot:
       """
       Fetch snapshot from iSolarCloud.
       
       Args:
           impianto: Must have nome_impianto, tag_impianto, potenza_installata_kw
           window: MetricsWindow with start_date, end_date
       
       Returns:
           ProviderPlantSnapshot
       
       Raises:
           NotImplementedError: If plant not found on iSolarCloud
           RuntimeError: If API login fails
       """
   ```

### High Priority (Sprint 2-3)

4. **Caching**: Implementare Redis cache
   ```python
   @cache_result(ttl=86400)  # 24 hours
   def fetch_portale_snapshot(self, impianto, sorgente, window):
       ...
   ```

5. **Tests**: Aggiungere unit test per provider
   ```python
   # zilio_monitoring/tests/test_isc_provider.py
   def test_matching_plant_rct():
       provider = IscMetricsProvider()
       # Mock login
       # Mock get_all_plants
       snapshot = provider.fetch_snapshot(mock_impianto, window)
       assert snapshot.plant_name == "RCT"
   ```

6. **SAJ Enhancement**: Aggiungere support meteo
   - Interrogare API SAJ per weather data
   - Calcolare PR anche per SAJ

7. **Coverage Thresholding**: Bloccare sync se coverage < threshold
   ```python
   if metrics.coverage and metrics.coverage < 0.5:
       logger.error(f"Coverage too low: {metrics.coverage}")
       # Mark as error, don't persist
   ```

### Nice to Have (Sprint 4+)

8. **Multiple Provider Aggregation**: Sommare energie da più provider
   ```
   impianto con 2 sorgenti ISC → energy_totale = sorgente1 + sorgente2
   ```

9. **Drift Detection**: Identificare anomalie
   ```python
   if pr < 0.7 or pr > 0.95:
       logger.warning(f"Abnormal PR: {pr}")
   ```

10. **Historical Trend**: Tracciare PR/Eff.Hours su serie temporale
    ```
    FotovoltaicoMetricheTecniche per ogni mese
    → Grafico trend 12 mesi
    ```

---

## File Key Locations

```
Produzione/
├─ PortaleZilioService/
│  ├─ models.py              (ImpiantoAnagrafica, FotovoltaicoMetadata, ...)
│  ├─ views.py               (home_view, overview_view, API endpoints)
│  ├─ services/
│  │  ├─ sync.py             (MetricsSyncService)
│  │  ├─ persistence.py      (ORM save logic)
│  │  ├─ calculators.py      (View formatters)
│  │  ├─ rows_builder_fotovoltaico.py
│  │  ├─ rows_builder_idroelettrico.py
│  │  └─ ...
│  └─ API_inverter/          (Legacy ISC API, deprecate soon)
│
zilio_monitoring/            (Reusable library)
├─ clients/
│  ├─ isolarcloud.py         (HTTP client for iSolarCloud API)
│  ├─ saj.py                 (HTTP client for SAJ API)
│  ├─ api_config.py          (ISC endpoints, page sizes)
│  └─ config.py              (Environment variable helpers)
├─ providers/
│  ├─ isc.py                 (IscMetricsProvider adapter)
│  ├─ saj.py                 (SajMetricsProvider adapter)
│  ├─ fallback.py            (FallbackMetricsProvider)
│  └─ helpers.py             (normalize, safe_float, ...)
├─ calculators.py            (DefaultMetricsCalculator)
├─ dtos.py                   (ProviderPlantSnapshot, ComputedPlantMetrics)
├─ registry.py               (ProviderRegistry)
├─ sync.py                   (MetricsCollector)
├─ windows.py                (MetricsWindow, rolling_12_months)
└─ README.md                 (Usage examples)
```

---

## Conclusioni

**PortaleZilioService + zilio_monitoring** rappresenta una **architettura moderna e modulare**:

✅ **Strengths**:
- Separazione provider HTTP clients (riusabile)
- DTO pattern per type safety
- Registry pattern per estensibilità
- Atomic persistence (no partial updates)
- Phase separation (network I/O ≠ DB write)

⚠️ **Weaknesses**:
- Credenziali non gestite (security)
- Duck typing senza validazione (silent failures)
- Nessun caching (performance)
- SAJ manca irraggiamento (incomplete metrics)
- 3F special cases hardcoded (manutenzione)

🎯 **Next Steps**:
1. Ambiente variables per credenziali
2. Unit test per provider
3. Logging dettagliato
4. Caching Redis
5. SAJ meteo integration
