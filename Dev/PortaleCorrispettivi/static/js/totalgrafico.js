// Grafico aggregato di tutte le centrali
document.addEventListener('DOMContentLoaded', function() {
    // Nomi dei mesi in italiano
    const nomiMesi = [
        'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
    ];

    // Funzione per caricare i dati e creare il grafico
    function caricaDatiECreaGrafico(anno) {
        console.log('Caricamento dati per anno:', anno);
        
        // Mostra lo spinner
        document.getElementById('spinner').style.display = 'block';

        // Chiamata API per ottenere i dati aggregati
        fetch(`/corrispettivi/api/dati-aggregati/${anno}/`)
            .then(response => response.json())
            .then(data => {
                console.log('Dati ricevuti:', data);
                
                if (data.success) {
                    creaGrafico(data.dati, anno);
                    aggiornaTabella(data.dati);
                } else {
                    console.error('Errore nei dati:', data.error);
                    alert('Errore nel caricamento dei dati: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Errore nella chiamata API:', error);
                alert('Errore nella comunicazione con il server');
            })
            .finally(() => {
                // Nascondi lo spinner
                document.getElementById('spinner').style.display = 'none';
            });
    }

    // Funzione per creare il grafico con Highcharts
    function creaGrafico(dati, anno) {
        // Prepara i dati per Highcharts
        const categorie = dati.map(d => nomiMesi[d.mese - 1]);
        const energiaData = dati.map(d => Math.round(d.energia_kwh || 0));
        const corrispettiviData = dati.map(d => Math.round(d.corrispettivi_tfo || 0));
        const fatturazioneData = dati.map(d => Math.round(d.fatturazione_tfo || 0));
        const incassiData = dati.map(d => Math.round(d.incassi || 0));

        // Crea il grafico
        Highcharts.chart('chart', {
            chart: {
                zoomType: 'xy',
                backgroundColor: 'rgba(255,255,255,0.8)'
            },
            title: {
                text: `Andamento Aggregato Parco Idroelettrici - Anno ${anno}`,
                align: 'center',
                style: {
                    fontSize: '18px',
                    fontWeight: 'bold',
                    color: '#4a3c54'
                }
            },
            subtitle: {
                text: 'Energia incentivata, corrispettivi TFO, fatturazione e incassi',
                align: 'center'
            },
            xAxis: [{
                categories: categorie,
                crosshair: true
            }],
            yAxis: [{
                // Asse sinistro per l'energia
                labels: {
                    format: '{value} kWh',
                    style: {
                        color: Highcharts.getOptions().colors[0]
                    }
                },
                title: {
                    text: 'Energia (kWh)',
                    style: {
                        color: Highcharts.getOptions().colors[0]
                    }
                },
                gridLineColor: '#e6e6e6',
                gridLineWidth: 1
            }, {
                // Asse destro per i valori in euro
                title: {
                    text: 'Importi (€)',
                    style: {
                        color: '#FF6B6B'
                    }
                },
                labels: {
                    format: '{value} €',
                    style: {
                        color: '#FF6B6B'
                    }
                },
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
                column: {
                    pointPadding: 0.2,
                    borderWidth: 0,
                    dataLabels: {
                        enabled: false
                    }
                },
                line: {
                    dataLabels: {
                        enabled: false
                    },
                    marker: {
                        enabled: true,
                        radius: 4
                    }
                }
            },
            series: [{
                name: 'Energia Incentivata',
                type: 'line',
                yAxis: 0,
                data: energiaData,
                tooltip: {
                    valueSuffix: ' kWh'
                },
                color: '#2E8B57', // Verde foresta
                lineWidth: 3,
                marker: {
                    fillColor: '#2E8B57',
                    lineWidth: 2,
                    lineColor: '#1F5F3F'
                }
            }, {
                name: 'Corrispettivi TFO',
                type: 'column',
                yAxis: 1,
                data: corrispettiviData,
                tooltip: {
                    valueSuffix: ' €'
                },
                color: '#4169E1' // Blu reale
            }, {
                name: 'Fatturazione TFO',
                type: 'column',
                yAxis: 1,
                data: fatturazioneData,
                tooltip: {
                    valueSuffix: ' €'
                },
                color: '#FF6B6B' // Rosso corallo
            }, {
                name: 'Incassi',
                type: 'column',
                yAxis: 1,
                data: incassiData,
                tooltip: {
                    valueSuffix: ' €'
                },
                color: '#32CD32' // Verde lime
            }],
            legend: {
                layout: 'horizontal',
                align: 'center',
                verticalAlign: 'bottom',
                backgroundColor: 'rgba(255,255,255,0.9)',
                borderColor: '#CCC',
                borderWidth: 1,
                shadow: false
            },
            exporting: {
                enabled: true,
                buttons: {
                    contextButton: {
                        menuItems: [
                            'viewFullscreen',
                            'printChart',
                            'separator',
                            'downloadPNG',
                            'downloadJPEG',
                            'downloadPDF',
                            'downloadSVG',
                            'separator',
                            'downloadCSV',
                            'downloadXLS'
                        ]
                    }
                }
            },
            credits: {
                enabled: false
            }
        });
    }

    // Funzione per aggiornare la tabella dei dati
    function aggiornaTabella(dati) {
        const tabella = document.getElementById('tabella_corrispettivi');
        
        if (tabella) {
            // Distruggi la tabella esistente se esiste
            if ($.fn.DataTable.isDataTable(tabella)) {
                $(tabella).DataTable().destroy();
            }

            // Prepara i dati per la tabella
            const righeTabella = dati.map((d, index) => [
                index + 1, // numero
                nomiMesi[d.mese - 1], // mese
                Math.round(d.energia_kwh || 0).toLocaleString(), // energia
                Math.round(d.corrispettivi_tfo || 0).toLocaleString(), // corrispettivi
                Math.round(d.fatturazione_tfo || 0).toLocaleString(), // fatturazione
                Math.round(d.incassi || 0).toLocaleString() // incassi
            ]);

            // Calcola i totali
            const totaleEnergia = dati.reduce((sum, d) => sum + (d.energia_kwh || 0), 0);
            const totaleCorrispettivi = dati.reduce((sum, d) => sum + (d.corrispettivi_tfo || 0), 0);
            const totaleFatturazione = dati.reduce((sum, d) => sum + (d.fatturazione_tfo || 0), 0);
            const totaleIncassi = dati.reduce((sum, d) => sum + (d.incassi || 0), 0);

            // Inizializza la DataTable
            $(tabella).DataTable({
                data: righeTabella,
                paging: false,
                searching: false,
                info: false,
                ordering: false,
                language: {
                    emptyTable: "Nessun dato disponibile"
                },
                footerCallback: function(row, data, start, end, display) {
                    const api = this.api();
                    
                    // Aggiorna il footer con i totali
                    $(api.column(2).footer()).html(Math.round(totaleEnergia).toLocaleString());
                    $(api.column(3).footer()).html(Math.round(totaleCorrispettivi).toLocaleString());
                    $(api.column(4).footer()).html(Math.round(totaleFatturazione).toLocaleString());
                    $(api.column(5).footer()).html(Math.round(totaleIncassi).toLocaleString());
                }
            });
        }
    }

    // Event listener per il cambio anno
    const selettoreAnno = document.getElementById('selettore-anno');
    if (selettoreAnno) {
        selettoreAnno.addEventListener('change', function() {
            const annoSelezionato = this.value;
            caricaDatiECreaGrafico(annoSelezionato);
        });

        // Carica i dati per l'anno di default al caricamento della pagina
        const annoDefault = selettoreAnno.value || new Date().getFullYear();
        caricaDatiECreaGrafico(annoDefault);
    }
});
