document.addEventListener('DOMContentLoaded', function() {
    const yearSelect = document.getElementById('year-select');
    const saveButton = document.getElementById('diarioenergie_save');
    const tableContainer = document.getElementById('diarioenergie');
    
    // Verifica se il contenitore della tabella esiste e se è un contatore Kaifa
    if (tableContainer) {
        const contatoreMarca = tableContainer.dataset.marca;
        // Esegui l'importazione automatica solo per contatori Kaifa
        if (contatoreMarca === 'Kaifa') {
            // Importa automaticamente i dati all'avvio della pagina
            importTotale180nData(true);
        }
    }
    
    // Funzione che aggiorna i nomi dei mesi in tutte le tabelle
    function updateMonths() {
        const months = ['Gennaio ', 'Febbraio ', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
                         'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];
    
        // Ottieni l'anno selezionato dal menu a tendina
        const selectedYear = yearSelect.value;
    
        // Aggiorna tutte le celle con classe mese-con-anno
        document.querySelectorAll('.mese-con-anno').forEach((cell, index) => {
            // Ottieni il numero del mese dalla riga (attributo data-mese)
            const row = cell.closest('tr');
            const meseNumber = row ? parseInt(row.dataset.mese) : (index + 1);
    
        
        });
    
        // Aggiorna anche le altre celle del mese (senza anno, tipicamente la prima colonna)
        document.querySelectorAll('.table-content table tbody tr').forEach((row, index) => {
            // Aggiorna solo le prime 12 righe o la 13ª se non è in 'diarioenergie'
            if (index < 12 || (index === 12 && !row.closest('#diarioenergie'))) {
                const firstCell = row.querySelector('td:first-child:not(.mese-con-anno)');
                if (firstCell) {
                    // Imposta il testo della prima cella con il nome del mese (senza anno)
                    firstCell.textContent = months[index];
                }
            }
        });
    }
    
    // Correzione del listener per evento "change" sul menu a tendina dell'anno
    yearSelect.addEventListener('change', function() {
        // Rimuovo il feedback visivo che aggiunge l'animazione:
        // yearSelect.classList.add('loading');
        
        // Costruisci l'URL con l'anno selezionato
        const anno = yearSelect.value;
        const currentUrl = new URL(window.location.href);
        
        // Imposta il parametro anno nell'URL
        currentUrl.searchParams.set('anno', anno);
        
        // Stampa l'URL per debug nella console del browser (Premi F12 nel browser)
        console.log('JavaScript: Redirecting to: ' + currentUrl.toString());
        
        // Reindirizza alla pagina con il nuovo anno
        window.location.href = currentUrl.toString();
    });
    
    // Aggiorniamo subito i mesi al caricamento iniziale della pagina
    // per visualizzare l'anno correntemente selezionato (o quello di default).
    // updateMonths(); // Chiamata spostata alla fine dopo setupAutoCalculations
    
    updateMonths();
    
    // --- Inizio: Rendi le celle editabili ---
    
    // Seleziono tutte le celle <td> all'interno dei <tbody> delle tabelle con classe .table-content
    const tableCells = document.querySelectorAll('#diarioenergie table tbody tr td');
    tableCells.forEach(cell => {
        // Escludo la prima cella della riga (che di solito contiene il nome del mese)
        const firstCell = cell.parentElement.querySelector('td:first-child');
        if (cell !== firstCell && cell.dataset.field) {
            // Rende la cella modificabile direttamente dall'utente nel browser
            cell.setAttribute('contenteditable', 'true');
            
            // Aggiungi attributi data- per identificare il campo
            const columnIndex = Array.from(cell.parentElement.children).indexOf(cell);
            const fieldName = determineFieldName(columnIndex); // Devi implementare questa funzione
            if (fieldName) {
                cell.dataset.field = fieldName;
            }
    
            // Memorizzo il valore originale quando la cella riceve il focus (ci si clicca dentro)
            cell.addEventListener('focus', function() {
                cell.dataset.oldValue = cell.innerText.trim(); // Salva il contenuto testuale originale
            });
    
            // Appena l'utente inizia a digitare, aggiungo la classe "editing"
            // Utile per dare un feedback visivo (es. cambiare sfondo o bordo)
            cell.addEventListener('input', function() {
                cell.classList.add('editing');
            });
    
            // Quando la cella perde il focus (si clicca fuori)
            cell.addEventListener('blur', function() {
                // Rimuovo la classe di feedback visivo "editing"
                cell.classList.remove('editing');
                const currentValue = cell.innerText.trim();
                const oldValue = cell.dataset.oldValue || ''; // Usa stringa vuota se non c'è old value
    
                // Confronto il contenuto attuale (ripulito da spazi extra) con quello originale
                if (currentValue !== oldValue) {
                    // Se è cambiato, aggiungo la classe "modified" per segnalare la modifica
                    cell.classList.add('modified');
                } else {
                    // Se è tornato uguale all'originale, rimuovo la classe "modified"
                    cell.classList.remove('modified');
                }
            });
        }
    });
    
    // Funzione per mappare l'indice della colonna al nome del campo nel database
    function determineFieldName(columnIndex) {
        // Esempio di mappatura (da personalizzare in base alla struttura della tabella)
        const fieldMap = {
            1: 'prod_campo',
            2: 'prod_ed',
            3: 'prod_gse',
            4: 'prel_campo',
            5: 'prel_ed',
            6: 'prel_gse',
            7: 'autocons_campo',
            8: 'autocons_ed',
            9: 'autocons_gse',
            10: 'imm_campo',
            11: 'imm_ed',
            12: 'imm_gse'
        };
        
        return fieldMap[columnIndex] || null;
    }
    
    // Aggiungi l'event listener al pulsante Salva
    if (saveButton && tableContainer) {
        saveButton.addEventListener('click', function() {
            salvaTuttiDatiRegSegnanti(tableContainer); // Chiama la nuova funzione di salvataggio
        });
    } else {
        if (!saveButton) console.error("Pulsante Salva non trovato!");
        if (!tableContainer) console.error("Contenitore tabella 'diarioenergie' non trovato!");
    }
    
    // Aggiungi handler per il pulsante di importazione da totale_180n
    const importButton = document.getElementById('import-totale-180n');
    if (importButton) {
        importButton.addEventListener('click', function() {
            // Chiamare la funzione di importazione con false per mostrare i messaggi
            importTotale180nData(false);
        });
    }
    
    // Funzione unificata per importare i dati da totale_180n
    function importTotale180nData(isSilent = false) {
        // Ottieni l'anno selezionato
        const anno = yearSelect.value;
        // Ottieni il contatore ID dalla tabella
        const contatoreId = tableContainer.dataset.contatoreId;
        // Ottieni il valore k dal data-attribute
        const contatoreK = parseInt(tableContainer.dataset.contatoreK || "1");
    
        // Mostra indicatore di caricamento sul pulsante (solo se non è silenzioso)
        if (!isSilent && importButton) {
            importButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Importazione...';
            importButton.disabled = true;
        }
    
        // Chiamata AJAX per ottenere i dati Kaifa
        fetch(`/automazione-dati/get-kaifa-data/?contatore_id=${contatoreId}&anno=${anno}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Per ogni riga, imposta il valore moltiplicato nella colonna imm_campo
                data.letture.forEach(lettura => {
                    const mese = lettura.mese;
                    const totale180n = lettura.totale_180n;
                    
                    if (totale180n !== null && totale180n !== undefined) {
                        // Trova la riga della tabella per questo mese
                        const row = document.querySelector(`#diarioenergie table tbody tr[data-mese="${mese}"]`);
                        if (row) {
                            // Trova la cella imm_campo
                            const immCampoCell = row.querySelector('td[data-field="imm_campo"]');
                            if (immCampoCell) {
                                // Calcola il valore moltiplicato per k
                                const valoreMoltiplicato = (totale180n * contatoreK).toFixed(3);
                                // Imposta il nuovo valore
                                immCampoCell.textContent = valoreMoltiplicato;
                                immCampoCell.classList.add('modified');
                            }
                        }
                    }
                });
                
                // Mostra messaggio di successo solo se non è silenzioso
                if (!isSilent) {
                    alert('Importazione completata con successo!');
                } else {
                    console.log('Importazione automatica completata');
                }
            } else {
                // Mostra errore solo se non è silenzioso
                if (!isSilent) {
                    alert('Errore durante l\'importazione: ' + data.message);
                } else {
                    console.error('Errore durante l\'importazione automatica:', data.message);
                }
            }
        })
        .catch(error => {
            console.error('Errore durante l\'importazione:', error);
            if (!isSilent) {
                alert('Si è verificato un errore durante l\'importazione.');
            }
        })
        .finally(() => {
            // Ripristina il pulsante solo se non è silenzioso
            if (!isSilent && importButton) {
                importButton.innerHTML = '<i class="bi bi-arrow-down-circle"></i> Importa Dati';
                importButton.disabled = false;
            }
        });
    }
    
    // --- Modifica: Aggiungiamo la nuova funzione per salvare tutti i dati ---
    function salvaTuttiDatiRegSegnanti(containerTabella) {
        console.log("Tentativo di salvataggio dati diarioenergie...");
    
        // Recupera informazioni necessarie
        let contatoreId = containerTabella.dataset.contatoreId;
        
        // Se l'ID non è nel contenitore principale, prova ad ottenerlo da altre fonti
        if (!contatoreId) {
            // Prova a trovare l'ID del contatore in elementi figli che potrebbero averlo nel dataset
            const elementiConId = containerTabella.querySelectorAll('[data-contatore-id]');
            if (elementiConId.length > 0) {
                contatoreId = elementiConId[0].dataset.contatoreId;
                console.log("ID contatore trovato in un elemento figlio:", contatoreId);
            }
            
            // Prova a cercarlo in un input nascosto (se presente nel template)
            if (!contatoreId) {
                const hiddenInput = document.querySelector('input[name="contatore_id"]');
                if (hiddenInput) {
                    contatoreId = hiddenInput.value;
                    console.log("ID contatore trovato in input nascosto:", contatoreId);
                }
            }
            
            // Prova a estrarlo dall'URL se presente come parametro
            if (!contatoreId) {
                const urlParams = new URLSearchParams(window.location.search);
                contatoreId = urlParams.get('contatore_id');
                if (contatoreId) {
                    console.log("ID contatore estratto da URL:", contatoreId);
                }
            }
        }
        
        const anno = yearSelect ? yearSelect.value : new Date().getFullYear().toString();
        const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        const csrfToken = csrfTokenInput ? csrfTokenInput.value : '';

        if (!contatoreId) {
            alert("Errore: ID del contatore non trovato. Impossibile salvare.\nVerificare che l'elemento HTML contenga l'attributo data-contatore-id.");
            console.error("ID Contatore mancante nel dataset e in altre possibili fonti.");
            return;
        }
    
        // Raccogli i dati da tutte le righe della tabella specifica
        const rowsData = [];
        const righeTabella = containerTabella.querySelectorAll('table tbody tr');
    
        righeTabella.forEach(tr => {
            const mese = tr.dataset.mese;
            if (mese) { // Processa solo righe con un mese definito
                const rowData = { mese: parseInt(mese) }; // Assicurati che il mese sia un numero
                const celleDati = tr.querySelectorAll('td[data-field]'); // Seleziona solo celle con data-field
    
                celleDati.forEach(cell => {
                    const fieldName = cell.dataset.field;
                    const fieldValue = cell.innerText.trim(); // Prendi il testo visibile
                    rowData[fieldName] = fieldValue; // Aggiungi campo e valore all'oggetto della riga
                });
                rowsData.push(rowData); // Aggiungi l'oggetto riga all'array
            }
        });
    
        if (rowsData.length === 0) {
            alert("Nessun dato da salvare trovato nella tabella.");
            console.warn("Nessuna riga con data-mese trovata o nessuna cella con data-field.");
            return;
        }
    
        // Prepara il payload completo per l'invio
        const dataPayload = {
            contatore_id: contatoreId,
            anno: anno,
            tipo_tabella: 'diarioenergie', // Identifica la tabella per il backend
            rows: rowsData
        };
    
        console.log("Payload da inviare:", JSON.stringify(dataPayload, null, 2)); // Log per debug
    
        // Feedback visivo: disabilita il pulsante e mostra "Salvataggio..."
        if (saveButton) {
            saveButton.disabled = true;
            saveButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Salvataggio...';
        }
    
        // Esegui la chiamata AJAX (fetch) per inviare i dati al server
        fetch('/automazione-dati/salva-reg-segnanti/', { // Assicurati che questo URL sia corretto!
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify(dataPayload)
        })
        .then(response => {
            // Controlla se la risposta è OK (status 2xx)
            if (!response.ok) {
                // Se non è OK, cerca di leggere il messaggio di errore JSON, altrimenti usa lo status text
                return response.json().catch(() => null).then(errorData => {
                    throw new Error(errorData?.message || `Errore HTTP ${response.status}: ${response.statusText}`);
                });
            }
            return response.json(); // Se OK, processa il JSON
        })
        .then(result => {
            console.log("Risposta dal server:", result);
            if (result.status === 'success' || result.status === 'partial_success') {
                alert(result.message || 'Dati salvati con successo!'); // Mostra messaggio all'utente
    
                // Rimuovi la classe 'modified' da tutte le celle della tabella salvata
                containerTabella.querySelectorAll('td.modified').forEach(cell => {
                    cell.classList.remove('modified');
                    // Aggiorna il valore 'oldValue' per il prossimo confronto
                    cell.dataset.oldValue = cell.innerText.trim();
                });
    
                // Se ci sono errori specifici (partial_success), loggali
                if (result.errors && result.errors.length > 0) {
                    console.warn("Si sono verificati alcuni errori durante il salvataggio:", result.errors);
                    // Potresti mostrare questi errori in modo più dettagliato all'utente se necessario
                }
    
            } else {
                // Se lo status nella risposta non è 'success' o 'partial_success'
                alert('Errore nel salvataggio: ' + (result.message || 'Errore sconosciuto.'));
                console.error('Errore restituito dal server:', result);
            }
        })
        .catch(error => {
            console.error('Errore durante la chiamata fetch:', error);
            alert('Errore di comunicazione con il server: ' + error.message);
        })
        .finally(() => {
            // Riabilita il pulsante e ripristina il testo originale, indipendentemente dall'esito
            if (saveButton) {
                saveButton.disabled = false;
                saveButton.innerHTML = '<i class="bi bi-save"></i> Salva';
            }
        });
    }
});