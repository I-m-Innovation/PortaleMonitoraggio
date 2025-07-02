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

// Funzione per calcolare i totali di una riga
function calculateRowTotals(row) {
    // Calcola totale negativo (A1- + A2- + A3-)
    const a1_neg_text = row.querySelector('[data-field="a1_neg"]').textContent.trim();
    const a2_neg_text = row.querySelector('[data-field="a2_neg"]').textContent.trim();
    const a3_neg_text = row.querySelector('[data-field="a3_neg"]').textContent.trim();
    
    const a1_neg = a1_neg_text ? parseFloat(a1_neg_text.replace(',', '.')) : 0;
    const a2_neg = a2_neg_text ? parseFloat(a2_neg_text.replace(',', '.')) : 0;
    const a3_neg = a3_neg_text ? parseFloat(a3_neg_text.replace(',', '.')) : 0;
    
    // Calcola totale positivo (A1+ + A2+ + A3+)
    const a1_pos_text = row.querySelector('[data-field="a1_pos"]').textContent.trim();
    const a2_pos_text = row.querySelector('[data-field="a2_pos"]').textContent.trim();
    const a3_pos_text = row.querySelector('[data-field="a3_pos"]').textContent.trim();
    
    const a1_pos = a1_pos_text ? parseFloat(a1_pos_text.replace(',', '.')) : 0;
    const a2_pos = a2_pos_text ? parseFloat(a2_pos_text.replace(',', '.')) : 0;
    const a3_pos = a3_pos_text ? parseFloat(a3_pos_text.replace(',', '.')) : 0;
    
    // Verifica che tutti i numeri siano validi prima del calcolo
    if ([a1_neg, a2_neg, a3_neg, a1_pos, a2_pos, a3_pos].some(val => isNaN(val))) {
        console.warn('Alcuni valori non sono numeri validi, salto il calcolo');
        return;
    }
    
    const totale_neg = a1_neg + a2_neg + a3_neg;
    const totale_pos = a1_pos + a2_pos + a3_pos;
    
    // Aggiorna le celle dei totali con maggiore precisione
    row.querySelector('[data-field="totale_neg"]').textContent = totale_neg.toFixed(3).replace(/\.?0+$/, '');
    row.querySelector('[data-field="totale_pos"]').textContent = totale_pos.toFixed(3).replace(/\.?0+$/, '');
    
    console.log(`Riga mese ${row.getAttribute('data-mese')}: Totale- = ${totale_neg}, Totale+ = ${totale_pos}`);
}

// Funzione per validare se un valore è un numero valido (MIGLIORATA)
function isValidNumber(value) {
    const trimmedValue = value.trim();
    if (trimmedValue === '') return true; // Celle vuote sono permesse
    
    // Accetta numeri con punto o virgola come separatore decimale
    const normalizedValue = trimmedValue.replace(',', '.');
    const numero = parseFloat(normalizedValue);
    return !isNaN(numero) && isFinite(numero);
}

// Funzione per normalizzare i numeri mantenendo la precisione
function normalizeNumber(value) {
    if (!value || value.trim() === '') return '';
    
    const normalizedValue = value.trim().replace(',', '.');
    const numero = parseFloat(normalizedValue);
    
    if (isNaN(numero)) return '';
    
    // Mantieni massimo 6 decimali per evitare problemi di precisione
    return numero.toFixed(6).replace(/\.?0+$/, '');
}

// Gestione dell'evento blur (quando l'utente esce dalla cella)
document.addEventListener('DOMContentLoaded', function() {
    // Aggiungi debug all'inizio
    console.log('DEBUG JS: DOM Content Loaded');
    debugStatoApplicazione();
    
    const dateTimeCells = document.querySelectorAll('[data-field="data_ora_lettura"]');
    
    // Gestione delle celle data/ora
    dateTimeCells.forEach(cell => {
        cell.addEventListener('blur', function() {
            const value = this.textContent.trim();
            
            // Se la cella è vuota, rimuovi eventuali errori
            if (value === '') {
                this.classList.remove('date-error');
                return;
            }
            
            // Valida il formato
            if (validateDateTimeFormat(value)) {
                this.classList.remove('date-error');
                console.log('Data/ora valida:', value);
            } else {
                this.classList.add('date-error');
                alert('Formato data/ora non valido. Usa: gg/mm/aaaa hh:mm (esempio: 12/01/2024 14:36) oppure solo gg/mm/aaaa (esempio: 12/01/2024, verrà impostato 00:00 come orario)');
            }
        });
        
        // Aggiungi un helper per il formato durante la digitazione
        cell.addEventListener('input', function() {
            // Rimuovi l'errore mentre l'utente sta digitando
            this.classList.remove('date-error');
        });
    });
    
    // Gestione delle celle numeriche (MIGLIORATA)
    const numericFields = ['a1_neg', 'a2_neg', 'a3_neg', 'a1_pos', 'a2_pos', 'a3_pos'];
    
    numericFields.forEach(fieldName => {
        const cells = document.querySelectorAll(`[data-field="${fieldName}"]`);
        
        cells.forEach(cell => {
            // Evento quando l'utente finisce di modificare la cella
            cell.addEventListener('blur', function() {
                const value = this.textContent.trim();
                
                // Valida che sia un numero
                if (value !== '' && !isValidNumber(value)) {
                    this.classList.add('date-error');
                    alert('Inserisci un valore numerico valido (usa . o , per i decimali)');
                    return;
                } else {
                    this.classList.remove('date-error');
                    
                    // Normalizza il valore mantenendo la precisione
                    if (value !== '') {
                        this.textContent = normalizeNumber(value);
                    }
                }
                
                // Calcola i totali per questa riga
                const row = this.closest('tr');
                calculateRowTotals(row);
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
        });
    });
    
    // Calcola i totali iniziali per tutte le righe al caricamento della pagina
    const allRows = document.querySelectorAll('#datitrifascia tbody tr');
    allRows.forEach(row => {
        calculateRowTotals(row);
    });
    
    // Gestione del pulsante salvataggio trifascia
    document.getElementById('save-button-trifasica').addEventListener('click', function() {
        const contatore_id = this.getAttribute('data-contatore-id');
        const impianto_id = this.getAttribute('data-impianto-id');
        const save_url = this.getAttribute('data-save-url');
        const anno_selezionato = document.getElementById('year-select').value;
        
        // Raccogli tutti i dati dalla tabella
        const rows = document.querySelectorAll('#datitrifascia tbody tr');
        const dati = [];
        let hasErrors = false;
        
        // Cicla attraverso tutte le righe della tabella
        rows.forEach(row => {
            const mese = row.getAttribute('data-mese');
            // Per la 13a riga (gennaio dell'anno successivo), usa l'anno successivo
            const anno = mese === '13' ? parseInt(anno_selezionato) + 1 : parseInt(anno_selezionato);
            
            // Ottieni la data/ora inserita dall'utente
            const dataOraCell = row.querySelector('[data-field="data_ora_lettura"]');
            const dataOraValue = dataOraCell ? dataOraCell.textContent.trim() : '';
            
            // Valida il formato della data/ora se è presente
            if (dataOraValue && !validateDateTimeFormat(dataOraValue)) {
                alert(`Errore nel formato data/ora per la riga del mese ${mese}. Usa il formato: gg/mm/aaaa hh:mm oppure solo gg/mm/aaaa (verrà impostato 00:00 come orario)`);
                hasErrors = true;
                return;
            }
            
            // Verifica che non ci siano errori nelle celle numeriche
            const numericCells = row.querySelectorAll('.editable-cell[data-field^="a"]');
            numericCells.forEach(cell => {
                if (cell.classList.contains('date-error')) {
                    hasErrors = true;
                }
            });
            
            // Ottieni tutti i valori dalle celle
            const a1_neg = row.querySelector('[data-field="a1_neg"]')?.textContent.trim() || '';
            const a2_neg = row.querySelector('[data-field="a2_neg"]')?.textContent.trim() || '';
            const a3_neg = row.querySelector('[data-field="a3_neg"]')?.textContent.trim() || '';
            const a1_pos = row.querySelector('[data-field="a1_pos"]')?.textContent.trim() || '';
            const a2_pos = row.querySelector('[data-field="a2_pos"]')?.textContent.trim() || '';
            const a3_pos = row.querySelector('[data-field="a3_pos"]')?.textContent.trim() || '';
            const totale_neg = row.querySelector('[data-field="totale_neg"]')?.textContent.trim() || '';
            const totale_pos = row.querySelector('[data-field="totale_pos"]')?.textContent.trim() || '';
            
            // Crea l'oggetto dati per questa riga
            const rigaDati = {
                mese: mese === '13' ? 1 : parseInt(mese), // La 13a riga è gennaio dell'anno successivo
                anno: anno,
                data_ora_lettura: convertToISODateTime(dataOraValue),
                a1_neg: a1_neg,
                a2_neg: a2_neg,
                a3_neg: a3_neg,
                a1_pos: a1_pos,
                a2_pos: a2_pos,
                a3_pos: a3_pos,
                totale_neg: totale_neg,
                totale_pos: totale_pos,
            };
            
            dati.push(rigaDati);
        });
        
        // Se ci sono errori, non continuare con il salvataggio
        if (hasErrors) {
            alert('Correggi gli errori prima di salvare i dati.');
            return;
        }
        
        // Disabilita il pulsante durante il salvataggio per evitare doppi click
        this.disabled = true;
        this.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>Salvando...';
        
        console.log('Dati da salvare:', dati);
        console.log('URL di salvataggio:', save_url);
        
        // Invia i dati al server usando l'URL dal template
        fetch(save_url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
            body: JSON.stringify({
                dati: dati,
                contatore_id: contatore_id,
                impianto_id: impianto_id
            })
        })
        .then(response => {
            // Controlla se la risposta è ok
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Risposta dal server:', data);
            
            if (data.success) {
                // Costruisci il messaggio di successo
                let message = 'Dati salvati con successo!';
                
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
                
                // Opzionalmente, aggiorna la tabella con i dati salvati
                if (data.letture_salvate) {
                    aggiornaTabellaDatiSalvati(data.letture_salvate);
                }
            } else {
                // Mostra messaggio di errore
                alert('Errore durante il salvataggio: ' + (data.message || 'Errore sconosciuto'));
            }
        })
        .catch(error => {
            console.error('Errore durante il salvataggio:', error);
            alert('Errore durante il salvataggio dei dati. Riprova più tardi.');
        })
        .finally(() => {
            // Riabilita il pulsante
            this.disabled = false;
            this.innerHTML = '<i class="bi bi-save"></i> Salva';
        });
    });
    
    // Aggiungi questa nuova funzionalità per il cambio anno
    const yearSelect = document.getElementById('year-select');
    const saveButton = document.getElementById('save-button-trifasica');

    if (yearSelect && saveButton) {
        // Funzione per caricare i dati basati sull'anno selezionato
        const loadDataForSelectedYear = () => {
            const selectedYear = yearSelect.value;
            const contatoreId = saveButton.getAttribute('data-contatore-id');
            
            console.log(`DEBUG JS: loadDataForSelectedYear chiamata con anno=${selectedYear}, contatore=${contatoreId}`);
            
            if (contatoreId && selectedYear) {
                // Aggiorna prima le colonne del mese con il nuovo anno
                aggiornaColonneMese(selectedYear);
                // Poi carica i dati per l'anno selezionato
                caricaDatiAnno(selectedYear);
            } else {
                console.warn('Contatore ID o anno non disponibili per il caricamento dei dati.');
                console.warn(`- contatoreId: ${contatoreId}`);
                console.warn(`- selectedYear: ${selectedYear}`);
            }
        };

        // Aggiungi l'event listener per il cambio dell'anno
        yearSelect.addEventListener('change', function() {
            console.log('DEBUG JS: Anno cambiato a:', this.value);
            loadDataForSelectedYear();
        });

        // Carica i dati per l'anno inizialmente selezionato al caricamento della pagina
        console.log('DEBUG JS: Caricamento dati iniziale...');
        loadDataForSelectedYear(); 
    } else {
        console.error('DEBUG JS: yearSelect o saveButton non trovati');
        console.error('- yearSelect:', yearSelect);
        console.error('- saveButton:', saveButton);
    }
});

// Funzione per aggiornare le colonne del mese con l'anno selezionato
function aggiornaColonneMese(anno) {
    console.log(`Aggiornamento colonne mese per anno: ${anno}`);
    
    // Nomi dei mesi in italiano
    const nomiMesi = [
        'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
    ];
    
    // Aggiorna i mesi da 1 a 12 (dell'anno selezionato)
    for (let mese = 1; mese <= 12; mese++) {
        const riga = document.querySelector(`tr[data-mese="${mese}"]`);
        if (riga) {
            const colonnaUese = riga.querySelector('.mese-cell .anno-display');
            if (colonnaUese) {
                colonnaUese.textContent = anno;
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
    
    console.log(`Colonne mese aggiornate per anno ${anno} e anno successivo ${parseInt(anno) + 1}`);
}

// Funzione per convertire il formato italiano in formato ISO
function convertToISODateTime(italianDateTime) {
    if (!italianDateTime || italianDateTime.trim() === '') {
        return null;
    }
    
    const regexCompleto = /^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})$/;
    const regexSoloData = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
    
    const matchCompleto = italianDateTime.match(regexCompleto);
    const matchSoloData = italianDateTime.match(regexSoloData);
    
    if (matchCompleto) {
        const day = matchCompleto[1].padStart(2, '0');
        const month = matchCompleto[2].padStart(2, '0');
        const year = matchCompleto[3];
        const hour = matchCompleto[4].padStart(2, '0');
        const minute = matchCompleto[5];
        
        // Formato ISO: YYYY-MM-DD HH:MM:SS
        return `${year}-${month}-${day} ${hour}:${minute}:00`;
    } else if (matchSoloData) {
        const day = matchSoloData[1].padStart(2, '0');
        const month = matchSoloData[2].padStart(2, '0');
        const year = matchSoloData[3];
        
        // Formato ISO con orario default 00:00
        return `${year}-${month}-${day} 00:00:00`;
    }
    
    return null;
}

// Funzione per aggiornare la tabella con i dati salvati
function aggiornaTabellaDatiSalvati(letture_salvate) {
    console.log('Aggiornamento tabella con dati salvati:', letture_salvate);
    
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
            const campiNumerici = ['a1_neg', 'a2_neg', 'a3_neg', 'a1_pos', 'a2_pos', 'a3_pos', 'totale_neg', 'totale_pos'];
            campiNumerici.forEach(campo => {
                const cell = row.querySelector(`[data-field="${campo}"]`);
                if (cell && lettura[campo] !== null && lettura[campo] !== undefined) {
                    cell.textContent = parseFloat(lettura[campo]).toFixed(2);
                }
            });
        }
    });
}

// Funzione per convertire da formato ISO a formato italiano
function formatDateTimeToItalian(date) {
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    
    return `${day}/${month}/${year}  ${hours}:${minutes}`;
}

// Funzione per caricare i dati di un anno specifico
function caricaDatiAnno(anno) {
    const saveButton = document.getElementById('save-button-trifasica');
    const contatore_id = saveButton.getAttribute('data-contatore-id');
    
    console.log(`DEBUG JS: Caricamento dati per anno=${anno}, contatore_id=${contatore_id}`);
    
    if (!contatore_id) {
        console.error('DEBUG JS: Contatore ID non trovato nel pulsante salva');
        alert('Errore: ID contatore non trovato. Ricarica la pagina.');
        return;
    }

    // Disabilita il pulsante temporaneamente e mostra un indicatore
    const originalText = saveButton.innerHTML;
    saveButton.disabled = true;
    saveButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Caricamento...';

    // CORREZIONE: Aggiorna l'URL per includere il prefisso automazione-dati
    const baseUrl = window.location.origin;
    const url = `/automazione-dati/api/letture-trifasica/${contatore_id}/${anno}/`;
    const fullUrl = baseUrl + url;
    
    console.log(`DEBUG JS: Base URL: ${baseUrl}`);
    console.log(`DEBUG JS: Relative URL: ${url}`);
    console.log(`DEBUG JS: Full URL: ${fullUrl}`);
    console.log(`DEBUG JS: Current page URL: ${window.location.href}`);

    // Test di connettività di base
    testConnettivita(contatore_id).then(() => {
        console.log('DEBUG JS: Test connettività passato, procedo con la chiamata principale');
        
        // Chiamata fetch all'API
        fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            console.log(`DEBUG JS: Response status: ${response.status}`);
            console.log(`DEBUG JS: Response headers:`, response.headers);
            
            if (!response.ok) {
                // Se il response non è OK, prova a leggere il body per più dettagli
                return response.text().then(text => {
                    console.error(`DEBUG JS: Response body: ${text}`);
                    throw new Error(`HTTP error! status: ${response.status}, body: ${text}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Dati ricevuti dal server:', data);
            
            if (data.success) {
                // Prima pulisci la tabella
                pulisciTabella();
                // Poi popola la tabella con i dati ricevuti
                popolaTabellaConDati(data.letture, anno);
            } else {
                console.warn('Nessun dato trovato per l\'anno:', anno);
                // Pulisci la tabella se non ci sono dati
                pulisciTabella();
            }
        })
        .catch(error => {
            console.error('Errore durante il caricamento dei dati:', error);
            alert('Errore durante il caricamento dei dati per l\'anno ' + anno + ': ' + error.message);
        })
        .finally(() => {
            // Ripristina il pulsante
            saveButton.disabled = false;
            saveButton.innerHTML = originalText;
        });
    }).catch(error => {
        console.error('DEBUG JS: Test connettività fallito:', error);
        saveButton.disabled = false;
        saveButton.innerHTML = originalText;
    });
}

// Aggiorna anche la funzione testConnettivita
function testConnettivita(contatore_id) {
    console.log('DEBUG JS: Inizio test connettività...');
    
    // CORREZIONE: Aggiorna l'URL del test
    const testUrl = '/automazione-dati/api/test-connessione/';
    
    return fetch(testUrl, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        }
    })
    .then(response => {
        console.log(`DEBUG JS: Test connettività - Status: ${response.status}`);
        if (response.status === 404) {
            console.warn('DEBUG JS: Endpoint di test non trovato, probabilmente le URL non sono configurate');
            // Non fermiamo l'esecuzione, è solo un warning
        }
        return Promise.resolve();
    })
    .catch(error => {
        console.error('DEBUG JS: Errore nel test di connettività:', error);
        return Promise.reject(error);
    });
}

// Funzione per debug del state dell'applicazione
function debugStatoApplicazione() {
    console.log('=== DEBUG STATO APPLICAZIONE ===');
    console.log('URL corrente:', window.location.href);
    console.log('Origin:', window.location.origin);
    console.log('Pathname:', window.location.pathname);
    
    const saveButton = document.getElementById('save-button-trifasica');
    if (saveButton) {
        console.log('Pulsante salva trovato:');
        console.log('- data-contatore-id:', saveButton.getAttribute('data-contatore-id'));
        console.log('- data-impianto-id:', saveButton.getAttribute('data-impianto-id'));
        console.log('- data-save-url:', saveButton.getAttribute('data-save-url'));
    } else {
        console.error('Pulsante salva NON trovato');
    }
    
    const yearSelect = document.getElementById('year-select');
    if (yearSelect) {
        console.log('Selettore anno trovato, valore:', yearSelect.value);
    } else {
        console.error('Selettore anno NON trovato');
    }
    
    const tabella = document.getElementById('datitrifascia');
    if (tabella) {
        const righe = tabella.querySelectorAll('tbody tr');
        console.log(`Tabella trovata con ${righe.length} righe`);
    } else {
        console.error('Tabella NON trovata');
    }
    
    console.log('=== FINE DEBUG ===');
}

// Funzione per pulire tutte le celle della tabella
function pulisciTabella() {
    console.log('Pulizia tabella in corso...');
    
    const rows = document.querySelectorAll('#datitrifascia tbody tr');
    
    rows.forEach(row => {
        // Pulisci tutte le celle editabili
        const editableCells = row.querySelectorAll('.editable-cell');
        editableCells.forEach(cell => {
            cell.textContent = '';
            cell.classList.remove('date-error'); // Rimuovi eventuali errori
        });
        
        // Pulisci anche i campi calcolati
        const calculatedCells = row.querySelectorAll('.calculated-field');
        calculatedCells.forEach(cell => {
            cell.textContent = '';
        });
    });
    
    console.log('Tabella pulita completamente');
}

// Funzione per popolare la tabella con i dati ricevuti (MIGLIORATA)
function popolaTabellaConDati(letture, anno) {
    console.log('Popolamento tabella con', letture.length, 'letture per l\'anno', anno);
    
    // Prima pulisci completamente la tabella
    pulisciTabella();
    
    letture.forEach(lettura => {
        console.log('Processando lettura:', lettura);
        
        // Determina quale riga usare
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
                    const dataISO = new Date(lettura.data_ora_lettura);
                    const dataItaliana = formatDateTimeToItalian(dataISO);
                    dataOraCell.textContent = dataItaliana;
                }
            }
            
            // Aggiorna le celle numeriche (MIGLIORATO) - CORRETTO per visualizzare anche i valori zero
            const campiNumerici = ['a1_neg', 'a2_neg', 'a3_neg', 'a1_pos', 'a2_pos', 'a3_pos'];
            campiNumerici.forEach(campo => {
                const cell = row.querySelector(`[data-field="${campo}"]`);
                if (cell && lettura[campo] !== null && lettura[campo] !== undefined && lettura[campo] !== '') {
                    // Usa il valore direttamente dal database senza parseFloat per evitare perdita di precisione
                    const valoreDalDB = lettura[campo].toString().trim();
                    // CORREZIONE: Visualizza tutti i valori numerici validi, inclusi gli zeri
                    if (valoreDalDB !== '') {
                        cell.textContent = valoreDalDB;
                    } else {
                        cell.textContent = '';
                    }
                } else {
                    cell.textContent = '';
                }
            });
            
            // Ricalcola i totali per questa riga
            calculateRowTotals(row);
        } else {
            console.warn(`Riga non trovata per mese ${mese_riga}`);
        }
    });
    
    console.log('Tabella popolata completamente');
}

// Funzione per ottenere l'anno attualmente selezionato
function getAnnoSelezionato() {
    const yearSelect = document.getElementById('year-select');
    return yearSelect ? yearSelect.value : new Date().getFullYear().toString();
}

