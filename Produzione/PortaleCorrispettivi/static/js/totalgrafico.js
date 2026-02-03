// Grafico e tabella basati su API annuali - SOMMA TUTTI GLI IMPIANTI
document.addEventListener('DOMContentLoaded', function() {
    const nomiMesi = [
        'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
    ];

    function mostraSpinner(visibile) {
        const spinner = document.getElementById('spinner');
        if (spinner) spinner.style.display = visibile ? 'block' : 'none';
    }

    async function fetchJson(url) {
        try {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error('HTTP ' + resp.status + ' su ' + url);
            const json = await resp.json();
            return json && json.success === true ? json : { per_month: {} };
        } catch (error) {
            console.warn('Errore fetch:', error.message, 'per URL:', url);
            return { per_month: {} };
        }
    }

    // Carica dati annuali per singolo impianto da API
    async function caricaDatiImpiantoAnno(nickname, anno) {
        const base = `/corrispettivi/api/annuale`;
        
        try {
            const [energiaRes, tfoRes, fattRes, incassiRes] = await Promise.all([
                fetchJson(`${base}/energia-kwh/${encodeURIComponent(nickname)}/${anno}/`),
                fetchJson(`${base}/dati-tfo/${encodeURIComponent(nickname)}/${anno}/`),
                fetchJson(`${base}/dati-fatturazione-tfo/${encodeURIComponent(nickname)}/${anno}/`),
                fetchJson(`${base}/dati-riepilogo-pagamenti/${encodeURIComponent(nickname)}/${anno}/`)
            ]);

            return {
                energia_kwh: energiaRes.per_month || {},
                corrispettivi_tfo: tfoRes.per_month || {},
                fatturazione_tfo: fattRes.per_month || {},
                incassi: incassiRes.per_month || {}
            };
        } catch (error) {
            console.error(`Errore caricamento dati per ${nickname} ${anno}:`, error);
            return {
                energia_kwh: {},
                corrispettivi_tfo: {},
                fatturazione_tfo: {},
                incassi: {}
            };
        }
    }

    // Carica e somma dati di tutti gli impianti per anno
    async function caricaDatiAnno(impianti, anno) {
        // Carica i dati per tutti gli impianti in parallelo ma con limiti
        const chunkSize = 3; // Massimo 3 impianti alla volta
        const chunks = [];
        
        for (let i = 0; i < impianti.length; i += chunkSize) {
            const chunk = impianti.slice(i, i + chunkSize);
            chunks.push(chunk);
        }

        let tuttiDatiImpianti = [];

        for (const chunk of chunks) {
            const datiChunk = await Promise.all(
                chunk.map(nickname => caricaDatiImpiantoAnno(nickname, anno))
            );
            tuttiDatiImpianti = tuttiDatiImpianti.concat(datiChunk);
            
            // Piccola pausa tra i chunk per non sovraccaricare il server
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        // Inizializza struttura dati per 12 mesi
        const datiSommati = Array.from({ length: 12 }, (_, i) => ({
            mese: i + 1,
            energia_kwh: 0,
            corrispettivi_tfo: 0,
            fatturazione_tfo: 0,
            incassi: 0
        }));

        // Somma i dati di tutti gli impianti per ogni mese
        tuttiDatiImpianti.forEach(datiImpianto => {
            for (let mese = 1; mese <= 12; mese++) {
                datiSommati[mese - 1].energia_kwh += parseFloat(datiImpianto.energia_kwh[mese] || 0);
                datiSommati[mese - 1].corrispettivi_tfo += parseFloat(datiImpianto.corrispettivi_tfo[mese] || 0);
                datiSommati[mese - 1].fatturazione_tfo += parseFloat(datiImpianto.fatturazione_tfo[mese] || 0);
                datiSommati[mese - 1].incassi += parseFloat(datiImpianto.incassi[mese] || 0);
            }
        });

        return datiSommati;
    }

    function creaGrafico(dati, anno, impianti) {
        const chartContainer = document.getElementById('chart');
        if (!chartContainer) {
            console.error('Elemento #chart non trovato');
            return;
        }

        const categorie = dati.map(d => nomiMesi[d.mese - 1]);
        const energiaData = dati.map(d => Math.round(d.energia_kwh || 0));
        const corrispettiviData = dati.map(d => Math.round(d.corrispettivi_tfo || 0));
        const fatturazioneData = dati.map(d => Math.round(d.fatturazione_tfo || 0));
        const incassiData = dati.map(d => Math.round(d.incassi || 0));

        // Crea il titolo in base al numero di impianti
        const titoloImpianti = impianti.length === 1 
            ? impianti[0] 
            : `${impianti.length} Impianti (Somma Totale)`;

        try {
            Highcharts.chart('chart', {
                chart: {
                    zoomType: 'xy',
                    backgroundColor: 'rgba(255,255,255,0.8)'
                },
                // DISABILITA ACCESSIBILITY PER EVITARE ERRORI
                accessibility: {
                    enabled: false
                },
                title: {
                    text: `Andamento ${titoloImpianti} - Anno ${anno}`.trim(),
                    align: 'center',
                    style: { fontSize: '18px', fontWeight: 'bold', color: '#4a3c54' }
                },
                subtitle: {
                    text: 'Energia incentivata, corrispettivi TFO, fatturazione e incassi (dati sommati)',
                    align: 'center'
                },
                xAxis: [{ categories: categorie, crosshair: true }],
                yAxis: [{
                    labels: { format: '{value} kWh', style: { color: Highcharts.getOptions().colors[0] } },
                    title: { text: 'Energia (kWh)', style: { color: Highcharts.getOptions().colors[0] } },
                    gridLineColor: '#e6e6e6', gridLineWidth: 1
                }, {
                    title: { text: 'Importi (€)', style: { color: '#FF6B6B' } },
                    labels: { format: '{value} €', style: { color: '#FF6B6B' } },
                    opposite: true
                }],
                tooltip: {
                    headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
                    pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                        '<td style="padding:0"><b>{point.y:,.0f} {point.series.tooltipOptions.valueSuffix}</b></td></tr>',
                    footerFormat: '</table>',
                    shared: true,
                    useHTML: true
                },
                plotOptions: {
                    column: { pointPadding: 0.2, borderWidth: 0, dataLabels: { enabled: false } },
                    line: { dataLabels: { enabled: false }, marker: { enabled: true, radius: 4 } }
                },
                series: [{
                    name: 'Energia Incentivata', type: 'line', yAxis: 0, data: energiaData,
                    tooltip: { valueSuffix: ' kWh' }, color: '#ff7f0e', lineWidth: 3,
                    marker: { fillColor: '#ff7f0e', lineWidth: 2, lineColor: '#FFFFFF' },
                    zIndex: 10
                }, {
                    name: 'Corrispettivi TFO', type: 'column', yAxis: 1, data: corrispettiviData,
                    tooltip: { valueSuffix: ' €' }, color: '#4169E1'
                }, {
                    name: 'Fatturazione TFO', type: 'column', yAxis: 1, data: fatturazioneData,
                    tooltip: { valueSuffix: ' €' }, color: '#FF6B6B'
                }, {
                    name: 'Incassi', type: 'column', yAxis: 1, data: incassiData,
                    tooltip: { valueSuffix: ' €' }, color: '#32CD32'
                }],
                legend: {
                    layout: 'horizontal', align: 'center', verticalAlign: 'bottom',
                    backgroundColor: 'rgba(255,255,255,0.9)', borderColor: '#CCC', borderWidth: 1, shadow: false
                },
                exporting: { enabled: true },
                credits: { enabled: false }
            });
        } catch (error) {
            console.error('Errore nella creazione del grafico Highcharts:', error);
            chartContainer.innerHTML = '<div class="alert alert-danger">Errore nella creazione del grafico. Controlla la console.</div>';
        }
    }   

    // Aggiorna la tabella con i dati mensili
    function aggiornaTabella(dati) {
        const tabella = document.getElementById('tabella_corrispettivi');
        if (!tabella) {
            console.error('Tabella #tabella_corrispettivi non trovata');
            return;
        }

        // Verifica che DataTables sia caricato
        if (typeof $.fn.DataTable === 'undefined') {
            console.error('DataTables non caricato');
            return;
        }

        const oggi = new Date();
        const meseCorrente = oggi.getMonth() + 1;
        const annoCorrente = oggi.getFullYear();
        const annoSelezionato = parseInt(document.getElementById('selettore-anno').value);

        // Distruggi la DataTable esistente
        if ($.fn.DataTable.isDataTable(tabella)) {
            $(tabella).DataTable().destroy();
        }

        const righeTabella = dati.map((d, index) => {
            const isMeseFuturo = 
                annoSelezionato > annoCorrente || 
                (annoSelezionato === annoCorrente && d.mese > meseCorrente);

            const formattaNumero = (valore, isEuro = false) => {
                if (isMeseFuturo) return '-';
                if (isEuro) {
                    return Math.round(valore || 0).toLocaleString('it-IT') + ' €';
                }
                return Math.round(valore || 0).toLocaleString('it-IT');
            };

            return [
                index + 1,
                nomiMesi[d.mese - 1],
                formattaNumero(d.energia_kwh),
                formattaNumero(d.corrispettivi_tfo, true),
                formattaNumero(d.fatturazione_tfo, true),
                formattaNumero(d.incassi, true)
            ];
        });

        const calcolaTotale = (dati, campo) => {
            return dati.reduce((somma, d) => {
                const isMeseFuturo = 
                    annoSelezionato > annoCorrente || 
                    (annoSelezionato === annoCorrente && d.mese > meseCorrente);
                return somma + (isMeseFuturo ? 0 : (d[campo] || 0));
            }, 0);
        };

        const totaleEnergia = calcolaTotale(dati, 'energia_kwh');
        const totaleCorrispettivi = calcolaTotale(dati, 'corrispettivi_tfo');
        const totaleFatturazione = calcolaTotale(dati, 'fatturazione_tfo');
        const totaleIncassi = calcolaTotale(dati, 'incassi');

        // Inizializza DataTables con configurazione migliorata
        const dataTable = $(tabella).DataTable({
            data: righeTabella,
            paging: false,
            searching: false,
            info: false,
            ordering: false,
            language: { 
                emptyTable: 'Nessun dato disponibile',
                thousands: ".",
                decimal: ","
            },
            footerCallback: function() {
                const api = this.api();
                $(api.column(2).footer()).html(Math.round(totaleEnergia).toLocaleString('it-IT') + ' kWh');
                $(api.column(3).footer()).html(Math.round(totaleCorrispettivi).toLocaleString('it-IT') + ' €');
                $(api.column(4).footer()).html(Math.round(totaleFatturazione).toLocaleString('it-IT') + ' €');
                $(api.column(5).footer()).html(Math.round(totaleIncassi).toLocaleString('it-IT') + ' €');
            }
        });

        return dataTable;
    }

    // Funzione principale: carica dati anno selezionato e aggiorna grafico/tabella
    async function aggiornaAnnoSelezionato() {
        const selettoreAnno = document.getElementById('selettore-anno');
        const anno = selettoreAnno ? (selettoreAnno.value || new Date().getFullYear()) : new Date().getFullYear();

        const tabella = document.getElementById('tabella_corrispettivi');
        let impianti = [];
        
        if (tabella && tabella.dataset && tabella.dataset.impianti) {
            try {
                impianti = JSON.parse(tabella.dataset.impianti);
                if (!Array.isArray(impianti) || impianti.length === 0) {
                    throw new Error('data-impianti deve essere un array non vuoto');
                }
            } catch (e) {
                console.error('Errore parsing data-impianti:', e);
                alert('Errore: data-impianti non valido. Usa formato JSON array, es: ["ponte_giurino", "san_teodoro"]');
                return;
            }
        } else if (tabella && tabella.dataset && tabella.dataset.nickname) {
            impianti = [tabella.dataset.nickname];
        } else {
            console.warn('Lista impianti non specificata.');
            alert('Errore: specificare gli impianti tramite data-impianti="[...]" su #tabella_corrispettivi');
            return;
        }

        try {
            mostraSpinner(true);
            const dati = await caricaDatiAnno(impianti, anno);
            creaGrafico(dati, anno, impianti);
            aggiornaTabella(dati);
        } catch (e) {
            console.error('Errore durante il caricamento dei dati:', e);
            alert('Errore durante il caricamento dei dati. Controlla la console.');
        } finally {
            mostraSpinner(false);
        }
    }

    // Inizializzazione
    const selettoreAnno = document.getElementById('selettore-anno');
    if (selettoreAnno) {
        selettoreAnno.addEventListener('change', aggiornaAnnoSelezionato);
        
        // Carica i dati iniziali
        aggiornaAnnoSelezionato();
    }
});