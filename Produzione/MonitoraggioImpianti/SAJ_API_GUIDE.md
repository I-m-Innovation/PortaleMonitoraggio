# Integrazione API SAJ

Questo documento descrive l'integrazione SAJ attualmente usata dal monitoraggio
fotovoltaico e raccoglie le indicazioni utili per realizzare un servizio
separato di acquisizione dati.

## Componenti attuali

| File | Responsabilita |
| --- | --- |
| `MonitoraggioImpianti/API_SAJ.py` | Configurazione impianti, download storico, trasformazione serie, energia e LED. |
| `PortaleZilioService/API_inverter/saj_client.py` | Autenticazione SAJ, header comuni, elenco plant e device. |
| `MonitoraggioImpianti/APIViews.py` | Endpoint Django per i grafici; instrada gli impianti con `lettura_dati = API_SAJ`. |
| `templates/MonitoraggioImpianti/partials/pv_table.html` | Mini grafici e LED in homepage, incluso retry LED SAJ. |
| `PortaleZilioService/API_inverter/test_saj_plant_statistics.py` | Probe manuali e report HTML/CSV di confronto potenze. |
| `PortaleZilioService/tests_api/saj/probe_rctbramante.py` | Probe specifico EMS/device per RCT-Bramante. |

Le credenziali API non devono essere replicate in un nuovo progetto o in
documentazione. Devono essere trasferite da codice a variabili d'ambiente o a
un secret manager.

## Endpoint SAJ utilizzati

Base URL corrente:

```text
https://developer.saj-electric.com/prod-api
```

| Scopo | Metodo e percorso | Parametri principali |
| --- | --- | --- |
| Token | `GET /open/api/access_token` | `appId`, `appSecret` |
| Elenco plant | `GET /open/api/developer/plant/page` | `appId`, `pageSize`, `pageNum` |
| Elenco device di un plant | `GET /open/api/developer/device/page` | `appId`, `plantId`, `pageSize`, `pageNum` |
| Storico singolo device | `GET /open/api/device/historyDataCommon` | `deviceSn`, `startTime`, `endTime`, `fields` |
| Storico EMS | `GET /open/api/device/emsHistoryData` | `plantId`, `emsSn`, `startTime`, `endTime` |

Le richieste successive al token inviano gli header:

```text
accessToken: <token>
clientSecret: <secret>
content-language: en_US
```

Nel client applicativo il token e' memorizzato in cache in-process per 30
minuti con lock. Questo evita autenticazioni contemporanee quando la homepage
richiede i dati di piu impianti SAJ nello stesso momento.

## Impianti SAJ monitorati

L'impianto deve essere presente nel database `Impianto` con
`tipo = Fotovoltaico` e `lettura_dati = API_SAJ`. La configurazione tecnica
SAJ si trova in `PLANT_DEVICE_OVERRIDES` ed e' individuata normalizzando il
campo `nome_impianto` del database.

| Nome impianto DB | Nickname DB | Plant ID | Device interrogati | Sorgente potenza | Campo potenza |
| --- | --- | --- | --- | --- | --- |
| `Col Roigo 50 kWp` | `Col Roigo` | risolto per nome | `CSV6503J2416E00004` | device history | `totalPVPower` |
| `Zilio Group 490kW` | `Zilio Group` | risolto per nome | `C6T9104J2314E00560`, `C6T9104J2315E00670`, `C6V9104G2424E00228`, `C6V9104J2421E01334` | EMS history | `parallMeterPower` |
| `RCT-Bramante` | `rctbramante` | risolto per nome | `C6VC125J2430E03394`, `CSV6503J2506E00137`, `CSV6503J2506E00141` | EMS history | `parallMeterPower` |
| `Acquanova 1 - 150` | `acquanova_1` | `26049021801` | `C6V9104J2421E01334` | device history | `totalGridPowerWatt` |
| `Acquanova 2 - 90` | `acquanova_2` | `26051023789` | `C6T9104J2314E00560` | device history | `totalGridPowerWatt` |

### Energia giornaliera

| Impianti | Sorgente energia | Campo |
| --- | --- | --- |
| Col Roigo e Acquanova | storico device | `todayPvEnergy` |
| Zilio Group e RCT-Bramante | storico EMS | `parallTodayPVEnergy` |

## Flusso di recupero dati del grafico

Il browser chiama l'endpoint applicativo:

```text
/api/monitoraggio/<nickname>/
```

Per un record con `lettura_dati = API_SAJ`, il flusso e':

1. `APIViews.DayChartData` imposta la finestra dalla mezzanotte all'istante
   corrente.
2. `API_SAJ.get_saj_day_data()` carica la configurazione normalizzata
   dell'impianto.
3. `saj_client.get_token()` restituisce un token nuovo oppure quello in cache.
4. Il plant viene identificato tramite `plant_id` esplicito, se configurato;
   altrimenti tramite ricerca per nome/nickname/tag nell'elenco plant SAJ.
5. Viene richiesto l'elenco device del plant e vengono selezionati solo i
   serial number configurati.
6. Per una sorgente `device history`, ogni device viene interrogato tramite
   `historyDataCommon`.
7. Per una sorgente `EMS history`, viene interrogato `emsHistoryData`; nel
   ciclo attuale viene letto anche lo storico dei device configurati, mentre
   potenza ed energia esposte per questi impianti provengono dall'EMS.
8. Il valore di potenza espresso da SAJ in Watt viene trasformato in kW.
9. La serie viene aggregata o campionata su griglia a 5 minuti secondo la
   configurazione dell'impianto.
10. L'energia giornaliera e il LED vengono calcolati e restituiti alla view.
11. La view completa la serie fino alle `23:55`, usando valori vuoti nel futuro,
    e restituisce al frontend `time`, `pot`, `led`, `PLast` e `info.energy`.

## Strategie di potenza

### Storico device

La richiesta `historyDataCommon` recupera attualmente:

```text
deviceSn,dataTime,totalGridPowerWatt,totalPVPower,todayPvEnergy,totalPvEnergy,
pv1power,...,pv16power
```

Per Acquanova il campo da usare per confrontare il grafico applicativo con il
grafico del provider e':

```text
totalGridPowerWatt
```

Si tratta della potenza AC. La somma dei campi `pv1power` ... `pv16power`
rappresenta invece una misura DC e ha prodotto valori maggiori di quelli
visualizzati dal provider.

Col Roigo utilizza al momento `totalPVPower`; prima di riusare la stessa scelta
per nuovi impianti e' necessario confrontarla con il grafico ufficiale SAJ.

### Storico EMS

Zilio Group e RCT-Bramante utilizzano `emsHistoryData`, con:

```text
power_field_name = parallMeterPower
energy_field_name = parallTodayPVEnergy
```

L'endpoint EMS viene interrogato in finestre di massimo 1 ora e 55 minuti. In
presenza del codice risposta SAJ `429`, il codice riprova fino a quattro volte
con attesa crescente. I punti duplicati vengono eliminati usando `dataTime`.

## Campionamento e valori mostrati

- I dati di potenza SAJ sono convertiti da W a kW prima di essere inviati alla
  UI.
- Gli impianti configurati con `bucket_aggregation = nearest_grid` vengono
  campionati sulla griglia di 5 minuti, scegliendo il punto piu vicino entro
  `2min30s`.
- Gli impianti EMS aggregano le serie per timestamp; piccoli vuoti interni
  possono essere interpolati fino a due punti consecutivi.
- Un picco nel grafico dell'applicazione puo essere leggermente inferiore al
  massimo grezzo del provider quando il massimo cade fuori dalla griglia di
  campionamento a 5 minuti.

## Stato e LED

Il LED utilizza i dati dell'elenco device SAJ selezionati:

| Condizione | Classe CSS |
| --- | --- |
| Almeno un device con `isAlarm = 1` | `led-red` |
| Nessun allarme e almeno un device con `isOnline = 1` | `led-green` |
| Nessun device, device offline o errore di recupero | `led-gray` |

Non esiste attualmente uno stato giallo per SAJ.

La homepage interroga piu impianti in parallelo. Sono presenti due protezioni:

- token SAJ condiviso in cache per evitare errori dovuti a login simultanei;
- retry frontend solo sulle card SAJ che ricevono `led-gray`: tre tentativi,
  distanziati di 15 secondi.

Limite noto: `led-gray` non distingue un device realmente offline da un errore
temporaneo di comunicazione. Per un nuovo progetto e' preferibile modellare
separatamente `offline`, `api_error`, `not_configured` e `unknown`, eseguendo
il retry solo sui problemi transitori.

## Casi particolari e rischi noti

### Identificazione del plant

Acquanova usa un `plant_id` esplicito perche la ricerca nella lista plant puo
non trovare l'impianto, ad esempio in caso di paginazione o elenco variabile.
Il client attuale scarica soltanto la prima pagina da 100 plant. Per un servizio
dedicato e' opportuno memorizzare sempre il `plant_id` e implementare la
paginazione completa per la discovery.

### Associazioni device da verificare

I serial number configurati per Acquanova compaiono anche nella configurazione
storica di `Zilio Group`. Se il provider ha spostato i device tra plant, la
configurazione di Zilio Group va rivalidata tramite discovery e confronto dei
dati prima di essere modificata.

### Error handling

Nella view corrente una qualsiasi eccezione SAJ produce grafico vuoto e LED
grigio. Un retriever dedicato dovrebbe conservare:

- codice e testo dell'errore API;
- plant/device interessati;
- istante dell'ultima lettura riuscita;
- numero di tentativi e stato del retry;
- payload grezzo, o una copia redatta, per debug.

### Segreti

Il client corrente contiene credenziali direttamente nel sorgente. Un nuovo
servizio non deve ereditare questa scelta: usare almeno variabili d'ambiente
come `SAJ_APP_ID` e `SAJ_APP_SECRET`, evitando di scrivere token e secret nei
log.

## Probe disponibili

Per confrontare potenza AC, somma canali DC e campo `totalPVPower`, dalla
directory `Produzione`:

```powershell
.\.venv\Scripts\python.exe PortaleZilioService\API_inverter\test_saj_plant_statistics.py `
  --endpoint device-power-compare `
  --plant-id 26049021801 `
  --plant-name "Acquanova 1 - 150" `
  --device-sn C6V9104J2421E01334 `
  --date 2026-05-25
```

```powershell
.\.venv\Scripts\python.exe PortaleZilioService\API_inverter\test_saj_plant_statistics.py `
  --endpoint device-power-compare `
  --plant-id 26051023789 `
  --plant-name "Acquanova 2 - 90" `
  --device-sn C6T9104J2314E00560 `
  --date 2026-05-25
```

Il probe genera CSV e grafico HTML nella directory predefinita:

```text
temporary/saj_reports
```

Per RCT-Bramante e' inoltre disponibile:

```powershell
.\.venv\Scripts\python.exe PortaleZilioService\tests_api\saj\probe_rctbramante.py `
  --date 2026-05-25
```

## Indicazioni per un mini progetto di retrieving

Una prima versione separata dovrebbe contenere:

1. Configurazione esplicita per plant: `plant_id`, device serial, eventuale
   `ems_sn`, campo potenza, campo energia e tipo sorgente.
2. Client HTTP unico con secret esterni al repository, token cache, timeout,
   retry con backoff e gestione dei rate limit.
3. Discovery command per elencare plant e device e verificare periodicamente
   che i serial configurati appartengano ancora al plant atteso.
4. Collector per `historyDataCommon` e collector per `emsHistoryData`, senza
   mescolare logica HTTP e trasformazione dei dati.
5. Normalizzazione in un formato comune, ad esempio:

   ```text
   timestamp, plant_id, device_sn, power_ac_kw, energy_today_kwh, online, alarm, source
   ```

6. Persistenza dei dati grezzi o normalizzati per poter ricostruire grafici e
   diagnosticare differenze con il provider.
7. Job schedulato e idempotente, capace di riprendere dall'ultimo timestamp
   salvato senza duplicare punti.
8. Test con risposte API registrate per validare parsing, conversioni W/kW,
   rate limit, device offline e cambi di associazione plant/device.

Prima di integrare un nuovo impianto, occorre verificare con un probe quale
campo corrisponda alla misura mostrata nel portale SAJ: la scelta non e'
necessariamente identica per device history ed EMS history.
