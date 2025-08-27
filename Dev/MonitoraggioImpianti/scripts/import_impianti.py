from MonitoraggioImpianti.models import *
import pandas as pd
# import os
# dir_path = os.path.dirname(os.path.realpath(__file__))


if __name__=='__main__':
	# print(dir_path)
	df = pd.read_excel('info_impianti.xlsx')
	df['societa'].fillna('-', inplace=True)
	df['localita'].fillna('-', inplace=True)
	df['portata_concessione'].fillna(0, inplace=True)
	df['salto'].fillna(0, inplace=True)
	df['potenza_installata'].fillna(0, inplace=True)
	records = [
		Impianto(
			nickname=row['nickname'],
			societa=row['societa'],
			nome_impianto=row['nome_impianto'],
			tag=row['tag'],
			tipo=row['tipo_impianto'],
			lat=row['latitudine'],
			lon=row['longitudine'],
			localita=row['localita'],
			portata_concessione=row['portata_concessione'],
			salto=row['salto'],
			potenza_installata=row['potenza_installata'],
			lettura_dati=row['lettura_dati'],
			proprieta=row['proprieta'] == 'zilio',
		) for i, row in df.iterrows()
	]
	Impianto.objects.bulk_create(records)