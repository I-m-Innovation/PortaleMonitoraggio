# Flusso SAJ - Visualizzazione Grafici nel PortaleMonitoraggio

**Documento di Analisi**: Controllo del flusso per il provider SAJ nella visualizzazione dei grafici

**Data**: Maggio 2026  
**Repository**: I-m-Innovation/PortaleImpianti  
**Branch**: feature/portale-zilio-service-app

---

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Routing e Endpoint](#routing-e-endpoint)
3. [Flusso Completo Richiesta](#flusso-completo-richiesta)
4. [Configurazione Impianti SAJ](#configurazione-impianti-saj)
5. [Source Selection Logic](#source-selection-logic)
6. [API SAJ - Dettagli Tecnici](#api-saj---dettagli-tecnici)
7. [Aggregazione e Processing Dati](#aggregazione-e-processing-dati)
8. [Risposta al Frontend](#risposta-al-frontend)
9. [Problemi Noti e Criticità](#problemi-noti-e-criticità)
10. [Testing e Debug](#testing-e-debug)
11. [Diagramma Sequenza](#diagramma-sequenza)

---

## Panoramica

### Cosa fa il flusso SAJ?
Quando un utente visualizza il grafico giornaliero di potenza di un impianto SAJ nel PortaleMonitoraggio:

1. **Request**: `GET /get-chart-real-time/` riceve il parametro `nickname` impianto
2. **Validazione**: Verifica che `lettura_dati = 'API_SAJ'`
3. **Configurazione**: Carica la configurazione specifica dell'impianto da `PLANT_DEVICE_OVERRIDES`
4. **Autenticazione SAJ**: Ottiene token dalle credenziali configurate
5. **Query SAJ**: Recupera lista plant, lista device, dati storici
6. **Source Selection**: Sceglie la sorgente (device vs EMS) e il campo potenza in base all'impianto
7. **Aggregazione**: Aggrega dati temporali e interpola eventuali gap
8. **Response**: Ritorna JSON con serie temporale in 5 minuti

### Caratteristica Principale
**Non c'è una logica unica per tutti gli impianti SAJ**. La configurazione varia significativamente per ogni plant perché SAJ espone i dati in modi diversi.

---

## Routing e Endpoint

### Endpoint Principale
```
GET /get-chart-real-time/?nickname=<impianto_nickname>
```

**Ubicazione**: [MonitoraggioImpianti/APIViews.py](MonitoraggioImpianti/APIViews.py)

**Metodo**: `chart_real_time(request)` (line ~340)

**Handler SAJ**: Sezione `elif impianto.lettura_dati == 'API_SAJ'` (line 344-405)

### URL Pattern
```python
# urls.py
path('get-chart-real-time/', APIViews.chart_real_time, name='chart-real-time'),
```

---

## Flusso Completo Richiesta

```
┌─────────────────────────────────────────────────────────────────────┐
│ USER: Clicca su impianto SAJ nel PortaleMonitoraggio                │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND: GET /get-chart-real-time/?nickname=acquanova290           │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
╔═════════════════════════════════════════════════════════════════════╗
║ DJANGO VIEW: chart_real_time() @ APIViews.py:340                    ║
║                                                                      ║
║ 1. Recupera parametro 'nickname' dalla query string                 ║
║ 2. Carica Impianto da DB                                            ║
║ 3. Verifica: impianto.lettura_dati == 'API_SAJ'                     ║
║ 4. Se ≠ SAJ → branch diverso (ISC, HIGECO, etc)                     ║
╚═════════════════════════════════────════────────────────────────────╝
                                   │
                                   ▼
╔═════════════════════════════════════════════════════════════════════╗
║ SAJ HANDLER: (line 344-405)                                          ║
║                                                                      ║
║ • nome_impianto = impianto.nome_impianto                            ║
║ • t_start = 00:00:00 today                                          ║
║ • t_end_display = 23:55:00 today                                    ║
║                                                                      ║
║ CALL: SAJ.get_saj_day_data(impianto, start=t_start, end=Now)        ║
╚═════════════════════════════════════════════════════════════════════╝
                                   │
                                   ▼
╔═════════════════════════════════════════════════════════════════════╗
║ get_saj_day_data() @ API_SAJ.py:355                                 ║
║ ────────────────────────────────────────────────────────────────────║
║ Ritorna: (df_time_series, led, today_energy_kwh)                   ║
║                                                                      ║
║ STEPS INTERNI:                                                       ║
║  1. Carica configurazione impianto da PLANT_DEVICE_OVERRIDES        ║
║  2. Estrae device_serial_numbers da config                          ║
║  3. Autentica con SAJ (get_token)                                   ║
║  4. Recupera lista plant (get_plants)                               ║
║  5. Trova plant corretto (name/nickname/tag matching)               ║
║  6. Recupera device del plant (get_devices)                         ║
║  7. Se power_source=='ems_history':                                 ║
║     → Recupera dati EMS (_get_ems_history_records)                  ║
║  8. Per ogni device in selected_device_serials:                     ║
║     → Recupera dati storici (_get_history_records)                  ║
║  9. Aggrega/campiona serie temporale                                ║
║ 10. Genera LED status dai device                                    ║
╚═════════════════════════════════════════════════════════════════════╝
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RESPONSE PROCESSING (APIViews.py:360-405)                           │
│                                                                      │
│ • Converti timestamp in formato display (%H:%M)                     │
│ • Interpola valori mancanti (merge con 5min grid)                   │
│ • Calcola info aggiuntive:                                          │
│   - today_energy_kwh                                                │
│   - co2_kg = energy * 0.457                                         │
│   - alberi equivalenti = co2 / (annuale/1000)                      │
│   - case equivalenti = energy / 9.5                                 │
│ • Prepara df_display per output JSON                                │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ JSON RESPONSE:                                                       │
│ {                                                                    │
│   "time": ["00:00", "00:05", ..., "23:55"],                         │
│   "pot": [null, 125.3, ..., 0],                 # potenza in kW    │
│   "k_last": 287,                 # indice ultimo punto valido       │
│   "t_last": "23:50:00",          # timestamp ultimo punto           │
│   "led": "led-green",            # stato device                     │
│   "PLast": 234.5,                # potenza ultima in kW             │
│   "info": {                                                          │
│     "co2": 45.3,                 # kg CO2 prodotti                  │
│     "case": 34,                  # case equivalenti                 │
│     "alberi": 127,               # alberi equivalenti               │
│     "energy": 321.8              # energia totale kWh               │
│   }                                                                  │
│ }                                                                    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND: Renderizza grafico con Highcharts                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Configurazione Impianti SAJ

### Location File
**[MonitoraggioImpianti/API_SAJ.py](MonitoraggioImpianti/API_SAJ.py) - Line 14-68**

### Struttura Dictionary PLANT_DEVICE_OVERRIDES

```python
PLANT_DEVICE_OVERRIDES = {
    "<impianto_nickname_normalizzato>": {
        # Device Management
        "device_serial_numbers_to_query": [  # Quali inverter/device interrogare
            "CSV6503J2416E00004",
        ],
        
        # Power Data Source Selection
        "power_source": "devices",           # "devices" | "ems_history"
        "power_extraction_mode": "field",    # "field" | "pv_channels_sum"
        "power_field_name": "totalPVPower",  # Campo potenza da usare
        
        # Energy Data Source
        "energy_source": "devices",          # "devices" | "ems_history"
        "energy_field_name": "todayPvEnergy",# Campo energia
        
        # EMS Configuration (se power_source == "ems_history")
        "ems_sn": "M5530J2428000038",        # Serial Number EMS
        
        # Sampling Strategy
        "bucket_aggregation": "nearest_grid", # "nearest_grid" | "sum"
        "timestamp_rounding": "none",        # "5min" | "none"
    },
    ...
}
```

### Impianti Configurati Attuali

#### 1. **Col Roigo 50 kWp**
```python
"colroigo50kwp": {
    "device_serial_numbers_to_query": ["CSV6503J2416E00004"],
    "bucket_aggregation": "nearest_grid",
    "timestamp_rounding": "none",
    "power_extraction_mode": "field",
    "power_field_name": "totalPVPower",
    "energy_field_name": "todayPvEnergy",
}
```

**Caratteristiche**:
- Sorgente: Device singolo
- Strategia: Campionamento del valore più vicino su griglia 5min
- Motivo: L'endpoint EMS non ritorna record per questo plant

#### 2. **Zilio Group 490 kW**
```python
"ziliogroup490kw": {
    "device_serial_numbers_to_query": [
        "C6T9104J2314E00560",   # inverter
        "C6T9104J2315E00670",   # inverter
        "C6V9104G2424E00228",   # inverter
        "C6V9104J2421E01334",   # inverter
    ],
    "power_source": "ems_history",
    "ems_sn": "M5530J2428000038",
    "power_extraction_mode": "field",
    "power_field_name": "parallMeterPower",
    "energy_source": "ems_history",
    "energy_field_name": "parallTodayPVEnergy",
}
```

**Caratteristiche**:
- Sorgente: EMS (non device)
- Motivo: Device C6 avevano totalPVPower=0 ma curve corrette non somme device
- Il dato corretto della dashboard SAJ è `parallMeterPower`

#### 3. **RCT Bramante**
```python
"rctbramante": {
    "device_serial_numbers_to_query": [
        "C6VC125J2430E03394",   # inverter
        "CSV6503J2506E00137",   # S12
        "CSV6503J2506E00141",   # S12
    ],
    "power_source": "ems_history",
    "ems_sn": "M5530J2428000023",
    "power_extraction_mode": "field",
    "power_field_name": "parallMeterPower",
    "energy_source": "ems_history",
    "energy_field_name": "parallTodayPVEnergy",
}
```

**Caratteristiche**: EMS-based come Zilio

#### 4. **Acquanova 1150 kW**
```python
"acquanova1150": {
    "device_serial_numbers_to_query": ["C6V9104J2421E01334"],
    "bucket_aggregation": "nearest_grid",
    "timestamp_rounding": "none",
    "power_extraction_mode": "field",
    "power_field_name": "totalGridPowerWatt",
    "energy_field_name": "todayPvEnergy",
}
```

#### 5. **Acquanova 290 kW**
```python
"acquanova290": {
    "device_serial_numbers_to_query": ["C6T9104J2314E00560"],
    "bucket_aggregation": "nearest_grid",
    "timestamp_rounding": "none",
    "power_extraction_mode": "field",
    "power_field_name": "totalGridPowerWatt",
    "energy_field_name": "todayPvEnergy",
}
```

---

## Source Selection Logic

Il flusso sceglie la sorgente dati in base alla configurazione:

### 1️⃣ Device-Based Power (power_source = "devices")

```python
# Per ogni device_sn in selected_device_serials:
records = _get_history_records(headers, device_sn, start, end)
device_df = _build_device_timeseries_dataframe(records, config)
device_dataframes.append(device_df)

# Aggregazione: SOMMA di tutti i device
df_time_series = _aggregate_device_timeseries(device_dataframes)
# Oppure: CAMPIONAMENTO su griglia se bucket_aggregation="nearest_grid"
```

**Campi Estratti** (in base a `power_extraction_mode`):
- `field`: Legge il campo specificato in `power_field_name`
- `pv_channels_sum`: Somma i campi `pv1power, pv2power, ..., pv16power`

### 2️⃣ EMS-Based Power (power_source = "ems_history")

```python
# Interroga endpoint EMS storico:
ems_records = _get_ems_history_records(
    headers=headers,
    plant_id=str(plant["plantId"]),
    ems_sn=ems_sn,      # Master EMS
    start=start,
    end=end,
)
ems_df = _build_device_timeseries_dataframe(ems_records, config)
device_dataframes.append(ems_df)

# Nota: Quando è EMS, si interrogano ANCHE i device per l'energia
# (se energy_source != "ems_history")
```

**Endpoint**: `/open/api/device/emsHistoryData`

**Limite**: ⚠️ Massimo 1h55min per request (API limit SAJ)
- Il flusso divide le richieste in finestre di 1h55min se il range è più lungo

**Handling Rate Limit (429)**:
```python
if payload.get("code") == 429:
    time.sleep(0.6 * (attempt + 1))  # Retry con backoff
    continue
```

### 3️⃣ Energy Extraction

```python
# Se energy_source == "ems_history":
today_energy_kwh = _extract_last_today_energy_kwh(
    ems_records, 
    config["energy_field_name"]
)
# Altrimenti somma dai device:
today_energy_kwh = sum(device_today_energy_values)
```

---

## API SAJ - Dettagli Tecnici

### File di Integrazione

**Location**: [PortaleZilioService/API_inverter/saj_client.py](PortaleZilioService/API_inverter/saj_client.py)

### Credenziali API

```python
APP_ID = "VH_rQtUpniM"
APP_SECRET = "hiDHa5riPzzTl2vixkVCWh4kpniM6ZrJZxkjunfShyuVrQtUFmPCbKu6oUaw7WAi"
BASE_URL = "https://developer.saj-electric.com/prod-api"
```

### Endpoint API SAJ Utilizzati

#### 1. **Autenticazione**
```
GET /open/api/access_token?appId=<id>&appSecret=<secret>

Response:
{
  "code": 200,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "expires_in": 86400
  }
}
```

#### 2. **Lista Plant**
```
GET /open/api/developer/plant/page?
    appId=<id>
    &pageSize=100
    &pageNum=1

Headers:
  accessToken: <token>
  clientSecret: <secret>
  content-language: en_US

Response:
{
  "code": 200,
  "rows": [
    {
      "plantId": "12345",
      "plantName": "Col Roigo 50 kWp",
      "capacity": 50000,
      ...
    }
  ]
}
```

#### 3. **Lista Device del Plant**
```
GET /open/api/developer/device/page?
    appId=<id>
    &plantId=<plant_id>
    &pageSize=100
    &pageNum=1

Response:
{
  "rows": [
    {
      "deviceSn": "CSV6503J2416E00004",
      "deviceName": "Inverter 1",
      "isOnline": 1,
      "isAlarm": 0,
      ...
    }
  ]
}
```

#### 4. **Dati Storici Device**
```
GET /open/api/device/historyDataCommon?
    deviceSn=<device_sn>
    &startTime=2026-05-25 00:00:00
    &endTime=2026-05-25 23:59:59
    &fields=deviceSn,dataTime,totalGridPowerWatt,totalPVPower,
             todayPvEnergy,totalPvEnergy,pv1power,...,pv16power

Response:
{
  "code": 200,
  "data": [
    {
      "dataTime": "2026-05-25 08:32:15",
      "totalPVPower": 125600,     # Watts
      "todayPvEnergy": 1254.23,   # kWh
      ...
    }
  ]
}
```

#### 5. **Dati Storici EMS**
```
GET /open/api/device/emsHistoryData?
    emsSn=<ems_serial>
    &plantId=<plant_id>
    &startTime=2026-05-25 00:00:00
    &endTime=2026-05-25 01:55:00

Response:
{
  "code": 200,
  "data": [
    {
      "dataTime": "2026-05-25 08:32:15",
      "parallMeterPower": 234500,     # Watts
      "parallTodayPVEnergy": 3214.5,  # kWh
      ...
    }
  ]
}
```

⚠️ **Limitazione**: Range massimo 1h55min per request

### Error Handling

```python
class SajApiError(RuntimeError):
    pass

# Viene generato in caso di:
- Token missing
- Plant not found
- No devices available
- EMS SN not configured
- API errors (429, 5xx, etc)
```

---

## Aggregazione e Processing Dati

### Step 1: Estrazione Timestamp

```python
def _extract_timestamp(record: dict) -> datetime | None:
    """Prova più possibili chiavi di timestamp"""
    for key in ("dataTime", "time", "collectTime", "createTime", "recordTime", "timestamp"):
        raw_value = record.get(key)
        if raw_value:
            parsed = pd.to_datetime(raw_value, errors="coerce")
            if pd.notna(parsed):
                return parsed.to_pydatetime()
    return None
```

### Step 2: Estrazione Potenza

```python
def _extract_power_watts(record: dict, config: dict) -> float | None:
    if config.get("power_extraction_mode") == "pv_channels_sum":
        # Somma pv1power + pv2power + ... + pv16power
        values = [_parse_float(record.get(f"pv{i}power")) for i in range(1, 17)]
        return sum([v for v in values if v is not None])
    
    # Altrimenti leggi il campo specificato
    field_name = config.get("power_field_name")
    return _parse_float(record.get(field_name))
```

### Step 3: Costruzione DataFrame per Device

```python
def _build_device_timeseries_dataframe(records: list[dict], config: dict) -> pd.DataFrame:
    rows = []
    for record in records:
        timestamp = _extract_timestamp(record)
        power_w = _extract_power_watts(record, config)
        
        if timestamp is None or power_w is None:
            continue
            
        # Rounding timestamp
        if config.get("timestamp_rounding") == "5min":
            timestamp = pd.Timestamp(timestamp).round("5min").to_pydatetime()
        
        rows.append({
            "timestamp": timestamp,
            "power_kw": power_w / 1000.0,  # Converti W → kW
        })
    
    # Deduplicazione e sort
    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["timestamp"], keep="last").sort_values("timestamp")
```

### Step 4: Aggregazione Multi-Device

```python
def _aggregate_device_timeseries(device_dataframes: list[pd.DataFrame]) -> pd.DataFrame:
    """Somma potenza di multiple devices per ogni timestamp"""
    if not device_dataframes:
        return pd.DataFrame(columns=["t", "P"])
    
    merged = pd.concat(device_dataframes, ignore_index=True)
    aggregated = merged.groupby("timestamp", as_index=False)["power_kw"].sum()
    aggregated.columns = ["t", "P"]
    return aggregated
```

### Step 5: Campionamento su Griglia (bucket_aggregation="nearest_grid")

```python
def _sample_nearest_to_5min_grid(device_dataframes: list[pd.DataFrame], 
                                  start: datetime, end: datetime) -> pd.DataFrame:
    """Campiona il valore più vicino su griglia 5min standard"""
    
    # Griglia 5 minuti
    grid = pd.DataFrame({"timestamp": pd.date_range(start, end, freq="5min")})
    
    # Merge asof: per ogni timestamp griglia, trova il record più vicino
    # (entro tolleranza 2min30s)
    merged = pd.merge_asof(
        grid, 
        merged_df.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("2min30s")
    )
    
    return merged[merged["power_kw"].notna()]
```

**Differenza tra le strategie**:
- **"sum"**: Aggrega somma con frequenza naturale dati
- **"nearest_grid"**: Campiona su griglia 5min fissa, riempiendo con valore più vicino

### Step 6: Interpolazione Gap Interni

```python
def _fill_small_internal_gaps(df_time_series: pd.DataFrame, 
                               max_missing_points: int = 2) -> pd.DataFrame:
    """Interpola lineari gap interni (max 2 punti = 10 minuti)"""
    
    # Reindex su griglia 5min completa
    full_index = pd.date_range(df_time_series["t"].iloc[0], 
                                df_time_series["t"].iloc[-1], 
                                freq="5min")
    
    df_reindexed = df_time_series.set_index("t").reindex(full_index)
    
    # Interpolazione lineare (solo interni, max 2 punti)
    df_reindexed["P"] = df_reindexed["P"].interpolate(
        method="linear",
        limit=max_missing_points,
        limit_area="inside"
    )
    
    return df_reindexed.reset_index()
```

⚠️ Usato solo per EMS-based power (che tende ad avere gap occasionali)

### Step 7: LED Status

```python
def _build_led_from_devices(devices: list[dict]) -> str:
    """Determina lo stato LED dai device selezionati"""
    
    alarms = [d for d in devices if str(d.get("isAlarm", 0)) == "1"]
    online = [d for d in devices if str(d.get("isOnline", 0)) == "1"]
    
    if alarms:
        return "led-red"      # Almeno un device in allarme
    if online:
        return "led-green"    # Almeno un device online
    return "led-gray"         # Tutti offline
```

---

## Risposta al Frontend

### Transformazioni Finali (APIViews.py:360-405)

```python
# 1. Ordinamento e validazione
df_time_series = df_time_series.sort_values('t').reset_index(drop=True)

# 2. Merge con griglia 5min per visualizzazione
display_index = pd.DataFrame({
    't': pd.date_range(start=t_start, end=t_end_display, freq='5min')
})
df_display = display_index.merge(df_time_series[['t', 'P']], on='t', how='left')

# 3. Mascherare punti futuri
df_display.loc[df_display['t'] > Now, 'P'] = None

# 4. Formattiamo timestamp per UI
df_display['t'] = pd.to_datetime(df_display['t']).dt.strftime('%H:%M')

# 5. Prepariamo valori per output (vuoto se NaN)
df_display['P'] = df_display['P'].where(df_display['P'].notna(), '')
```

### Calcoli Info Aggiuntive

```python
energy = float(today_energy_kwh) if today_energy_kwh is not None else None

# CO2 equivalente (Fattore emissione 0.457 kg/kWh)
co2_kg = energy * 0.457 if energy is not None else None

# Alberi equivalenti e case
tdelta = Now - datetime(Now.year, Now.month, Now.day, 0, 0, 0)
if energy is not None and tdelta.total_seconds() > 0:
    # Fattori empirici:
    # - 1000 kg CO2 ≈ 1 albero/anno
    # - 1 kWh ≈ 1 casa/9.5kWh
    alberi = int(co2_kg / (tdelta.total_seconds() / 3600) * 24 * 365 / 1000)
    case = int(energy / 9.5)
else:
    alberi = case = 0
```

### JSON Response

```json
{
  "time": ["00:00", "00:05", "00:10", ..., "23:55"],
  "pot": [null, 125.3, 234.5, ..., 0],
  "k_last": 287,
  "t_last": "23:50:15",
  "led": "led-green",
  "PLast": 234.5,
  "info": {
    "co2": 45.3,
    "case": 34,
    "alberi": 127,
    "energy": 321.8
  }
}
```

**Descrizione Campi**:
- `time`: Array timestamp formattati %H:%M
- `pot`: Array potenze in kW (null se nessun dato)
- `k_last`: Indice dell'ultimo punto valido nel grafico
- `t_last`: Timestamp dell'ultimo punto valido
- `led`: Stato device ("led-green" | "led-red" | "led-gray")
- `PLast`: Potenza dell'ultimo punto valido
- `info.co2`: Kg CO2 equivalente prodotti oggi
- `info.case`: Case equivalenti riscaldate
- `info.alberi`: Alberi equivalenti (assorbimento CO2/anno)
- `info.energy`: Energia prodotta oggi in kWh

---

## Problemi Noti e Criticità

### ❌ Problema 1: Non Tutti gli Impianti Espongono la Potenza Allo Stesso Modo

**Casistica**:
- **Col Roigo**: `totalPVPower` è attendibile
- **Zilio**: `totalPVPower = 0`, ma curve corrette nei campi `pv1power...pv16power`

**Impatto**: Impossibile usare una configurazione unica per tutti i plant SAJ

**Soluzione Attuale**: 
- Ogni impianto ha sua configurazione specifica in `PLANT_DEVICE_OVERRIDES`
- Campo potenza è parametrizzato in `power_field_name`

**Mitigazione Futura**:
- [ ] Discovery automatico del campo potenza corretto
- [ ] Heuristica basata su trendline coerenza

### ❌ Problema 2: Alcuni Impianti Non Espongono Dati Device-Level Corretti

**Casistica**: Zilio Group
- Somma singoli device C6: curve parziali/scorrette
- Somma canali PV (pv1...pv16): non replica dashboard
- Endpoint EMS con `parallMeterPower`: CORRETTO ✅

**Impatto**: Richiede endpoint diverso (EMS storico) per questi impianti

**Soluzione Attuale**:
- Query EMS storico per impianti EMS-based
- Fallback a device singoli per impianti non-EMS

### ❌ Problema 3: Limite 1h55min Endpoint EMS

**Dettaglio**: 
```
GET /open/api/device/emsHistoryData
```
Accetta massimo 1h55min per request (limite SAJ)

**Impatto**: Request giornaliera (24h) richiede chunking

**Soluzione Attuale**:
```python
# Dividi in finestre 1h55min
windows = []
cursor = start
max_span = timedelta(hours=1, minutes=55)
while cursor <= end:
    window_end = min(cursor + max_span, end)
    windows.append((cursor, window_end))
    cursor = window_end + timedelta(minutes=5)
```

**Mitigazione**: Merge risultati per timestamp

### ❌ Problema 4: Rate Limiting (429) su EMS Queries

**Dettaglio**: API SAJ ritorna 429 quando interrogate troppo frequentemente

**Soluzione Attuale**:
```python
if payload.get("code") == 429:
    time.sleep(0.6 * (attempt + 1))  # Backoff esponenziale
    continue
```
Max 4 retry per window

**Mitigazione Futura**:
- [ ] Caching layer (Redis) per dati storici
- [ ] Circuit breaker per API SAJ

### ⚠️ Problema 5: Configurazione Manuale e Fragile

**Dettaglio**: 
- Ogni impianto richiede entry manuale in `PLANT_DEVICE_OVERRIDES`
- String matching per nome impianto (soggetto a case/whitespace issues)
- Nessuna validazione configurazione a runtime

**Impatto**: Risk di configurationi errate

**Mitigazione**:
```python
def _normalize(value: str | None) -> str:
    """Normalizza per matching case-insensitive"""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())
```

---

## Testing e Debug

### Debug Logging

Ogni richiesta SAJ produce logging dettagliato:

```python
# API_SAJ.py:430
print(
    f"SAJ DEBUG {impianto.nickname} "
    f"power_source={config.get('power_source', 'devices')} "
    f"power_field={config.get('power_field_name')} "
    f"bucket_aggregation={config.get('bucket_aggregation', 'sum')} "
    f"selected_devices={len(selected_device_serials)} "
    f"power_series={len(device_dataframes)} "
    f"points={len(df_time_series)} "
    f"today_energy_kwh={today_energy_kwh} "
    f"energy_source={config.get('energy_source', 'devices')} "
    f"energy_field={config.get('energy_field_name')}"
)
```

**Output Tipico**:
```
SAJ DEBUG acquanova290 power_source=devices power_field=totalGridPowerWatt 
bucket_aggregation=nearest_grid selected_devices=1 power_series=1 points=287 
today_energy_kwh=125.3 energy_source=devices energy_field=todayPvEnergy
```

### APIViews Debug Logging

```python
# APIViews.py:385
print(f"SAJ DEBUG {nickname} chart_points={len(df_display)} "
      f"chart_non_empty={len(valid_points)} k_last={k_last} p_last={p_last}")
```

### Test Script

**Location**: [PortaleZilioService/API_inverter/test_saj_plant_statistics.py](PortaleZilioService/API_inverter/test_saj_plant_statistics.py)

**Usage**:
```powershell
python .\.venv\Scripts\python.exe `
  PortaleZilioService\tests_api\saj\probe_rctbramante.py `
  --date 2026-05-25
```

**Cosa fa**:
- Testa integrazione SAJ per un impianto
- Verifica token, plant discovery, device query
- Recupera dati storici
- Valida aggregazione

---

## Diagramma Sequenza

```
┌──────────┐         ┌────────────────┐      ┌──────────────┐      ┌─────────────┐
│ Frontend │         │ APIViews (View)│      │ API_SAJ.py   │      │ SAJ API     │
└────┬─────┘         └────────┬───────┘      └──────┬───────┘      └──────┬──────┘
     │                        │                     │                      │
     │ GET /get-chart-...     │                     │                      │
     │ ?nickname=acquanova290 │                     │                      │
     ├───────────────────────>│                     │                      │
     │                        │ get_saj_day_data()  │                      │
     │                        ├────────────────────>│                      │
     │                        │                     │ get_token()          │
     │                        │                     ├─────────────────────>│
     │                        │                     │<─ token ────────────┤
     │                        │                     │                      │
     │                        │                     │ get_plants()         │
     │                        │                     ├─────────────────────>│
     │                        │                     │<─ [plant1, ...]─────┤
     │                        │                     │                      │
     │                        │                     │ _find_matching_plant │
     │                        │                     │ (name normalization) │
     │                        │                     │                      │
     │                        │                     │ get_devices()        │
     │                        │                     ├─────────────────────>│
     │                        │                     │<─ [device1, ...]────┤
     │                        │                     │                      │
     │                        │                     │ Per device_sn:       │
     │                        │                     │ _get_history_records │
     │                        │                     ├─────────────────────>│
     │                        │                     │<─ records ──────────┤
     │                        │                     │                      │
     │                        │ (aggregation,       │                      │
     │                        │  interpolation)     │                      │
     │                        │                     │                      │
     │                        │<──── return ────────┤                      │
     │                        │ (df, led, energy)   │                      │
     │                        │                      │                      │
     │                        │ (format, calc info)  │                      │
     │ Response JSON          │                      │                      │
     │<───────────────────────┤                      │                      │
     │                        │                      │                      │
```

---

## File Rilevanti

| File | Descrizione |
|------|------------|
| [MonitoraggioImpianti/APIViews.py](MonitoraggioImpianti/APIViews.py) | View principale, handler SAJ @ line 340-405 |
| [MonitoraggioImpianti/API_SAJ.py](MonitoraggioImpianti/API_SAJ.py) | Logica core SAJ, `get_saj_day_data()`, configurazioni |
| [PortaleZilioService/API_inverter/saj_client.py](PortaleZilioService/API_inverter/saj_client.py) | Client SAJ API, token e endpoint |
| [MonitoraggioImpianti/models.py](MonitoraggioImpianti/models.py) | Modello Impianto, choice `lettura_dati` |
| [MonitoraggioImpianti/README.md](MonitoraggioImpianti/README.md) | Documentazione integrazioni, problemi noti |

---

## Checklist per Troubleshooting

### ❓ "Grafico SAJ vuoto"

- [ ] Verifica `impianto.lettura_dati == 'API_SAJ'`
- [ ] Controlla logs debug SAJ nella console
- [ ] Verifica configurazione in `PLANT_DEVICE_OVERRIDES` per nome impianto
- [ ] Valida nome_impianto matching (case-insensitive)
- [ ] Controlla token SAJ valido (scade ogni 24h)
- [ ] Verifica device disponibili su plant SAJ

### ❓ "Curva SAJ non corretta"

- [ ] Controlla campo potenza (`power_field_name`) è giusto
- [ ] Se EMS-based: verifica `ems_sn` e `parallMeterPower`
- [ ] Se device-based: controlla somma device è corretta
- [ ] Valida timestamp alignment tra device

### ❓ "Energia giornaliera manca"

- [ ] Verifica `energy_field_name` configurato
- [ ] Controlla `energy_source` (device vs ems_history)
- [ ] Valida ultimo record ha valore energia non null

---

## Conclusione

Il flusso SAJ è **complesso ma robusto**, caratterizzato da:

✅ **Punti di forza**:
- Flessibilità per configurazioni eterogenee
- Support sia device-based che EMS-based
- Logging dettagliato per debug
- Error handling con retry

⚠️ **Aree di miglioramento**:
- Configurazione manuale fragile
- Limitazioni API SAJ (1h55min, rate limit)
- Nessun caching layer
- Accoppiamento stretto impianto ↔ configurazione

---

**Fine Documento**  
Generato: Maggio 2026
