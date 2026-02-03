from datetime import datetime
import time

import numpy as np
import requests
import json
import pandas as pd
import pytz


def getLogData(token,plant):
    headers = {
        "accept": "application/json",
        "Authorization": str(token),
        "Content-Type": "application/json"
    }   # QUESTA LINEA VA CAMBIATA PER MASCHERARE LE CREDENZIALI

    if plant == '20kw': #dual immobiliare
        PlantId = '53'
        DevId = '2360PGKGI8E8'
        Logs = [{'id': '2000629', 'name': 'HSI', 'samplingTime': 600}, {'id': '1999813', 'name': 'HSI PLUS', 'samplingTime': 30}, {'id': '2000643', 'name': 'HSI Avanzato', 'samplingTime': 300}]
        LogId = Logs[2]['id']
        PId = '1999813105'
        VarId = '1999813106'
        # BaseURL = 'https://hsi.higeco.com/api/v1/plants/'
        BaseURL = 'https://hsi.higeco.com/api/v1/getLogData/'

    elif plant == '43kw': #zilio
        PlantId = '54'
        DevId = '2360ZGKGI5E7'
        Logs = [{'id': '2000629', 'name': 'HSI', 'samplingTime': 600}, {'id': '1999813', 'name': 'HSI PLUS', 'samplingTime': 30}]
        LogId = Logs[0]['id']
        # itemId = items[6]['id']
        # BaseURL = 'https://hsi.higeco.com/api/v1/plants/'
        BaseURL = 'https://hsi.higeco.com/api/v1/getLogData/'

    else:
        print('Invalid plant')
        return

    Now = datetime.now()
    t_start = datetime(Now.year,Now.month,Now.day,0,0,0)
    t_start = str(int(time.mktime(t_start.timetuple())))
    # URL = BaseURL + PlantId + "/devices/" + DevId + "/logs/" + LogId + "/items" #info loggers e dati
    URL = BaseURL + PlantId + "/" + DevId + "/" + LogId

    resp = requests.get(URL, headers=headers)
    Dict = resp.json()
    items = Dict["items"]
    df_items = pd.DataFrame.from_dict(items)
    data = Dict["data"]
    df_data = pd.DataFrame.from_dict(data)
    return Dict, df_data, df_items


def authenticateHigeco():
    params = {
        "username": "Zilio group",
        "password": "he9gieLi"
    }
    URL = 'https://hsi.higeco.com/api/v1/authenticate'
    responseApi = requests.post(URL, data=json.dumps(params))
    token = json.loads(responseApi.text)['token']
    return token


if __name__ == "__main__":
    plants = ['20kw','43kw']
    token = authenticateHigeco()
    Dict, df_data, df_items = getLogData(token,plants[0])
    df_data[0] = pd.to_datetime(df_data[0],unit='s')
    df_data = df_data[[0, 34]]
    df_data.columns = ['t', 'P']
    df_data.t = df_data.t + pd.Timedelta('01:00:00')
    df_data = df_data.replace(['#E2', '#E3'], None)
    df_data.P = df_data.P / 1000


def getDataHIGECO(num):
    plants = ['20kw', '43kw']
    token = authenticateHigeco()
    Dict, df_data, df_items = getLogData(token, plants[num])
    df_data[0] = pd.to_datetime(df_data[0], unit='s')
    df_data = df_data[[0, 34]]
    df_data.columns = ['t', 'P']
    df_data.t = df_data.t + pd.Timedelta('01:00:00')
    df_data = df_data.replace(['#E2', '#E3'], None)
    df_data.P = df_data.P / 1000
    return df_data


