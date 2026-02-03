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
        const linkGrafico = document.querySelector(`a[href="#grafico_${anno}"]`);
        if (linkGrafico) {
            linkGrafico.addEventListener('click', function() {
                console.log("Click rilevato per grafico anno:", anno);
                setTimeout(function() {
                    inizializzaGrafico(anno);
                }, 300); // Aumentato il timeout per dare più tempo al DOM
            });
        } else {
            console.warn(`Link per grafico anno ${anno} non trovato`);
        }
        
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

		// Carica i dati annuali via JSON dagli endpoint e costruisce le serie
		// Recupera il nickname dal container del grafico (ha data-nickname) con fallback alla tabella annuale
		let nickname = container ? container.getAttribute('data-nickname') : null;
		if (!nickname) {
			const tableFallback = document.querySelector(`.js-tabella-corrispettivi[data-anno="${anno}"]`);
			if (tableFallback) {
				nickname = tableFallback.getAttribute('data-nickname');
			}
		}
		if (!nickname) {
			console.warn(`Nickname non trovato per l'anno ${anno} (né nel chart né nella tabella)`);
			return;
		}

		const mesi = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic'];
		const mesiNumeri = Array.from({ length: 12 }, (_, i) => i + 1);

		Promise.all([
			fetch(`/corrispettivi/api/annuale/energia-kwh/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success: false })),
			fetch(`/corrispettivi/api/annuale/dati-tfo/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success: false })),
			fetch(`/corrispettivi/api/annuale/dati-CNI/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success: false })),
			fetch(`/corrispettivi/api/annuale/dati-fatturazione-tfo/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success: false })),
			fetch(`/corrispettivi/api/annuale/dati-energia-non-incentivata/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success: false })),
			fetch(`/corrispettivi/api/annuale/dati-riepilogo-pagamenti/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success: false }))
		]).then(([energiaAnn, tfoAnn, cniAnn, fattTfoAnn, niAnn, incAnn]) => {
			const energiaByM = (energiaAnn && energiaAnn.per_month) || {};
			const tfoByM = (tfoAnn && tfoAnn.per_month) || {};
			const cniByM = (cniAnn && cniAnn.per_month) || {};
			const fattTfoByM = (fattTfoAnn && fattTfoAnn.per_month) || {};
			const niByM = (niAnn && niAnn.per_month) || {};
			const incByM = (incAnn && incAnn.per_month) || {};

			const getVal = (obj, m) => {
				if (!obj) return 0;
				const v = obj[m] ?? obj[String(m)];
				const num = parseFloat(v);
				return Number.isFinite(num) ? num : 0;
			};

			const datiEnergia = mesiNumeri.map(m => getVal(energiaByM, m));
			const datiCorrispettivi = mesiNumeri.map(m => getVal(tfoByM, m) + getVal(cniByM, m));
			const datiFatturazione = mesiNumeri.map(m => getVal(fattTfoByM, m) + getVal(niByM, m));
			const datiIncassi = mesiNumeri.map(m => getVal(incByM, m));

			const hasDati = [datiEnergia, datiCorrispettivi, datiFatturazione, datiIncassi].some(arr => arr.some(v => v > 0));
			if (!hasDati) {
				console.warn(`Nessun dato trovato per il grafico dell'anno ${anno}`);
				document.getElementById(`chart_${anno}`).innerHTML = '<div class="alert alert-info">Nessun dato disponibile per il grafico.</div>';
				return;
			}

			console.log(`Dati recuperati per anno ${anno}:`, { energia: datiEnergia, corrispettivi: datiCorrispettivi, fatturazione: datiFatturazione, incassi: datiIncassi });

			const maxEnergia = Math.max(...datiEnergia) * 1.2 || 140000;
			const maxMonetario = Math.max(...datiCorrispettivi, ...datiFatturazione, ...datiIncassi) * 1.2 || 180000;

			try {
				Highcharts.chart(`chart_${anno}`, {
					chart: {
						zoomType: 'xy',
						backgroundColor: 'rgba(255, 255, 255, 0.8)',
						animation: false,
						events: { load: function() { console.log(`Grafico per anno ${anno} caricato con successo`); } }
					},
					title: { text: 'Visualizzazione grafica', style: { fontSize: '18px' } },
					xAxis: { categories: mesi, crosshair: true },
					yAxis: [{
						title: { text: 'Energie (kWh)', style: { color: '#333' } },
						labels: { format: '{value:,.0f}', style: { color: '#333' } },
						min: 0,
						max: maxEnergia
					}, {
						title: { text: '€', style: { color: '#333' } },
						labels: { format: '{value:,.0f} €', style: { color: '#333' } },
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
								} else if (point.y > 0) {
									s += '<span style="color:' + point.series.color + '">● ' + point.series.name + '</span>: <b>' + Highcharts.numberFormat(point.y, 0) + ' €</b><br/>';
									hasData = true;
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
						marker: { enabled: true, radius: 4 },
						dataLabels: {
							enabled: true,
							formatter: function() { return this.y > 0 ? this.y.toLocaleString() + ' kWh' : ''; },
							style: { fontSize: '10px' }
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
				document.getElementById(`chart_${anno}`).innerHTML = '<div class="alert alert-danger">Errore durante la creazione del grafico. Controlla la console per dettagli.</div>';
			}
		}).catch(err => {
			console.error(`Errore nel recupero dei dati JSON per anno ${anno}:`, err);
			document.getElementById(`chart_${anno}`).innerHTML = '<div class="alert alert-danger">Errore nel recupero dei dati JSON.</div>';
		});
    }
});