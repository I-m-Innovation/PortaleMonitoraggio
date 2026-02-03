document.addEventListener('DOMContentLoaded', function() {
    // Trova tutti gli elementi con classe js-data invece di solo il primo
    const dataElements = document.querySelectorAll('.js-tabella-data');
    if (!dataElements || dataElements.length === 0) {
        console.error('Nessun elemento con i dati necessari trovato');
        return;
    }
    
    // Itera su tutti gli elementi trovati
    dataElements.forEach(function(dataElement) {
        const anno = dataElement.getAttribute('data-anno');
        const nickname = dataElement.getAttribute('data-nickname');
        
        // Carica i dati per questo anno
        caricaDatiTabella2(anno, nickname);
        
        // Aggiungi event listener per il pulsante di aggiornamento
        const refreshButton = document.getElementById('refresh-table2-data-' + anno);
        if (refreshButton) {
            refreshButton.addEventListener('click', function() {
                caricaDatiTabella2(anno, nickname);
            });
        } else {
            console.warn(`Elemento con ID 'refresh-table2-data-${anno}' non trovato.`);
        }
    });
});

// Carica dati misure per anno/nickname da API e popola tabella
function caricaDatiTabella2(anno, nickname) {
    const loadingAlertId = 'loading-alert-' + anno;
    const successAlertId = 'success-table2-alert-' + anno;
    const errorAlertId = 'error-table2-alert-' + anno;

    const loadingAlert = document.getElementById(loadingAlertId);
    const successAlert = document.getElementById(successAlertId);
    const errorAlert = document.getElementById(errorAlertId);

    // Mostra l'alert di caricamento
    if (loadingAlert) {
        loadingAlert.style.display = 'block';
    } else {
        console.warn(`Elemento con ID '${loadingAlertId}' non trovato.`);
    }
    
    // Nasconde gli alert precedenti
    if (successAlert) {
        successAlert.style.display = 'none';
    } else {
        console.warn(`Elemento con ID '${successAlertId}' non trovato.`);
    }
    if (errorAlert) {
        errorAlert.style.display = 'none';
    } else {
        console.warn(`Elemento con ID '${errorAlertId}' non trovato.`);
    }
    
    // Effettua la richiesta AJAX per ottenere i dati
    fetch(`/corrispettivi/api/misure/${anno}_${nickname}/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Errore nella risposta del server');
            }
            return response.json();
        })
        .then(data => {
            // Popola la tabella con i dati ricevuti
            popolaTabella2(data.TableMisure, anno);
            
            // Nascondi l'alert di caricamento e mostra quello di successo
            if (loadingAlert) {
                loadingAlert.style.display = 'none';
            }
            if (successAlert) {
                successAlert.style.display = 'block';
            }
            
            // Nascondi l'alert di successo dopo 3 secondi
            setTimeout(() => {
                if (successAlert) {
                    successAlert.style.display = 'none';
                }
            }, 3000);
        })
        .catch(error => {
            console.error('Errore:', error);
            
            // Nascondi l'alert di caricamento e mostra quello di errore
            if (loadingAlert) {
                loadingAlert.style.display = 'none';
            }
            if (errorAlert) {
                errorAlert.style.display = 'block';
            }
        });
}

// Funzione per popolare la tabella con i dati
function popolaTabella2(dati, anno) {
    const mesiNomi = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 
                     'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];
    
    // Totali per i calcoli finali
    let totali = {
        prod_campo: 0, imm_campo: 0, prel_campo: 0,
        prod_ed: 0, imm_ed: 0, prel_ed: 0,
        prod_gse: 0, imm_gse: 0
    };
    
    // Popola le celle della tabella con i dati
    for (let i = 0; i < dati.length; i++) {
        const dato = dati[i];
        const mese = dato.mese;
        const meseIndex = mese - 1;
        
        // Ottieni gli elementi con selettore sicuro
        try {
            // Imposta il nome del mese
            const meseElement = document.querySelector(`#table2_${anno} .mese[data-mese="${mese}"]`);
            if (meseElement) meseElement.textContent = mesiNomi[meseIndex];
            
            // Imposta i valori per ogni cella
            const prodCampoElement = document.querySelector(`#table2_${anno} .prod-campo[data-mese="${mese}"]`);
            if (prodCampoElement) prodCampoElement.textContent = dato.prod_campo || '';
            
            const immCampoElement = document.querySelector(`#table2_${anno} .imm-campo[data-mese="${mese}"]`);
            if (immCampoElement) immCampoElement.textContent = dato.imm_campo || '';
            
            const prelCampoElement = document.querySelector(`#table2_${anno} .prel-campo[data-mese="${mese}"]`);
            if (prelCampoElement) prelCampoElement.textContent = dato.prel_campo || '';
            
            const prodEdElement = document.querySelector(`#table2_${anno} .prod-ed[data-mese="${mese}"]`);
            if (prodEdElement) prodEdElement.textContent = dato.prod_ed || '';
            
            const immEdElement = document.querySelector(`#table2_${anno} .imm-ed[data-mese="${mese}"]`);
            if (immEdElement) immEdElement.textContent = dato.imm_ed || '';
            
            const prelEdElement = document.querySelector(`#table2_${anno} .prel-ed[data-mese="${mese}"]`);
            if (prelEdElement) prelEdElement.textContent = dato.prel_ed || '';
            
            const prodGseElement = document.querySelector(`#table2_${anno} .prod-gse[data-mese="${mese}"]`);
            if (prodGseElement) prodGseElement.textContent = dato.prod_gse || '';
            
            const immGseElement = document.querySelector(`#table2_${anno} .imm-gse[data-mese="${mese}"]`);
            if (immGseElement) immGseElement.textContent = dato.imm_gse || '';
            
            // Controllo misure con indicatori di differenza percentuale
            let controlloHTML = '';
            if (dato.prod_campo && dato.prod_ed) {
                const diffProd = ((parseFloat(dato.prod_campo) - parseFloat(dato.prod_ed)) / parseFloat(dato.prod_ed) * 100).toFixed(2);
                controlloHTML += `<i class="fa fa-bolt" aria-hidden="true"></i> ${diffProd}%<br>`;
            }
            
            if (dato.imm_campo && dato.imm_ed) {
                const diffImm = ((parseFloat(dato.imm_campo) - parseFloat(dato.imm_ed)) / parseFloat(dato.imm_ed) * 100).toFixed(2);
                controlloHTML += `<i class="fa fa-share" aria-hidden="true"></i> ${diffImm}%`;
            }
            
            const controlloElement = document.querySelector(`#table2_${anno} .controllo[data-mese="${mese}"]`);
            if (controlloElement) controlloElement.innerHTML = controlloHTML;
        } catch (error) {
            console.error(`Errore durante l'elaborazione del mese ${mese}:`, error);
        }
        
        // Aggiorna i totali
        totali.prod_campo += parseFloat(dato.prod_campo || 0);
        totali.imm_campo += parseFloat(dato.imm_campo || 0);
        totali.prel_campo += parseFloat(dato.prel_campo || 0);
        totali.prod_ed += parseFloat(dato.prod_ed || 0);
        totali.imm_ed += parseFloat(dato.imm_ed || 0);
        totali.prel_ed += parseFloat(dato.prel_ed || 0);
        totali.prod_gse += parseFloat(dato.prod_gse || 0);
        totali.imm_gse += parseFloat(dato.imm_gse || 0);
    }
    
    // Aggiorna i totali nella tabella in modo sicuro
    try {
        const totProdCampoElement = document.querySelector(`#table2_${anno} .totale-prod-campo`);
        if (totProdCampoElement) totProdCampoElement.textContent = totali.prod_campo.toFixed(3);
        
        const totImmCampoElement = document.querySelector(`#table2_${anno} .totale-imm-campo`);
        if (totImmCampoElement) totImmCampoElement.textContent = totali.imm_campo.toFixed(3);
        
        const totPrelCampoElement = document.querySelector(`#table2_${anno} .totale-prel-campo`);
        if (totPrelCampoElement) totPrelCampoElement.textContent = totali.prel_campo.toFixed(3);
        
        const totProdEdElement = document.querySelector(`#table2_${anno} .totale-prod-ed`);
        if (totProdEdElement) totProdEdElement.textContent = totali.prod_ed.toFixed(3);
        
        const totImmEdElement = document.querySelector(`#table2_${anno} .totale-imm-ed`);
        if (totImmEdElement) totImmEdElement.textContent = totali.imm_ed.toFixed(3);
        
        const totPrelEdElement = document.querySelector(`#table2_${anno} .totale-prel-ed`);
        if (totPrelEdElement) totPrelEdElement.textContent = totali.prel_ed.toFixed(3);
        
        const totProdGseElement = document.querySelector(`#table2_${anno} .totale-prod-gse`);
        if (totProdGseElement) totProdGseElement.textContent = totali.prod_gse.toFixed(3);
        
        const totImmGseElement = document.querySelector(`#table2_${anno} .totale-imm-gse`);
        if (totImmGseElement) totImmGseElement.textContent = totali.imm_gse.toFixed(3);
    } catch (error) {
        console.error('Errore durante l\'aggiornamento dei totali:', error);
    }
}