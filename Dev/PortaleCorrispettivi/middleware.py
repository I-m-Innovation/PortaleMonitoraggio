from datetime import datetime, timedelta
from django.utils import timezone
import threading
from django.conf import settings
from .models import PunMonthlyData
from .APIgme import scarica_dati_pun_mensili, GME_FTP_USERNAME, GME_FTP_PASSWORD

class PunUpdateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Flag per evitare aggiornamenti multipli simultanei
        self.updating = False
        # Timestamp dell'ultimo controllo
        self.last_check = None
        # Intervallo tra i controlli (6 ore)
        self.check_interval = getattr(settings, 'PUN_CHECK_INTERVAL', timedelta(hours=6))

    def __call__(self, request):
        # Esegui l'aggiornamento solo su richieste di GET che non siano file statici o admin
        if (request.method == 'GET' and 
            not request.path.startswith('/admin/') and 
            not request.path.startswith('/static/') and
            not request.path.startswith('/media/')):
            
            # Verifica se è necessario controllare gli aggiornamenti
            now = timezone.now()
            if (not self.last_check or 
                (now - self.last_check) > self.check_interval):
                
                self.last_check = now
                
                # Avvia l'aggiornamento in un thread separato per non bloccare la richiesta
                if not self.updating:
                    self.updating = True
                    thread = threading.Thread(target=self.check_and_update_pun_data)
                    thread.daemon = True
                    thread.start()
        
        response = self.get_response(request)
        return response
    
    def check_and_update_pun_data(self):
        try:
            # Verifica i dati degli ultimi 3 anni
            oggi = datetime.now()
            anni_da_verificare = [oggi.year, oggi.year - 1, oggi.year - 2]
            
            for anno in anni_da_verificare:
                # Per l'anno corrente, verifica solo fino al mese corrente
                mesi_da_verificare = range(1, oggi.month + 1) if anno == oggi.year else range(1, 13)
                
                for mese in mesi_da_verificare:
                    # Controlla se i dati devono essere aggiornati (più vecchi di 7 giorni)
                    try:
                        pun_data = PunMonthlyData.objects.get(anno=anno, mese=mese)
                        if pun_data.ultima_modifica < timezone.now() - timedelta(days=7):
                            # Aggiorna i dati se sono più vecchi di 7 giorni
                            scarica_dati_pun_mensili(
                                anno, mese, GME_FTP_USERNAME, GME_FTP_PASSWORD, 
                                stampare_media_dettaglio=False, force_download=True
                            )
                            print(f"Dati PUN aggiornati automaticamente per {mese}/{anno}")
                    except PunMonthlyData.DoesNotExist:
                        # Se i dati non esistono, scaricali
                        scarica_dati_pun_mensili(
                            anno, mese, GME_FTP_USERNAME, GME_FTP_PASSWORD, 
                            stampare_media_dettaglio=False, force_download=False
                        )
                        print(f"Dati PUN scaricati automaticamente per {mese}/{anno}")
        finally:
            self.updating = False 