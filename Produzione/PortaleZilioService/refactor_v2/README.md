# PortaleZilioService Refactor V2

Questa directory contiene una proposta di rifattorizzazione parallela al codice attuale.

Obiettivi:
- separare provider esterni, calcoli metriche e persistenza;
- introdurre una strategia per provider (`API_ISC`, `API_HIGECO`, `API_LEO`, ...);
- normalizzare l'output in DTO comuni;
- permettere finestre temporali esplicite, come "ultimi 12 mesi fino a ieri".

Stato:
- non sostituisce il flusso esistente;
- non e` ancora collegata alle view correnti;
- include gia` il provider iSolarCloud.

Flusso previsto:
1. `ProviderRegistry` risolve il provider in base a `impianto.lettura_dati`
2. il provider restituisce `ProviderPlantSnapshot`
3. `MetricsCalculator` calcola `ComputedPlantMetrics`
4. `MetricsSyncService` salva i dati su `Impianto`
