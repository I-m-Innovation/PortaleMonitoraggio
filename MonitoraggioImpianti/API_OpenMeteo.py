from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

import numpy as np
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry

from .models import *


def get_OpenMeteoData(lat, long):
	cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
	retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
	openmeteo = openmeteo_requests.Client(session=retry_session)

	url = "https://api.open-meteo.com/v1/forecast"

	params = {
		"latitude": float(lat),
		"longitude": float(long),
		"current": ["temperature_2m", "weather_code"],
		"timezone": "Europe/Berlin"
	}
	responses = openmeteo.weather_api(url, params=params)

	response = responses[0]
	current = response.Current()
	current_temperature_2m = current.Variables(0).Value()
	current_weather_code = current.Variables(1).Value()
	return [current_weather_code, current_temperature_2m]


# FUNZIONI/DIZIONARIO PER IL METEO
def get_WeatherIcon(weather_code):
	weather_icons = {
		0: '1530392_weather_sun_sunny_temperature.png',  # 'Clear sky', Cielo sereno
		1: '1530391_clouds_sun_sunny_weather.png',  # 'Mainly clear', Principalmente Sereno
		2: '1530391_clouds_sun_sunny_weather.png',  # Parzialmente nuvoloso
		3: '1530369_cloudy_weather_clouds_cloud.png',  # 'Overcast', Coperto
		45: '1530368_foggy_weather_fog_clouds_cloudy.png',  # Nebbia
		48: 'Depositing rime fog',  # Depositing brina
		51: '1530365_rain_cloud_drizzel_weather.png',  # Pioviggine: leggera, Drizzle: light
		53: '1530365_rain_cloud_drizzel_weather.png',  # Pioviggine: moderata Drizzle: moderate
		55: '1530365_rain_cloud_drizzel_weather.png',  # Pioviggina: intensità densa Drizzle: dense intensity
		56: 'Freezing Drizzle: light',  # Pioviggina gelida: leggera
		57: 'Freezing Drizzle: dense intensity',  # Pioviggina gelata: intensità densa
		61: '1530365_rain_cloud_drizzel_weather.png',  # Pioggia: debole
		63: '1530364_rain_storm_shower_weather.png',  # Pioggia: moderata
		65: '1530362_cloudy_weather_forecast_rain_clouds.png',  # Pioggia: forte intensità
		66: 'Freezing Rain: light',  # Pioggia gelata: debole
		67: 'Freezing Rain: heavy intensity',  # Pioggia gelata: forte intensita'
		71: 'Snow fall: slight',  # Nevicate: leggere
		73: 'Snow fall: moderate',  # Nevicate: moderate
		75: 'Snow fall: heavy intensity',  # Nevicate: di forte intensità
		77: 'Snow grains',  # Granelli di neve
		80: '1530365_rain_cloud_drizzel_weather.png',  # Rovesci di pioggia: leggeri
		81: '1530364_rain_storm_shower_weather.png',  # Rovesci di pioggia: moderati
		82: '1530364_rain_storm_shower_weather.png',  # Rovesci di pioggia: violenti
		85: 'Snow showers: slight',  # Rovesci di neve: deboli
		86: 'Snow showers: heavy',  # Rovesci di neve: forti
		95: '1530363_storm_weather_night_clouds.png',  # Temporale
		96: '1530363_storm_weather_night_clouds.png',  # Temporale con leggera grandinata, Thunderstorm with slight hail
		99: '1530363_storm_weather_night_clouds.png'  # Temporale con forte grandinata, Thunderstorm with slight hail
	}
	codici_meteo = {
		0: 'Cielo sereno',  #  Clear sky
		1: 'Principalmente Sereno',  # Mainly clear
		2: 'Parzialmente nuvoloso',  # Partly Cloudy
		3: 'Coperto',  # Overcast
		45: 'Nebbia',  # Fog
		48: 'Depositing rime fog',  # Depositing brina
		51: 'Drizzle: light',  # Pioviggine: leggera
		53: 'Drizzle: moderate',  # Pioviggine: moderata
		55: 'Drizzle: dense intensity',  # Pioviggina: intensità densa
		56: 'Freezing Drizzle: light',  # Pioviggina gelida: leggera
		57: 'Freezing Drizzle: dense intensity',  # Pioviggina gelata: intensità densa
		61: 'Rain: slight',  # Pioggia: debole
		63: 'Rain: moderate',  # Pioggia: moderata
		65: 'Rain: heavy intensity',  # Pioggia: forte intensità
		66: 'Freezing Rain: light',  # Pioggia gelata: debole
		67: 'Freezing Rain: heavy intensity',  # Pioggia gelata: forte intensita'
		71: 'Snow fall: slight',  # Nevicate: leggere
		73: 'Snow fall: moderate',  # Nevicate: moderate
		75: 'Snow fall: heavy intensity',  # Nevicate: di forte intensità
		77: 'Snow grains',  # Granelli di neve
		80: 'Rovesci di pioggia: leggeri',  # Rain showers: slight
		81: 'Rain showers: moderate',  # Rovesci di pioggia: moderati
		82: 'Rain showers: violent',  # Rovesci di pioggia: violenti
		85: 'Snow showers: slight',  # Rovesci di neve: deboli
		86: 'Snow showers: heavy',  # Rovesci di neve: forti
		95: 'Thunderstorm',  # Temporale
		96: 'Thunderstorm with slight hail',  # Temporale con leggera grandinata
		99: 'Thunderstorm with heavy hail'  # Temporale con forte grandinata
	}

	meteo = codici_meteo[weather_code]
	meteo_icona = weather_icons[weather_code]

	return [meteo, meteo_icona]
