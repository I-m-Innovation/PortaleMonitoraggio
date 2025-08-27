import numpy as np
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


def get_leo_data(t_start, t_end):
    token = login_LEO()['token']
    df = pd.DataFrame()

    delta = t_end - t_start
    t_curr_end = t_start + delta
    t_start_epoch = int(time.mktime(t_start.timetuple()))
    t_end_epoch = int(time.mktime(t_curr_end.timetuple()))

    headers = {
        'Accept': 'application/json',
        'Authorization': 'Token ' + token
    }

    param = {
        "date_from": t_start_epoch,
        "date_to": t_end_epoch,
        "type": "C"
    }

    URL = 'https://myleonardo.western.it/api/external/advanced/0019816425961B0C/'
    # param = json.dumps(param)
    resp = requests.get(URL, params=param, headers=headers)
    start = time.process_time()
    content = json.loads(resp.content)
    curr_df = pd.DataFrame(content['data'])
    # curr_df = pd.concat([df, dfNew], ignore_index=True)
    newDB = {
        "t": pd.to_datetime(curr_df["Stime"]),
        "PacPV": curr_df["avgPacPV"].astype('float64'),
        "Pbat": curr_df["avgPbat"].astype('float64'),
        "PacGrid": curr_df["avgPacGrid"].astype('float64'),
        "PacHome": curr_df["avgPacHome"].astype('float64'),
        "IBat": curr_df["Ibat"].astype('float64'),
        "TBat": curr_df["Tbat"].astype('float64'),
        "VBat": curr_df["Vbat"].astype('float64'),
        "SoC": curr_df["SoC"].astype('float64'),
        "SoH": curr_df["SoH"].astype('float64'),
        "FreqIn": curr_df["FacIn"].astype('float64'),
        "FreqOut": curr_df["FacOut"].astype('float64'),
        "nCicli": curr_df["nCicli"].astype('float64'),
    }
    curr_df = pd.DataFrame(newDB)
    df = pd.concat([df, curr_df], ignore_index=True)

    # Stampare gli ultimi time stamps per controllare i dati recuperati
 

    return df