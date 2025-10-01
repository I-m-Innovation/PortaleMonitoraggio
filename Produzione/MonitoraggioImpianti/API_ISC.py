import time

import requests
import json
from datetime import datetime,timedelta
import pandas as pd
from functools import reduce


plant_keys = {
	'Videndum F6': 5419300,
	'Videndum F5': 5413906,
	'Alessi': 5316735,
	'Cavarzan': 5297443,
	'HII - GATE 1': 5086460,
	'HII - Tetto': 5086074,
	'HII - GATE 2': 5086064,
	'3F - Ferro': 5079244,
	'3F - Plastica': 5079150,
	'Sibat Tomarchio': 5483816,
	'RCT': 5488121,
	'CFFT': 5646781
}


# nome --> ps_key
inv_keys = {
	'Videndum F6': ['5419300_1_2_1', '5419300_1_5_1', '5419300_1_1_1', '5419300_1_4_1', '5419300_1_3_1', '5419300_1_6_1'],
	'Videndum F5': ['5413906_1_2_1', '5413906_1_1_1', '5413906_1_3_1'],
	'Alessi': ['5316735_1_7_8', '5316735_1_6_8', '5316735_1_5_8', '5316735_1_4_8', '5316735_1_3_8', '5316735_1_2_8', '5316735_1_1_8'],
	'Cavarzan': ['5297443_1_7_1', '5297443_1_6_1', '5297443_1_5_1', '5297443_1_4_1', '5297443_1_3_1', '5297443_1_2_1', '5297443_1_1_1'],
	'HII - GATE 1': [],
	'HII - Tetto': [],
	'HII - GATE 2': [],
	'3F - Ferro': ['5079244_1_1_1', '5079244_1_2_1', '5079244_1_3_1'],
	'3F - Plastica': ['5079150_1_9_1', '5079150_1_5_1', '5079150_1_8_1', '5079150_1_4_1', '5079150_1_7_1', '5079150_1_3_1', '5079150_1_6_1'],
	'Sibat Tomarchio': ['5483816_1_2_1', '5483816_1_1_1', '5483816_1_3_1'],
	'RCT': ['5488121_1_1_5', '5488121_1_2_5'],
	'CFFT': ['5646781_1_2_1', '5646781_1_11_1', '5646781_1_9_1', '5646781_1_5_1', '5646781_1_14_1',
			 '5646781_1_10_1', '5646781_1_16_1', '5646781_1_3_1', '5646781_1_12_1', '5646781_1_6_1', '5646781_1_15_1',
			 '5646781_1_8_1', '5646781_1_4_1', '5646781_1_13_1', '5646781_1_7_1']
}


def login_ISC():

	headers = {
		"accept": "application/json",
		"x-access-key": 'dpiixeb8cnn34widwp7ihg5nzfb8eybw',
		"sys_code": '901',
		"Content-Type": "application/json"
	}

	param = {
		"appkey": 'AAA324AF620903ED6ECCDDEA0B6BC866',
		"user_account": 'tecnico@zilioservice.com',
		"user_password": "monitorinG_eesco22",
		"lang": "_it_IT"
	}

	param = json.dumps(param)
	# headers = json.dumps(headers)
	URL = 'https://gateway.isolarcloud.eu/openapi/login'

	resp = requests.post(URL, headers=headers, data=param)
	resp = resp.json()
	# token = resp["result_data"]["token"]
	return resp


def getPlantList(token):
	headers = {
		"accept": "application/json",
		"x-access-key": 'dpiixeb8cnn34widwp7ihg5nzfb8eybw',
		"sys_code": '901',
		"Content-Type": "application/json"
	}

	param = {
		"appkey": 'AAA324AF620903ED6ECCDDEA0B6BC866',
		"token": token,
		"curPage": "1",
		"size": "10",
	}
	param = json.dumps(param)
	# headers = json.dumps(headers)
	URL = 'https://gateway.isolarcloud.eu/openapi/getPowerStationList'
	resp = requests.post(URL, headers=headers, data=param)
	resp = resp.json()
	# token = resp["result_data"]["token"]
	return resp


def plantDetail(token, PlantID):
	headers = {
		"accept": "application/json",
		"x-access-key": 'dpiixeb8cnn34widwp7ihg5nzfb8eybw',
		"sys_code": '901',
		"Content-Type": "application/json"
	}

	param = {
		"appkey": 'AAA324AF620903ED6ECCDDEA0B6BC866',
		"token": token,
		"ps_id": PlantID,
	}

	param = json.dumps(param)
	# headers = json.dumps(headers)

	URL = 'https://gateway.isolarcloud.eu/openapi/getPowerStationDetail'
	resp = requests.post(URL, headers=headers, data=param)
	resp = resp.json()
	# token = resp["result_data"]["token"]
	return resp


def DeviceList(token, PlantID):
	URL = 'https://gateway.isolarcloud.eu/openapi/getDeviceList'
	headers = {
		"accept": "application/json",
		"x-access-key": 'dpiixeb8cnn34widwp7ihg5nzfb8eybw',
		"sys_code": '901',
		"Content-Type": "application/json"
	}

	param = {
		"appkey": 'AAA324AF620903ED6ECCDDEA0B6BC866',
		"token": token,
		"ps_id": PlantID,
		"curPage": "1",
		"size": "32",
	}

	param = json.dumps(param)
	# headers = json.dumps(headers)
	resp = requests.post(URL, headers=headers, data=param)
	resp = resp.json()
	return resp


def PlantData_3h(t_in, t_out, token, INV_keysList, PlantID):
	ps_id = PlantID
	keys = INV_keysList
	URL = 'https://gateway.isolarcloud.eu/openapi/getDevicePointMinuteDataList'
	start =t_in
	end =t_out

	headers = {
		"accept": "application/json",
		"x-access-key": 'dpiixeb8cnn34widwp7ihg5nzfb8eybw',
		"sys_code": '901',
		"Content-Type": "application/json"
	}

	end_time_stamp = end.strftime("%Y%m%d%H%M%S")
	start_time_stamp = start.strftime("%Y%m%d%H%M%S")

	param = {
		"appkey": 'AAA324AF620903ED6ECCDDEA0B6BC866',
		"token": token,
		"ps_id": ps_id,
		"ps_key_list": keys,
		"start_time_stamp": start_time_stamp,
		"end_time_stamp": end_time_stamp,
		"points": "p24",
	}

	param = json.dumps(param)
	# headers = json.dumps(headers)

	resp = requests.post(URL, headers=headers, data=param)
	resp = resp.json()
	return resp


# crea una lista di intervalli 'delta' (tre ore) da 'start' a 'end'
def deltatime(start, end, delta):
	curr = start
	list = []
	while curr < end:
		list.append(curr)
		curr += delta
	list.append(end)
	return [[list[i], list[i + 1]] for i in range(len(list) - 1)]


def inv_status(token, INV_keysList):
	keys = INV_keysList
	URL = 'https://gateway.isolarcloud.eu/openapi/getPVInverterRealTimeData'

	headers = {
		"accept": "application/json",
		"x-access-key": 'dpiixeb8cnn34widwp7ihg5nzfb8eybw',
		"sys_code": '901',
		"Content-Type": "application/json"
	}

	param = {
		"appkey": 'AAA324AF620903ED6ECCDDEA0B6BC866',
		"token": token,
		'ps_key_list': keys
	}
	param = json.dumps(param)
	resp = requests.post(URL, headers=headers, data=param)
	resp = resp.json()
	# token = resp["result_data"]["token"]
	return resp


def getDATA(impianto, start, end):
# if __name__ == '__main__':
	# LOGIN API E GET TOKEN
	delay = 1.5
	try:
		login_resp = login_ISC()
		time.sleep(delay)
		token = login_resp["result_data"]["token"]
	except Exception as error:
		print("Errore LOGIN:", type(error).__name__, "–", error)
		return

	# IDs DEVICES (SALVATI SOPRA)
	# resp = getPlantList(token)
	# deviceList_resp = DeviceList(token,plant_keys[Impianto])
	# devices = {}
	# devices_keyList = []
	# for item in deviceList_resp['result_data']['pageList']:
	# 	devices[item['device_name']] = {'ps_id':item['ps_id'],
	# 	                                'ps_key' :item['ps_key']
	# 	                                }
	# 	devices_keyList = [devices[name]['ps_key'] for name in devices if name[:-1]=='Inverter']

	# STATO INVERTERS IMPIANTO
	try:
		status_resp = inv_status(token, inv_keys[impianto])['result_data']['device_point_list']
		time.sleep(delay)
		plant_status = []
		# CREAZIONE DATAFRAME CON I VARI STATI DEGLI INVERTER
		for item in status_resp:
			dz = item['device_point']
			plant_status.append(
				{'inv_key': dz['ps_key'], 'dev_fault_status': dz['dev_fault_status'], 'dev_status': dz['dev_status']}
			)
		df_plant_status = pd.DataFrame(plant_status)

	except Exception as error:
		print('Errore inv_status', type(error).__name__, error)
		return

	# INTERVALLI DI 3H
	steps = deltatime(start, end, timedelta(hours=3))

	try:
		# CREO IL DIZIONARIO CON I DATI PER OGNI INVERTER
		data = {}
		for inv in inv_keys[impianto]:
			data[inv] = []
		for k in range(len(steps)):
			# RICHIESTA DATI DI POTENZA
			ans_dict = PlantData_3h(steps[k][0], steps[k][1], token, inv_keys[impianto], plant_keys[impianto])['result_data']
			time.sleep(delay)
			# POPOLO IL DIZIONARIO CON I DATI RICAVATI
			for inv_key, values in ans_dict.items():
				data[inv_key].append(values)
		for inv_key in inv_keys[impianto]:
			data[inv_key] = [x for y in data[inv_key] for x in y]

	except Exception as error:
		print("Errore data 3h:", type(error).__name__, "–", error)
		return

	# RIMODULO LA STRUTTURA DEI DAI PER CREARE UN DIZIONARIO DEL TIPO
	# {inv_key: {'t': [lista_timestamps], 'Power_inv_key': [lista valori potenza]}}
	db = {}
	for inv_key in inv_keys[impianto]:
		db[inv_key] = {}
		db[inv_key]['t'] = []
		db[inv_key]['Power_'+inv_key] = []
		for record in data[inv_key]:
			db[inv_key]['Power_'+inv_key].append(float(record['p24']))
			db[inv_key]['t'].append(datetime.strptime(record['time_stamp'], '%Y%m%d%H%M%S'))

	# elimino eventuali duplicati orari
	frames = [pd.DataFrame(db[inv_key]).drop_duplicates() for inv_key in inv_keys[impianto]]
	# UNISCO I VARI DATI UN DATAFRAME UNICO
	df_merged = reduce(lambda left, right: pd.merge(left, right, on=['t'], how='outer'), frames)
	df_merged.iloc[:, 1:] = df_merged.iloc[:, 1:] / 1000

	# LINEA DI POTENZA TOTALE DELL'IMPIANTO
	df_merged['Total'] = df_merged.iloc[:, 1:].sum(axis=1)

	return df_merged[['t', 'Total']], df_plant_status

