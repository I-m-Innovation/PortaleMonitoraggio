from PortaleCorrispettivi.models import *
import pandas as pd

if __name__ == '__main__':
	df = pd.read_excel('impianti.xlsx')

	records = [
		Impianto(
			id=row['id'],
			nickname=row['nickname'],
			societa=row['societa'],
			nome_impianto=row['nome_impianto'],
			tag=row['tag'],
			tipo=row['tipo'],
			lat=row['lat'],
			lon=row['lon'],
			unita_misura=row['unita_misura'],
			localita=row['localita'],
			portata_concessione=row['portata_concessione'],
			salto=row['salto'],
			potenza_installata=row['potenza_installata'],
			lettura_dati=row['lettura_dati'],
			proprieta=row['proprieta'],
		)
		for index, row in df.iterrows()
	]
	Impianto.objects.bulk_create(records)