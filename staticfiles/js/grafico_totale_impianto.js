// questo file fa riferimento a 'totaliAnnualiCaricati' creato da tabellacorrispettivi.js
// e crea il grafico Highcharts con i dati già elaborati ricevuti

console.log('[GRAFICO TOTALE] Modulo caricato - Versione Event-Driven');

// Formatta il nickname: "impianto_solar_power" diventa "Impianto Solar Power"
function formatNickname(nickname) {
    if (!nickname) return '';
    
    return nickname
        .split('_')
        .map(word => 
            word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        )
        .join(' ');
}

// Crea il grafico Highcharts e aggiorna la tabella con i totali annuali ricevuti dall'evento
function creaGraficoETabellaRiepilogativa(totaliAnnuali, nickname) {
    console.log('[GRAFICO TOTALE] Creazione grafico con dati ricevuti:', totaliAnnuali);
    const chartContainer = document.getElementById('chart_totale_impianto');
    
    // Controllo validità dei dati e presenza del container
    if (!chartContainer || !totaliAnnuali || totaliAnnuali.length === 0) {
        console.error('[GRAFICO TOTALE] Dati mancanti o container non trovato');
        chartContainer.innerHTML = '<div class="alert alert-warning">Nessun dato disponibile per il grafico.</div>';
        return;
    }

    // Ordina gli anni in ordine crescente
    totaliAnnuali.sort((a, b) => a.anno - b.anno);

    // Calcola i totali complessivi sommando tutti gli anni
    const totaliComplessivi = {
        energia: totaliAnnuali.reduce((sum, anno) => sum + (anno.energia || 0), 0),
        corrispettivi: totaliAnnuali.reduce((sum, anno) => sum + (anno.tfo || 0) + (anno.cni || 0), 0), // Somma TFO + CNI
        fatturazione: totaliAnnuali.reduce((sum, anno) => sum + (anno.fatturazione || 0), 0),
        incassi: totaliAnnuali.reduce((sum, anno) => sum + (anno.pagamenti || 0), 0)
    };

    // Aggiorna la tabella HTML con la riga dei totali (formattazione italiana)
    const tbody = document.querySelector('#tabella_totale_impianto tbody');
    if (tbody) {
        tbody.innerHTML = `
            <tr class="table-info fw-bold">
                <td class="text-center">Totale (tutti gli anni)</td>
                <td class="text-center">${totaliComplessivi.energia.toLocaleString('it-IT', {minimumFractionDigits: 0, maximumFractionDigits: 0})}</td>
                <td class="text-center">${totaliComplessivi.corrispettivi.toLocaleString('it-IT', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="text-center">${totaliComplessivi.fatturazione.toLocaleString('it-IT', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="text-center">${totaliComplessivi.incassi.toLocaleString('it-IT', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            </tr>`;
    }

    // Prepara i dati per il grafico
    const categorie = totaliAnnuali.map(a => a.anno.toString());
    const datiEnergia = totaliAnnuali.map(a => a.energia || 0);
    const datiCorrispettivi = totaliAnnuali.map(a => (a.tfo || 0) + (a.cni || 0));
    const datiFatturazione = totaliAnnuali.map(a => a.fatturazione || 0);
    const datiIncassi = totaliAnnuali.map(a => a.pagamenti || 0);

    // Crea il grafico
    Highcharts.chart('chart_totale_impianto', {
        chart: { 
            type: 'column',
            zoomType: 'xy',
            height: 450,
            backgroundColor: 'transparent',
            style: {
                fontFamily: 'Arial, sans-serif'
            }
        },
        title: { 
            text: `Andamento Annuale ${formatNickname(nickname)}`,
            style: { 
                fontSize: '18px', 
                fontWeight: 'bold',
                color: '#333'
            }
        },
        subtitle: {
            text: 'Energia incentivata, corrispettivi TFO, fatturazione e incassi (dati sommati)',
            style: { 
                fontSize: '0.8em', 
                fontWeight: 'normal',
                color: '#666'
            }
        },
        xAxis: {
            categories: categorie,
            crosshair: true,
            labels: {
                style: {
                    fontSize: '12px'
                }
            }
        },
        yAxis: [{
            min: 0,
            title: { 
                text: 'Energia (kWh)',
                style: {
                    color: '#7cb5ec'
                }
            },
            labels: {
                format: '{value:,.0f}',
                style: {
                    color: '#7cb5ec'
                }
            }
        }, {
            min: 0,
            title: { 
                text: 'Importi (€)',
                style: {
                    color: 'rgb(255, 107, 107)'
                }
            },
            labels: {
                format: '{value:,.0f} €',
                style: {
                    color: 'rgb(255, 107, 107)'
                }
            },
            opposite: true
        }],
        tooltip: {
            shared: true,
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            borderColor: '#ddd',
            borderRadius: 5,
            borderWidth: 1,
            shadow: true,
            useHTML: true,
            style: {
                padding: '10px',
                fontSize: '13px'
            }
        },
        plotOptions: {
            column: {
                borderWidth: 0,
                groupPadding: 0.1,
                pointPadding: 0.05
            },
            series: {
                dataLabels: {
                    enabled: false
                }
            }
        },
        legend: {
            layout: 'horizontal',
            align: 'center',
            verticalAlign: 'bottom',
            borderWidth: 0,
            itemStyle: {
                fontWeight: 'normal'
            }
        },
        series: [{
            name: 'Energia Incentivata',
            type: 'spline',
            yAxis: 0,
            data: datiEnergia,
            color: '#7cb5ec',
            tooltip: { 
                valueSuffix: ' kWh',
                valueDecimals: 0
            }
        }, {
            name: 'Corrispettivi TFO',
            yAxis: 1,
            data: datiCorrispettivi,
            color: 'rgb(65,105,225)',
            tooltip: { 
                valueSuffix: ' €',
                valueDecimals: 2
            }
        }, {
            name: 'Fatturazione TFO',
            yAxis: 1,
            data: datiFatturazione,
            color: 'rgb(255,107,107)',
            tooltip: { 
                valueSuffix: ' €',
                valueDecimals: 2
            }
        }, {
            name: 'Incassi',
            yAxis: 1,
            data: datiIncassi,
            color: 'rgb(50,205,50)',
            tooltip: { 
                valueSuffix: ' €',
                valueDecimals: 2
            }
        }]
    });
}

// Inizializza il container mostrando uno spinner in attesa dei dati dall'evento
function inizializzaGrafico() {
    const chartContainer = document.getElementById('chart_totale_impianto');
    
    if (!chartContainer) {
        console.error('[GRAFICO TOTALE] Container #chart_totale_impianto non trovato nel DOM');
        return;
    }

    // Mostra spinner in attesa dei dati dall'evento
    chartContainer.innerHTML = `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Caricamento...</span>
            </div>
            <p class="mt-3 text-muted">Caricamento dati del grafico...</p>
        </div>
    `;
    
    console.log('[GRAFICO TOTALE] Container inizializzato, in attesa dell\'evento totaliAnnualiCaricati');
}

// Ascolta l'evento 'totaliAnnualiCaricati' emesso quando i dati sono pronti
window.addEventListener('totaliAnnualiCaricati', function(event) {
    console.log('[GRAFICO TOTALE] ✅ Evento totaliAnnualiCaricati ricevuto');
    console.log('[GRAFICO TOTALE] Dati ricevuti:', event.detail);
    
    const { totaliAnnuali } = event.detail;
    
    if (!totaliAnnuali || totaliAnnuali.length === 0) {
        console.warn('[GRAFICO TOTALE] Nessun dato disponibile nell\'evento');
        const chartContainer = document.getElementById('chart_totale_impianto');
        if (chartContainer) {
            chartContainer.innerHTML = '<div class="alert alert-warning">Nessun dato disponibile per il grafico.</div>';
        }
        return;
    }
    
    // Recupera il nickname per il titolo del grafico
    const dataContainer = document.querySelector('[data-nickname]');
    const nickname = dataContainer ? dataContainer.getAttribute('data-nickname') : 'Impianto';
    
    // Crea il grafico con i dati ricevuti
    creaGraficoETabellaRiepilogativa(totaliAnnuali, nickname);
});

// Inizializza il grafico quando il DOM è pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inizializzaGrafico);
} else {
    inizializzaGrafico();
}