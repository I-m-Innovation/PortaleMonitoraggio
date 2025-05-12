import ftplib
import xml.etree.ElementTree as ET
import io
import calendar
from datetime import datetime, timedelta
import os

# Credenziali FTP del GME
GME_FTP_USERNAME = "DAMIANOZILIO"  # Rimossi gli spazi superflui
GME_FTP_PASSWORD = "O12L10Z1"

def scarica_dati_pun_mensili(anno, mese, username=None, password=None, cartella_salvataggio=None, stampare_media_dettaglio=True):
    """
    Scarica i dati PUN per un mese specifico dal server FTP del Mercato Elettrico
    e calcola la media mensile.
    
    Args:
        anno (int): Anno di riferimento (es. 2024)
        mese (int): Mese di riferimento (1-12)
        username (str, optional): Nome utente per l'accesso FTP. Se None, usa credenziali predefinite.
        password (str, optional): Password per l'accesso FTP. Se None, usa credenziali predefinite.
        cartella_salvataggio (str, optional): Percorso dove salvare i file XML scaricati
        stampare_media_dettaglio (bool, optional): Se True, stampa la media mensile.
                                                 Default a True.
    
    Returns:
        float or None: Media mensile dei valori PUN, o None se non trovati.
    """
    # Se username o password sono None, usa le credenziali predefinite
    if username is None:
        username = GME_FTP_USERNAME
    if password is None:
        password = GME_FTP_PASSWORD
        
    # Crea la cartella di salvataggio se specificata e non esiste
    if cartella_salvataggio and not os.path.exists(cartella_salvataggio):
        os.makedirs(cartella_salvataggio)
    
    # Calcola il numero di giorni nel mese
    num_giorni = calendar.monthrange(anno, mese)[1]
    
    # Inizializza la connessione FTP
    ftp = ftplib.FTP('download.mercatoelettrico.org')
    ftp.login(username, password)
    
    # Naviga alla cartella corretta
    ftp.cwd('MercatiElettrici/MGP_Prezzi')
    
    valori_pun = []
    
    # Per ogni giorno del mese
    for giorno in range(1, num_giorni + 1):
        # Formatta la data nel formato AAAAMMGGMGP
        data_file = f"{anno}{mese:02d}{giorno:02d}MGPPrezzi.xml"
        
        try:
            # Crea un buffer in memoria per i dati XML
            xml_buffer = io.BytesIO()
            
            # Scarica il file nel buffer
            ftp.retrbinary(f'RETR {data_file}', xml_buffer.write)
            
            # Se richiesto, salva il file XML
            if cartella_salvataggio:
                xml_buffer.seek(0)  # Torna all'inizio del buffer
                with open(os.path.join(cartella_salvataggio, data_file), 'wb') as f:
                    f.write(xml_buffer.getvalue())
            
            # Resetta il puntatore del buffer all'inizio
            xml_buffer.seek(0)
            
            # Analizza il file XML
            tree = ET.parse(xml_buffer)
            root = tree.getroot()
            
            # Trova l'elemento PUN
            pun_element = root.find('.//PUN')
            if pun_element is not None and pun_element.text:
                # Converti il valore da formato italiano (virgola) a float
                valore_pun = float(pun_element.text.replace(',', '.'))
                valori_pun.append(valore_pun)
                print(f"Giorno {giorno}: PUN = {valore_pun}")
            else:
                print(f"Nessun valore PUN trovato per il giorno {giorno}")
                
        except Exception as e:
            print(f"Errore nel scaricare/analizzare il file per il giorno {giorno}: {e}")
    
    # Chiudi la connessione FTP
    ftp.quit()
    
    # Calcola la media se abbiamo dei valori
    if valori_pun:
        media_mensile = sum(valori_pun) / len(valori_pun)
        if stampare_media_dettaglio:
            print(f"\nMedia mensile PUN per {calendar.month_name[mese]} {anno}: {media_mensile:.6f}")
        return media_mensile
    else:
        if stampare_media_dettaglio:
            print(f"Nessun valore PUN trovato per {calendar.month_name[mese]} {anno}")
        return None

def analizza_dati_storici(anno_inizio, username=None, password=None, salva_files=False, cartella_base_salvataggio=None):
    """
    Analizza i dati PUN storici a partire da un anno specifico fino al mese scorso.
    Restituisce un dizionario con le medie mensili.

    Args:
        anno_inizio (int): Anno da cui iniziare l'analisi (es. 2019).
        username (str, optional): Nome utente per l'accesso FTP. Se None, usa credenziali predefinite.
        password (str, optional): Password per l'accesso FTP. Se None, usa credenziali predefinite.
        salva_files (bool): True se si desidera salvare i file XML scaricati.
        cartella_base_salvataggio (str, optional): Percorso base dove salvare le cartelle
                                                  dei file XML mensili. Ignorato se salva_files è False.
    Returns:
        dict: Un dizionario con chiave (anno, mese) e valore la media PUN.
    """
    # Se username o password sono None, usa le credenziali predefinite
    if username is None:
        username = GME_FTP_USERNAME
    if password is None:
        password = GME_FTP_PASSWORD
        
    print(f"\n--- Inizio Analisi Storica Dati PUN dal {anno_inizio} ---")

    oggi = datetime.now()
    # Calcola l'ultimo giorno del mese precedente
    primo_giorno_mese_corrente = oggi.replace(day=1)
    ultimo_giorno_mese_scorso = primo_giorno_mese_corrente - timedelta(days=1) # type: ignore

    anno_fine_reale = ultimo_giorno_mese_scorso.year
    mese_fine_reale = ultimo_giorno_mese_scorso.month

    if anno_inizio > anno_fine_reale:
        print(f"L'anno di inizio ({anno_inizio}) è successivo all'ultimo periodo analizzabile ({mese_fine_reale}/{anno_fine_reale}). Nessuna analisi eseguita.")
        return

    medie_raccolte = {} # Dizionario per conservare le medie: {(anno, mese): media}

    for anno_corrente_analisi in range(anno_inizio, anno_fine_reale + 1):
        mese_inizio_iterazione = 1
        mese_fine_iterazione = 12

        if anno_corrente_analisi == anno_fine_reale:
            mese_fine_iterazione = mese_fine_reale

        for mese_corrente_analisi in range(mese_inizio_iterazione, mese_fine_iterazione + 1):
            print(f"\nAnalisi per: {calendar.month_name[mese_corrente_analisi]} {anno_corrente_analisi}")
            cartella_salvataggio_mese = None
            if salva_files:
                nome_cartella_mese = f"PUN_{anno_corrente_analisi}_{mese_corrente_analisi:02d}"
                if cartella_base_salvataggio:
                    cartella_salvataggio_mese = os.path.join(cartella_base_salvataggio, nome_cartella_mese)
                else:
                    # Salva nella directory corrente dello script, in una sottocartella per quel mese
                    cartella_salvataggio_mese = nome_cartella_mese
            
            media_mensile = scarica_dati_pun_mensili(
                anno_corrente_analisi,
                mese_corrente_analisi,
                username,
                password,
                cartella_salvataggio_mese,
                stampare_media_dettaglio=False # Non stampare la media qui, lo faremo nel riepilogo
            )
            if media_mensile is not None:
                medie_raccolte[(anno_corrente_analisi, mese_corrente_analisi)] = media_mensile
    
    return medie_raccolte

# Esempio di utilizzo
if __name__ == "__main__":
    # Importazione aggiuntiva per analizza_dati_storici
    from datetime import datetime, timedelta

    modalita = input("Vuoi analizzare un 'singolo mese' o fare un''analisi storica'? (singolo/storica): ").lower()

    if modalita == 'singolo':
        anno = int(input("Inserisci l'anno (es. 2024): "))
        mese = int(input("Inserisci il mese (1-12): "))
        
        salva_files_input = input("Vuoi salvare i file XML scaricati? (s/n): ").lower() == 's'
        cartella_salvataggio_singolo = None
        if salva_files_input:
            cartella_salvataggio_singolo = input("Inserisci il percorso dove salvare i file (lascia vuoto per la cartella corrente del mese): ")
            if not cartella_salvataggio_singolo: # Se l'utente preme invio senza scrivere nulla
                cartella_salvataggio_singolo = f"PUN_{anno}_{mese:02d}"
        
        # Usa le credenziali predefinite
        scarica_dati_pun_mensili(anno, mese, GME_FTP_USERNAME, GME_FTP_PASSWORD, cartella_salvataggio_singolo)
    
    elif modalita == 'storica':
        anno_inizio_analisi = int(input("Inserisci l'anno di inizio per l'analisi storica (minimo 2019): "))
        if anno_inizio_analisi < 2019:
            print("L'anno di inizio deve essere almeno 2019.")
        else:
            salva_files_storici_input = input("Vuoi salvare i file XML scaricati durante l'analisi storica? (s/n): ").lower() == 's'
            cartella_base_storica = None
            if salva_files_storici_input:
                cartella_base_storica = input("Inserisci il percorso della cartella base dove salvare i file XML (lascia vuoto per creare sottocartelle nella directory corrente): ")
                if not cartella_base_storica: # Se l'utente preme invio
                    cartella_base_storica = None # Le sottocartelle verranno create nella dir corrente
            
            # Usa le credenziali predefinite
            medie_calcolate = analizza_dati_storici(anno_inizio_analisi, GME_FTP_USERNAME, GME_FTP_PASSWORD, salva_files_storici_input, cartella_base_storica)
            
            print("\n--- Riepilogo Medie Mensili Calcolate ---")
            if medie_calcolate:
                for (anno_media, mese_media), media in medie_calcolate.items():
                    print(f"{calendar.month_name[mese_media]} {anno_media}: {media:.6f}")
            else:
                print("Nessuna media mensile è stata calcolata.")
            print("\n--- Fine Analisi Storica Dati PUN ---")
    else:
        print("Modalità non riconosciuta. Esegui nuovamente lo script e scegli 'singolo' o 'storica'.")
