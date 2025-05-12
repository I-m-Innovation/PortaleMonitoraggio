$(document).ready(function() {
    // Aggiungere questo per il debug
    console.log("URL base della pagina:", window.location.origin);
    console.log("Percorso della pagina:", window.location.pathname);
    
    // Ottieni tutti gli anni disponibili dalle tabelle nella pagina
    const anni = [];
    $('table[id^="table1_"]').each(function() {
        const anno = $(this).attr('id').split('_')[1];
        anni.push(anno);
        console.log("Trovata tabella per l'anno:", anno);
    });
    
    // Costanti TFO per impianto (€/kWh)
    const TFO_RATES = {
        'ionico_foresta': 0.21,
        'san_teodoro': 0.21,
        'ponte_giurino': 0.21,
        'petilia_bf_partitore': 0.21
        // Aggiungi altri impianti secondo necessità
    };
    
    // Ottieni il nickname dell'impianto dal percorso URL
    const nickname = window.location.pathname.split('/').filter(segment => segment).pop();
    
    // Imposta il tasso TFO per questo impianto
    const tfoRate = TFO_RATES[nickname] || 0.21; // Default a 0.21 se non trovato
    
    // Mostra il tasso TFO nell'header della tabella
    $('.tfo-rate-indicator').text(` (${tfoRate} €/kWh)`);
    
    // Inizializzazione per ogni anno
    anni.forEach(function(anno) {
        caricaDatiTabella(anno);
        
        // Aggiungi event listener per salvare i dati
        $(`#save-table-data-${anno}`).on('click', function() {
            salvaDatiTabella(anno);
        });
    });
    
    // Aggiungi event listener per il calcolo dei controlli
    $(document).on('input', '.table-input', function() {
        const tableId = $(this).closest('table').attr('id');
        const anno = tableId.split('_')[1];
        calcolaControlli(anno);
        calcolaTotali(anno);
    });
    
    // Aggiungi event listener per il calcolo TFO quando cambia l'energia
    $(document).on('input', '.energy-input', function() {
        const mese = $(this).data('mese');
        const anno = $(this).closest('table').attr('id').split('_')[1];
        const energia = parseFloat($(this).val()) || 0;
        const prodCampoOriginale = parseFloat($(this).attr('data-prod-campo')) || 0; // Usa il valore originale salvato
        
        // Calcola il valore TFO
        const tfoValue = energia * tfoRate;
        
        // Aggiorna la cella TFO
        $(`#table1_${anno} .tfo-value[data-mese="${mese}"]`).text(tfoValue.toFixed(2));
        
        // Aggiorna automaticamente anche il campo corrispettivo_incentivo per mantenere la consistenza dei dati
        $(`#table1_${anno} input[data-mese="${mese}"][data-campo="corrispettivo_incentivo"]`).val(tfoValue.toFixed(2));

        // Calcola e aggiorna il valore PUN
        const media_pun_mensile_attr = $(this).attr('data-media-pun'); // Leggi l'attributo data
        let valorePUN = 0;
        if (media_pun_mensile_attr !== undefined && media_pun_mensile_attr !== null && !isNaN(parseFloat(media_pun_mensile_attr))) {
            const media_pun_mensile = parseFloat(media_pun_mensile_attr);
            if (!isNaN(media_pun_mensile)) {
                // Usa prodCampoOriginale per calcolare il PUN
                valorePUN = (prodCampoOriginale * 0.02) * media_pun_mensile;
            }
        }
        $(`#table1_${anno} .pun-value[data-mese="${mese}"]`).text(valorePUN.toFixed(3)); // Formattato a 3 decimali
        
        // Ricalcola controlli e totali
        calcolaControlli(anno);
        calcolaTotali(anno);
    });
    
    function caricaDatiTabella(anno) {
        const nickname = window.location.pathname.split('/').filter(segment => segment).pop();
        
        // Modifichiamo il percorso per allinearlo con la configurazione del server
        $.ajax({
            url: '/corrispettivi/api/dati-mensili-tabella/',
            method: 'GET',
            data: {
                impianto: nickname,
                anno: anno
            },
            success: function(response) {
                if (response.success) {
                    // Popola la tabella con i dati ricevuti
                    popolaTabella(response.data, anno);
                    calcolaControlli(anno);
                    calcolaTotali(anno);
                } else {
                    console.error(`Errore durante il caricamento dei dati per l'anno ${anno}:`, response.error);
                }
            },
            error: function(error) {
                console.error(`Errore durante la richiesta dei dati per l'anno ${anno}:`, error);
            }
        });
    }
    
    function popolaTabella(dati, anno) {
        // Resetta i campi della tabella per l'anno specifico
        $(`#table1_${anno} .table-input`).val('');
        $(`#table1_${anno} .tfo-value`).text('');
        $(`#table1_${anno} .pun-value`).text(''); // Resetta anche le celle PUN
        
        // Popola i campi con i dati ricevuti
        dati.forEach(function(dato) {
            const energia = parseFloat(dato.energia_kwh) || 0;
            const prodCampoOriginale = parseFloat(dato.prod_campo_originale) || 0; // Valore originale di prod_campo
            const tfoValue = energia * tfoRate;
            
            // Memorizza la media PUN e il valore prod_campo sull'input energia per ricalcoli
            const media_pun_mensile = parseFloat(dato.media_pun_mensile);
            const energyInputElement = $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="energia_kwh"]`);
            
            if (!isNaN(media_pun_mensile)) {
                energyInputElement.attr('data-media-pun', media_pun_mensile); // Salva come attributo data
            } else {
                energyInputElement.removeAttr('data-media-pun');
            }
            
            // Salva anche il valore originale di prod_campo
            energyInputElement.attr('data-prod-campo', prodCampoOriginale);

            let valorePUN = 0;
            if (!isNaN(media_pun_mensile)) {
                // Il calcolo PUN usa direttamente il 2% di prod_campo_originale
                valorePUN = (prodCampoOriginale * 0.02) * media_pun_mensile;
            }
            
            energyInputElement.val(dato.energia_kwh);
            $(`#table1_${anno} .tfo-value[data-mese="${dato.mese}"]`).text(tfoValue.toFixed(2));
            $(`#table1_${anno} .pun-value[data-mese="${dato.mese}"]`).text(valorePUN.toFixed(3)); // Popola cella PUN
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="corrispettivo_incentivo"]`).val(dato.corrispettivo_incentivo); // Questo potrebbe essere il TFO
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="corrispettivo_altro"]`).val(dato.corrispettivo_altro);
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="fatturazione_tfo"]`).val(dato.fatturazione_tfo);
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="fatturazione_altro"]`).val(dato.fatturazione_altro);
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="incassi"]`).val(dato.incassi);
        });
        
        // Calcola i valori TFO e PUN per i dati caricati (potrebbe essere ridondante se già fatto sopra, ma assicura consistenza)
        for (let mese = 1; mese <= 12; mese++) {
            const energiaInput = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="energia_kwh"]`);
            const energia = parseFloat(energiaInput.val()) || 0;
            
            const tfoValue = energia * tfoRate;
            $(`#table1_${anno} .tfo-value[data-mese="${mese}"]`).text(tfoValue.toFixed(2));

            const media_pun_mensile_attr = energiaInput.attr('data-media-pun');
            let valorePUN = 0;
            if (media_pun_mensile_attr !== undefined && media_pun_mensile_attr !== null && !isNaN(parseFloat(media_pun_mensile_attr))) {
                 const media_pun_mensile = parseFloat(media_pun_mensile_attr);
                 if(!isNaN(media_pun_mensile)){
                    valorePUN = (energia * 0.02) * media_pun_mensile;
                 }
            }
            $(`#table1_${anno} .pun-value[data-mese="${mese}"]`).text(valorePUN.toFixed(3));
        }
    }
    
    function salvaDatiTabella(anno) {
        const nickname = window.location.pathname.split('/').filter(segment => segment).pop();
        const dati = [];
        
        // Raccoglie i dati da tutti i mesi per l'anno specifico
        for (let mese = 1; mese <= 12; mese++) {
            const energia_kwh = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="energia_kwh"]`).val();
            const tfoValue = energia_kwh ? (parseFloat(energia_kwh) * tfoRate).toFixed(2) : null;
            const corrispettivo_altro = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="corrispettivo_altro"]`).val();
            const fatturazione_tfo = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_tfo"]`).val();
            const fatturazione_altro = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_altro"]`).val();
            const incassi = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="incassi"]`).val();
            
            // Salva solo se almeno un campo è compilato
            if (energia_kwh || corrispettivo_altro || fatturazione_tfo || fatturazione_altro || incassi) {
                dati.push({
                    mese: mese,
                    energia_kwh: energia_kwh || null,
                    corrispettivo_incentivo: tfoValue, // Usa il valore calcolato
                    corrispettivo_altro: corrispettivo_altro || null,
                    fatturazione_tfo: fatturazione_tfo || null,
                    fatturazione_altro: fatturazione_altro || null,
                    incassi: incassi || null
                });
            }
        }
        
        // Invia i dati al server
        $.ajax({
            url: '/corrispettivi/api/dati-mensili-tabella/',
            method: 'POST',
            data: {
                impianto: nickname,
                anno: anno,
                dati: JSON.stringify(dati),
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
            },
            success: function(response) {
                if (response.success) {
                    $(`#success-alert-${anno}`).fadeIn().delay(3000).fadeOut();
                    caricaDatiTabella(anno); // Ricarica i dati per aggiornare gli scarti e percentuali
                } else {
                    $(`#error-alert-${anno}`).text('Errore: ' + response.error).fadeIn().delay(5000).fadeOut();
                }
            },
            error: function(error) {
                $(`#error-alert-${anno}`).text('Errore durante il salvataggio dei dati.').fadeIn().delay(5000).fadeOut();
                console.error(`Errore durante il salvataggio dei dati per l'anno ${anno}:`, error);
            }
        });
    }
    
    function calcolaControlli(anno) {
        // Calcola gli scarti e le percentuali per ogni mese dell'anno specifico
        for (let mese = 1; mese <= 12; mese++) {
            const corrispettivo_incentivo = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="corrispettivo_incentivo"]`).val()) || 0;
            const corrispettivo_altro = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="corrispettivo_altro"]`).val()) || 0;
            const fatturazione_tfo = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_tfo"]`).val()) || 0;
            const fatturazione_altro = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_altro"]`).val()) || 0;
            
            const corrispettivi_totali = corrispettivo_incentivo + corrispettivo_altro;
            const fatturazione_totale = fatturazione_tfo + fatturazione_altro;
            
            const scarto = corrispettivi_totali - fatturazione_totale;
            let percentuale = 0;
            
            if (fatturazione_totale !== 0) {
                percentuale = (scarto / fatturazione_totale) * 100;
            }
            
            $(`#table1_${anno} .controllo-scarto[data-mese="${mese}"]`).text(scarto.toFixed(2));
            $(`#table1_${anno} .controllo-percentuale[data-mese="${mese}"]`).text(percentuale.toFixed(2) + '%');
            
            // Aggiungi classe per colorare le celle in base ai valori
            const controlloScartoCell = $(`#table1_${anno} .controllo-scarto[data-mese="${mese}"]`);
            const controlloPercentualeCell = $(`#table1_${anno} .controllo-percentuale[data-mese="${mese}"]`);
            
            // Reset classi
            controlloScartoCell.removeClass('text-danger text-success');
            controlloPercentualeCell.removeClass('text-danger text-success');
            
            // Applica colori
            if (Math.abs(scarto) > 0.01) {
                controlloScartoCell.addClass('text-danger');
            } else {
                controlloScartoCell.addClass('text-success');
            }
            
            if (Math.abs(percentuale) > 0.1) {
                controlloPercentualeCell.addClass('text-danger');
            } else {
                controlloPercentualeCell.addClass('text-success');
            }
        }
    }
    
    function calcolaTotali(anno) {
        // Calcola i totali annuali per ogni colonna dell'anno specifico
        let totale_energia = 0;
        let totale_corrispettivo_incentivo = 0; // Questo è il TFO
        let totale_pun_calcolato = 0; // Nuovo totale per PUN
        let totale_corrispettivo_altro = 0;
        let totale_fatturazione_tfo = 0;
        let totale_fatturazione_altro = 0;
        let totale_incassi = 0;
        let totale_tfo = 0;
        
        for (let mese = 1; mese <= 12; mese++) {
            totale_energia += parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="energia_kwh"]`).val()) || 0;
            totale_corrispettivo_incentivo += parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="corrispettivo_incentivo"]`).val()) || 0; // Somma TFO da input (o cella .tfo-value)
            totale_corrispettivo_altro += parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="corrispettivo_altro"]`).val()) || 0;
            totale_fatturazione_tfo += parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_tfo"]`).val()) || 0;
            totale_fatturazione_altro += parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_altro"]`).val()) || 0;
            totale_incassi += parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="incassi"]`).val()) || 0;
            
            // Calcola e somma il valore TFO (per il totale_tfo usato sotto)
            const energia = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="energia_kwh"]`).val()) || 0;
            totale_tfo += energia * tfoRate;

            // Per il calcolo del totale PUN, leggiamo direttamente dalle celle
            totale_pun_calcolato += parseFloat($(`#table1_${anno} .pun-value[data-mese="${mese}"]`).text()) || 0;
        }
        
        // Calcola totali di scarto e percentuale
        const totale_corrispettivi = totale_corrispettivo_incentivo + totale_corrispettivo_altro;
        const totale_fatturazione = totale_fatturazione_tfo + totale_fatturazione_altro;
        const totale_scarto = totale_corrispettivi - totale_fatturazione;
        let totale_percentuale = 0;
        
        if (totale_fatturazione !== 0) {
            totale_percentuale = (totale_scarto / totale_fatturazione) * 100;
        }
        
        // Aggiorna i totali nella riga del totale annuale
        $(`#table1_${anno} .totale-energia`).text(totale_energia.toFixed(2));
        $(`#table1_${anno} .totale-corrispettivo-incentivo`).text(totale_tfo.toFixed(2)); // Totale TFO
        $(`#table1_${anno} .totale-pun`).text(totale_pun_calcolato.toFixed(3)); // Aggiorna totale PUN
        $(`#table1_${anno} .totale-corrispettivo-altro`).text(totale_corrispettivo_altro.toFixed(2));
        $(`#table1_${anno} .totale-fatturazione-tfo`).text(totale_fatturazione_tfo.toFixed(2));
        $(`#table1_${anno} .totale-fatturazione-altro`).text(totale_fatturazione_altro.toFixed(2));
        $(`#table1_${anno} .totale-incassi`).text(totale_incassi.toFixed(2));
        $(`#table1_${anno} .totale-controllo-scarto`).text(totale_scarto.toFixed(2));
        $(`#table1_${anno} .totale-controllo-percentuale`).text(totale_percentuale.toFixed(2) + '%');
    }
});
