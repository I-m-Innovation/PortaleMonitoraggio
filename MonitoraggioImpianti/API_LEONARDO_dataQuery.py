import requests
import json
from datetime import datetime, timedelta
import time
import pandas as pd
from functools import reduce


def login_LEO():

	headers = {
		'Accept': 'application/json',
		'Content-Type': 'application/json'
	}

	param = {
		'username': 'tecnico@zilioservice.com',
		'password': '6j0LdUmjI2'
	}

	param = json.dumps(param)
	# headers = json.dumps(headers)
	URL = 'https://myleonardo.western.it/api/login/'

	resp = requests.post(URL, data=param, headers=headers)
	resp = resp.json()
	# token = resp["result_data"]["token"]

	return resp


def get_leo_data(token):

	dfNew = pd.DataFrame()
	oldDB = pd.read_csv('DBZG.csv')
	AllDB = oldDB

	try:
		Now = datetime.now()
		last_t_stored = datetime.strptime(oldDB["t"].iloc[-1], "%Y-%m-%d %H:%M:%S")

		# qua devo inserire come tstart l'ultimo + dt
		t_start = last_t_stored + timedelta(minutes=5)
		t_end = t_start + timedelta(days=2)
		t_start_epoch = int(time.mktime(t_start.timetuple()))
		t_end_epoch = int(time.mktime(t_end.timetuple()))

		df = pd.DataFrame()

		while t_end <= Now+timedelta(days=1):
			# t_end = int(time.mktime(Now.timetuple()))
			print(t_start, t_end)

			headers = {
				'Accept': 'application/json',
				'Authorization': 'Token ' + token
			}

			param = {
				"date_from": t_start_epoch,
				"date_to": t_end_epoch,
				"type": "B"
			}

			URL = 'https://myleonardo.western.it/api/external/advanced/0019816425961B0C/'
			# param = json.dumps(param)
			resp = requests.get(URL, params=param, headers=headers)

			dt = json.loads(resp.content)
			dfNew = pd.DataFrame(dt['data'])
			df = pd.concat([df, dfNew], ignore_index=True)

			t_start = t_end
			t_end = t_end + timedelta(days=2)
			t_start_epoch = int(time.mktime(t_start.timetuple()))
			t_end_epoch = int(time.mktime(t_end.timetuple()))
			Assorbita = dfNew["avgPacPV"] - dfNew["avgPacGrid"] - dfNew["avgPbat"]
			newDB = {
				"t": pd.to_datetime(dfNew["Stime"]), "PAC_PV": dfNew["avgPacPV"], "P_BESS": dfNew["avgPbat"],
				"P_Grid": dfNew["avgPacGrid"], "IBat": dfNew["Ibat"], "TBat": dfNew["Tbat"], "VBat": dfNew["Vbat"],
				"Soc": dfNew["SoC"], "FreqIn": dfNew["FacIn"], "FreqOut": dfNew["FacOut"], "nCicli": dfNew["nCicli"],
				"Assorbita": Assorbita
			}

			newDBdf = pd.DataFrame(newDB)
			AllDB = pd.concat([oldDB, newDBdf])
			AllDB.to_csv("DBZG.csv", index=False)

	except Exception as e:
		print(e)

	return