r""" Probe per impianto iSolarCloud: calcolo dell'energia prodotta negli ultimi 12 mesi 

Run: 
    py Produzione\PortaleZilioService\tests_api\isolarcloud\probe_last_12_month_energy_produced.py

"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Aggiungi il percorso del progetto alla variabile di ambiente PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PortaleImpianti_project.settings")
import django
django.setup()


from PortaleZilioService.models import ImpiantoAnagrafica
from PortaleZilioService.models import ImpiantoDispositivo 
from PortaleZilioService.models import ImpiantoSorgenteDati

from PortaleZilioService.services.providers.isc import IscMetricsProvider
from PortaleZilioService.services.windows import rolling_12_months_until_yesterday


def main() -> None: 
    impianti = ImpiantoAnagrafica.objects.filter(
        tipo_impianto = ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO,
        sorgenti_dati__tipo_sorgente = ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
        sorgenti_dati__nome_sorgente = "iSolarCloud",
        sorgenti_dati__attiva = True,
    ).order_by("nome_impianto")

    print(f"Impianti fotovoltaici con sorgente dati iSolarCloud: {impianti.count()}")
    print("-" * 80)
    
    provider = IscMetricsProvider()
    window = rolling_12_months_until_yesterday()
    
    for impianto in impianti: 
        sorgente = impianto.sorgenti_dati.filter(
            tipo_sorgente = ImpiantoSorgenteDati.TipoSorgente.MONITORAGGIO_TECNICO,
            nome_sorgente = "iSolarCloud",
            attiva = True
        ).first()
        
        try: 
            snapshot = provider.fetch_portale_snapshot(impianto, sorgente, window)
            energy = round(snapshot.window_energy_kwh, 2) if snapshot.window_energy_kwh is not None else None
            print(f"{impianto.nome_impianto:<40} energia_kWh: {energy}")
        except Exception as e:
            print(f"{impianto.nome_impianto:<40} ERROR: {e}")
        
    
    
    
    
if __name__ == "__main__":
    main()






'''
Dati restituiti usando i provider all'interno di IscProviderMetrics (02/04/2026 15:16:30)

Impianti fotovoltaici con sorgente dati iSolarCloud: 9
--------------------------------------------------------------------------------
3F - Ferro                               energia_kWh: 315209.9
3F - Plastica                            energia_kWh: 344175.5
Alessi                                   energia_kWh: 1030762.9
CFFT                                     energia_kWh: 2811896.3
Cavarzan                                 energia_kWh: 264360.5
RCT                                      energia_kWh: 251580.8
SIbat Tomarchio                          energia_kWh: 430524.5
Videndum F5                              energia_kWh: 250623.0
Videndum F6                              energia_kWh: 825736.2
'''
