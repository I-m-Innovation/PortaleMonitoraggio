# PortaleZilioService API Tests

Questa cartella contiene test e script di controllo dedicati alle API esterne usate da `PortaleZilioService`.

Struttura corrente:

- `isolarcloud/`: controlli per il provider iSolarCloud
- `saj/`: controlli per il provider SAJ
- `myleonardo/`: controlli per il provider MyLeonardo

Obiettivi principali:

- verificare autenticazione e disponibilita' endpoint
- validare la forma dei payload restituiti
- controllare coerenza minima dei dati usati dal portale
- facilitare debug e regressioni quando cambia un provider

Nota:

- questi file sono iniziali e pensati come base di lavoro
- i test live potranno richiedere credenziali e dati ambiente
