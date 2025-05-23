document.addEventListener('DOMContentLoaded', function() {
    console.log("Inizializzazione script grafico corrispettivi");
    
    // Ottieni tutti gli elementi con class "collapse multi-collapse" che contengono "grafico_"
    document.querySelectorAll('.collapse.multi-collapse[id^="grafico_"]').forEach(function(graficoDiv) {
        // Estrai l'anno dall'ID del div
        const anno = graficoDiv.id.replace('grafico_', '');
        console.log("Trovato grafico per anno:", anno);
        
        // Inizializza immediatamente il grafico se è già visibile
        if (graficoDiv.classList.contains('show')) {
            console.log("Grafico già visibile, inizializzazione immediata");
            inizializzaGrafico(anno);
        }
        
        // Attendi che il div del grafico sia visibile
        document.querySelector(`a[href="#grafico_${anno}"]`).addEventListener('click', function() {
            console.log("Click rilevato per grafico anno:", anno);
            setTimeout(function() {
                inizializzaGrafico(anno);
            }, 300); // Aumentato il timeout per dare più tempo al DOM
        });
        
        // Aggiungi anche un listener per gli eventi bootstrap
        graficoDiv.addEventListener('shown.bs.collapse', function() {
            console.log("Evento bootstrap collapse rilevato per anno:", anno);
            inizializzaGrafico(anno);
        });
    });

    function inizializzaGrafico(anno) {
        console.log(`Inizializzazione grafico per anno ${anno}`);
        
        // Controllo se il grafico è già stato inizializzato
        if (Highcharts.charts.find(chart => chart && chart.renderTo.id === `chart_${anno}`)) {
            console.log(`Grafico per anno ${anno} già inizializzato`);
            return;
        }

        // Verifica che il container esista
        const container = document.getElementById(`chart_${anno}`);
        if (!container) {
            console.error(`Container chart_${anno} non trovato!`);
            return;
        }
        
        console.log(`Recupero dati per grafico anno ${anno}...`);
        
        // Recupera i dati reali dalla tabella invece di usare dati di esempio
        const datiEnergia = [];
        const datiCorrispettivi = [];
        const datiFatturazione = [];
        const datiIncassi = [];
        const mesi = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic'];
        
        let hasDati = false; // Flag per verificare se abbiamo dati validi
        
        // Itera su ogni mese per recuperare i dati dalla tabella
        for (let mese = 1; mese <= 12; mese++) {
            // Recupera energia dall'input della tabella
            const energiaElement = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="energia_kwh"]`);
            if (energiaElement.length === 0) {
                console.warn(`Elemento energia per mese ${mese} anno ${anno} non trovato`);
            }
            
            const energia = parseFloat(energiaElement.val()) || 0;
            datiEnergia.push(energia);
            if (energia > 0) hasDati = true;
            
            // Recupera corrispettivi (TFO + parteInternaPerPun)
            const tfoElement = $(`#table1_${anno} .tfo-value[data-mese="${mese}"]`);
            const punElement = $(`#table1_${anno} .pun-value[data-mese="${mese}"]`);
            
            if (tfoElement.length === 0 || punElement.length === 0) {
                console.warn(`Elementi TFO o PUN per mese ${mese} anno ${anno} non trovati`);
            }
            
            const tfoValue = parseFloat(tfoElement.text()) || 0;
            const punValue = parseFloat(punElement.text()) || 0;
            
            // Calcola parte interna per PUN
            const energyInput = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="energia_kwh"]`);
            const lettura_imm_campo = parseFloat(energyInput.attr('data-imm-campo')) || 0;
            let parteInternaPerPun = 0;
            if (0.21 !== 0) { // Evita divisione per zero
                const parteInterna = lettura_imm_campo - (tfoValue / 0.21);
                parteInternaPerPun = parteInterna * (punValue / 1000);
            }
            
            const valoreCorrispettivi = tfoValue + parteInternaPerPun;
            datiCorrispettivi.push(valoreCorrispettivi);
            if (valoreCorrispettivi > 0) hasDati = true;
            
            // Recupera fatturazione totale
            const tfoFatturazioneElement = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_tfo"]`);
            const energiaNonIncElement = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="fatturazione_altro"]`);
            
            if (tfoFatturazioneElement.length === 0 || energiaNonIncElement.length === 0) {
                console.warn(`Elementi fatturazione per mese ${mese} anno ${anno} non trovati`);
            }
            
            const tfoFatturazione = parseFloat(tfoFatturazioneElement.val()) || 0;
            const energiaNonIncentivata = parseFloat(energiaNonIncElement.val()) || 0;
            const valoreFatturazione = tfoFatturazione + energiaNonIncentivata;
            datiFatturazione.push(valoreFatturazione);
            if (valoreFatturazione > 0) hasDati = true;
            
            // Recupera incassi
            const incassiElement = $(`#table1_${anno} input[data-mese="${mese}"][data-campo="incassi"]`);
            if (incassiElement.length === 0) {
                console.warn(`Elemento incassi per mese ${mese} anno ${anno} non trovato`);
            }
            
            const incassi = parseFloat(incassiElement.val()) || 0;
            datiIncassi.push(incassi);
            if (incassi > 0) hasDati = true;
        }
        
        if (!hasDati) {
            console.warn(`Nessun dato trovato per il grafico dell'anno ${anno}`);
            // Inseriamo un messaggio nel container
            document.getElementById(`chart_${anno}`).innerHTML = 
                '<div class="alert alert-info">Nessun dato disponibile per il grafico. Inserisci i dati nella tabella.</div>';
            return;
        }
        
        console.log(`Dati recuperati per anno ${anno}:`, {
            energia: datiEnergia,
            corrispettivi: datiCorrispettivi,
            fatturazione: datiFatturazione,
            incassi: datiIncassi
        });
        
        // Calcola i valori massimi per gli assi Y
        const maxEnergia = Math.max(...datiEnergia) * 1.2 || 140000;
        const maxMonetario = Math.max(...datiCorrispettivi, ...datiFatturazione, ...datiIncassi) * 1.2 || 180000;
        
        try {
            Highcharts.chart(`chart_${anno}`, {
                chart: {
                    zoomType: 'xy',
                    backgroundColor: 'rgba(255, 255, 255, 0.8)',
                    animation: false, // Disabilita animazioni
                    events: {
                        load: function() {
                            console.log(`Grafico per anno ${anno} caricato con successo`);
                        }
                    }
                },
                title: {
                    text: 'Visualizzazione grafica',
                    style: { fontSize: '18px' }
                },
                xAxis: {
                    categories: mesi,
                    crosshair: true
                },
                yAxis: [{
                    // Asse sinistro per l'energia
                    title: {
                        text: 'Energie (kWh)',
                        style: { color: '#333' }
                    },
                    labels: {
                        format: '{value:,.0f}',
                        style: { color: '#333' }
                    },
                    min: 0,
                    max: maxEnergia
                }, {
                    // Asse destro per i valori monetari
                    title: {
                        text: '€',
                        style: { color: '#333' }
                    },
                    labels: {
                        format: '{value:,.0f} €',
                        style: { color: '#333' }
                    },
                    min: 0,
                    max: maxMonetario,
                    opposite: true
                }],
                tooltip: {
                    shared: true,
                    formatter: function() {
                        let s = '<b>' + this.x + '</b><br/>';
                        let hasData = false;
                        
                        this.points.forEach(function(point) {
                            if (point.series.name === 'Energia incentivata') {
                                s += '<span style="color:' + point.series.color + '">● ' + point.series.name + '</span>: <b>' + Highcharts.numberFormat(point.y, 0) + ' kWh</b><br/>';
                                hasData = true;
                            } else {
                                if (point.y > 0) {
                                    s += '<span style="color:' + point.series.color + '">● ' + point.series.name + '</span>: <b>' + Highcharts.numberFormat(point.y, 0) + ' €</b><br/>';
                                    hasData = true;
                                }
                            }
                        });
                        
                        return hasData ? s : false;
                    }
                },
                series: [{
                    name: 'Energia incentivata',
                    type: 'line',
                    yAxis: 0,
                    data: datiEnergia,
                    color: '#FF0000',
                    marker: {
                        enabled: true,
                        radius: 4
                    },
                    dataLabels: {
                        enabled: true,
                        formatter: function() {
                            return this.y > 0 ? this.y.toLocaleString() + ' kWh' : '';
                        },
                        style: {
                            fontSize: '10px'
                        }
                    },
                    zIndex: 4
                }, {
                    name: 'Corrispettivi',
                    type: 'column',
                    yAxis: 1,
                    data: datiCorrispettivi,
                    color: '#E5DCC3',
                    zIndex: 3
                }, {
                    name: 'Fatturazione',
                    type: 'column',
                    yAxis: 1,
                    data: datiFatturazione,
                    color: '#FFC19E',
                    zIndex: 2
                }, {
                    name: 'Incassi',
                    type: 'column',
                    yAxis: 1,
                    data: datiIncassi,
                    color: '#C4D7ED',
                    zIndex: 1
                }]
            });
        } catch (error) {
            console.error(`Errore durante la creazione del grafico per anno ${anno}:`, error);
            document.getElementById(`chart_${anno}`).innerHTML = 
                '<div class="alert alert-danger">Errore durante la creazione del grafico. Controlla la console per dettagli.</div>';
        }
    }
});