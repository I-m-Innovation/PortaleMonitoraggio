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
        $(`#table1_${anno} .tfo-value[data-mese="${mese}"]`).text(tfoValue.toFixed(2) + " €");
        
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
    
    function mostraDebugInfo(dati, anno) {
        // Crea o recupera il contenitore per il debug
        let debugContainer = $(`#debug-container-${anno}`);
        if (debugContainer.length === 0) {
            $(`#table1_${anno}`).after(`<div id="debug-container-${anno}" class="debug-container" style="margin: 10px 0; padding: 10px; border: 1px solid #ccc; background-color: #f9f9f9; display: none;"><h5>Informazioni di debug</h5><div id="debug-content-${anno}"></div></div>`);
            debugContainer = $(`#debug-container-${anno}`);
            
            
           
        }
        
        // Raccogli tutte le informazioni di debug
        let debugContent = $(`#debug-content-${anno}`);
        debugContent.empty();
        
        // Aggiungi informazioni generali
        debugContent.append(`<p><strong>Dati ricevuti:</strong> ${dati.length} record</p>`);
        
        // Aggiungi informazioni specifiche per ogni mese
        dati.forEach(function(dato) {
            if (dato.debug_info && dato.debug_info.length > 0) {
                const debugBox = $(`<div class="debug-box" style="margin-bottom: 10px; padding: 8px; border-left: 3px solid #518ffa;"></div>`);
                debugBox.append(`<h6>Debug per il mese ${dato.mese}</h6>`);
                
                const debugList = $('<ul style="margin-bottom: 0;"></ul>');
                dato.debug_info.forEach(function(info) {
                    debugList.append(`<li>${info}</li>`);
                });
                
                debugBox.append(debugList);
                debugContent.append(debugBox);
            }
        });
    }
    
    function caricaDatiTabella(anno) {
        console.log(`Caricamento dati per l'anno ${anno}...`);
        
        $.ajax({
            url: '/corrispettivi/api/dati-mensili-tabella/',
            method: 'GET',
            data: {
                impianto: nickname,
                anno: anno
            },
            success: function(response) {
                if (!response.success) {
                    console.error(`Errore nel caricamento dei dati: ${response.error}`);
                    return;
                }
                
                console.log(`Dati caricati con successo per ${anno}: ${response.data.length} record`);
                
                // Aggiorna la tabella con i dati ricevuti
                aggiornaTabellaConDati(response.data, anno);
                
                // Mostra informazioni di debug se presenti
                if (response.data.some(d => d.debug_info && d.debug_info.length > 0)) {
                    mostraDebugInfo(response.data, anno);
                }
                
                // Calcola controlli e totali dopo aver caricato i dati
                calcolaControlli(anno);
                calcolaTotali(anno);
            },
            error: function(error) {
                console.error(`Errore durante il caricamento dei dati per l'anno ${anno}:`, error);
            }
        });
    }
    
    function aggiornaTabellaConDati(dati, anno) {
        dati.forEach(function(dato) {
            if (dato.mese < 1 || dato.mese > 12) return;
            
            // Input per l'energia
            const energyInputElement = $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="energia_kwh"]`);
            
            // Salva il valore originale dell'energia per calcoli futuri
            energyInputElement.attr('data-prod-campo', dato.energia_kwh);
            
            // Salva il valore PUN se disponibile
            if (dato.media_pun_mensile !== undefined) {
                energyInputElement.attr('data-media-pun', dato.media_pun_mensile);
            }
            
            // Calcola il valore TFO
            const tfoRate = parseFloat($('.tfo-rate-indicator').text().match(/[\d.]+/)[0] || 0.21);
            const tfoValue = (parseFloat(dato.energia_kwh) || 0) * tfoRate;
            
            // Calcola il valore PUN
            const media_pun_mensile = parseFloat(energyInputElement.attr('data-media-pun')) || 0;
            let valorePUN = (parseFloat(dato.energia_kwh) || 0) * 0.02 * media_pun_mensile;
            
            // Popola i campi della tabella con i dati caricati
            energyInputElement.val(dato.energia_kwh || '');
            
            // Aggiorna TFO e PUN nelle celle di visualizzazione
            $(`#table1_${anno} .tfo-value[data-mese="${dato.mese}"]`).text((tfoValue || 0).toFixed(2) + " €");
            $(`#table1_${anno} .pun-value[data-mese="${dato.mese}"]`).text((valorePUN || 0).toFixed(3));
            
            // CORRISPETTIVI
            // Aggiorna campo corrispettivo_incentivo (nascosto ma usato nei calcoli)
            $(`<input type="hidden" data-mese="${dato.mese}" data-campo="corrispettivo_incentivo" value="${tfoValue.toFixed(2)}">`)
                .appendTo(`#table1_${anno} td.tfo-value[data-mese="${dato.mese}"]`);
            
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="corrispettivo_altro"]`).val(dato.corrispettivo_altro || '');
            
            // FATTURAZIONE - Correzione: assicurarsi che i dati vadano nelle colonne corrette
            // Il valore "fatturazione_tfo" va nella colonna "TFO**"
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="fatturazione_tfo"]`).val(dato.fatturazione_tfo || '');
            // Il valore "fatturazione_altro" va nella colonna "Energia non incentivata"
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="fatturazione_altro"]`).val(dato.fatturazione_altro || '');
            
            // INCASSI - Corrispondente alla colonna "Incassi" (Riepilogo Pagamenti)
            $(`#table1_${anno} input[data-mese="${dato.mese}"][data-campo="incassi"]`).val(dato.incassi || '');
            
            // Calcola controllo
            const corrispettivi = (parseFloat(tfoValue) || 0) + (parseFloat(dato.corrispettivo_altro) || 0);
            const fatturazione = (parseFloat(dato.fatturazione_tfo) || 0) + (parseFloat(dato.fatturazione_altro) || 0);
            
            if (!isNaN(corrispettivi) && !isNaN(fatturazione)) {
                const scarto = corrispettivi - fatturazione;
                const percentuale = fatturazione !== 0 ? (scarto / fatturazione) * 100 : 0;
                
                // Mostra i risultati del controllo
                $(`#table1_${anno} .controllo-scarto[data-mese="${dato.mese}"]`).text(scarto.toFixed(2));
                $(`#table1_${anno} .controllo-percentuale[data-mese="${dato.mese}"]`).text(percentuale.toFixed(2) + '%');
                
                // Colora le celle di controllo in base allo scarto
                const controlloScartoCell = $(`#table1_${anno} .controllo-scarto[data-mese="${dato.mese}"]`);
                const controlloPercentualeCell = $(`#table1_${anno} .controllo-percentuale[data-mese="${dato.mese}"]`);
                
                controlloScartoCell.removeClass('text-danger text-success');
                controlloPercentualeCell.removeClass('text-danger text-success');
                
                if (Math.abs(scarto) < 0.01) {
                    controlloScartoCell.addClass('text-success');
                    controlloPercentualeCell.addClass('text-success');
                } else {
                    controlloScartoCell.addClass('text-danger');
                    controlloPercentualeCell.addClass('text-danger');
                }
            }
        });
    }
    
    function salvaDatiTabella(anno) {
        console.log(`Salvataggio dati per l'anno ${anno}...`);
        
        const dati = [];
        
        // Per ogni mese dell'anno, raccogli i dati dalla tabella
        for (let mese = 1; mese <= 12; mese++) {
            const energia_kwh = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="energia_kwh"]`).val()) || null;
            
            // Se non c'è energia, non salviamo i dati per questo mese
            if (energia_kwh === null) continue;
            
            // Ottieni il valore TFO dalla cella o dall'input nascosto
            const tfoValue = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="corrispettivo_incentivo"]`).val()) || 
                            parseFloat($(`#table1_${anno} .tfo-value[data-mese="${mese}"]`).text()) || null;
            
            const punValue = parseFloat($(`#table1_${anno} .pun-value[data-mese="${mese}"]`).text()) || null;
            
            // Leggi i valori dai campi FATTURAZIONE e INCASSI
            const fatturazione_tfo = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_tfo"]`).val()) || null;
            const fatturazione_altro = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_altro"]`).val()) || null;
            const corrispettivo_altro = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="corrispettivo_altro"]`).val()) || null;
            const incassi = parseFloat($(`#table1_${anno} input[data-mese="${mese}"][data-campo="incassi"]`).val()) || null;
            
            dati.push({
                mese: mese,
                energia_kwh: energia_kwh,
                corrispettivo_incentivo: tfoValue,
                corrispettivo_altro: corrispettivo_altro,
                fatturazione_tfo: fatturazione_tfo,
                fatturazione_altro: fatturazione_altro,
                incassi: incassi
            });
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
