document.addEventListener('DOMContentLoaded', function() {
const yearSelect = document.getElementById('year-select');
    const saveButton = document.getElementById('reg_segnanti_save');
    const tableContainer = document.getElementById('reg_segnanti');

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
            // Aggiorna solo le prime 12 righe o la 13ª se non è in 'reg_segnanti'
            if (index < 12 || (index === 12 && !row.closest('#reg_segnanti'))) {
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
        
        // Stampa l'URL per debug
        console.log('Redirecting to: ' + currentUrl.toString());
        
        // Reindirizza alla pagina con il nuovo anno
        window.location.href = currentUrl.toString();
    });

    // Aggiorniamo subito i mesi al caricamento iniziale della pagina
    // per visualizzare l'anno correntemente selezionato (o quello di default).
    // updateMonths(); // Chiamata spostata alla fine dopo setupAutoCalculations

    updateMonths();

    // --- Inizio: Rendi le celle editabili ---

    // Seleziono tutte le celle <td> all'interno dei <tbody> delle tabelle con classe .table-content
const tableCells = document.querySelectorAll('.table-content table tbody tr td');
tableCells.forEach(cell => {
    // Escludo la prima cella della riga (che di solito contiene il nome del mese)
    const firstCell = cell.parentElement.querySelector('td:first-child');
    if (cell !== firstCell) {
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
            cell.dataset.oldValue = cell.innerHTML; // Salva il contenuto HTML originale
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
            // Confronto il contenuto attuale (ripulito da spazi extra) con quello originale
            if (cell.innerHTML.trim() !== cell.dataset.oldValue.trim()) {
                // Se è cambiato, aggiungo la classe "modified" per segnalare la modifica
                cell.classList.add('modified');
                
                // Salva immediatamente questa singola cella
                salvaSingolaCella(cell);
            } else {
                // Se è tornato uguale all'originale, rimuovo la classe "modified"
                cell.classList.remove('modified');
            }

            // Gestione specifica per i campi data ('data_presa')
            if (cell.dataset.field === 'data_presa') {
                const dateValue = cell.textContent.trim();
                if (dateValue) {
                    // Se l'utente inserisce una data nel formato gg/mm/aaaa...
                    const dateMatch = dateValue.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
                    if (dateMatch) {
                        // ...la converto nel formato standard AAAA-MM-GG
                        const day = dateMatch[1].padStart(2, '0');
                        const month = dateMatch[2].padStart(2, '0');
                        const year = dateMatch[3];
                        // Memorizzo il valore formattato in un attributo 'data-raw-value'
                        // Questo sarà il valore inviato al server
                        cell.dataset.rawValue = `${year}-${month}-${day}`;
                    } else {
                        // Se il formato non corrisponde, salvo comunque il testo inserito
                        cell.dataset.rawValue = dateValue;
                    }
                } else {
                    // Se la cella è vuota, imposto il valore raw a vuoto
                    cell.dataset.rawValue = '';
                }
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

// *** Nuova funzione: salvaSingolaCella ***
function salvaSingolaCella(cell) {
    // Ottieni il valore nuovo inserito
    let newValue = cell.innerText.trim();
    const fieldName = cell.dataset.field;

    // Trova l'elemento contenitore della tabella per recuperare l'ID del contatore impostato come data attribute
    const tableContainer = cell.closest('.table-content');
    // Assicurati di avere l'attributo "data-contatore-id" (vedi HTML della tabella: data-contatore-id="{{ contatore.id }}")
    const contatoreId = tableContainer.dataset.contatoreId;

    // Recupera l'anno; in questo esempio, lo estraiamo dalla query string oppure da un valore di default
    const urlParams = new URLSearchParams(window.location.search);
    const anno = urlParams.get('anno') || '2024';

    // Recupera la riga <tr> per ottenere il mese (presente nell'attributo data-mese)
    const tr = cell.closest('tr');
    const mese = parseInt(tr.dataset.mese);

    // Prepara l'oggetto riga che invieremo al server
    let rowData = { mese: mese };
    rowData[fieldName] = newValue;

    // Prepara il payload completo
    const dataPayload = {
        contatore_id: contatoreId,
        anno: anno,
        tipo_tabella: 'reg_segnanti',
        rows: [ rowData ]
    };

    // Recupera il token CSRF dal DOM
    const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfTokenInput ? csrfTokenInput.value : '';

    // Esegui la chiamata AJAX (fetch) per inviare i dati al server
    fetch('/automazione-dati/salva-reg-segnanti/', {  // Assicurati che questo endpoint corrisponda a quello configurato nelle URL di Django
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(dataPayload)
    })
    .then(response => response.json())
    .then(result => {
        if(result.status === 'success'){
            // Se il salvataggio è andato a buon fine, puoi aggiornare la cella con eventuale formattazione.
            // Ad esempio, se il campo è numerico, lo formattiamo a tre decimali:
            if (!isNaN(newValue)) {
                newValue = parseFloat(newValue).toFixed(3);
            }
            cell.innerText = newValue;
            cell.classList.remove('modified');
        } else {
            console.error('Errore nel salvataggio: ' + result.message);
        }
    })
    .catch(error => {
        console.error('Errore durante il fetch:', error);
    });
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
                        const row = document.querySelector(`#reg_segnanti table tbody tr[data-mese="${mese}"]`);
                        if (row) {
                            // Trova la cella imm_campo
                            const immCampoCell = row.querySelector('td[data-field="imm_campo"]');
                            if (immCampoCell) {
                                // Calcola il valore moltiplicato per k
                                const valoreMoltiplicato = (totale180n * contatoreK).toFixed(3);
                                // Imposta il nuovo valore
                                immCampoCell.textContent = valoreMoltiplicato;
                                immCampoCell.classList.add('modified');
                                
                                // Opzionale: salva immediatamente il valore modificato
                                salvaSingolaCella(immCampoCell);
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

});
