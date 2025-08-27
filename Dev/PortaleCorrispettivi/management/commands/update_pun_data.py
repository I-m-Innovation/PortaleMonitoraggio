from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from PortaleCorrispettivi.models import PunMonthlyData
from PortaleCorrispettivi.APIgme import scarica_dati_pun_mensili, GME_FTP_USERNAME, GME_FTP_PASSWORD
import calendar

class Command(BaseCommand):
    help = 'Aggiorna i dati PUN nel database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forza il download e aggiornamento di tutti i dati',
        )

    def handle(self, *args, **options):
        force_update = options['force']
        oggi = datetime.now()
        
        # Aggiorna dati degli ultimi 3 anni
        anni_da_aggiornare = [oggi.year, oggi.year - 1, oggi.year - 2]
        
        for anno in anni_da_aggiornare:
            # Per l'anno corrente, aggiorna solo fino al mese corrente
            mesi_da_aggiornare = range(1, oggi.month + 1) if anno == oggi.year else range(1, 13)
            
            for mese in mesi_da_aggiornare:
                self.stdout.write(f"Verifica dati PUN per {mese}/{anno}...")
                
                # Controlla se i dati sono già presenti e aggiornati (ultimi 30 giorni)
                dati_esistenti = False
                if not force_update:
                    try:
                        pun_data = PunMonthlyData.objects.get(anno=anno, mese=mese)
                        if pun_data.ultima_modifica > timezone.now() - timedelta(days=30):
                            self.stdout.write(f"Dati per {mese}/{anno} già aggiornati, salto.")
                            dati_esistenti = True
                    except PunMonthlyData.DoesNotExist:
                        pass
                
                # Se i dati non esistono o forziamo l'aggiornamento
                if not dati_esistenti or force_update:
                    self.stdout.write(f"Download dati PUN per {mese}/{anno}...")
                    try:
                        media = scarica_dati_pun_mensili(
                            anno, mese, GME_FTP_USERNAME, GME_FTP_PASSWORD, 
                            stampare_media_dettaglio=False, force_download=True
                        )
                        if media is not None:
                            self.stdout.write(self.style.SUCCESS(f"Dati PUN per {mese}/{anno} aggiornati: {media:.6f}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"Nessun dato PUN trovato per {mese}/{anno}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Errore durante il download dei dati PUN per {mese}/{anno}: {e}")) 