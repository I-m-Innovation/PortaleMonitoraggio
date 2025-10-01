from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

from MonitoraggioImpianti.utils import functions as fn
from MonitoraggioImpianti.models import *

import pandas as pd
import numpy as np
from datetime import datetime


class ChartData(APIView):
	renderer_classes = [JSONRenderer]
	permission_classes = (IsAuthenticated,)

	def get(self, request, nickname, format=None):
		impianto = Impianto.objects.filter(nickname=nickname)[0]
		time_series_year_file = impianto.filemonitoraggio_set.filter(tipo='YearTL')[0]
		try:
			df_TS = fn.read_DATA(time_series_year_file.cartella, str(time_series_year_file), nickname)
			df_TS['t'] = pd.to_datetime(df_TS.t)

		except:
			return

		Now = datetime.now()
		today = datetime(Now.year, Now.month, Now.day,0,0,0)
		current_month = datetime(today.year, today.month, 1)
		today_indexes = np.where(df_TS['t']>=today)[0]
		today_max = df_TS.P[today_indexes].max()
		current_month_indexes = np.where(df_TS['t'] >= current_month)[0]
		month_max = df_TS.P[current_month_indexes].max()
		year_max = df_TS.P.max()

		df_TS['t'] = df_TS['t'].dt.strftime('%d/%m/%Y %H:%M')
		df_TS['Eta'] = df_TS['Eta'] * 100

		Chart_data = {
			'time': df_TS.t,
			'pot': df_TS.P.fillna(''),
			'eta': df_TS.Eta.fillna(''),
			'today_max': today_max,
			'month_max': month_max,
			'year_max': year_max
		}

		if impianto.unita_misura == 'l/s':
			df_TS['Q'] = df_TS['Q'] * 1000

		Chart_data['port'] = df_TS.Q.fillna('')
		Chart_data['pres'] = df_TS.Bar.fillna('')
		return Response(Chart_data)
