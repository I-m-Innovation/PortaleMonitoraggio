from MonitoraggioImpianti.models import *
import pandas as pd


if __name__=='__main__':
	impianti = Impianto.objects.values()
	df = pd.DataFrame(impianti)
	df.to_excel('Impianti.xlsx', index=False)