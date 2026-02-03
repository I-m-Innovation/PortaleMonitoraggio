document.addEventListener('DOMContentLoaded', function() {
    // Seleziona l'elemento <select> con l'ID 'year-select'
    const yearSelect = document.getElementById('year-select');

    // Verifica che l'elemento esista prima di aggiungere un event listener
    if (yearSelect) {
        // Aggiunge un 'ascoltatore di eventi' che si attiva quando il valore selezionato cambia
        yearSelect.addEventListener('change', function(event) {
            // Ottiene il valore dell'anno selezionato (es. "2023")
            const selectedYear = event.target.value;
            
            // Crea un oggetto URL basato sull'indirizzo web corrente della pagina
            // Questo ci permette di manipolare facilmente i parametri della query string (la parte dopo '?')
            const currentUrl = new URL(window.location.href);

            // Imposta (o aggiorna se già esistente) il parametro 'year' nella query string
            // con il valore dell'anno selezionato.
            // Ad esempio, se l'URL era "pagina.htIlml?contatore_id=1" e selectedYear è "2022",
            // diventerà "pagina.html?contatore_id=1&year=2022".
            // Se era "pagina.html?year=2023", diventerà "pagina.html?year=2022".
            currentUrl.searchParams.set('year', selectedYear);

            // Mostra un messaggio di caricamento (opzionale)
            console.log(`Caricamento dati per l'anno ${selectedYear}...`);

            // Ricarica la pagina navigando verso il nuovo URL costruito.
            // Questo farà sì che il server Django riceva la richiesta con il nuovo anno
            // e la vista 'diarioenergie' possa caricare i dati corretti.
            window.location.href = currentUrl.toString();
        });
    }

    // Funzione per evidenziare visivamente l'anno attualmente selezionato
    function highlightCurrentYear() {
        if (yearSelect) {
            // Ottieni l'anno corrente dalla URL o dal valore selezionato
            const urlParams = new URLSearchParams(window.location.search);
            const currentYear = urlParams.get('year') || new Date().getFullYear().toString();
            
            // Imposta il valore selezionato nel dropdown
            yearSelect.value = currentYear;
            
            // Aggiungi una classe CSS per evidenziare (opzionale)
            yearSelect.classList.add('year-selected');
        }
    }

    // Chiama la funzione per evidenziare l'anno corrente al caricamento della pagina
    highlightCurrentYear();

    // Aggiungi un event listener per il pulsante di salvataggio se esiste
    const saveButton = document.getElementById('diarioenergie_save');
    if (saveButton) {
        saveButton.addEventListener('click', async function() {
            console.log('Tentativo di salvataggio dati...');
            
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const table = document.getElementById('diarioenergie');
            const contatoreId = table.dataset.contatoreId;
            const annoCorrente = yearSelect.value; // Anno attualmente selezionato

            const modifiedData = [];
            const rows = table.querySelectorAll('tbody tr[data-mese]');
            
            rows.forEach(row => {
                const meseNumero = row.dataset.mese;
                const rowData = { mese_numero: meseNumero };
                
                // Raccogli solo i dati delle celle editabili
                row.querySelectorAll('td[contenteditable="true"]').forEach(cell => {
                    const field = cell.dataset.field;
                    let value = cell.textContent.trim();
                    // Converti in numero se il tipo di dato è numerico e non è vuoto
                    if (cell.dataset.type === 'number' && value !== '') {
                        value = parseFloat(value.replace(',', '.')); // Sostituisci virgola con punto per i decimali
                        if (isNaN(value)) {
                            value = null; // Imposta a null se non è un numero valido
                        }
                    } else if (value === '') {
                        value = null; // Imposta a null se la cella è vuota
                    }
                    rowData[field] = value;
                });
                modifiedData.push(rowData);
            });
            
            console.log('Dati da salvare:', modifiedData);

            try {
                const response = await fetch('/automazione-dati/api/salva_diario_energie/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({
                        contatore_id: contatoreId,
                        anno: annoCorrente,
                        dati_mensili: modifiedData
                    })
                });

                const result = await response.json();

                if (response.ok) {
                    showNotification(result.message || 'Dati salvati con successo!', 'success');
                    // Aggiorna la pagina dopo il salvataggio per ricaricare i dati da DB
                    window.location.reload(); 
                } else {
                    showNotification(result.error || 'Errore durante il salvataggio dei dati.', 'danger');
                }
            } catch (error) {
                console.error('Errore nella richiesta di salvataggio:', error);
                showNotification('Si è verificato un errore di rete o del server.', 'danger');
            }
            
            // Rimuovi il feedback visivo temporaneo, sarà ricaricato con il reload
            saveButton.textContent = 'Salva';
            saveButton.classList.remove('btn-success');
        });
    }

    // Funzione di utilità per mostrare notifiche all'utente
    function showNotification(message, type = 'info') {
        // Crea un elemento di notifica temporaneo
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Rimuovi automaticamente dopo 3 secondi
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    // Aggiungi un event listener per gestire eventuali errori durante il caricamento
    window.addEventListener('error', function(event) {
        console.error('Errore durante il caricamento dei dati:', event.error);
        showNotification('Errore durante il caricamento dei dati. Riprova.', 'danger');
    });
});
