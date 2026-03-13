from django.core.management.base import BaseCommand

from MonitoraggioImpianti.services.isc_sync import sync_isc_impianti


class Command(BaseCommand):
    help = "Sincronizza status, ore equivalenti ed energia annua per gli impianti API_ISC."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Anno da usare per il calcolo dei dati annuali ISC. Default: anno corrente.",
        )
        parser.add_argument(
            "--no-refresh",
            action="store_true",
            help="Non chiama le API iSolarCloud e usa solo il contenuto attuale di plants_data.json.",
        )

    def handle(self, *args, **options):
        result = sync_isc_impianti(
            refresh=not options["no_refresh"],
            year=options["year"],
        )

        self.stdout.write(f"JSON snapshot: {result['json_path']}")
        self.stdout.write(f"Impianti aggiornati: {result['updated']}")
        self.stdout.write(f"Impianti non trovati nello snapshot: {result['skipped']}")

        if result["missing"]:
            self.stdout.write(self.style.WARNING("Impianti senza match:"))
            for name in result["missing"]:
                self.stdout.write(f"- {name}")

        if result["snapshot_refreshed"]:
            self.stdout.write(self.style.SUCCESS("Snapshot ISC aggiornato via API."))
