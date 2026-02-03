import pandas as pd

from PortaleCorrispettivi.models import *

if __name__ == '__main__':
	df = pd.read_excel('commenti.xlsx',header=0)
	records = [
		Commento(
			id=row['id'],
			testo=row['testo'],
			mese_misura=row['mese_misura'],
			impianto=Impianto.objects.get(nickname=row['impianto']),
			stato=row['stato']
		) for index, row in df.iterrows()
	]
	Commento.objects.bulk_create(records)
