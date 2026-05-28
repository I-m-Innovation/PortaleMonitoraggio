# MonitoraggioImpianti

## Integrazione SAJ

Questo modulo contiene la logica di monitoraggio per gli impianti che leggono dati da SAJ.

Il punto di ingresso lato backend e':

- [API_SAJ.py](./API_SAJ.py)

La view che lo usa per costruire il grafico giornaliero e':

- [APIViews.py](./APIViews.py)

Lo script di test/debug usato durante l'analisi e':

- [test_saj_plant_statistics.py](../PortaleZilioService/API_inverter/test_saj_plant_statistics.py)

## Come funziona SAJ nel portale

La logica SAJ oggi non e' unica per tutti gli impianti. Dipende da come il dato corretto e' esposto dall'API SAJ per quello specifico plant.

Il flusso comune e':

1. il portale trova l'impianto in admin e verifica che `lettura_dati = API_SAJ`
2. in [API_SAJ.py](./API_SAJ.py), tramite `PLANT_DEVICE_OVERRIDES`, viene caricata la configurazione specifica dell'impianto
3. il backend chiede a SAJ:
   - la lista plant
   - il plant corretto
   - i device del plant
4. in base alla configurazione dell'impianto viene scelta la sorgente dati corretta per:
   - potenza del grafico
   - energia prodotta del giorno
5. il risultato viene riportato nella griglia temporale usata dal frontend

## Configurazione attuale

La configurazione degli impianti SAJ si trova in `PLANT_DEVICE_OVERRIDES` dentro [API_SAJ.py](./API_SAJ.py).

### Col Roigo

`Col Roigo 50 kWp` oggi usa una logica device-based:

- sorgente potenza: `/open/api/device/historyDataCommon`
- device usato: `CSV6503J2416E00004`
- campo potenza: `totalPVPower`
- campo energia: `todayPvEnergy`
- strategia grafico: campionamento del valore reale piu' vicino su una griglia a 5 minuti

Questa scelta e' stata fatta perche' l'endpoint EMS, con gli identificativi oggi noti di Col Roigo, rispondeva `200` ma senza record.

### Zilio Group

`Zilio Group 490kW` oggi usa una logica EMS-based:

- sorgente potenza: `/open/api/device/emsHistoryData`
- `emsSn`: `M5530J2428000038`
- campo potenza: `parallMeterPower`
- campo energia: `parallTodayPVEnergy`

Per Zilio la potenza non viene piu' ricostruita dalla somma dei singoli inverter. Il dato corretto della dashboard SAJ e' risultato essere il valore EMS `parallMeterPower`.

### Acquanova

Per `Acquanova 1 - 150`, l'energia prodotta giornaliera letta da `historyDataCommon`
tramite `todayPvEnergy` e' coerente con la supervisione SAJ, ma i campi
device-level `todaySellEnergy` e `todayFeedInEnergy` non sono affidabili per
ricostruire l'autoconsumo: nel test del `2026-05-27` tornavano a `0`.

Per ricostruire i valori della card energia della supervisione SAJ bisogna
usare l'endpoint EMS:

```text
GET /open/api/device/emsHistoryData
```

con:

```text
plantId = 26049021801
emsSn = M5530J2541000285
```

L'endpoint EMS va interrogato a finestre inferiori a 2 ore, ad esempio chunk da
`1h55`, per evitare risposte vuote o rate limit.

Campi verificati su `Acquanova 1 - 150` per il giorno `2026-05-27`:

| Campo SAJ | Valore |
| --- | ---: |
| `parallTodayPVEnergy` | `281.930 kWh` |
| `parallTodaySellEnergy` | `1.780 kWh` |
| `parallTodayFeedInEnergy` | `1295.420 kWh` |
| `parallTodayTotalLoadEnergy` | `1575.570 kWh` |
| `parallTodayBatChgEnergy` | `0.000 kWh` |
| `parallTodayBatDisEnergy` | `0.000 kWh` |

La supervisione SAJ mostrava:

| Voce supervisione | Valore |
| --- | ---: |
| Electric energy production | `281.93 kWh` |
| Self-Consumption | `280.15 kWh` |
| Export | `1.78 kWh` |

La formula coerente con la supervisione e':

```text
Self-Consumption = parallTodayPVEnergy - parallTodaySellEnergy
```

Esempio verificato:

```text
281.930 - 1.780 = 280.150 kWh
```

Quindi, per Acquanova EMS:

- energia prodotta: `parallTodayPVEnergy`
- energia immessa/esportata: `parallTodaySellEnergy`
- energia autoconsumata: `parallTodayPVEnergy - parallTodaySellEnergy`
- non usare `parallTodayFeedInEnergy` per questa card: nel test non coincide
  con il valore `Export` della supervisione

## Problemi incontrati

Durante l'integrazione SAJ sono emerse alcune criticita' importanti.

### 1. Non tutti gli impianti espongono la potenza nello stesso modo

Caso reale:

- per `Col Roigo` il campo `totalPVPower` del device e' risultato plausibile
- per `Zilio` i device `C6` avevano `totalPVPower = 0`, mentre la produzione reale era nei campi `pv1power ... pv16power`

Conclusione:

- non bisogna assumere che `totalPVPower` sia sempre il campo giusto

### 2. La dashboard SAJ non sempre usa un dato device-level

Per `Zilio` la dashboard SAJ mostrava un valore corretto di `photovoltaic power`, ma:

- la somma dei `C6`
- la somma dei `C6 - S12`
- la somma dei campi `pv1 ... pv16`

non replicavano perfettamente la curva della dashboard.

Il dato corretto e' stato trovato solo interrogando l'endpoint EMS storico e usando:

- `parallMeterPower`

Conclusione:

- alcuni impianti vanno letti a livello EMS/plant, non a livello singolo device

### 3. L'endpoint EMS ha un limite massimo di 2 ore

L'endpoint:

- `/open/api/device/emsHistoryData`

non accetta richieste su tutta la giornata in un solo colpo.

Vincolo osservato:

- intervallo massimo inferiore a 2 ore

Per questo in [API_SAJ.py](./API_SAJ.py) la lettura EMS e':

- spezzata in chunk
- unita a posteriori
- deduplicata per `dataTime`

### 4. L'endpoint EMS puo' andare in rate limit

SAJ puo' rispondere:

- `code: 429`
- `msg: exceed the interface max request times per second!`

Per questo nel codice principale e nello script di test e' stato aggiunto:

- retry con backoff progressivo

### 5. Un EMS puo' esistere ma non restituire serie storica utile

Per `Col Roigo` e' stato provato:

- `plantId = 24110165619`
- `emsSn = M5380J2415071297`

L'endpoint EMS rispondeva:

- `code: 200`
- `msg: request success`

ma senza `data`.

Conclusione:

- non basta conoscere un communication module
- bisogna verificare davvero che l'endpoint storico EMS restituisca record

### 6. La bucketizzazione puo' falsare il valore del grafico

La dashboard SAJ puo' mostrare punti ad alta frequenza, ad esempio ogni 30 secondi.

Se il portale:

- arrotonda tutto a 5 minuti
- e poi somma i valori del bucket

si rischia di gonfiare il valore del grafico.

Per questo `Col Roigo` oggi non usa la somma del bucket. Usa invece:

- griglia a 5 minuti
- valore reale piu' vicino a ciascun timestamp

## Cosa considerare quando si aggiunge un nuovo impianto SAJ

Quando si aggiunge un nuovo impianto SAJ, non bisogna limitarsi a inserire i `deviceSn`.

Serve decidere prima:

- qual e' la sorgente corretta della potenza
- qual e' la sorgente corretta dell'energia
- se il plant va letto a livello device o a livello EMS

## Procedura consigliata per un nuovo impianto

### 1. Configurazione in admin

Verificare almeno:

- `nome_impianto`
- `nickname`
- `tipo = Fotovoltaico`
- `lettura_dati = API_SAJ`
- `potenza_installata`
- `lat`
- `lon`

### 2. Configurazione in `PLANT_DEVICE_OVERRIDES`

Aggiungere una nuova voce con chiave normalizzata del nome impianto.

Esempio:

```python
"nuovoimpianto100kwp": {
    "device_serial_numbers_to_query": [
        "SERIALE_1",
        "SERIALE_2",
    ],
    "power_extraction_mode": "field",
    "power_field_name": "totalPVPower",
    "energy_field_name": "todayPvEnergy",
}
```

La chiave e' il nome normalizzato:

- minuscolo
- senza spazi
- senza caratteri non alfanumerici

Esempio:

- `Nuovo Impianto 100 kWp` -> `nuovoimpianto100kwp`

### 3. Verifica dei dati reali

Prima di confermare la configurazione bisogna testare con lo script:

- [test_saj_plant_statistics.py](../PortaleZilioService/API_inverter/test_saj_plant_statistics.py)

Obiettivi del test:

- verificare quale `plantId` SAJ viene realmente usato
- verificare i `deviceSn`
- verificare se esiste un `emsSn` utile
- capire quale campo della potenza coincide con la dashboard
- capire quale campo dell'energia coincide con la dashboard

### 4. Decidere la sorgente corretta

Per un nuovo impianto bisogna capire quale di queste strade usare.

#### Caso A: device-level semplice

Usare `historyDataCommon` se:

- l'impianto ha uno o pochi device
- `totalPVPower` o altro campo device-level coincide con la dashboard
- `todayPvEnergy` coincide con il totale giornaliero SAJ

#### Caso B: EMS-level

Usare `emsHistoryData` se:

- i campi dei singoli inverter non replicano correttamente la dashboard
- la dashboard sembra mostrare un dato plant-level
- l'endpoint EMS restituisce una serie storica reale

In questo caso bisogna definire:

- `power_source = "ems_history"`
- `ems_sn = "..."`
- `power_field_name`
- `energy_source = "ems_history"`
- `energy_field_name`

### 5. Controllare la frequenza temporale reale

Bisogna sempre chiedersi:

- SAJ restituisce punti ogni 30 secondi?
- ogni 5 minuti?
- con timestamp irregolari?

Da questa risposta dipende come costruire il grafico:

- somma nel bucket
- ultimo valore del bucket
- punto reale piu' vicino sulla griglia

Per impianti con un solo device, di solito:

- sommare i punti del bucket e' la scelta meno affidabile

### 6. Controllare i limiti dell'endpoint

Per gli endpoint EMS considerare sempre:

- finestre massime < 2 ore
- possibile rate limit `429`

Quindi:

- se si usa EMS nel codice di produzione, servono chunk e retry

## Checklist per un nuovo impianto SAJ

Prima di chiudere l'attivazione:

1. impianto configurato in admin
2. `lettura_dati = API_SAJ`
3. `nome_impianto` coerente con la chiave normalizzata
4. `deviceSn` verificati
5. eventuale `emsSn` verificato
6. `plantId` corretto verificato con script
7. potenza grafico coerente con dashboard SAJ
8. energia giornaliera coerente con dashboard SAJ
9. comportamento stabile fino all'ultimo timestamp disponibile
10. nessun buco o troncamento dovuto a rate limit o finestra EMS

## Nota pratica importante

Con SAJ non conviene generalizzare troppo presto.

La lezione emersa da `Zilio` e `Col Roigo` e':

- due impianti SAJ diversi possono richiedere due logiche diverse

Quindi, quando si aggiunge un nuovo impianto:

- prima si misura come risponde davvero l'API
- poi si decide la strategia corretta
- solo dopo si consolida la configurazione in `PLANT_DEVICE_OVERRIDES`
