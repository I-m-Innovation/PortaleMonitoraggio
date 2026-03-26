# MonitoraggioImpianti

## Aggiungere un impianto con API SAJ

Per aggiungere un nuovo impianto fotovoltaico che usa SAJ come sorgente dati, oggi servono due passaggi:

1. configurare l'impianto in Django admin
2. configurare il mapping SAJ nel codice

### 1. Configurazione impianto in admin

Creare o completare l'impianto in admin e verificare almeno questi campi:

- `nome_impianto`
- `nickname`
- `tipo = Fotovoltaico`
- `lettura_dati = API_SAJ`
- `potenza_installata`
- `lat`
- `lon`

Note:

- `lat` e `lon` servono per mostrare il meteo nella lista impianti.
- `nome_impianto` deve essere coerente con la configurazione SAJ usata nel codice.

### 2. Configurazione SAJ nel codice

La configurazione SAJ si trova in [API_SAJ.py](./API_SAJ.py), nella costante `PLANT_DEVICE_OVERRIDES`.

Struttura attuale:

```python
PLANT_DEVICE_OVERRIDES = {
    "colroigo50kwp": {
        "device_serial_numbers_to_query": [
            "CSV6503J2416E00004",
        ],
        "api_response_field_for_instantaneous_power_watts": "totalPVPower",
        "api_response_field_for_energy_produced_today_kwh": "todayPvEnergy",
    },
}
```

Per aggiungere un nuovo impianto, inserire una nuova voce con:

- chiave: nome impianto normalizzato
- `device_serial_numbers_to_query`: lista dei `deviceSn` SAJ da interrogare
- `api_response_field_for_instantaneous_power_watts`: campo SAJ usato per la potenza
- `api_response_field_for_energy_produced_today_kwh`: campo SAJ usato per l'energia prodotta oggi

Esempio:

```python
PLANT_DEVICE_OVERRIDES = {
    "colroigo50kwp": {
        "device_serial_numbers_to_query": [
            "CSV6503J2416E00004",
        ],
        "api_response_field_for_instantaneous_power_watts": "totalPVPower",
        "api_response_field_for_energy_produced_today_kwh": "todayPvEnergy",
    },
    "nuovoimpianto100kwp": {
        "device_serial_numbers_to_query": [
            "SERIALE_DEVICE_1",
            "SERIALE_DEVICE_2",
        ],
        "api_response_field_for_instantaneous_power_watts": "totalPVPower",
        "api_response_field_for_energy_produced_today_kwh": "todayPvEnergy",
    },
}
```

### Come viene ricavata la chiave dell'impianto

La chiave del dizionario non e' il nome visualizzato, ma il nome normalizzato.

Esempio:

- `Col Roigo 50 kWp` -> `colroigo50kwp`
- `Nuovo Impianto 100 kWp` -> `nuovoimpianto100kwp`

La normalizzazione attuale:

- converte in minuscolo
- rimuove spazi
- rimuove caratteri non alfanumerici

### Caso con un solo inverter

Se l'impianto ha un solo inverter SAJ, inserire un solo seriale nella lista:

```python
"device_serial_numbers_to_query": [
    "CSV6503J2416E00004",
]
```

### Caso con piu' inverter

Se l'impianto ha piu' inverter SAJ, inserire tutti i `deviceSn` nella lista:

```python
"device_serial_numbers_to_query": [
    "INV_AAAAA",
    "INV_BBBBB",
    "INV_CCCCC",
]
```

La logica attuale:

- fa una chiamata `historyDataCommon` per ogni device configurato
- costruisce la serie temporale di potenza per ogni device
- somma i valori di potenza che hanno lo stesso timestamp
- somma i valori giornalieri di energia estratti dall'ultimo record valido di ciascun device

### Endpoint usato

L'integrazione SAJ usa l'endpoint:

- `/open/api/device/historyDataCommon`

Campi usati attualmente:

- `totalPVPower` per la potenza istantanea
- `todayPvEnergy` per l'energia giornaliera

### Verifica prima di usare un nuovo impianto

Prima di considerare conclusa la configurazione, conviene verificare:

1. che il plant SAJ corretto venga trovato
2. che i `deviceSn` configurati siano quelli giusti
3. che la potenza mostrata nel portale coincida con la dashboard SAJ
4. che l'energia giornaliera sia coerente con SAJ

Per fare queste verifiche si puo' usare lo script:

[test_saj_plant_statistics.py](./test_saj_plant_statistics.py)

Lo script serve per:

- testare `getPlantStatisticsData`
- testare `historyDataCommon`
- confrontare i device di un plant SAJ e identificare quello corretto

### Checklist finale

Prima di chiudere l'attivazione di un nuovo impianto SAJ, verificare:

1. impianto presente in admin
2. `lettura_dati = API_SAJ`
3. `lat` e `lon` valorizzati
4. voce aggiunta in `PLANT_DEVICE_OVERRIDES`
5. `deviceSn` verificati con lo script di test
6. potenza corretta nella pagina dettaglio
7. energia corretta nella pagina dettaglio
8. card corretta nella lista impianti
