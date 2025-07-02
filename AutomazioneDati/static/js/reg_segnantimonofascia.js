// Funzione per validare il formato data/ora
function validateDateTimeFormat(dateTimeString) {
    // Regex per il formato gg/mm/aaaa hh:mm
    const regexCompleto = /^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})$/;
    // Regex per il formato gg/mm/aaaa (senza orario)
    const regexSoloData = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
    
    const matchCompleto = dateTimeString.match(regexCompleto);
    const matchSoloData = dateTimeString.match(regexSoloData);
    
    // Se è una data completa con orario
    if (matchCompleto) {
        const day = parseInt(matchCompleto[1], 10);
        const month = parseInt(matchCompleto[2], 10);
        const year = parseInt(matchCompleto[3], 10);
        const hour = parseInt(matchCompleto[4], 10);
        const minute = parseInt(matchCompleto[5], 10);
        
        // Verifica che i valori siano validi
        if (month < 1 || month > 12) return false;
        if (day < 1 || day > 31) return false;
        if (hour < 0 || hour > 23) return false;
        if (minute < 0 || minute > 59) return false;
        
        // Verifica giorni per mese (semplificata)
        const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        if (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)) {
            daysInMonth[1] = 29; // Anno bisestile
        }
        
        if (day > daysInMonth[month - 1]) return false;
        
        return true;
    }
    // Se è solo data senza orario
    else if (matchSoloData) {
        const day = parseInt(matchSoloData[1], 10);
        const month = parseInt(matchSoloData[2], 10);
        const year = parseInt(matchSoloData[3], 10);
        
        // Verifica che i valori siano validi
        if (month < 1 || month > 12) return false;
        if (day < 1 || day > 31) return false;
        
        // Verifica giorni per mese (semplificata)
        const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        if (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)) {
            daysInMonth[1] = 29; // Anno bisestile
        }
        
        if (day > daysInMonth[month - 1]) return false;
        
        return true;
    }
    
    return false;
}

// Funzione per calcolare i totali di una riga per sistema monofasica
function calculateRowTotalsMonofasica(row) {
    if (!row) return;
    
    const kaifa180nCell = row.querySelector('[data-field="kaifa_180n"]');
    const totale180nCell = row.querySelector('[data-field="totale_180n"]');
    const kaifa280nCell = row.querySelector('[data-field="kaifa_280n"]');
    const totaleKaifa280nCell = row.querySelector('[data-field="totale_kaifa_280n"]');
    
    if (!kaifa180nCell || !totale180nCell || !kaifa280nCell || !totaleKaifa280nCell) {
        return;
    }
    
    // Recupera i valori delle celle editabili
    const kaifa180nValue = parseFloat(kaifa180nCell.textContent.trim().replace(',', '.')) || 0;
    const kaifa280nValue = parseFloat(kaifa280nCell.textContent.trim().replace(',', '.')) || 0;
    
    // Calcola i totali (per ora manteniamo una logica semplice)
    // In futuro potresti implementare calcoli più complessi basati sui valori precedenti
    if (kaifa180nValue > 0) {
        totale180nCell.textContent = kaifa180nValue.toString();
    }
    
    if (kaifa280nValue > 0) {
        totaleKaifa280nCell.textContent = kaifa280nValue.toString();
    }
    
    // Dopo aver aggiornato i totali, ricalcola i consumi per tutte le righe
    calculateAllConsumptions();
}

// Funzione per calcolare i consumi mensili per tutte le righe
function calculateAllConsumptions() {
    console.log('Calcolo consumi mensili per tutte le righe...');
    
    // Ottieni tutte le righe della tabella
    const allRows = document.querySelectorAll('#datimonofascia tbody tr');
    
    // Array per memorizzare i totali di ogni mese
    const totali180n = [];
    const totali280n = [];
    
    // Prima passa: raccogli tutti i totali
    allRows.forEach((row, index) => {
        const totale180nCell = row.querySelector('[data-field="totale_180n"]');
        const totale280nCell = row.querySelector('[data-field="totale_kaifa_280n"]');
        
        const totale180n = parseFloat(totale180nCell.textContent.trim().replace(',', '.')) || 0;
        const totale280n = parseFloat(totale280nCell.textContent.trim().replace(',', '.')) || 0;
        
        totali180n[index] = totale180n;
        totali280n[index] = totale280n;
    });
    
    // Seconda passa: calcola i consumi come differenza
    allRows.forEach((row, index) => {
        const consumo180nCell = row.querySelector('[data-field="consumo_180n"]');
        const consumo280nCell = row.querySelector('[data-field="consumo_280n"]');
        
        if (!consumo180nCell || !consumo280nCell) return;
        
        // Per calcolare il consumo del mese corrente:
        // consumo = totale_mese_successivo - totale_mese_corrente
        let consumo180n = 0;
        let consumo280n = 0;
        
        // Se non è l'ultima riga, calcola la differenza con il mese successivo
        if (index < allRows.length - 1) {
            const totaleCorrente180n = totali180n[index];
            const totaleSuccessivo180n = totali180n[index + 1];
            const totaleCorrente280n = totali280n[index];
            const totaleSuccessivo280n = totali280n[index + 1];
            
            // Calcola solo se entrambi i valori sono presenti e validi
            if (totaleCorrente180n > 0 && totaleSuccessivo180n > 0) {
                consumo180n = totaleSuccessivo180n - totaleCorrente180n;
            }
            
            if (totaleCorrente280n > 0 && totaleSuccessivo280n > 0) {
                consumo280n = totaleSuccessivo280n - totaleCorrente280n;
            }
        }
        
        // Aggiorna le celle dei consumi
        if (consumo180n > 0) {
            consumo180nCell.textContent = consumo180n.toFixed(2);
            consumo180nCell.style.backgroundColor = '#e8f5e8'; // Verde chiaro per indicare valore calcolato
        } else {
            consumo180nCell.textContent = '';
            consumo180nCell.style.backgroundColor = '';
        }
        
        if (consumo280n > 0) {
            consumo280nCell.textContent = consumo280n.toFixed(2);
            consumo280nCell.style.backgroundColor = '#e8f5e8'; // Verde chiaro per indicare valore calcolato
        } else {
            consumo280nCell.textContent = '';
            consumo280nCell.style.backgroundColor = '';
        }
    });
    
    console.log('Calcolo consumi completato');
}

// Funzione per validare che un valore sia numerico
function isValidNumber(value) {
    if (value === '') return true; // Campo vuoto è valido
    
    // Sostituisci virgola con punto per la validazione
    const normalizedValue = value.replace(',', '.');
    const num = parseFloat(normalizedValue);
    
    return !isNaN(num) && isFinite(num);
}

// Funzione per convertire da formato italiano a formato ISO
function convertToISODateTime(dateTimeString) {
    if (!dateTimeString || dateTimeString.trim() === '') {
        return null;
    }
    
    // Valida prima il formato
    if (!validateDateTimeFormat(dateTimeString)) {
        console.warn('Formato data/ora non valido:', dateTimeString);
        return null;
    }
    
    // Regex per il formato gg/mm/aaaa hh:mm
    const regexCompleto = /^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})$/;
    // Regex per il formato gg/mm/aaaa (senza orario)
    const regexSoloData = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
    
    const matchCompleto = dateTimeString.trim().match(regexCompleto);
    const matchSoloData = dateTimeString.trim().match(regexSoloData);
    
    if (matchCompleto) {
        const day = matchCompleto[1].padStart(2, '0');
        const month = matchCompleto[2].padStart(2, '0');
        const year = matchCompleto[3];
        const hour = matchCompleto[4].padStart(2, '0');
        const minute = matchCompleto[5];
        
        // Crea la stringa in formato ISO: YYYY-MM-DDTHH:MM:SS
        const isoDateTime = `${year}-${month}-${day}T${hour}:${minute}:00`;
        
        // Verifica che la data sia valida
        const date = new Date(isoDateTime);
        if (isNaN(date.getTime())) {
            console.warn('Data non valida generata:', isoDateTime);
            return null;
        }
        
        console.log(`Conversione: ${dateTimeString} -> ${isoDateTime}`);
        return isoDateTime;
    } else if (matchSoloData) {
        const day = matchSoloData[1].padStart(2, '0');
        const month = matchSoloData[2].padStart(2, '0');
        const year = matchSoloData[3];
        
        // Crea la stringa in formato ISO con orario 00:00
        const isoDateTime = `${year}-${month}-${day}T00:00:00`;
        
        // Verifica che la data sia valida
        const date = new Date(isoDateTime);
        if (isNaN(date.getTime())) {
            console.warn('Data non valida generata:', isoDateTime);
            return null;
        }
        
        console.log(`Conversione (con orario default): ${dateTimeString} -> ${isoDateTime}`);
        return isoDateTime;
    }
    
    console.warn('Match regex fallito per:', dateTimeString);
    return null;
}

// Funzione per ottenere il token CSRF (se non esiste già)
function getCSRFToken() {
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput) {
        return csrfInput.value;
    }
    
    // Prova a prenderlo dai cookie
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    
    console.warn('Token CSRF non trovato');
    return '';
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM caricato - Inizializzazione sistema monofasica');
    
    // Gestione del selettore anno
    const yearSelect = document.getElementById('year-select');
    if (yearSelect) {
        yearSelect.addEventListener('change', function() {
            const nuovoAnno = this.value;
            const contatore_id = document.getElementById('save-button-monofasica').getAttribute('data-contatore-id');
            console.log(`Anno cambiato a: ${nuovoAnno} per contatore ${contatore_id}`);
            
            // Aggiorna prima le colonne del mese con il nuovo anno
            aggiornaColonneMeseMonofasica(nuovoAnno);
            // Poi carica i dati per il nuovo anno
            caricaDatiPerAnnoMonofasica(contatore_id, nuovoAnno);
        });
    }
    
    // Gestione delle celle data/ora
    const dateCells = document.querySelectorAll('[data-field="data_ora_lettura"]');
    dateCells.forEach(cell => {
        // Evento quando l'utente finisce di modificare la cella
        cell.addEventListener('blur', function() {
            const value = this.textContent.trim();
            
            if (value === '') {
                this.classList.remove('date-error');
                return;
            }
            
            if (!validateDateTimeFormat(value)) {
                this.classList.add('date-error');
                alert('Formato data/ora non valido. Usa il formato: gg/mm/aaaa hh:mm oppure solo gg/mm/aaaa (verrà impostato 00:00 come orario)');
            } else {
                this.classList.remove('date-error');
            }
        });
        
        // Evento durante la digitazione
        cell.addEventListener('input', function() {
            this.classList.remove('date-error');
        });
    });
    
    // Gestione delle celle numeriche per sistema monofasica
    const numericFields = ['kaifa_180n', 'kaifa_280n', 'totale_180n', 'totale_kaifa_280n', 'consumo_180n', 'consumo_280n'];
    
    numericFields.forEach(fieldName => {
        const cells = document.querySelectorAll(`[data-field="${fieldName}"]`);
        
        cells.forEach(cell => {
            // Solo i campi editabili dovrebbero avere questi eventi
            if (cell.classList.contains('editable-cell')) {
                // Evento quando l'utente finisce di modificare la cella
                cell.addEventListener('blur', function() {
                    const value = this.textContent.trim();
                    
                    // Valida che sia un numero
                    if (value !== '' && !isValidNumber(value)) {
                        this.classList.add('date-error'); // Riutilizziamo la classe per l'errore
                        alert('Inserisci un valore numerico valido (usa . o , per i decimali)');
                        return;
                    } else {
                        this.classList.remove('date-error');
                        
                        // Normalizza il formato (converti virgola in punto)
                        if (value !== '') {
                            const normalizedValue = value.replace(',', '.');
                            this.textContent = parseFloat(normalizedValue).toString();
                        }
                    }
                    
                    // Calcola i totali per questa riga
                    const row = this.closest('tr');
                    calculateRowTotalsMonofasica(row);
                });
                
                // Evento durante la digitazione
                cell.addEventListener('input', function() {
                    this.classList.remove('date-error');
                });
                
                // Evento quando l'utente preme Invio
                cell.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        this.blur(); // Attiva l'evento blur per calcolare i totali
                    }
                });
            }
        });
    });
    
    // Calcola i totali iniziali per tutte le righe al caricamento della pagina
    const allRows = document.querySelectorAll('#datimonofascia tbody tr');
    allRows.forEach(row => {
        calculateRowTotalsMonofasica(row);
    });
    
    // Calcola i consumi iniziali
    calculateAllConsumptions();
    
    // Gestione del pulsante salvataggio monofasica
    const saveButton = document.getElementById('save-button-monofasica');
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const contatore_id = this.getAttribute('data-contatore-id');
            const impianto_id = this.getAttribute('data-impianto-id');
            const save_url = this.getAttribute('data-save-url');
            const anno_selezionato = document.getElementById('year-select').value;
            
            console.log('Avvio salvataggio monofasica...');
            console.log('Contatore ID:', contatore_id);
            console.log('Anno selezionato:', anno_selezionato);
            console.log('URL salvataggio:', save_url);
            
            // Raccogli tutti i dati dalla tabella
            const righe = document.querySelectorAll('#datimonofascia tbody tr');
            const datiDaSalvare = [];
            
            righe.forEach(riga => {
                const mese = riga.getAttribute('data-mese');
                const anno_riga = riga.getAttribute('data-anno') || anno_selezionato;
                
                // Raccogli i dati della riga
                const rigaDati = {
                    mese: parseInt(mese),
                    anno: parseInt(anno_riga),
                    data_ora_lettura: convertToISODateTime(riga.querySelector('[data-field="data_ora_lettura"]').textContent.trim()),
                    kaifa_180n: riga.querySelector('[data-field="kaifa_180n"]').textContent.trim(),
                    totale_180n: riga.querySelector('[data-field="totale_180n"]').textContent.trim(),
                    kaifa_280n: riga.querySelector('[data-field="kaifa_280n"]').textContent.trim(),
                    totale_kaifa_280n: riga.querySelector('[data-field="totale_kaifa_280n"]').textContent.trim()
                };
                
                console.log(`Riga mese ${mese}:`, rigaDati);
                datiDaSalvare.push(rigaDati);
            });
            
            // Prepara i dati per l'invio
            const payload = {
                letture: datiDaSalvare,
                anno: parseInt(anno_selezionato),
                contatore_id: parseInt(contatore_id)
            };
            
            console.log('Payload da inviare:', payload);
            
            // Disabilita il pulsante durante il salvataggio
            const originalText = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<i class="bi bi-hourglass-split"></i> Salvataggio...';
            
            // Invia i dati al server
            fetch(save_url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                console.log('Response status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Risposta dal server:', data);
                
                if (data.success) {
                    // Aggiorna la tabella con i dati salvati
                    if (data.letture_salvate && data.letture_salvate.length > 0) {
                        aggiornaTabellaDatiSalvatiMonofasica(data.letture_salvate);
                    }
                    
                    // Costruisci il messaggio di successo
                    let message = data.message || 'Dati salvati con successo!';
                    
                    // Aggiungi informazioni sul backup se disponibili
                    if (data.backup) {
                        if (data.backup.success) {
                            message += '\n\nBackup automatico creato: ' + data.backup.message;
                        } else {
                            message += '\n\nAttenzione: Il backup automatico non è riuscito: ' + data.backup.message;
                        }
                    }
                    
                    // Mostra messaggio di successo
                    alert(message);
                } else {
                    // Mostra errori
                    let errorMessage = data.message;
                    if (data.errori && data.errori.length > 0) {
                        errorMessage += '\n\nErrori specifici:\n' + data.errori.join('\n');
                    }
                    alert(errorMessage);
                }
            })
            .catch(error => {
                console.error('Errore durante il salvataggio:', error);
                alert('Errore durante il salvataggio. Controlla la console per maggiori dettagli.');
            })
            .finally(() => {
                // Riabilita il pulsante
                this.disabled = false;
                this.innerHTML = originalText;
            });
        });
    }
    
    // Carica i dati per l'anno corrente al caricamento della pagina
    const contatore_id = saveButton ? saveButton.getAttribute('data-contatore-id') : null;
    const anno_corrente = yearSelect ? yearSelect.value : new Date().getFullYear();
    
    if (contatore_id) {
        console.log(`Caricamento dati iniziale per contatore ${contatore_id}, anno ${anno_corrente}`);
        caricaDatiPerAnnoMonofasica(contatore_id, anno_corrente);
    }
});

// Funzione per aggiornare le colonne del mese con l'anno selezionato
function aggiornaColonneMeseMonofasica(anno) {
    console.log(`Aggiornamento colonne mese monofasica per anno: ${anno}`);
    
    // Nomi dei mesi in italiano
    const nomiMesi = [
        'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
    ];
    
    // Aggiorna i mesi da 1 a 12 (dell'anno selezionato)
    for (let mese = 1; mese <= 12; mese++) {
        const riga = document.querySelector(`tr[data-mese="${mese}"]`);
        if (riga) {
            const colonnaAnno = riga.querySelector('.mese-cell .anno-display');
            if (colonnaAnno) {
                colonnaAnno.textContent = anno;
            }
        }
    }
    
    // Aggiorna gennaio dell'anno successivo (riga 13)
    const rigaGennaioSuccessivo = document.querySelector('tr[data-mese="13"]');
    if (rigaGennaioSuccessivo) {
        const colonnaGennaioSuccessivo = rigaGennaioSuccessivo.querySelector('.mese-cell .anno-display');
        if (colonnaGennaioSuccessivo) {
            const annoSuccessivo = parseInt(anno) + 1;
            colonnaGennaioSuccessivo.textContent = annoSuccessivo;
        }
    }
    
    console.log(`Colonne mese monofasica aggiornate per anno ${anno} e anno successivo ${parseInt(anno) + 1}`);
}

// Funzione per caricare i dati per un anno specifico
function caricaDatiPerAnnoMonofasica(contatore_id, anno) {
    console.log(`Caricamento dati monofasica per contatore ${contatore_id}, anno ${anno}`);
    
    // Test connettività prima del caricamento
    testConnettivitaMonofasica(contatore_id)
        .then(() => {
            const loadUrl = `/automazione-dati/api/letture-monofasica/${contatore_id}/${anno}/`;
            
            return fetch(loadUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                }
            });
        })
        .then(response => {
            console.log(`DEBUG JS: Risposta caricamento - status: ${response.status}`);
            if (!response.ok) {
                throw new Error(`Errore nel caricamento: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('DEBUG JS: Dati ricevuti:', data);
            
            if (data.success) {
                // Pulisci la tabella prima di popolarla
                pulisciTabellaMonofasica();
                
                // Popola con i nuovi dati
                if (data.letture && data.letture.length > 0) {
                    popolaTabellaConDatiMonofasica(data.letture, anno);
                } else {
                    console.log('Nessuna lettura trovata per questo anno');
                }
            } else {
                console.error('Errore nei dati ricevuti:', data.message);
                alert(`Errore nel caricamento dei dati: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Errore durante il caricamento:', error);
            alert('Errore durante il caricamento dei dati. Controlla la console per maggiori dettagli.');
        });
}

// Funzione per aggiornare la tabella con i dati salvati
function aggiornaTabellaDatiSalvatiMonofasica(letture_salvate) {
    console.log('Aggiornamento tabella monofasica con dati salvati:', letture_salvate);
    
    letture_salvate.forEach(lettura => {
        // Trova la riga corrispondente
        const mese_riga = lettura.mese === 1 && lettura.anno > parseInt(document.getElementById('year-select').value) ? '13' : lettura.mese.toString();
        const row = document.querySelector(`tr[data-mese="${mese_riga}"]`);
        
        if (row) {
            // Aggiorna le celle con i dati salvati
            if (lettura.data_ora_lettura) {
                const dataOraCell = row.querySelector('[data-field="data_ora_lettura"]');
                if (dataOraCell) {
                    // Converti da formato ISO a formato italiano
                    const dataISO = new Date(lettura.data_ora_lettura);
                    const dataItaliana = formatDateTimeToItalian(dataISO);
                    dataOraCell.textContent = dataItaliana;
                }
            }
            
            // Aggiorna le celle numeriche
            const campiNumerici = ['kaifa_180n', 'totale_180n', 'kaifa_280n', 'totale_kaifa_280n'];
            campiNumerici.forEach(campo => {
                const cell = row.querySelector(`[data-field="${campo}"]`);
                if (cell && lettura[campo] !== null && lettura[campo] !== undefined) {
                    cell.textContent = parseFloat(lettura[campo]).toString();
                }
            });
        }
    });
    
    // Ricalcola i consumi dopo aver aggiornato tutti i dati salvati
    calculateAllConsumptions();
}

// Funzione per convertire da formato ISO a formato italiano
function formatDateTimeToItalian(date) {
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    
    return `${day}/${month}/${year} ${hours}:${minutes}`;
}

// Funzione per testare la connettività
function testConnettivitaMonofasica(contatore_id) {
    const testUrl = `/automazione-dati/api/test-dati-monofasica/${contatore_id}/`;
    
    return fetch(testUrl, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        }
    })
    .then(response => {
        console.log(`DEBUG JS: Test connettività - status: ${response.status}`);
        if (!response.ok) {
            throw new Error(`Test connettività fallito: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('DEBUG JS: Test connettività completato:', data);
    });
}

// Funzione per pulire la tabella
function pulisciTabellaMonofasica() {
    console.log('Pulizia tabella monofasica...');
    
    const righe = document.querySelectorAll('#datimonofascia tbody tr');
    righe.forEach(riga => {
        // Pulisci tutte le celle editabili
        const celleEditabili = riga.querySelectorAll('.editable-cell');
        celleEditabili.forEach(cella => {
            cella.textContent = '';
        });
        
        // Pulisci anche i campi calcolati
        const celleCalcolate = riga.querySelectorAll('.calculated-field');
        celleCalcolate.forEach(cella => {
            cella.textContent = '';
        });
        
        // Pulisci anche i campi di consumo
        const celleConsumo = riga.querySelectorAll('.consumption-field');
        celleConsumo.forEach(cella => {
            cella.textContent = '';
            cella.style.backgroundColor = ''; // Rimuovi anche il colore di sfondo
        });
    });
    
    console.log('Tabella monofasica pulita');
}

// Funzione per popolare la tabella con i dati ricevuti
function popolaTabellaConDatiMonofasica(letture, anno) {
    console.log('Popolazione tabella monofasica con dati:', letture);
    
    letture.forEach(lettura => {
        console.log('Processando lettura:', lettura);
        
        // Determina quale riga usare
        // Se è gennaio dell'anno successivo, usa la riga 13
        let mese_riga;
        if (lettura.mese === 1 && lettura.anno > parseInt(anno)) {
            mese_riga = '13';
        } else {
            mese_riga = lettura.mese.toString();
        }
        
        // Trova la riga corrispondente
        const row = document.querySelector(`tr[data-mese="${mese_riga}"]`);
        
        if (row) {
            console.log(`Aggiornamento riga mese ${mese_riga} con dati:`, lettura);
            
            // Aggiorna la data/ora se presente
            if (lettura.data_ora_lettura) {
                const dataOraCell = row.querySelector('[data-field="data_ora_lettura"]');
                if (dataOraCell) {
                    // Converti da formato ISO a formato italiano
                    const dataISO = new Date(lettura.data_ora_lettura);
                    const dataItaliana = formatDateTimeToItalian(dataISO);
                    dataOraCell.textContent = dataItaliana;
                }
            }
            
            // Aggiorna le celle numeriche
            const campiNumerici = ['kaifa_180n', 'totale_180n', 'kaifa_280n', 'totale_kaifa_280n'];
            campiNumerici.forEach(campo => {
                const cell = row.querySelector(`[data-field="${campo}"]`);
                if (cell && lettura[campo] !== null && lettura[campo] !== undefined) {
                    // Formatta il numero con 2 decimali se è un valore valido
                    const valore = parseFloat(lettura[campo]);
                    cell.textContent = !isNaN(valore) ? valore.toString() : '';
                }
            });
        } else {
            console.warn(`Riga non trovata per mese ${mese_riga}`);
        }
    });
    
    console.log('Tabella monofasica popolata completamente');
    
    // Calcola i consumi dopo aver popolato tutti i dati
    calculateAllConsumptions();
}