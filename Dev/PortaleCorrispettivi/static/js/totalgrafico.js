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
        const resp = await fetch(url);
        if (!resp.ok) throw new Error('HTTP ' + resp.status + ' su ' + url);
        const json = await resp.json();
        if (!json || json.success !== true) return { per_month: {} };
        return json;
    }

    /**
     * Carica i dati annuali per un singolo impianto usando gli endpoint annuali ottimizzati
     */
    async function caricaDatiImpiantoAnno(nickname, anno) {
        const base = `/corrispettivi/api/annuale`;
        
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
    }

    /**
     * Carica e somma i dati di tutti gli impianti per l'anno specificato
     */
    async function caricaDatiAnno(impianti, anno) {
        // Carica i dati per tutti gli impianti in parallelo
        const datiImpianti = await Promise.all(
            impianti.map(nickname => caricaDatiImpiantoAnno(nickname, anno))
        );

        // Inizializza struttura dati per 12 mesi
        const datiSommati = Array.from({ length: 12 }, (_, i) => ({
            mese: i + 1,
            energia_kwh: 0,
            corrispettivi_tfo: 0,
            fatturazione_tfo: 0,
            incassi: 0
        }));

        // Somma i dati di tutti gli impianti per ogni mese
        datiImpianti.forEach(datiImpianto => {
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
        const categorie = dati.map(d => nomiMesi[d.mese - 1]);
        const energiaData = dati.map(d => Math.round(d.energia_kwh || 0));
        const corrispettiviData = dati.map(d => Math.round(d.corrispettivi_tfo || 0));
        const fatturazioneData = dati.map(d => Math.round(d.fatturazione_tfo || 0));
        const incassiData = dati.map(d => Math.round(d.incassi || 0));

        // Crea il titolo in base al numero di impianti
        const titoloImpianti = impianti.length === 1 
            ? impianti[0] 
            : `${impianti.length} Impianti (Somma Totale)`;

        Highcharts.chart('chart', {
            chart: {
                zoomType: 'xy',
                backgroundColor: 'rgba(255,255,255,0.8)'
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
                marker: { fillColor: '#ff7f0e', lineWidth: 2, lineColor: '#FFFFFF' }
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
    }

    function aggiornaTabella(dati) {
        const tabella = document.getElementById('tabella_corrispettivi');
        if (!tabella) return;

        if ($.fn.DataTable.isDataTable(tabella)) {
            $(tabella).DataTable().destroy();
        }

        const righeTabella = dati.map((d, index) => [
            index + 1,
            nomiMesi[d.mese - 1],
            Math.round(d.energia_kwh || 0).toLocaleString(),
            Math.round(d.corrispettivi_tfo || 0).toLocaleString(),
            Math.round(d.fatturazione_tfo || 0).toLocaleString(),
            Math.round(d.incassi || 0).toLocaleString()
        ]);

        const totaleEnergia = dati.reduce((sum, d) => sum + (d.energia_kwh || 0), 0);
        const totaleCorrispettivi = dati.reduce((sum, d) => sum + (d.corrispettivi_tfo || 0), 0);
        const totaleFatturazione = dati.reduce((sum, d) => sum + (d.fatturazione_tfo || 0), 0);
        const totaleIncassi = dati.reduce((sum, d) => sum + (d.incassi || 0), 0);

        $(tabella).DataTable({
            data: righeTabella,
            paging: false,
            searching: false,
            info: false,
            ordering: false,
            language: { emptyTable: 'Nessun dato disponibile' },
            footerCallback: function() {
                const api = this.api();
                $(api.column(2).footer()).html(Math.round(totaleEnergia).toLocaleString());
                $(api.column(3).footer()).html(Math.round(totaleCorrispettivi).toLocaleString());
                $(api.column(4).footer()).html(Math.round(totaleFatturazione).toLocaleString());
                $(api.column(5).footer()).html(Math.round(totaleIncassi).toLocaleString());
            }
        });
    }

    async function aggiornaAnnoSelezionato() {
        const selettoreAnno = document.getElementById('selettore-anno');
        const anno = selettoreAnno ? (selettoreAnno.value || new Date().getFullYear()) : new Date().getFullYear();

        // Recupero lista impianti da attributo data-impianti (formato JSON array)
        // Esempio: data-impianti='["ponte_giurino", "san_teodoro", "ionico_foresta"]'
        // oppure data-impianti='["ponte_giurino"]' per singolo impianto
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
            // Fallback: supporta ancora data-nickname per retrocompatibilità
            impianti = [tabella.dataset.nickname];
        } else {
            console.warn('Lista impianti non specificata. Imposta data-impianti o data-nickname su #tabella_corrispettivi.');
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

    const selettoreAnno = document.getElementById('selettore-anno');
    if (selettoreAnno) {
        selettoreAnno.addEventListener('change', aggiornaAnnoSelezionato);
    }

    // Caricamento iniziale
    aggiornaAnnoSelezionato();
});
