const cacheTotali = new Map();

document.addEventListener('DOMContentLoaded', function() {
    // console.log('tabellacorrispettivi.js: DOM pronto!');

    const tables = document.querySelectorAll('.js-tabella-corrispettivi');
    if (!tables || tables.length === 0) {
        console.warn('Nessuna tabella .js-tabella-corrispettivi trovata');
        return;
    }

    // console.log(`Trovate ${tables.length} tabelle corrispettivi`);

    // Mappa per tracciare le chiamate API già fatte
    const apiCallsCache = new Map();
    
    // Filtra solo le tabelle valide (con data-anno e data-nickname)
    const tabelleValide = Array.from(tables).filter(table => {
        const anno = table.getAttribute('data-anno');
        const nickname = table.getAttribute('data-nickname');
        if (!anno || !nickname) {
            console.warn('Tabella senza data-anno o data-nickname:', table);
            return false;
        }
        return true;
    });
    
    // console.log(`Tabelle valide da processare: ${tabelleValide.length}`);
    
    // Contatore per tracciare quante tabelle hanno completato il caricamento
    let tabelleCompletate = 0;
    const totaleTabelleAttese = tabelleValide.length;
    
    // Se non ci sono tabelle valide, esci
    if (totaleTabelleAttese === 0) {
        console.warn('[TABELLA CORRISPETTIVI] Nessuna tabella valida trovata');
        return;
    }

    // Funzione per fare chiamate API con cache
    const fetchWithCache = async (url) => {
        if (apiCallsCache.has(url)) {
            return apiCallsCache.get(url);
        }
        
        const promise = fetch(url)
            .then(r => r.json())
            .catch(() => ({ success: false }));
        
        apiCallsCache.set(url, promise);
        return promise;
    };

    tabelleValide.forEach(function(table) {
        const anno = table.getAttribute('data-anno');
        const nickname = table.getAttribute('data-nickname');
        if (!anno || !nickname) {
            console.warn('Tabella senza data-anno o data-nickname:', table);
            return;
        }

        // console.log(`Elaboro tabella per ${nickname} - ${anno}`);

        const mesi = Array.from({ length: 12 }, (_, i) => i + 1);

        // Chiamate annuali con cache
        Promise.all([
            fetchWithCache(`/corrispettivi/api/annuale/energia-kwh/${encodeURIComponent(nickname)}/${anno}/`),
            fetchWithCache(`/corrispettivi/api/annuale/dati-tfo/${encodeURIComponent(nickname)}/${anno}/`),
            fetchWithCache(`/corrispettivi/api/annuale/dati-CNI/${encodeURIComponent(nickname)}/${anno}/`),
            fetchWithCache(`/corrispettivi/api/annuale/dati-fatturazione-tfo/${encodeURIComponent(nickname)}/${anno}/`),
            fetchWithCache(`/corrispettivi/api/annuale/dati-energia-non-incentivata/${encodeURIComponent(nickname)}/${anno}/`),
            fetchWithCache(`/corrispettivi/api/annuale/dati-riepilogo-pagamenti/${encodeURIComponent(nickname)}/${anno}/`),
            fetchWithCache(`/corrispettivi/api/annuale/percentuale-controllo/${encodeURIComponent(nickname)}/${anno}/`),
            fetchWithCache(`/corrispettivi/api/annuale/commenti/${encodeURIComponent(nickname)}/${anno}/`)
        ]).then(([energiaAnn, tfoAnn, cniAnn, fattTfoAnn, niAnn, incAnn, percCtrlAnn, commAnn]) => {
            const energiaByM = (energiaAnn && energiaAnn.per_month) || {};
            const tfoByM = (tfoAnn && tfoAnn.per_month) || {};
            const cniByM = (cniAnn && cniAnn.per_month) || {};
            const fattTfoByM = (fattTfoAnn && fattTfoAnn.per_month) || {};
            const niByM = (niAnn && niAnn.per_month) || {};
            const incByM = (incAnn && incAnn.per_month) || {};
            const percCtrlByM = (percCtrlAnn && percCtrlAnn.per_month) || {};
            const commentsByM = (commAnn && commAnn.comments_by_month) || {};

            // Array per raccogliere tutte le promesse dei fetch PUN
            const punPromises = [];

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

                // PUN (Prezzo Unico Nazionale): Richiama endpoint API dedicato per ciascun mese e aggiorna la cella
                const cellPUN = table.querySelector(`.pun-value[data-mese="${mese}"]`);
                if (cellPUN) {
                    // console.log(`[DEBUG][PUN] Fetching PUN for nickname=${nickname}, anno=${anno}, mese=${mese}`);
                    // Crea la promessa per questo fetch e aggiungila all'array
                    const punPromise = fetch(`/corrispettivi/api/dati-PUN/${encodeURIComponent(nickname)}/${anno}/${mese}/`)
                        .then(r => {
                            // console.log(`[DEBUG][PUN] Fetch response for mese ${mese}:`, r);
                            return r.json();
                        })
                        .then(resp => {
                            // console.log(`[DEBUG][PUN] JSON response for mese ${mese}:`, resp);
                            if (resp && resp.success && Array.isArray(resp.data) && resp.data.length > 0) {
                                // Di solito il backend restituisce una lista di dict con timestamp e mean_pun: prendi il primo
                                let mean_pun = null;
                                if (typeof resp.data[0] === 'object' && resp.data[0] !== null && 'mean_pun' in resp.data[0]) {
                                    mean_pun = resp.data[0].mean_pun;
                                    // console.log(`[DEBUG][PUN] mean_pun from object for mese ${mese}:`, mean_pun);
                                } else if (!isNaN(resp.data[0])) {
                                    mean_pun = resp.data[0];
                                    // console.log(`[DEBUG][PUN] mean_pun from direct value for mese ${mese}:`, mean_pun);
                                }
                                if (mean_pun === null || typeof mean_pun === 'undefined') {
                                    cellPUN.textContent = 'NuN';
                                    // console.log(`[DEBUG][PUN] mean_pun is null or undefined for mese ${mese}, set to 'NuN'`);
                                } else {
                                    const sum = parseFloat(mean_pun) || 0;
                                    cellPUN.textContent = sum === 0 ? '0 €' : sum.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
                                    // console.log(`[DEBUG][PUN] mean_pun parsed as ${sum}, set cell text to:`, cellPUN.textContent);
                                }
                            } else {
                                cellPUN.textContent = 'NuN';
                                // console.log(`[DEBUG][PUN] Response invalid or empty for mese ${mese}, set to 'NuN'`);
                            }
                        })
                        .catch((err) => {
                            cellPUN.textContent = 'NuN';
                            console.error(`[DEBUG][PUN] Error fetching or parsing response for mese ${mese}:`, err);
                        });
                    // Aggiungi la promessa all'array
                    punPromises.push(punPromise);
                }

                // TFO
                const cellTFO = table.querySelector(`.tfo-value[data-mese="${mese}"]`);
                if (cellTFO) {
                    const v = tfoByM[mese] ?? tfoByM[String(mese)] ?? null;
                    if (v === null || typeof v === 'undefined') {
                        cellTFO.textContent = 'NuN';
                    } else {
                        const sum = parseFloat(v) || 0;
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
                        cellCNI.textContent = sum === 0 ? '0 €' : Math.round(sum).toLocaleString('it-IT') + ' €';
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
                        cellEnergiaNonIncentivata.textContent = sum === 0 ? '0 €' : sum.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
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

            // Aggiorna totali una volta sola dopo il riempimento di questa tabella annuale
            aggiornaTotaleEnergiaAnnuale(table);
            aggiornaTotaleTFOAnnuale(table);
            aggiornaTotaleCNIAncellCNI(table);
            aggiornaTotaleEnergiaNonIncentivata(table);
            aggiornaTotaleFatturazioneTFOAnnuale(table);
            aggiornaTotaleIncassiAnnuale(table);
            aggiornaTotaleControlloPercentualeAnnuale(table);
            
            // Attendi che tutti i fetch PUN siano completati prima di calcolare il totale
            Promise.all(punPromises).then(() => {
                aggiornaTotalePUNAnnuale(table);
            }).catch(() => {
                // Anche in caso di errore, prova comunque a calcolare il totale con i dati disponibili
                aggiornaTotalePUNAnnuale(table);
            });
            
            // Incrementa il contatore e controlla se tutte le tabelle sono state processate
            tabelleCompletate++;
            // console.log(`[TABELLA CORRISPETTIVI] Tabella ${tabelleCompletate}/${totaleTabelleAttese} completata`);
            
            if (tabelleCompletate === totaleTabelleAttese) {
                // Tutte le tabelle sono state caricate, emetti l'evento
                // console.log('[TABELLA CORRISPETTIVI] Tutte le tabelle caricate, emetto evento');
                calcolaEmettiTotaliComplessivi(tables);
            }

        }).catch(err => {
            console.error('Errore caricamento annuale:', err);
            
            // Anche in caso di errore, incrementa il contatore
            tabelleCompletate++;
            if (tabelleCompletate === totaleTabelleAttese) {
                // console.log('[TABELLA CORRISPETTIVI] Tutte le tabelle processate (con errori), emetto evento');
                calcolaEmettiTotaliComplessivi(tables);
            }
        });
    });

}); 

// Calcola totali di tutte le tabelle ed emette evento 'totaliAnnualiCaricati'
function calcolaEmettiTotaliComplessivi(tables) {
    const totaliAnnuali = [];

    tables.forEach(table => {
        // Queste chiamate sono necessarie per popolare i totali (es. .totale-energia) che la funzione estraiTotale andrà a leggere.
        aggiornaTotaleEnergiaAnnuale(table);
        aggiornaTotaleTFOAnnuale(table);
        aggiornaTotaleFatturazioneTFOAnnuale(table);
        aggiornaTotaleIncassiAnnuale(table);

        const anno = parseInt(table.getAttribute('data-anno'));
        const energia = estraiTotale(table, '.totale-energia');
        const tfo = estraiTotale(table, '.totale-corrispettivo-incentivo');
        const cni = estraiTotale(table, '.totale-CNI') || 0; // Assumi 0 se non calcolabile/selettore non trovato
        const fatturazione = estraiTotale(table, '.totale-fatturazione-tfo');
        const pagamenti = estraiTotale(table, '.totale-incassi');

        totaliAnnuali.push({
            anno, energia, tfo, cni, fatturazione, pagamenti
        });
    });

    // Filtra per dati validi e ordina per anno
    const totaliFiltrati = totaliAnnuali.filter(t => t.anno && (t.energia > 0 || t.tfo > 0 || t.fatturazione > 0));
    totaliFiltrati.sort((a, b) => a.anno - b.anno);

    // Emetti l'evento UNA SOLA VOLTA con tutti i dati
    window.dispatchEvent(new CustomEvent('totaliAnnualiCaricati', {
        detail: { totaliAnnuali: totaliFiltrati }
    }));
    console.log('Evento totaliAnnualiCaricati emesso con:', totaliFiltrati);
}

// Estrae il valore numerico da una cella del totale, pulendola da formattazione.
function estraiTotale(table, selector) {
    const cella = table.querySelector(selector);
    if (!cella) return 0;
    const testo = cella.textContent.trim();
    if (!testo || testo === 'NuN' || testo === 'Nun') return 0;
    // Pulisce da punti (separatore migliaia), sostituisce virgola (separatore decimale) con punto, rimuove ' €'
    const valore = parseFloat(testo.replace(/\./g, '').replace(',', '.').replace(' €', ''));
    return isNaN(valore) ? 0 : valore;
}

// Aggiorna totali annuali energia
function aggiornaTotaleEnergiaAnnuale(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.energia-value');
    celle.forEach(td => {
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.'));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-energia');
    if (totaleCell) totaleCell.textContent = totale ? totale.toString().replace('.', ',') : '';
}

function aggiornaTotaleCNIAncellCNI(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.CNI-value');
    celle.forEach(td => {
        // Ignora le celle che contengono "NuN" o "Nun"
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        
        // Rimuoviamo i separatori delle migliaia e convertiamo la virgola decimale
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.'));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-CNI');
    if (totaleCell) totaleCell.textContent = totale ? totale.toString().replace('.', ',') + ' €' : '';
}

// Aggiorna totali annuali TFO
function aggiornaTotaleTFOAnnuale(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.tfo-value');
    celle.forEach(td => {
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.').replace(' €', ''));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-corrispettivo-incentivo');
    if (totaleCell) totaleCell.textContent = totale ? totale.toFixed(2).replace('.', ',') + ' €' : '';
}

// Aggiorna totali annuali energia non incentivata
function aggiornaTotaleEnergiaNonIncentivata(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.fatturazione-altro-value');
    celle.forEach(td => {
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.'));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-fatturazione-altro');
    if (totaleCell) totaleCell.textContent = totale ? totale.toFixed(2).replace('.', ',') + ' €' : '';
}

// Aggiorna totali annuali fatturazione TFO
function aggiornaTotaleFatturazioneTFOAnnuale(table) {
    let totale = 0;
    const celle = table.querySelectorAll('.fatturazione-tfo-value');
    celle.forEach(td => {
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
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
        if (td.textContent === 'NuN' || td.textContent === 'Nun') return;
        const v = parseFloat(td.textContent.replace(/\./g, '').replace(',', '.').replace(' €', ''));
        if (!isNaN(v)) totale += v;
    });
    const totaleCell = table.querySelector('.totale-incassi');
    if (totaleCell) totaleCell.textContent = totale ? totale.toFixed(2).replace('.', ',') + ' €' : '';
}

function aggiornaTotaleControlloPercentualeAnnuale(table) {
    // Helper per estrarre valore float da una cella (pulisce simboli, spazi, ecc.)
    function estraiValoreFloat(cell, removeEuro = false) {
        if (!cell) return 0;
        let text = cell.textContent.trim();
        if (text === 'NuN' || text === 'Nun' || text === '') return 0;
        if (removeEuro) text = text.replace(' €', '');
        text = text.replace(/\./g, '').replace(',', '.');
        const v = parseFloat(text);
        return isNaN(v) ? 0 : v;
    }

    // Prendi i totali dalle rispettive celle
    const incassiCell = table.querySelector('.totale-incassi');
    const corrIncentivoCell = table.querySelector('.totale-corrispettivo-incentivo');
    const totaleCniCell = table.querySelector('.totale-CNI');
    // (Nota: Se manca, considera 0)

    const totaleIncassi = estraiValoreFloat(incassiCell, true);
    const totaleCorrIncentivo = estraiValoreFloat(corrIncentivoCell, true);
    const totaleCni = estraiValoreFloat(totaleCniCell);

    const scarto = totaleIncassi - totaleCorrIncentivo - totaleCni;
    const totaleCell = table.querySelector('.totale-controllo-percentuale');
    if (totaleCell) {
        if (Number.isFinite(scarto) && Math.abs(scarto) >= 0.005) {
            // Mostra due decimali, separatore italiano, con segno se negativo
            totaleCell.textContent = scarto.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).replace('.', ',') + ' €';
        } else {
            totaleCell.textContent = '';
        }
    }
}

function aggiornaTotalePUNAnnuale(table) {
    let totale = 0.0;
    const celle = table.querySelectorAll('.pun-value');

    celle.forEach(td => {
        let text = td.textContent.trim();

        // ignora valori non validi
        if (!text || text.toLowerCase() === 'nun') return;

        // Rimuove il simbolo "€" se presente, rimuove punti (migliaia) e converte virgola in punto decimale
        text = text.replace(' €', '').replace(/\./g, '').replace(',', '.');

        const v = parseFloat(text);

        if (!isNaN(v)) {
            totale += v;
        }
    });

    const totaleCell = table.querySelector('.totale-pun');
    if (totaleCell) {
        // Mostra come real con due decimali, separatore italiano, e simbolo euro
        totaleCell.textContent = totale
            ? totale.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'
            : '';
    }
}