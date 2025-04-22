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
        
        console.log("Pulsante salva premuto. Contatore ID:", contatoreId, "Anno:", anno);
        
        // Determina quale tabella è visibile in base allo stile display
        const libroEnergie = document.getElementById('libro_energie');
        const libroKaifa = document.getElementById('libro_kaifa');
        
        console.log("Visibilità tabelle:", {
            "libro_energie": libroEnergie ? libroEnergie.style.display : "elemento non trovato",
            "libro_kaifa": libroKaifa ? libroKaifa.style.display : "elemento non trovato"
        });
        
        // IMPORTANTE: Rimuoviamo il setTimeout per la tabella Kaifa
        // Questo garantisce che i dati vengano raccolti immediatamente dopo l'aggiornamento forzato
        if (libroEnergie && libroEnergie.style.display === 'block') {
            console.log("Tabella ENERGIE attiva - Aggiornamento totali...");
            updateAllDifferentials();
            tipoContatore = 'libro_energie';
            datiTabella = raccogliDatiLibroEnergie(contatoreId, anno);
        } else if (libroKaifa && libroKaifa.style.display === 'block') {
            console.log("Tabella KAIFA attiva - Aggiornamento totali...");
            // La funzione raccogliDatiLibroKaifa ora include forceUpdateKaifaTotals al suo interno
            tipoContatore = 'libro_kaifa';
            datiTabella = raccogliDatiLibroKaifa(contatoreId, anno);
        } else {
            console.warn("ATTENZIONE: Nessuna tabella attiva trovata!");
            tipoContatore = document.getElementById('tipo-contatore-attivo') ? 
                           document.getElementById('tipo-contatore-attivo').value : 'sconosciuto';
            alert('Errore: impossibile determinare il tipo di tabella attiva. Tipo rilevato: ' + tipoContatore);
            return;
        }
        
        // Se non ci sono dati da salvare, esci
        if (datiTabella.length === 0) {
            alert('Nessun dato da salvare. Verificare che la tabella contenga dati.');
            return;
        }
        
        // Ottieni il token CSRF
        const csrfToken = csrfTokenElement.value;
        
        // Procedi con il salvataggio
        salvaDati(this, tipoContatore, datiTabella, csrfToken);
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

    // Inizializza il pulsante per il toggle delle somme
    setupToggleSumsButton();
});

    




// Funzione per raccogliere i dati dalla tabella Libro Energie
function raccogliDatiLibroEnergie(contatoreId, anno) {
    const dati = [];
    const tabella = document.getElementById('libro_energie');
    const righe = tabella.querySelectorAll('tbody tr');

    righe.forEach(riga => {
        const mese = riga.dataset.mese;
        const dataPresaCell = riga.querySelector('td[data-field="data_presa"]');
        let dataPresaISO = null; // Inizializza a null. Conterrà la data in formato YYYY-MM-DD
        let oraLettura = null;

        if (dataPresaCell) {
            const testoCella = dataPresaCell.textContent.trim(); // Leggi sempre il testo visibile
            if (testoCella) {
                // Prova a convertire il testo visualizzato (che dovrebbe essere GG/MM/AAAA) in ISO
                const dateTimeInfo = convertDateToISO(testoCella);
                dataPresaISO = dateTimeInfo.date;
                oraLettura = dateTimeInfo.time;
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
            ora_lettura: oraLettura,
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
    const tabella = document.querySelector('#libro_kaifa table');
    if (!tabella) {
        console.error('Tabella Libro Kaifa non trovata');
        return [];
    }
    
    const righe = tabella.querySelectorAll('tbody tr');
    const dati = [];
    
    righe.forEach((riga, index) => {
        const mese = riga.dataset.mese;
        if (!mese) {
            console.warn(`Riga ${index}: attributo data-mese mancante, saltata`);
            return; // Salta questa iterazione
        }
        
        // Gestione data_presa con ora
        const dataPresaCell = riga.querySelector('td[data-field="data_presa"]');
        let dataPresaISO = null;
        let oraLettura = null;
        
        if (dataPresaCell) {
            const testoCella = dataPresaCell.textContent.trim();
            if (testoCella) {
                const dateTimeInfo = convertDateToISO(testoCella);
                dataPresaISO = dateTimeInfo.date;
                oraLettura = dateTimeInfo.time;
            }
        }
        
        // Lettura valori numerici input (invariato)
        const kaifa180nCell = riga.querySelector('td[data-field="kaifa_180n"]');
        const kaifa280nCell = riga.querySelector('td[data-field="kaifa_280n"]');
        const kaifa180n = parseNumericValue(kaifa180nCell);
        const kaifa280n = parseNumericValue(kaifa280nCell);
        
        // Lettura ancora più robusta dei totali
        const totale180nCell = riga.querySelector('td[data-field="totale_180n"]');
        const totale280nCell = riga.querySelector('td[data-field="totale_280n"]');
        
        // Variabili per memorizzare i totali
        let totale180n = null;
        let totale280n = null;
        
        // L'ultimo mese (13) non ha totali
        const isUltimoMese = parseInt(mese) === 13;
        
        if (!isUltimoMese) {
            // Lettura del totale 1.8.0.n direttamente dal dataset
            if (totale180nCell && totale180nCell.dataset.value !== undefined) {
                totale180n = parseFloat(totale180nCell.dataset.value);
                console.log(`Mese ${mese}: totale_180n letto da dataset.value = ${totale180n}`);
            } else if (totale180nCell) {
                // Fallback alla differenza tra i valori attuali e successivi
                const rigaSuccessiva = tabella.querySelector(`tbody tr[data-mese="${parseInt(mese) + 1}"]`);
                if (rigaSuccessiva) {
                    const kaifa180nCorrente = parseNumericValue(kaifa180nCell);
                    const kaifa180nSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="kaifa_180n"]'));
                    totale180n = kaifa180nSuccessiva - kaifa180nCorrente;
                    console.log(`Mese ${mese}: totale_180n calcolato al volo = ${totale180n}`);
                }
            }
            
            // Lettura del totale 2.8.0.n direttamente dal dataset
            if (totale280nCell && totale280nCell.dataset.value !== undefined) {
                totale280n = parseFloat(totale280nCell.dataset.value);
                console.log(`Mese ${mese}: totale_280n letto da dataset.value = ${totale280n}`);
            } else if (totale280nCell) {
                // Fallback alla differenza tra i valori attuali e successivi
                const rigaSuccessiva = tabella.querySelector(`tbody tr[data-mese="${parseInt(mese) + 1}"]`);
                if (rigaSuccessiva) {
                    const kaifa280nCorrente = parseNumericValue(kaifa280nCell);
                    const kaifa280nSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="kaifa_280n"]'));
                    totale280n = kaifa280nSuccessiva - kaifa280nCorrente;
                    console.log(`Mese ${mese}: totale_280n calcolato al volo = ${totale280n}`);
                }
            }
        }
        
        // Aggiungi i dati all'array includendo l'ora
        dati.push({
            contatore_id: contatoreId,
            anno: anno,
            mese: mese,
            tipo_tabella: 'libro_kaifa',
            data_presa: dataPresaISO,
            ora_lettura: oraLettura,
            kaifa_180n: kaifa180n !== 0 ? kaifa180n : null,
            kaifa_280n: kaifa280n !== 0 ? kaifa280n : null,
            totale_180n: (isUltimoMese || isNaN(totale180n)) ? null : totale180n,
            totale_280n: (isUltimoMese || isNaN(totale280n)) ? null : totale280n
        });
    });
    
    // Visualizza i totali prima dell'invio per debug
    let totaliString = "Riepilogo totali da inviare:\n";
    dati.forEach(row => {
        if (row.mese !== '13') { // Escludi l'ultimo mese che non ha totali
            totaliString += `Mese ${row.mese}: 1.8.0.n=${row.totale_180n}, 2.8.0.n=${row.totale_280n}\n`;
        }
    });
    console.log(totaliString);
    
    console.log(`Totale ${dati.length} record Kaifa raccolti.`);
    return dati;
}

// Funzione per aggiornare la tabella con i dati ricevuti dal server
function aggiornaTabellaDatiEnergie(datiAggiornati) {
    if (!datiAggiornati || !Array.isArray(datiAggiornati)) {
        console.warn('Nessun dato aggiornato ricevuto per la tabella Energie');
        return;
    }
    console.log('Aggiornamento tabella Energie con', datiAggiornati.length, 'righe');
    
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
    if (!datiAggiornati || !Array.isArray(datiAggiornati)) {
        console.warn('Nessun dato aggiornato ricevuto per la tabella Kaifa');
        return;
    }
    console.log('Aggiornamento tabella Kaifa con', datiAggiornati.length, 'righe');
    
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
            cellaPresa.dataset.rawvalue = dato.data_presa || '';
            
            // Formatta la visualizzazione della data con ora
            let displayText = formatDateDisplay(dato.data_presa);
            if (dato.ora_lettura) {
                displayText += ' ' + dato.ora_lettura;
            }
            
            cellaPresa.textContent = displayText;
            
            if (dato.data_presa) {
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
     updateAllDifferentials(); // Utilizziamo questa funzione esistente invece di updateAllKaifaTotals
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

// Funzione per aggiornare i differenziali di una specifica riga// Aggiunto parametro tableId per sapere quale tabella stiamo aggiornando
function updateRowDifferentials(riga, index, tipo, tableId) {
    // --- Logica per Libro Energie (MODIFICATA) ---
    if (tableId === 'libro_energie') {
        // Calcola la SOMMA per la riga corrente, non la differenza con la successiva

        if (tipo === 'neg' || tipo === 'all') {
            // Calcola la somma dei valori negativi della riga corrente
            const a1NegCorrente = parseNumericValue(riga.querySelector('td[data-field="a1_neg"]'));
            const a2NegCorrente = parseNumericValue(riga.querySelector('td[data-field="a2_neg"]'));
            const a3NegCorrente = parseNumericValue(riga.querySelector('td[data-field="a3_neg"]'));
            const sommaNegCorrente = a1NegCorrente + a2NegCorrente + a3NegCorrente;

            // Aggiorna la cella totale negativo con la SOMMA
            const totaleNegCell = riga.querySelector('td[data-field="totale_neg"]');
            updateCalculatedCell(totaleNegCell, sommaNegCorrente);
        }

        if (tipo === 'pos' || tipo === 'all') {
            // Calcola la somma dei valori positivi della riga corrente
            const a1PosCorrente = parseNumericValue(riga.querySelector('td[data-field="a1_pos"]'));
            const a2PosCorrente = parseNumericValue(riga.querySelector('td[data-field="a2_pos"]'));
            const a3PosCorrente = parseNumericValue(riga.querySelector('td[data-field="a3_pos"]'));
            const sommaPosCorrente = a1PosCorrente + a2PosCorrente + a3PosCorrente;

            // Aggiorna la cella totale positivo con la SOMMA
            const totalePosCell = riga.querySelector('td[data-field="totale_pos"]');
            updateCalculatedCell(totalePosCell, sommaPosCorrente);
        }
        // NOTA: Non è più necessario aggiornare la riga precedente per la logica di somma semplice.
    }
    // --- Logica per Libro Kaifa (INVARIATA - Calcola la differenza) ---
    else if (tableId === 'libro_kaifa') {
        // Ottieni la riga successiva (necessaria per la differenza)
        const rigaSuccessiva = document.querySelector(`#${tableId} table tbody tr[data-mese="${parseInt(riga.dataset.mese) + 1}"]`);
        if (!rigaSuccessiva) return; // Non calcolare se non c'è una riga successiva

        // Calcola totale 1.8.0.n (differenza)
        const kaifa180nCorrente = parseNumericValue(riga.querySelector('td[data-field="kaifa_180n"]'));
        const kaifa180nSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="kaifa_180n"]'));
        const differenza180n = kaifa180nSuccessiva - kaifa180nCorrente;
        const totale180nCell = riga.querySelector('td[data-field="totale_180n"]');
        updateCalculatedCell(totale180nCell, differenza180n);

        // Calcola totale 2.8.0.n (differenza)
        const kaifa280nCorrente = parseNumericValue(riga.querySelector('td[data-field="kaifa_280n"]'));
        const kaifa280nSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="kaifa_280n"]'));
        const differenza280n = kaifa280nSuccessiva - kaifa280nCorrente;
        const totale280nCell = riga.querySelector('td[data-field="totale_280n"]');
        updateCalculatedCell(totale280nCell, differenza280n);

        // Aggiorna anche la riga precedente per Kaifa, perché il suo totale dipende da questa riga
        const rigaPrecedente = document.querySelector(`#${tableId} table tbody tr[data-mese="${parseInt(riga.dataset.mese) - 1}"]`);
        if (rigaPrecedente) {
            const indexPrecedente = index - 1;
            // Chiamata ricorsiva per aggiornare la riga precedente, passando il tipo e tableId corretti
            // Assicurati che questa chiamata non causi loop infiniti se la logica è complessa
            // Potrebbe essere necessario un controllo aggiuntivo o un approccio diverso se updateRowDifferentials
            // viene chiamato da più punti contemporaneamente.
            // Per ora, assumiamo che funzioni correttamente per la logica Kaifa.
            // NOTA: Questa chiamata è specifica per Kaifa dove il totale dipende dalla riga successiva.
             updateRowDifferentials(rigaPrecedente, indexPrecedente, 'all', tableId); // Usiamo 'all' per ricalcolare entrambi i totali Kaifa
        }
    }
}

// Funzione helper per aggiornare una cella calcolata
function updateCalculatedCell(cell, value) {
    if (cell) {
        // --- Modifica: Verifica se il valore è un numero valido ---
        const numericValue = parseFloat(value); // Prova a convertire il valore in numero
        if (isNaN(numericValue)) {
            // Se non è un numero valido (es. NaN, Infinity)
            console.warn(`Tentativo di aggiornare la cella ${cell.dataset.field || 'sconosciuta'} con un valore non valido: ${value}`);
            cell.textContent = ''; // Pulisci il testo visualizzato nella cella
            delete cell.dataset.value; // Rimuovi l'attributo dataset.value se non valido
        } else {
            // Se è un numero valido
            cell.textContent = formatNumericValue(numericValue); // Formatta per la visualizzazione (es. con virgola)
            cell.dataset.value = numericValue.toString(); // Memorizza il valore numerico grezzo come stringa nel dataset
            // Log di conferma per vedere cosa è stato effettivamente impostato
            console.log(`Cella ${cell.dataset.field || 'sconosciuta'} aggiornata: text='${cell.textContent}', dataset.value='${cell.dataset.value}'`);

            // Aggiungi effetto visivo per indicare il cambiamento (invariato)
            cell.classList.add('updated-cell');
            setTimeout(() => cell.classList.remove('updated-cell'), 2000);
        }
    } else {
        // Log se la cella non viene trovata (utile per debug)
        // console.warn("Tentativo di aggiornare una cella calcolata non trovata.");
    }
}

// Aggiorna la funzione updateAllDifferentials per gestire entrambe le tabelle
function updateAllDifferentials() {
    // --- Libro Energie ---
    const righeEnergie = document.querySelectorAll('#libro_energie table tbody tr');
    // Modifica: Itera su TUTTE le righe, non fino a length - 1, perché la somma non dipende dalla riga successiva
    for (let i = 0; i < righeEnergie.length; i++) {
        const rigaCorrente = righeEnergie[i];
        // Passa 'all' per calcolare sia pos che neg, e l'ID della tabella
        updateRowDifferentials(rigaCorrente, i, 'all', 'libro_energie');
    }

    // --- Libro Kaifa ---
    const righeKaifa = document.querySelectorAll('#libro_kaifa table tbody tr');
    // Per Kaifa, iteriamo ancora fino a length - 1 perché il calcolo della differenza necessita della riga successiva
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

// Funzione per forzare l'aggiornamento dei totali Kaifa
function forceUpdateKaifaTotals() {
    console.log('Inizio calcolo forzato totali Kaifa...');
    const tabella = document.getElementById('libro_kaifa');
    if (!tabella) {
        console.error('Tabella Kaifa non trovata!');
        return false; // Restituisci false in caso di errore
    }
    
    const righe = tabella.querySelectorAll('tbody tr');
    
    // Esegui immediatamente senza setTimeout per garantire sincronicità
    try {
        // Calcola i totali per ogni coppia di righe
        for (let i = 0; i < righe.length - 1; i++) {
            const rigaCorrente = righe[i];
            const rigaSuccessiva = righe[i + 1];
            const mese = rigaCorrente.dataset.mese;
            
            // Lettura valori 1.8.0.n
            const kaifa180nCorrente = parseNumericValue(rigaCorrente.querySelector('td[data-field="kaifa_180n"]'));
            const kaifa180nSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="kaifa_180n"]'));
            let differenza180n = kaifa180nSuccessiva - kaifa180nCorrente;
            
            // Lettura valori 2.8.0.n
            const kaifa280nCorrente = parseNumericValue(rigaCorrente.querySelector('td[data-field="kaifa_280n"]'));
            const kaifa280nSuccessiva = parseNumericValue(rigaSuccessiva.querySelector('td[data-field="kaifa_280n"]'));
            let differenza280n = kaifa280nSuccessiva - kaifa280nCorrente;
            
            // Aggiorna le celle dei totali in modo più diretto
            const totale180nCell = rigaCorrente.querySelector('td[data-field="totale_180n"]');
            const totale280nCell = rigaCorrente.querySelector('td[data-field="totale_280n"]');
            
            if (totale180nCell) {
                // Usa un metodo più diretto senza animazioni o altre operazioni
                totale180nCell.textContent = formatNumericValue(differenza180n);
                totale180nCell.dataset.value = differenza180n;
                console.log(`Mese ${mese}: totale_180n impostato a ${differenza180n}, textContent="${totale180nCell.textContent}", dataset.value=${totale180nCell.dataset.value}`);
            }
            
            if (totale280nCell) {
                // Usa un metodo più diretto senza animazioni o altre operazioni
                totale280nCell.textContent = formatNumericValue(differenza280n);
                totale280nCell.dataset.value = differenza280n;
                console.log(`Mese ${mese}: totale_280n impostato a ${differenza280n}, textContent="${totale280nCell.textContent}", dataset.value=${totale280nCell.dataset.value}`);
            }
        }
        
        // L'ultima riga non ha totali
        const ultimaRiga = righe[righe.length - 1];
        if (ultimaRiga) {
            const totale180nCellUltima = ultimaRiga.querySelector('td[data-field="totale_180n"]');
            const totale280nCellUltima = ultimaRiga.querySelector('td[data-field="totale_280n"]');
            if (totale180nCellUltima) {
                totale180nCellUltima.textContent = '';
                delete totale180nCellUltima.dataset.value;
            }
            if (totale280nCellUltima) {
                totale280nCellUltima.textContent = '';
                delete totale280nCellUltima.dataset.value;
            }
        }
        
        console.log('Calcolo forzato totali Kaifa completato con successo.');
        return true; // Restituisci true se il calcolo è riuscito
    } catch (error) {
        console.error('Errore durante il calcolo forzato dei totali Kaifa:', error);
        return false; // Restituisci false in caso di errore
    }
}

// Funzione per controllare se ci sono totali validi nei dati
function checkTotaliKaifa(dati) {
    let totaliValidi = false;
    let messaggioDiagnostica = "Diagnostica totali Kaifa:\n";
    
    dati.forEach(row => {
        if (row.mese !== '13') { // Escludi l'ultimo mese che non ha totali
            const totale180nPresente = row.totale_180n !== null && row.totale_180n !== undefined;
            const totale280nPresente = row.totale_280n !== null && row.totale_280n !== undefined;
            
            messaggioDiagnostica += `Mese ${row.mese}: `;
            messaggioDiagnostica += totale180nPresente ? `1.8.0.n=${row.totale_180n} ✓ ` : "1.8.0.n=assente ✘ ";
            messaggioDiagnostica += totale280nPresente ? `2.8.0.n=${row.totale_280n} ✓` : "2.8.0.n=assente ✘";
            messaggioDiagnostica += "\n";
            
            if (totale180nPresente || totale280nPresente) {
                totaliValidi = true;
            }
        }
    });
    
    return {
        validi: totaliValidi,
        messaggio: messaggioDiagnostica
    };
}

// Nuova funzione per estrarre la logica di salvataggio, migliorata per Kaifa
function salvaDati(saveButton, tipoContatore, datiTabella, csrfToken) {
    // Log per debug
    console.log('Tipo tabella rilevato:', tipoContatore);
    console.log('Dati raccolti:', datiTabella.length, 'righe');
    
    // Verifica che ci siano dati da salvare
    if (!datiTabella || datiTabella.length === 0) {
        alert('Errore: Nessun dato da salvare.');
        return;
    }
    
    // Verifica token CSRF
    if (!csrfToken) {
        alert('Errore: Token CSRF non trovato. Impossibile procedere con il salvataggio.');
        return;
    }
    
    // Per Kaifa, verifica che i totali siano presenti e validi
    if (tipoContatore === 'libro_kaifa') {
        const checkTotali = checkTotaliKaifa(datiTabella);
        console.log(checkTotali.messaggio);
        
        if (!checkTotali.validi) {
            const rispostaDiagnostica = confirm('ATTENZIONE: Non sono stati rilevati totali validi nei dati Kaifa.\n\n' + 
                                               'Questo potrebbe causare un salvataggio incompleto.\n\n' +
                                               'Vuoi vedere i dettagli diagnostici e continuare?');
            
            if (rispostaDiagnostica) {
                alert(checkTotali.messaggio + '\n\nVerrà effettuato un nuovo tentativo di calcolo dei totali.');
                
                // Forza un nuovo calcolo più aggressivo dei totali
                forceUpdateKaifaTotals();
                
                // Raccogli nuovamente i dati dopo il nuovo calcolo
                const contatoreId = datiTabella[0].contatore_id;
                const anno = datiTabella[0].anno;
                datiTabella = raccogliDatiLibroKaifa(contatoreId, anno);
                
                // Verifica nuovamente
                const nuovoCheck = checkTotaliKaifa(datiTabella);
                if (!nuovoCheck.validi) {
                    if (!confirm('I totali sembrano ancora mancanti. Continuare comunque con il salvataggio?')) {
                        return; // Annulla il salvataggio
                    }
                }
            } else {
                return; // Annulla il salvataggio
            }
        }
    }
    
    // Prepara i dati da inviare
    const datiDaInviare = {
        tipo_tabella: tipoContatore,
        rows: datiTabella
    };
    
    // Log del corpo completo della richiesta per debug
    console.log('Dati completi da inviare:', JSON.stringify(datiDaInviare));
    
    // Mostra un indicatore di caricamento
    saveButton.disabled = true;
    saveButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Salvataggio in corso...';
    
    // Salvataggio temporaneo dei dati in localStorage in caso di errore
    localStorage.setItem('last_save_attempt', JSON.stringify(datiDaInviare));
    
    // Invia i dati al server
    fetch('/automazione-dati/salva-dati-letture/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(datiDaInviare)
    })
    .then(response => {
        console.log('Risposta server ricevuta:', response.status, response.statusText);
        if (!response.ok) {
            throw new Error('Errore nella risposta del server: ' + response.status + ' ' + response.statusText);
        }
        return response.json();
    })
    .then(data => {
        console.log('Dati ricevuti dal server:', data);
        if (data.status === 'success') {
            alert('Dati salvati con successo!');
            // Aggiorna i dati visualizzati con quelli salvati
            if (tipoContatore === 'libro_energie') {
                aggiornaTabellaDatiEnergie(data.rows);
            } else if (tipoContatore === 'libro_kaifa') {
                aggiornaTabellaDatiKaifa(data.rows);
            }
            // Rimuovi i dati di backup
            localStorage.removeItem('last_save_attempt');
        } else {
            alert('Errore durante il salvataggio: ' + data.message);
            console.error('Errore server:', data);
        }
    })
    .catch(error => {
        console.error('Errore durante la richiesta:', error);
        alert('Si è verificato un errore durante il salvataggio dei dati: ' + error.message + 
              '\n\nI dati sono stati salvati temporaneamente nel browser. ' +
              'Contattare l\'amministratore per assistenza.');
    })
    .finally(() => {
        // Ripristina il pulsante di salvataggio
        saveButton.disabled = false;
        saveButton.innerHTML = '<i class="bi bi-save"></i> Salva';
    });
}

// Funzione per alternare tra visualizzazione completa e solo totali
function toggleColumnSums() {
    // Ottieni lo stato corrente
    const showDetailsElement = document.getElementById('show-details');
    const showDetails = showDetailsElement ? showDetailsElement.value === 'true' : true;
    
    // Ottieni tutte le colonne di dettaglio in entrambe le tabelle
    const detailColumnsEnergie = document.querySelectorAll('#libro_energie table th[data-column-type="detail"], #libro_energie table td[data-field^="a"]');
    const detailColumnsKaifa = document.querySelectorAll('#libro_kaifa table th[data-column-type="detail"], #libro_kaifa table td[data-field^="kaifa_"]');
    
    // Ottieni il pulsante toggle
    const toggleButton = document.getElementById('toggle-sums-button');
    
    // Cambia lo stato
    const newShowDetails = !showDetails;
    
    // Aggiorna la visualizzazione delle colonne
    const displayValue = newShowDetails ? 'table-cell' : 'none';
    
    detailColumnsEnergie.forEach(col => {
        col.style.display = displayValue;
    });
    
    detailColumnsKaifa.forEach(col => {
        col.style.display = displayValue;
    });
    
    // Aggiorna il testo del pulsante
    if (toggleButton) {
        toggleButton.innerHTML = newShowDetails ? 
            '<i class="bi bi-eye-slash"></i> Mostra solo totali' : 
            '<i class="bi bi-eye"></i> Mostra dettagli';
    }
    
    // Memorizza lo stato
    if (showDetailsElement) {
        showDetailsElement.value = newShowDetails.toString();
    } else {
        // Crea l'elemento se non esiste
        const stateElement = document.createElement('input');
        stateElement.type = 'hidden';
        stateElement.id = 'show-details';
        stateElement.value = newShowDetails.toString();
        document.body.appendChild(stateElement);
    }
    
    // Aggiorna anche i titoli delle tabelle
    const tableHeaders = document.querySelectorAll('.table-title');
    tableHeaders.forEach(header => {
        if (newShowDetails) {
            header.classList.remove('only-totals');
        } else {
            header.classList.add('only-totals');
        }
    });
    
    console.log(`Visualizzazione cambiata: ${newShowDetails ? 'dettagli visibili' : 'solo totali'}`);
}

// Funzione per inizializzare il pulsante toggle
function setupToggleSumsButton() {
    // Cerca un container esistente per i pulsanti
    const buttonContainer = document.querySelector('.button-container') || document.querySelector('.controls');
    
    if (!buttonContainer) {
        console.warn('Contenitore pulsanti non trovato, creazione nuovo container');
        // Crea un nuovo container se non esiste
        const newContainer = document.createElement('div');
        newContainer.className = 'button-container mt-3 mb-3';
        
        // Inserisci il container prima della prima tabella
        const firstTable = document.querySelector('#libro_energie') || document.querySelector('#libro_kaifa');
        if (firstTable && firstTable.parentNode) {
            firstTable.parentNode.insertBefore(newContainer, firstTable);
        } else {
            document.body.appendChild(newContainer);
        }
        
        // Usa il nuovo container
        setupToggleButton(newContainer);
    } else {
        // Usa il container esistente
        setupToggleButton(buttonContainer);
    }
    
    // Imposta gli attributi data-column-type necessari
    setupColumnAttributes();
}

// Funzione helper per creare il pulsante
function setupToggleButton(container) {
    // Crea il pulsante
    const toggleButton = document.createElement('button');
    toggleButton.id = 'toggle-sums-button';
    toggleButton.className = 'btn btn-outline-primary me-2';
    toggleButton.innerHTML = '<i class="bi bi-eye-slash"></i> Mostra solo totali';
    toggleButton.addEventListener('click', toggleColumnSums);
    
    // Aggiungi il pulsante al container
    container.appendChild(toggleButton);
    
    // Aggiungi stili CSS per la visualizzazione "solo totali"
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        .only-totals::after {
            content: " (Solo Totali)";
            font-style: italic;
            color: #666;
        }
    `;
    document.head.appendChild(styleElement);
}

// Funzione per impostare gli attributi data-column-type su intestazioni e celle
function setupColumnAttributes() {
    // Per Libro Energie
    const thEnergie = document.querySelectorAll('#libro_energie table th');
    thEnergie.forEach(th => {
        const headerText = th.textContent.trim().toLowerCase();
        if (headerText.includes('a1') || headerText.includes('a2') || headerText.includes('a3')) {
            th.setAttribute('data-column-type', 'detail');
        } else if (headerText.includes('totale')) {
            th.setAttribute('data-column-type', 'total');
        }
    });
    
    // Per Libro Kaifa
    const thKaifa = document.querySelectorAll('#libro_kaifa table th');
    thKaifa.forEach(th => {
        const headerText = th.textContent.trim().toLowerCase();
        if (headerText.includes('1.8.0') || headerText.includes('2.8.0')) {
            th.setAttribute('data-column-type', 'detail');
        } else if (headerText.includes('totale')) {
            th.setAttribute('data-column-type', 'total');
        }
    });
}

// Funzione migliorata per convertire date in formato ISO e gestire l'ora
function convertDateToISO(dateString) {
    if (!dateString || dateString.trim() === '') {
        return null;
    }
    
    // Separa data e ora se presenti
    let datePart = dateString;
    let timePart = null;
    
    if (dateString.includes(' ')) {
        const parts = dateString.split(' ');
        datePart = parts[0];
        timePart = parts.length > 1 ? parts[1] : null;
    }
    
    // Converti la parte data
    let isoDate = null;
    
    // Prova formato italiano GG/MM/AAAA
    if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(datePart)) {
        const parts = datePart.split('/');
        if (parts.length === 3) {
            const day = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10);
            const year = parseInt(parts[2], 10);
            
            // Verifica validità data
            if (day >= 1 && day <= 31 && month >= 1 && month <= 12) {
                isoDate = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
            }
        }
    }
    
    // Restituisci oggetto con data ISO e ora
    return {
        date: isoDate,
        time: timePart && /^\d{1,2}:\d{1,2}$/.test(timePart) ? timePart : null
    };
}

