document.addEventListener('DOMContentLoaded', function() {
    const tables = document.querySelectorAll('.js-tabella-corrispettivi');
    if (!tables || tables.length === 0) return;

    tables.forEach(function(table) {
        const anno = table.getAttribute('data-anno');
        const nickname = table.getAttribute('data-nickname');
        if (!anno || !nickname) return;

        const mesi = Array.from({ length: 12 }, (_, i) => i + 1);

        // Chiamate annuali (5-6 richieste al posto di 12xN)
        Promise.all([
            fetch(`/corrispettivi/api/annuale/energia-kwh/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success:false })),
            fetch(`/corrispettivi/api/annuale/dati-tfo/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success:false })),
            fetch(`/corrispettivi/api/annuale/dati-CNI/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success:false })),
            fetch(`/corrispettivi/api/annuale/dati-fatturazione-tfo/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success:false })),
            fetch(`/corrispettivi/api/annuale/dati-energia-non-incentivata/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success:false })),
            fetch(`/corrispettivi/api/annuale/dati-riepilogo-pagamenti/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success:false })),
            fetch(`/corrispettivi/api/annuale/percentuale-controllo/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success:false })),
            fetch(`/corrispettivi/api/annuale/commenti/${encodeURIComponent(nickname)}/${anno}/`).then(r => r.json()).catch(() => ({ success:false }))
        ]).then(([energiaAnn, tfoAnn, cniAnn, fattTfoAnn, niAnn, incAnn, percCtrlAnn, commAnn]) => {
            const energiaByM = (energiaAnn && energiaAnn.per_month) || {};
            const tfoByM = (tfoAnn && tfoAnn.per_month) || {};
            const cniByM = (cniAnn && cniAnn.per_month) || {};
            const fattTfoByM = (fattTfoAnn && fattTfoAnn.per_month) || {};
            const niByM = (niAnn && niAnn.per_month) || {};
            const incByM = (incAnn && incAnn.per_month) || {};
            const percCtrlByM = (percCtrlAnn && percCtrlAnn.per_month) || {};
            const commentsByM = (commAnn && commAnn.comments_by_month) || {};

            mesi.forEach(mese => {
                // Energia
                const cellEnergia = table.querySelector(`.energia-value[data-mese="${mese}"]`);
                if (cellEnergia) {
                    const v = energiaByM[mese] ?? energiaByM[String(mese)] ?? null;
                    if (v === null || typeof v === 'undefined') {
                        cellEnergia.textContent = 'NuN';
                    } else {
                        const sum = parseFloat(v) || 0;
                        cellEnergia.textContent = sum === 0 ? '0' : Math.round(sum).toLocaleString('it-IT');
                    }
                }

                // TFO
                const cellTFO = table.querySelector(`.tfo-value[data-mese="${mese}"]`);
                if (cellTFO) {
                    const v = tfoByM[mese] ?? tfoByM[String(mese)] ?? null;
                    console.log(`[DEBUG TFO] Mese: ${mese}, Valore originale: ${v}, Tipo: ${typeof v}`);
                    if (v === null || typeof v === 'undefined') {
                        cellTFO.textContent = 'NuN';
                    } else {
                        const sum = parseFloat(v) || 0;
                        console.log(`[DEBUG TFO] Mese: ${mese}, Valore convertito: ${sum}, Testo finale: ${sum === 0 ? '0 €' : sum.toFixed(2).replace('.', ',') + ' €'}`);
                        cellTFO.textContent = sum === 0 ? '0 €' : sum.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
                    }
                }

                // CNI
                const cellCNI = table.querySelector(`.CNI-value[data-mese="${mese}"]`);
                if (cellCNI) {
                    const v = cniByM[mese] ?? cniByM[String(mese)] ?? null;
                    if (v === null || typeof v === 'undefined') {
                        cellCNI.textContent = 'NuN';
                    } else {
                        const sum = parseFloat(v) || 0;
                        cellCNI.textContent = sum === 0 ? '0' : Math.round(sum).toLocaleString('it-IT');
                    }
                }

                // Fatturazione TFO
                const cellfatturazioneTFO = table.querySelector(`.fatturazione-tfo-value[data-mese="${mese}"]`);
                if (cellfatturazioneTFO) {
                    const v = fattTfoByM[mese] ?? fattTfoByM[String(mese)] ?? null;
                    if (v === null || typeof v === 'undefined') {
                        cellfatturazioneTFO.textContent = 'NuN';
                    } else {
                        const sum = parseFloat(v) || 0;
                        cellfatturazioneTFO.textContent = sum === 0 ? '0 €' : sum.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
                    }
                }

                // Energia non incentivata (altro)
                const cellEnergiaNonIncentivata = table.querySelector(`.fatturazione-altro-value[data-mese="${mese}"]`);
                if (cellEnergiaNonIncentivata) {
                    const v = niByM[mese] ?? niByM[String(mese)] ?? null;
                    if (v === null || typeof v === 'undefined') {
                        cellEnergiaNonIncentivata.textContent = 'NuN';
                    } else {
                        const sum = parseFloat(v) || 0;
                        cellEnergiaNonIncentivata.textContent = sum === 0 ? '0' : sum.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                }

                // Incassi
                const cellIncassi = table.querySelector(`.incassi-value[data-mese="${mese}"]`);
                if (cellIncassi) {
                    const v = incByM[mese] ?? incByM[String(mese)] ?? null;
                    if (v === null || typeof v === 'undefined') {
                        cellIncassi.textContent = 'NuN';
                    } else {
                        const sum = parseFloat(v) || 0;
                        cellIncassi.textContent = sum === 0 ? '0 €' : sum.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
                    }
                }

                // Percentuale/controllo scarto
                const cellPercentualeControllo = table.querySelector(`.controllo-scarto[data-mese="${mese}"]`);
                if (cellPercentualeControllo) {
                    const v = percCtrlByM[mese] ?? percCtrlByM[String(mese)] ?? null;
                    if (v === null || typeof v === 'undefined') {
                        cellPercentualeControllo.textContent = 'NuN €';
                    } else {
                        const val = parseFloat(v) || 0;
                        cellPercentualeControllo.textContent = val.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
                    }
                }

                // Commenti
                const cellCommento = table.querySelector(`.commento-value[data-mese="${mese}"]`);
                if (cellCommento) {
                    const input = cellCommento.querySelector('.js-commento-input');
                    const btn = cellCommento.querySelector('.js-salva-commento');
                    const dataCommento = commentsByM[mese] || commentsByM[String(mese)] || { testo: '', stato: '' };
                    if (input) input.value = dataCommento.testo || '';
                    if (btn && input) {
                        btn.addEventListener('click', function () {
                            const payload = { nickname: nickname, anno: parseInt(anno), mese: mese, testo: input.value };
                            fetch(`/corrispettivi/api/salva-commento/`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(payload)
                            })
                                .then(resp => { if (!resp.ok) throw new Error('Errore risposta server'); return resp.json(); })
                                .then(json => {
                                    if (json && json.success) {
                                        btn.innerHTML = '<i class="fa fa-check" aria-hidden="true"></i>';
                                        setTimeout(() => { btn.innerHTML = '<i class="fa fa-save" aria-hidden="true"></i>'; }, 1200);
                                    } else {
                                        alert('Errore nel salvataggio del commento');
                                    }
                                })
                                .catch(err => {
                                    console.error('Errore salva commento:', err);
                                    alert('Errore nel salvataggio del commento');
                                });
                        });
                    }
                }
            });

            // Aggiorna totali una volta sola dopo il riempimento
            aggiornaTotaleEnergiaAnnuale(table);
            aggiornaTotaleTFOAnnuale(table);
            aggiornaTotaleEnergiaNonIncentivata(table);
            aggiornaTotaleFatturazioneTFOAnnuale(table);
            aggiornaTotaleIncassiAnnuale(table);
        }).catch(err => {
            console.error('Errore caricamento annuale:', err);
        });
    });
});

function aggiornaTotaleEnergiaAnnuale(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.energia-value');
    celle.forEach(td => {
        // Ignora le celle che contengono "NuN" o "Nun"
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        
        // Rimuoviamo i separatori delle migliaia e convertiamo la virgola decimale
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.'));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-energia');
    if (totaleCell) totaleCell.textContent = totale ? totale.toString().replace('.', ',') : '';
}

function aggiornaTotaleTFOAnnuale(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.tfo-value');
   
    celle.forEach(td => {
        // Ignora le celle che contengono "NuN" o "Nun"
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        
        // Rimuoviamo i separatori delle migliaia e il simbolo dell'euro, poi convertiamo la virgola decimale
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.').replace(' €', ''));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-corrispettivo-incentivo');
    if (totaleCell) totaleCell.textContent = totale ? totale.toFixed(2).replace('.', ',') + ' €' : '';
}


function aggiornaTotaleEnergiaNonIncentivata(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.fatturazione-altro-value');
    celle.forEach(td => {
        // Ignora le celle che contengono "NuN" o "Nun"
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        
        // Rimuoviamo i separatori delle migliaia e convertiamo la virgola decimale
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.'));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-fatturazione-altro');
    if (totaleCell) totaleCell.textContent = totale ? totale.toString().replace('.', ',') : '';
}

function aggiornaTotaleFatturazioneTFOAnnuale(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.fatturazione-tfo-value');
    celle.forEach(td => {
        // Ignora le celle che contengono "NuN" o "Nun"
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        
        // Rimuoviamo i separatori delle migliaia e il simbolo dell'euro, poi convertiamo la virgola decimale
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.').replace(' €', ''));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-fatturazione-tfo');
    if (totaleCell) totaleCell.textContent = totale ? totale.toFixed(2).replace('.', ',') + ' €' : '';
}

function aggiornaTotaleIncassiAnnuale(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.incassi-value');
    celle.forEach(td => {
        // Ignora le celle che contengono "NuN" o "Nun"
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        
        // Rimuoviamo i separatori delle migliaia e il simbolo dell'euro, poi convertiamo la virgola decimale
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.').replace(' €', ''));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-incassi');
    if (totaleCell) totaleCell.textContent = totale ? totale.toFixed(2).replace('.', ',') + ' €' : '';
}
