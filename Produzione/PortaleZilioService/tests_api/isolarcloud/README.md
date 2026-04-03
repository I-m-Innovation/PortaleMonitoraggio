# iSolarCloud API Probes

Questa cartella contiene script manuali per interrogare gli endpoint iSolarCloud e vedere direttamente i payload restituiti.

Script correnti:

- `probe_auth.py`: verifica login e token
- `probe_plants.py`: stampa la lista impianti disponibile
- `probe_devices.py`: stampa i device per tutti i plant o per un plant filtrato
- `probe_irradiation.py`: calcola l'irraggiamento degli ultimi 12 mesi per un plant
- `probe_irradiation_all_plants.py`: calcola l'irraggiamento degli ultimi 12 mesi per tutti i plant
- `probe_expected_energy_all_plants.py`: calcola l'energia attesa degli ultimi 12 mesi per tutti i plant
- `probe_missed_energy_all_plants.py`: calcola la mancata produzione degli ultimi 12 mesi per tutti i plant
- `probe_energy_window.py`: calcola energia, ore equivalenti, irraggiamento e PR sulla finestra rolling 12 mesi

Note:

- gli script riusano il codice reale già presente in `API_iSolarCloud.py`
- `probe_devices.py`, `probe_irradiation.py` e `probe_energy_window.py` accettano opzionalmente un plant name o `ps_id`
- non sono test automatici, ma strumenti di debug/ispezione
