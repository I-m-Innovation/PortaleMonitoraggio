document.addEventListener('DOMContentLoaded', function() {
    const yearSelect = document.getElementById('year-select');
    
    // Funzione che aggiorna i nomi dei mesi in entrambe le tabelle
    function updateMonths() {
        const selectedYear = yearSelect.value;
        // Estraiamo le ultime due cifre dell'anno (ad esempio "2024" -> "24")
        const yearSuffix = selectedYear.toString().substr(2);
        
        // Creiamo la chiave per il localStorage: es. "months-2024"
        const storageKey = 'months-' + selectedYear;
        
        // Proviamo a recuperare i dati già salvati
        let monthsData = localStorage.getItem(storageKey);
        
        if (!monthsData) {
            console.log("Dati dei mesi non presenti in cache. Creazione dei dati per l'anno " + selectedYear);
            // Array dei nomi base dei mesi
            const baseMonths = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];
            // Aggiungiamo il suffisso dell'anno ad ogni mese
            const updatedMonths = baseMonths.map(mese => mese + '-' + yearSuffix);
            
            // Salviamo l'array (in formato JSON) nel localStorage
            localStorage.setItem(storageKey, JSON.stringify(updatedMonths));
            monthsData = JSON.stringify(updatedMonths);
        } else {
            console.log("Dati in cache trovati per l'anno " + selectedYear);
        }
        
        // Converto la stringa JSON in un array
        const loadedMonths = JSON.parse(monthsData);
        
        // Aggiorna le celle della prima colonna (nomi dei mesi)
        const tBodies = document.querySelectorAll('.table-content table tbody');
        tBodies.forEach(tbody => {
            const rows = tbody.querySelectorAll('tr');
            rows.forEach((row, index) => {
                const cell = row.querySelector('td:first-child');
                if (cell && index < loadedMonths.length) {
                    cell.textContent = loadedMonths[index];
                }
            });
        });
    }
    
    // Listener per evento "change" sul menu a tendina dell'anno
    yearSelect.addEventListener('change', updateMonths);
    
    // Aggiorniamo subito i mesi al caricamento della pagina
    updateMonths();
    
    // --- Inizio: Rendi le celle editabili ---
    
    // Seleziono tutte le celle <td> all'interno dei <tbody> delle tabelle
    const tableCells = document.querySelectorAll('.table-content table tbody tr td');
    tableCells.forEach(cell => {
        // Escludo la prima cella della riga (contenente il nome del mese)
        const firstCell = cell.parentElement.querySelector('td:first-child');
        if (cell !== firstCell) {
            // Rende la cella modificabile
            cell.setAttribute('contenteditable', 'true');
    
            // Memorizzo il valore originale al momento del focus
            cell.addEventListener('focus', function() {
                cell.dataset.oldValue = cell.innerHTML;
            });
            
            // Appena l'utente inizia a digitare, aggiungo la classe "editing" per il feedback visivo
            cell.addEventListener('input', function() {
                cell.classList.add('editing');
            });
    
            // Quando l'editing termina (blur), rimuovo la classe "editing" e, se il contenuto è cambiato,
            // aggiungo la classe "modified"
            cell.addEventListener('blur', function() {
                cell.classList.remove('editing');
                if (cell.innerHTML.trim() !== cell.dataset.oldValue.trim()) {
                    cell.classList.add('modified');
                } else {
                    cell.classList.remove('modified');
                }
            });
        }
    });
    
    // --- Fine: Rendi le celle editabili ---
});