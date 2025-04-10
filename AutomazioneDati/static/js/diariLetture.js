document.addEventListener('DOMContentLoaded', function() {
    const yearSelect = document.getElementById('year-select');

    // Verifica che il token CSRF sia presente
    const csrfTokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    if (!csrfTokenElement) {
        console.error('Token CSRF non trovato!');
    } else {
        console.log('Token CSRF trovato:', csrfTokenElement.value.substring(0, 5) + '...');
    }

    // Inizializza i nomi dei mesi nelle intestazioni
    updateMonths();

    // Funzione che aggiorna i nomi dei mesi nelle intestazioni delle tabelle (non tocca le date nelle celle)
    function updateMonths() {
        const months = ['Gennaio 01/01 0:00', 'Febbraio 01/02 0:00', 'Marzo 01/03 0:00', 'Aprile 01/04 0:00', 'Maggio 01/05 0:00', 'Giugno 01/06 0:00',
                        'Luglio 01/07 0:00', 'Agosto 01/08 0:00', 'Settembre 01/09 0:00', 'Ottobre 01/10 0:00', 'Novembre 01/11 0:00', 'Dicembre 01/12 0:00', 'Gennaio 01/01 0:00'];

        const selectedYear = yearSelect.value;

        // Aggiorna le celle speciali mese-con-anno
        document.querySelectorAll('.mese-con-anno').forEach((cell, index) => {
            const row = cell.closest('tr');
            // Assumiamo che data-mese sia sempre presente e corretto (1-13)
            const meseNumber = row ? parseInt(row.dataset.mese) : (index + 1);

            if (meseNumber >= 1 && meseNumber <= 13) {
                let yearToShow = selectedYear;
                if (meseNumber === 13) {
                    yearToShow = parseInt(selectedYear) + 1;
                }
                // Usiamo l'indice 0-based per l'array months
                cell.textContent = months[meseNumber - 1] + ' ' + yearToShow;
            }
        });

        // Aggiorna le altre celle del mese (senza anno) - Questa logica sembra complessa e potrebbe essere semplificata se non necessaria
        document.querySelectorAll('.table-content table tbody tr').forEach((row, index) => {
             // Assicurati che questa logica sia corretta per le tue tabelle
            if (index < 12 || (index === 12 && !row.closest('#reg_segnanti'))) { // Attenzione a questa condizione
                const firstCell = row.querySelector('td:first-child:not(.mese-con-anno)');
                if (firstCell && index < months.length) { // Usa l'indice della riga se corrisponde ai mesi
                    firstCell.textContent = months[index];
                }
            }
        });
    }

    // Listener per evento "change" sul menu a tendina dell'anno
    yearSelect.addEventListener('change', function() {
        // Reindirizza alla stessa pagina ma con l'anno selezionato come parametro
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('anno', yearSelect.value);
        window.location.href = currentUrl.toString();
    });

    // Ottieni il pulsante di salvataggio
    const saveButtonDiarioLetture = document.getElementById('save-button-diarioletture');
    
    // Aggiungi event listener al pulsante di salvataggio
    saveButtonDiarioLetture.addEventListener('click', function() {
        // Ottieni i dati dal pulsante
        const contatoreId = this.dataset.contatoreId;
        const impiantoId = this.dataset.impiantoId;
        
        // Ottieni l'anno selezionato
        const anno = document.getElementById('year-select').value;
        
        // Ottieni il tipo di contatore attivo
        let tipoContatore = '';
        let datiTabella = [];
        
        // Determina quale tabella è attualmente visibile e raccoglie i dati
        if (document.getElementById('libro_energie').style.display === 'block') {
            tipoContatore = 'libro_energie';
            datiTabella = raccogliDatiLibroEnergie(contatoreId, anno);
        } else if (document.getElementById('libro_kaifa').style.display === 'block') {
            tipoContatore = 'libro_kaifa';
            datiTabella = raccogliDatiLibroKaifa(contatoreId, anno);
        }
        
        // Se non ci sono dati da salvare, esci
        if (datiTabella.length === 0) {
            alert('Nessun dato da salvare.');
            return;
        }
        
        // Ottieni il token CSRF
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Prepara i dati da inviare
        const datiDaInviare = {
            tipo_tabella: tipoContatore,
            rows: datiTabella
        };
        
        // Mostra un indicatore di caricamento
        const saveButton = this;
        saveButton.disabled = true;
        saveButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Salvataggio in corso...';
        
        // Invia i dati al server - usa l'endpoint corretto
        fetch('/automazione-dati/salva-dati-letture/', {  // Modifica l'URL per puntare al corretto endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(datiDaInviare)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Errore nella risposta del server: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                alert('Dati salvati con successo!');
                // Aggiorna i dati visualizzati con quelli salvati
                if (tipoContatore === 'libro_energie') {
                    aggiornaTabellaDatiEnergie(data.rows);
                } else if (tipoContatore === 'libro_kaifa') {
                    aggiornaTabellaDatiKaifa(data.rows);
                }
            } else {
                alert('Errore durante il salvataggio: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            alert('Si è verificato un errore durante il salvataggio dei dati: ' + error.message);
        })
        .finally(() => {
            // Ripristina il pulsante di salvataggio
            saveButton.disabled = false;
            saveButton.innerHTML = '<i class="bi bi-save"></i> Salva';
        });
    });

    // Crea elemento di stile per l'evidenziazione delle righe e celle aggiornate
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        .updated-cell {
            animation: highlightCell 2s;
        }
        
        .updated-row {
            animation: highlightRow 2s;
        }
        
        
    `;
    document.head.appendChild(styleElement);

    // Aggiungi listeners alle celle editabili
    addCellListeners();

    // Calcola i totali iniziali
    setTimeout(updateAllDifferentials, 500);
});

// Funzione per convertire la data italiana (GG/MM/AAAA) in formato ISO (YYYY-MM-DD)
// Restituisce la stringa ISO o null se il formato/data non è valido.
function convertDateToISO(italianDate) {
    if (!italianDate || typeof italianDate !== 'string') {
        return null; // Input non valido
    }
    const parts = italianDate.trim().split('/');
    if (parts.length === 3) {
        const day = parts[0].padStart(2, '0');
        const month = parts[1].padStart(2, '0');
        const year = parts[2];
        // Verifica base della validità dei componenti
        if (parseInt(day) > 0 && parseInt(day) <= 31 && parseInt(month) > 0 && parseInt(month) <= 12 && year.length === 4 && parseInt(year) > 1000) {
             // Verifica aggiuntiva creando un oggetto Date per validare giorni/mesi
             // Nota: Mesi in JS Date sono 0-indicizzati (0=Gen, 11=Dic)
             const testDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
             // Controlla se l'oggetto Date creato corrisponde ai valori originali
             if (testDate && testDate.getFullYear() == year && testDate.getMonth() == month - 1 && testDate.getDate() == day) {
                 return `${year}-${month}-${day}`; // Data valida, restituisci ISO
             }
        }
    }
    // Se il formato non è GG/MM/AAAA o la data non è valida
    console.warn(`Formato data non valido o data non valida: "${italianDate}". Impossibile convertire in ISO.`);
    return null; // Restituisce null per indicare fallimento
}

// Funzione per formattare la data ISO (YYYY-MM-DD) in GG/MM/AAAA per la visualizzazione
function formatDateDisplay(isoDate) {
    if (!isoDate || typeof isoDate !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) {
        return ""; // Restituisce stringa vuota se l'input non è una data ISO valida
    }
    try {
        // Dividi la stringa ISO
        const parts = isoDate.split('-');
        const year = parts[0];
        const month = parts[1];
        const day = parts[2];
        // Verifica base della validità dei componenti (già fatta dal regex, ma doppia sicurezza)
        if (parseInt(day) > 0 && parseInt(day) <= 31 && parseInt(month) > 0 && parseInt(month) <= 12 && year.length === 4) {
             return `${day}/${month}/${year}`; // Ritorna formato GG/MM/AAAA
        } else {
             console.warn(`Data ISO non valida ricevuta per la visualizzazione: ${isoDate}`);
             return ""; // Data ISO non valida
        }
    } catch (e) {
        console.error("Errore formattazione data display:", isoDate, e);
        return ""; // Restituisce stringa vuota in caso di errore
    }
}

// Funzione per raccogliere i dati dalla tabella Libro Energie
function raccogliDatiLibroEnergie(contatoreId, anno) {
    const dati = [];
    const tabella = document.getElementById('libro_energie');
    const righe = tabella.querySelectorAll('tbody tr');

    righe.forEach(riga => {
        const mese = riga.dataset.mese;
        const dataPresaCell = riga.querySelector('td[data-field="data_presa"]');
        let dataPresaISO = null; // Inizializza a null. Conterrà la data in formato YYYY-MM-DD

        if (dataPresaCell) {
            const testoCella = dataPresaCell.textContent.trim(); // Leggi sempre il testo visibile
            if (testoCella) {
                // Prova a convertire il testo visualizzato (che dovrebbe essere GG/MM/AAAA) in ISO
                dataPresaISO = convertDateToISO(testoCella);
                // Se la conversione fallisce, dataPresaISO rimarrà null (gestito da convertDateToISO)
                // Potresti aggiungere un feedback all'utente qui se la conversione fallisce
                if (dataPresaISO === null && testoCella !== "") {
                     console.warn(`Data inserita per mese ${mese} non valida: "${testoCella}"`);
                     // Aggiungi una classe di errore alla cella?
                     // dataPresaCell.classList.add('input-error');
                } //else {
                     // Rimuovi classe di errore se presente?
                     // dataPresaCell.classList.remove('input-error');
                //}
            }
            // Se testoCella è vuoto, dataPresaISO rimane null
        }

        // --- Lettura degli altri campi (invariata) ---
        const a1Neg = parseNumericValue(riga.querySelector('td[data-field="a1_neg"]'));
        const a2Neg = parseNumericValue(riga.querySelector('td[data-field="a2_neg"]'));
        const a3Neg = parseNumericValue(riga.querySelector('td[data-field="a3_neg"]'));
        const a1Pos = parseNumericValue(riga.querySelector('td[data-field="a1_pos"]'));
        const a2Pos = parseNumericValue(riga.querySelector('td[data-field="a2_pos"]'));
        const a3Pos = parseNumericValue(riga.querySelector('td[data-field="a3_pos"]'));
        
        // --- Lettura migliorata dei totali ---
        const totaleCellNeg = riga.querySelector('td[data-field="totale_neg"]');
        const totaleCellPos = riga.querySelector('td[data-field="totale_pos"]');

        let totaleNeg = null;
        if (totaleCellNeg) {
            // Prova a leggere prima dal dataset.value (memorizzato da updateCalculatedCell)
            const rawValue = totaleCellNeg.dataset.value;
            if (rawValue !== undefined && rawValue !== null && rawValue !== '') {
                const parsed = parseFloat(rawValue);
                if (!isNaN(parsed)) {
                    totaleNeg = parsed;
                }
            }
            // Fallback: se dataset.value non è valido/presente, leggi dal textContent
            if (totaleNeg === null) {
                totaleNeg = parseNumericValue(totaleCellNeg);
            }
        }

        let totalePos = null;
        if (totaleCellPos) {
            // Prova a leggere prima dal dataset.value
            const rawValue = totaleCellPos.dataset.value;
            if (rawValue !== undefined && rawValue !== null && rawValue !== '') {
                const parsed = parseFloat(rawValue);
                if (!isNaN(parsed)) {
                    totalePos = parsed;
                }
            }
            // Fallback: leggi dal textContent
            if (totalePos === null) {
                totalePos = parseNumericValue(totaleCellPos);
            }
        }
        // Assicura che i valori null/NaN diventino null
        totaleNeg = (totaleNeg === null || isNaN(totaleNeg)) ? null : totaleNeg;
        totalePos = (totalePos === null || isNaN(totalePos)) ? null : totalePos;


        // --- Aggiunta dati all'array ---
        // Applica la logica 'valore !== 0 ? valore : null' anche ai totali letti
        // Questo invia null se la cella è vuota (parseNumericValue restituisce 0) o se il totale calcolato è 0
        dati.push({
            contatore_id: contatoreId,
            anno: anno,
            mese: mese,
            tipo_tabella: 'libro_energie',
            data_presa: dataPresaISO, // Invia il valore ISO convertito (o null)
            a1_neg: a1Neg !== 0 ? a1Neg : null,
            a2_neg: a2Neg !== 0 ? a2Neg : null,
            a3_neg: a3Neg !== 0 ? a3Neg : null,
            totale_neg: totaleNeg !== 0 ? totaleNeg : null, // Applica la stessa logica ai totali
            a1_pos: a1Pos !== 0 ? a1Pos : null,
            a2_pos: a2Pos !== 0 ? a2Pos : null,
            a3_pos: a3Pos !== 0 ? a3Pos : null,
            totale_pos: totalePos !== 0 ? totalePos : null // Applica la stessa logica ai totali
        });
    });

    return dati;
}

// Funzione per raccogliere i dati dalla tabella Libro Kaifa
function raccogliDatiLibroKaifa(contatoreId, anno) {
    const dati = [];
    const tabella = document.getElementById('libro_kaifa');
    const righe = tabella.querySelectorAll('tbody tr');

    righe.forEach(riga => {
        const mese = riga.dataset.mese;
        const dataPresaCell = riga.querySelector('td[data-field="data_presa"]');
        let dataPresaISO = null; // Inizializza a null. Conterrà la data in formato YYYY-MM-DD

        if (dataPresaCell) {
            const testoCella = dataPresaCell.textContent.trim(); // Leggi sempre il testo visibile
            if (testoCella) {
                // Tentativo 1: È già ISO (YYYY-MM-DD)?
                if (/^\d{4}-\d{2}-\d{2}$/.test(testoCella)) {
                    // Validiamo se è una data ISO sensata
                    try {
                        const testDate = new Date(testoCella + 'T00:00:00Z'); // Usa UTC
                        // Verifica che la data creata corrisponda alla stringa
                        if (!isNaN(testDate.getTime()) && testDate.toISOString().startsWith(testoCella)) {
                            dataPresaISO = testoCella; // È una data ISO valida
                        } else {
                             console.warn(`Data ISO non valida trovata in 'data_presa' per Kaifa mese ${mese}: "${testoCella}". Invio null.`);
                             // dataPresaISO rimane null
                        }
                    } catch (e) {
                         console.warn(`Errore validazione data ISO in 'data_presa' per Kaifa mese ${mese}: "${testoCella}". Invio null.`);
                         // dataPresaISO rimane null
                    }
                } else {
                    // Tentativo 2: Prova a convertire da GG/MM/AAAA usando la funzione helper
                    dataPresaISO = convertDateToISO(testoCella); // Riutilizza la funzione
                    // Se la conversione fallisce, dataPresaISO rimarrà null
                    if (dataPresaISO === null && testoCella !== "") {
                         console.warn(`Formato data non riconosciuto o non valido in 'data_presa' per Kaifa mese ${mese}: "${testoCella}". Invio null.`);
                         // Aggiungere classe di errore?
                         // dataPresaCell.classList.add('input-error');
                    } //else if (testoCella !== "") {
                         // Rimuovere classe di errore?
                         // dataPresaCell.classList.remove('input-error');
                    //}
                }
            }
            // Se testoCella era vuoto, dataPresaISO rimane null
        }

        // --- Lettura degli altri campi Kaifa (invariata) ---
        const kaifa180n = parseNumericValue(riga.querySelector('td[data-field="kaifa_180n"]'));
        const kaifa280n = parseNumericValue(riga.querySelector('td[data-field="kaifa_280n"]'));
        const totale180n = parseNumericValue(riga.querySelector('td[data-field="totale_180n"]')); // Leggi il totale calcolato
        const totale280n = parseNumericValue(riga.querySelector('td[data-field="totale_280n"]')); // Leggi il totale calcolato

        // --- Aggiunta dati all'array ---
        dati.push({
            contatore_id: contatoreId,
            anno: anno,
            mese: mese,
            tipo_tabella: 'libro_kaifa',
            data_presa: dataPresaISO, // Invia il valore ISO convertito (o null)
            kaifa_180n: kaifa180n !== 0 ? kaifa180n : null,
            kaifa_280n: kaifa280n !== 0 ? kaifa280n : null,
            totale_180n: totale180n, // Invia il totale letto dalla cella
            totale_280n: totale280n  // Invia il totale letto dalla cella
        });
    });

    return dati;
}

// Funzione per aggiornare la tabella con i dati ricevuti dal server
function aggiornaTabellaDatiEnergie(datiAggiornati) {
    datiAggiornati.forEach(dato => {
        // Trova la riga corrispondente usando l'attributo data-mese
        // Assicurati che 'dato.mese' corrisponda a quello nell'HTML (1-13)
        const riga = document.querySelector(`#libro_energie table tbody tr[data-mese="${dato.mese}"]`);
        if (!riga) {
            console.warn(`Riga non trovata per mese ${dato.mese} in aggiornaTabellaDatiEnergie`);
            return;
        }

        // Animazione per evidenziare brevemente le righe aggiornate
        riga.classList.add('updated-row');
        setTimeout(() => riga.classList.remove('updated-row'), 2000);

        // Aggiorna la data di presa
        const cellaPresa = riga.querySelector('td[data-field="data_presa"]');
        if (cellaPresa) {
            // dato.data_presa arriva dal backend come stringa YYYY-MM-DD o null
            cellaPresa.dataset.rawvalue = dato.data_presa || ''; // Aggiorna rawvalue con ISO o stringa vuota
            cellaPresa.textContent = formatDateDisplay(dato.data_presa); // Mostra formato GG/MM/AAAA o vuoto
            if (dato.data_presa) { // Evidenzia solo se c'è una data
                 cellaPresa.classList.add('updated-cell');
                 setTimeout(() => cellaPresa.classList.remove('updated-cell'), 2000);
            }
        }

        // Aggiorna tutti i campi numerici (A1-, A2-, A3-, ecc.)
        updateCellIfPresent(riga, 'a1_neg', dato.a1_neg);
        updateCellIfPresent(riga, 'a2_neg', dato.a2_neg);
        updateCellIfPresent(riga, 'a3_neg', dato.a3_neg);
        updateCellIfPresent(riga, 'totale_neg', dato.totale_neg, true); // true per indicare che è calcolato/non-editabile
        updateCellIfPresent(riga, 'a1_pos', dato.a1_pos);
        updateCellIfPresent(riga, 'a2_pos', dato.a2_pos);
        updateCellIfPresent(riga, 'a3_pos', dato.a3_pos);
        updateCellIfPresent(riga, 'totale_pos', dato.totale_pos, true); // true per indicare che è calcolato/non-editabile
    });

    // Ricalcola i totali dopo l'aggiornamento per assicurare coerenza
    updateAllDifferentials();
}

// Funzione per aggiornare la tabella Kaifa con i dati ricevuti dal server
function aggiornaTabellaDatiKaifa(datiAggiornati) {
    datiAggiornati.forEach(dato => {
        // Trova la riga corrispondente usando l'attributo data-mese
        // Assicurati che 'dato.mese' corrisponda a quello nell'HTML (1-13)
        const riga = document.querySelector(`#libro_kaifa table tbody tr[data-mese="${dato.mese}"]`);
         if (!riga) {
            console.warn(`Riga non trovata per mese ${dato.mese} in aggiornaTabellaDatiKaifa`);
            return;
        }

        // Animazione per evidenziare brevemente le righe aggiornate
        riga.classList.add('updated-row');
        setTimeout(() => riga.classList.remove('updated-row'), 2000);

        // Aggiorna la data di presa
        const cellaPresa = riga.querySelector('td[data-field="data_presa"]');
        if (cellaPresa) {
            // dato.data_presa arriva dal backend come stringa YYYY-MM-DD o null
            cellaPresa.dataset.rawvalue = dato.data_presa || ''; // Aggiorna rawvalue con ISO o stringa vuota
            cellaPresa.textContent = formatDateDisplay(dato.data_presa); // Mostra formato GG/MM/AAAA o vuoto
            if (dato.data_presa) { // Evidenzia solo se c'è una data
                 cellaPresa.classList.add('updated-cell');
                 setTimeout(() => cellaPresa.classList.remove('updated-cell'), 2000);
            }
        }

        // Aggiorna i valori numerici (input e calcolati)
        updateCellIfPresent(riga, 'kaifa_180n', dato.kaifa_180n);
        updateCellIfPresent(riga, 'totale_180n', dato.totale_180n, true); // Aggiorna anche la cella del totale (non editabile)
        updateCellIfPresent(riga, 'kaifa_280n', dato.kaifa_280n);
        updateCellIfPresent(riga, 'totale_280n', dato.totale_280n, true); // Aggiorna anche la cella del totale (non editabile)
    });

     // Ricalcola i totali Kaifa dopo l'aggiornamento
     updateAllKaifaTotals(); // Assicurati che questa funzione esista e faccia il ricalcolo
}

// Funzione di supporto per aggiornare una cella se il valore è presente
function updateCellIfPresent(riga, fieldName, value, isCalculated = false) {
    if (value === null || value === undefined) return;
    
    const cell = riga.querySelector(`td[data-field="${fieldName}"]`);
    if (!cell) return;
    
    // Formatta il valore numerico per la visualizzazione
    cell.textContent = formatNumericValue(value);
    
    // Se è un campo calcolato, memorizza anche il valore numerico originale
    if (isCalculated) {
        cell.dataset.value = value;
    }
    
    // Aggiungi classe per evidenziare temporaneamente la cella aggiornata
    cell.classList.add('updated-cell');
    setTimeout(() => cell.classList.remove('updated-cell'), 2000);
}

// Formatta una data in formato ISO in una visualizzazione più leggibile in formato italiano
function formatDateDisplay(isoDate) {
    if (!isoDate) return '';
    
    // Se è già in formato italiano (GG/MM/AAAA), restituiscilo così com'è
    if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(isoDate)) {
        return isoDate;
    }
    
    try {
        const date = new Date(isoDate);
        if (isNaN(date.getTime())) {
            // Prova a interpretare formati di data alternativi
            const parts = isoDate.split(/[-/]/);
            if (parts.length === 3) {
                // Assumiamo ISO YYYY-MM-DD o MM/DD/YYYY e proviamo a convertirlo
                if (parts[0].length === 4) {
                    // Formato YYYY-MM-DD
                    const year = parseInt(parts[0]);
                    const month = parseInt(parts[1]) - 1; // Mese in JS è 0-based
                    const day = parseInt(parts[2]);
                    return `${day.toString().padStart(2, '0')}/${(month + 1).toString().padStart(2, '0')}/${year}`;
                } else {
                    // Prova a interpretare un altro formato di data
                    return isoDate; // Restituisci l'originale se non riesci a interpretarlo
                }
            }
            return isoDate; // Se la data non è valida, restituisci il valore originale
        }
        
        // Formatta come GG/MM/AAAA
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const year = date.getFullYear();
        
        return `${day}/${month}/${year}`;
    } catch (e) {
        console.error("Errore nel formato data:", e);
        return isoDate; // In caso di errore, restituisci il valore originale
    }
}

// Funzione per analizzare valori numerici da elementi della tabella
function parseNumericValue(element) {
    if (!element) return 0;
    
    const text = element.textContent.trim();
    if (!text) return 0;
    
    // Rimuovi spazi e sostituisci virgole con punti per la conversione corretta
    const cleanedText = text.replace(/\s+/g, '').replace(',', '.');
    
    // Converti in numero
    const value = parseFloat(cleanedText);
    
    // Restituisci 0 se non è un numero valido
    return isNaN(value) ? 0 : value;
}

// Funzione per formattare valori numerici per la visualizzazione
function formatNumericValue(value) {
    if (value === null || value === undefined || isNaN(value)) return '';
    
    // Formatta il numero con virgola come separatore decimale (formato italiano)
    if (Number.isInteger(value)) {
        // Se è un intero, mostra senza decimali
        return value.toString();
    } else {
        // Se è un decimale, limita a 4 cifre decimali e converte il punto in virgola
        // Rimuove gli zeri finali non necessari
        const formattedValue = parseFloat(value.toFixed(4)).toString().replace('.', ',');
        return formattedValue;
    }
}

// Funzione per aggiungere listeners alle celle editabili
function addCellListeners() {
    // --- Libro Energie ---
    const righeEnergie = document.querySelectorAll('#libro_energie table tbody tr');
    righeEnergie.forEach((riga, index) => {
        // Campi negativi
        const a1NegCell = riga.querySelector('td[data-field="a1_neg"]');
        const a2NegCell = riga.querySelector('td[data-field="a2_neg"]');
        const a3NegCell = riga.querySelector('td[data-field="a3_neg"]');
        [a1NegCell, a2NegCell, a3NegCell].forEach(cell => {
            if (cell) {
                // Passiamo 'libro_energie' come ID tabella
                cell.addEventListener('input', () => updateRowDifferentials(riga, index, 'neg', 'libro_energie'));
                cell.addEventListener('blur', () => updateRowDifferentials(riga, index, 'neg', 'libro_energie'));
            }
        });

        // Campi positivi
        const a1PosCell = riga.querySelector('td[data-field="a1_pos"]');
        const a2PosCell = riga.querySelector('td[data-field="a2_pos"]');
        const a3PosCell = riga.querySelector('td[data-field="a3_pos"]');
        [a1PosCell, a2PosCell, a3PosCell].forEach(cell => {
            if (cell) {
                // Passiamo 'libro_energie' come ID tabella
                cell.addEventListener('input', () => updateRowDifferentials(riga, index, 'pos', 'libro_energie'));
                cell.addEventListener('blur', () => updateRowDifferentials(riga, index, 'pos', 'libro_energie'));
            }
        });
    });

    // --- Libro Kaifa ---
    const righeKaifa = document.querySelectorAll('#libro_kaifa table tbody tr');
    righeKaifa.forEach((riga, index) => {
        const kaifa180nCell = riga.querySelector('td[data-field="kaifa_180n"]');
        const kaifa280nCell = riga.querySelector('td[data-field="kaifa_280n"]');

        [kaifa180nCell, kaifa280nCell].forEach(cell => {
            if (cell) {
                // Passiamo 'libro_kaifa' come ID tabella e 'all' come tipo (non c'è distinzione pos/neg)
                cell.addEventListener('input', () => updateRowDifferentials(riga, index, 'all', 'libro_kaifa'));
                cell.addEventListener('blur', () => updateRowDifferentials(riga, index, 'all', 'libro_kaifa'));
            }
        });
    });
}

// Funzione per aggiornare i differenziali di una specifica riga
// Aggiunto parametro tableId per sapere quale tabella stiamo aggiornando
function updateRowDifferentials(riga, index, tipo, tableId) {
    // Ottieni la riga successiva (se esiste) all'interno della tabella specifica
    const rigaSuccessiva = document.querySelector(`#${tableId} table tbody tr[data-mese="${parseInt(riga.dataset.mese) + 1}"]`);
    if (!rigaSuccessiva) return; // Non calcolare se non c'è una riga successiva

    // --- Logica per Libro Energie ---
    if (tableId === 'libro_energie') {
        if (tipo === 'neg' || tipo === 'all') {
            // Calcola il totale negativo (codice esistente)
            const a1NegCorrente = parseNumericValue(riga.querySelector('td[data-field="a1_neg"]'));
            const a2NegCorrente = parseNumericValue(riga.querySelector('td[data-field="a2_neg"]'));
            const a3NegCorrente = parseNumericValue(riga.querySelector('td[data-field="a3_neg"]'));
            const a1NegSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="a1_neg"]'));
            const a2NegSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="a2_neg"]'));
            const a3NegSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="a3_neg"]'));
            const sommaNegCorrente = a1NegCorrente + a2NegCorrente + a3NegCorrente;
            const sommaNegSuccessiva = a1NegSuccessiva + a2NegSuccessiva + a3NegSuccessiva;
            const differenzaNeg = sommaNegSuccessiva - sommaNegCorrente;

            // Aggiorna la cella totale negativo
            const totaleNegCell = riga.querySelector('td[data-field="totale_neg"]');
            updateCalculatedCell(totaleNegCell, differenzaNeg);
        }

        if (tipo === 'pos' || tipo === 'all') {
            // Calcola il totale positivo (codice esistente)
            const a1PosCorrente = parseNumericValue(riga.querySelector('td[data-field="a1_pos"]'));
            const a2PosCorrente = parseNumericValue(riga.querySelector('td[data-field="a2_pos"]'));
            const a3PosCorrente = parseNumericValue(riga.querySelector('td[data-field="a3_pos"]'));
            const a1PosSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="a1_pos"]'));
            const a2PosSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="a2_pos"]'));
            const a3PosSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="a3_pos"]'));
            const sommaPosCorrente = a1PosCorrente + a2PosCorrente + a3PosCorrente;
            const sommaPosSuccessiva = a1PosSuccessiva + a2PosSuccessiva + a3PosSuccessiva;
            const differenzaPos = sommaPosSuccessiva - sommaPosCorrente;

            // Aggiorna la cella totale positivo
            const totalePosCell = riga.querySelector('td[data-field="totale_pos"]');
            updateCalculatedCell(totalePosCell, differenzaPos);
        }
    }
    // --- Logica per Libro Kaifa ---
    else if (tableId === 'libro_kaifa') {
        // Calcola totale 1.8.0.n
        const kaifa180nCorrente = parseNumericValue(riga.querySelector('td[data-field="kaifa_180n"]'));
        const kaifa180nSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="kaifa_180n"]'));
        const differenza180n = kaifa180nSuccessiva - kaifa180nCorrente;
        const totale180nCell = riga.querySelector('td[data-field="totale_180n"]');
        updateCalculatedCell(totale180nCell, differenza180n);

        // Calcola totale 2.8.0.n
        const kaifa280nCorrente = parseNumericValue(riga.querySelector('td[data-field="kaifa_280n"]'));
        const kaifa280nSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="kaifa_280n"]'));
        const differenza280n = kaifa280nSuccessiva - kaifa280nCorrente;
        const totale280nCell = riga.querySelector('td[data-field="totale_280n"]');
        updateCalculatedCell(totale280nCell, differenza280n);
    }

    // Aggiorna anche la riga precedente, perché il suo totale dipende da questa riga
    // Assicurati di passare lo stesso tableId
    const rigaPrecedente = document.querySelector(`#${tableId} table tbody tr[data-mese="${parseInt(riga.dataset.mese) - 1}"]`);
    if (rigaPrecedente) {
        const indexPrecedente = index - 1;
        // Chiamata ricorsiva per aggiornare la riga precedente, passando il tipo e tableId corretti
        updateRowDifferentials(rigaPrecedente, indexPrecedente, tipo, tableId);
    }
}

// Funzione helper per aggiornare una cella calcolata
function updateCalculatedCell(cell, value) {
    if (cell) {
        cell.textContent = formatNumericValue(value);
        cell.dataset.value = value; // Memorizza il valore numerico grezzo

        // Aggiungi effetto visivo per indicare il cambiamento
        cell.classList.add('updated-cell');
        setTimeout(() => cell.classList.remove('updated-cell'), 2000);
    }
}

// Aggiorna la funzione updateAllDifferentials per gestire entrambe le tabelle
function updateAllDifferentials() {
    // --- Libro Energie ---
    const righeEnergie = document.querySelectorAll('#libro_energie table tbody tr');
    for (let i = 0; i < righeEnergie.length - 1; i++) {
        const rigaCorrente = righeEnergie[i];
        // Passa 'all' per calcolare sia pos che neg, e l'ID della tabella
        updateRowDifferentials(rigaCorrente, i, 'all', 'libro_energie');
    }

    // --- Libro Kaifa ---
    const righeKaifa = document.querySelectorAll('#libro_kaifa table tbody tr');
    for (let i = 0; i < righeKaifa.length - 1; i++) {
        const rigaCorrente = righeKaifa[i];
        // Passa 'all' come tipo (non c'è distinzione) e l'ID della tabella
        updateRowDifferentials(rigaCorrente, i, 'all', 'libro_kaifa');
    }
}

// Funzione per rendere le celle editabili (se non è già implementata)
function setupEditableCells() {
    // Ottieni tutte le celle A1, A2, A3 (sia pos che neg)
    const editableCells = document.querySelectorAll('#libro_energie table tbody td[data-field^="a1_"], td[data-field^="a2_"], td[data-field^="a3_"]');
    
    editableCells.forEach(cell => {
        cell.setAttribute('contenteditable', 'true');
        
        // Gestisci input solo numerico
        cell.addEventListener('keypress', function(e) {
            // Permetti solo numeri, punto, virgola e tasti di controllo
            const isNumber = /[0-9.,]/.test(e.key);
            const isControl = ['Enter', 'Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key);
            
            if (!isNumber && !isControl) {
                e.preventDefault();
            }
        });
    });
}
