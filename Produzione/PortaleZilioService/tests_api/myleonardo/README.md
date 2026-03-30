# MyLeonardo API Probes

Questa cartella contiene script manuali per interrogare gli endpoint MyLeonardo gia' presenti nel progetto.

Script correnti:

- `probe_auth.py`: verifica login e token
- `probe_advanced_data.py`: interroga l'endpoint `external/advanced/...` e stampa first/last row
- `probe_fields.py`: elenca i campi disponibili e un valore esempio per ciascuno

Nota importante:

- nel codice attuale non emerge una vera lista impianti MyLeonardo come per SAJ o iSolarCloud
- i probe sono quindi basati sull'endpoint reale oggi usato in [API_MyLeo.py](c:/Users/Luca%20Parise/Desktop/sorgenti/PortaleImpianti/Produzione/MonitoraggioImpianti/API_MyLeo.py)
