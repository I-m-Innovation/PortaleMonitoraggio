from django.urls import reverse

from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import ticker
import folium
from statistics import mean
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def createMap(df,interactive,zoom):
  if df.size > 1:
    df = df.dropna(subset=['lon'])
    df = df.dropna(subset=['lat'])
  df.set_index('nickname', inplace=True)
  df = df[['nome_impianto', 'tipo', 'lat', 'lon', 'potenza_installata', 'inizio_esercizio']]
  lat = df['lat']
  long = df['lon']
  MeanLat = mean(lat)
  MeanLong = mean(long)
  figure = folium.Figure()
  map = folium.Map(location=[MeanLat, MeanLong],
                   zoom_start=zoom,
                   control_scale=interactive,
                   zoom_control=interactive,
                   scrollWheelZoom=interactive,
                   dragging=interactive,
                   # tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                   # attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
                   )

  # aggiunge icona
  for nickname in df.index:
    if df.loc[nickname, 'tipo'] == 'Fotovoltaico':
      folium.Marker(location=[lat.loc[nickname], long.loc[nickname]], max_width=2000, tooltip=df.loc[nickname, 'nome_impianto'],
                    icon=folium.Icon(icon='fa-solid fa-sun',color='lightred', prefix='fa')).add_to(map)
    else:
      url = reverse('analisi-impianto', kwargs={'nickname': nickname})
      folium.Marker(location=[lat.loc[nickname], long.loc[nickname]], max_width=2000, tooltip=df.loc[nickname,'nome_impianto'],
                    icon=folium.Icon(icon='fa-solid fa-droplet', prefix='fa'),
                    popup='<a href="'+url+'" target="_blank">'+df.loc[nickname, 'nome_impianto']+'</a>').add_to(map)

  map.add_to(figure)
  return figure._repr_html_()


def plot_analisi_dati_impianto(df_TS, start, end, impianto):
  q_max = impianto.infostat_set.filter(variabile='Var2_max')[0].valore

  impianto = impianto.__dict__

  unita_misura = impianto['unita_misura']
  pot_max = impianto['potenza_installata']
  pot_BP = impianto['potenza_business_plan']

  day_start = datetime(end.year, end.month, end.day, 0, 0)
  td_day = (end - day_start).total_seconds() / 3600
  td_interval = (end - start).total_seconds() / 3600
  td_year = (end-datetime(end.year, 1, 1, 0, 0)).total_seconds()/3600

  df_TS['t'] = pd.to_datetime(df_TS.t)
  df_TS_day = df_TS[day_start <= df_TS['t']]
  df_TS_interval = df_TS[datetime(start.year, start.month, start.day, start.hour, start.minute, 0) <= df_TS['t']]
  df_TS_interval = df_TS_interval[df_TS_interval['t'] <= datetime(end.year, end.month, end.day, end.hour, end.minute, 0)]

  P_day_mean = mean(list(df_TS_day.P))
  P_interval_mean = mean(list(df_TS_interval.P))
  P_year_mean = mean(list(df_TS.P))

  Q_day_mean = mean(list(df_TS_day.Q))
  Q_interval_mean = mean(list(df_TS_interval.Q))
  Q_year_mean = mean(list(df_TS.Q))

  P_last = df_TS['P'].iloc[-1]
  Q_last = df_TS['Q'].iloc[-1]

  EUR_last = mean(list(df_TS_day.P[ df_TS_day.t >= (end - timedelta(hours=1))])) * 0.21
  EUR_day = td_day * P_day_mean * 0.21
  EUR_interval = td_interval * P_interval_mean * 0.21
  EUR_year = td_year * P_year_mean * 0.21

  # CALCOLO TARGET DI PORTATA DI CONCESSIONE
  df_TS_target = df_TS.loc[(df_TS.Q-impianto['portata_concessione']).abs().nsmallest(1000).index]

  df_target_portata = pd.DataFrame(data={
    'Energia': [df_TS_target['P'].mean(), df_TS_target['P'].mean()*td_day, df_TS_target['P'].mean()*td_interval, df_TS_target['P'].mean()*td_year],
    'Portata': [impianto['portata_concessione'], df_TS_target['Q'].mean(), df_TS_target['Q'].std(), ''],
    '': [df_TS_target['P'].mean()*0.21, df_TS_target['P'].mean()*td_day*0.21, df_TS_target['P'].mean()*td_interval*0.21, df_TS_target['P'].mean()*td_year*0.21],
  })

  df_misure = pd.DataFrame(data = {
    'Energia': [P_last, P_day_mean*td_day, P_interval_mean*td_interval, P_year_mean*td_year,],
    'Portata': [Q_last, Q_day_mean, Q_interval_mean, Q_year_mean],
    'Corrispettivi': [EUR_last, EUR_day, EUR_interval, EUR_year],
  })

  df_BP = pd.DataFrame(data = {
    'Energia': [x * pot_BP for x in [1, td_day, td_interval, td_year]],
    'Corrispettivi': [x * pot_BP * 0.21 for x in [1, td_day, td_interval, td_year]]
  })

  import matplotlib.dates as mdates
  buffer = BytesIO()
  plt.style.use('bmh')
  fig, ax = plt.subplots(figsize=(10, 6), dpi=400,)
  color1 = 'indianred'
  color2 = 'steelblue'

  twin = ax.twinx()
  ax.set_ylim(0, pot_max)
  twin.set_ylim(0, q_max)

  ax.set_ylabel("Potenza (kW)")
  twin.set_ylabel(f"Portata ({unita_misura})")

  ax.yaxis.label.set_color(color1)
  twin.yaxis.label.set_color(color2)
  #
  ax.tick_params(axis='y', colors=color1)
  twin.tick_params(axis='y', colors=color2)

  plot1 = ax.plot(df_TS_interval.t, df_TS_interval.P, color=color1, label='Potenza (kW)',linewidth=1, zorder=0)
  h1 = ax.hlines(y=P_year_mean, color=color1, linestyle='-.', label='Media annuale (potenza)', xmin=df_TS_interval.t.iloc[0], xmax=df_TS_interval.t.iloc[-1],linewidth=1, zorder=0)
  plot2 = twin.plot(df_TS_interval.t, df_TS_interval.Q, color=color2, label=f'Portata ({unita_misura})', linewidth=1, zorder=0)
  h2 = twin.hlines(y=Q_year_mean, color=color2, linestyle='-.', label='Media annuale (portata)', xmin=df_TS_interval.t.iloc[0], xmax=df_TS_interval.t.iloc[-1],linewidth=1, zorder=0)
  ax.margins(x=0.01)
  ax.grid(axis='x', color='0.7', linestyle='dotted')
  ax.grid(axis='y',)
  twin.grid(axis='y',)
  ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%mT%H:%M'))

  handles1, labels1 = ax.get_legend_handles_labels()
  handles2, labels2 = twin.get_legend_handles_labels()
  plt.legend(handles1 + handles2, labels1 + labels2, facecolor='white', framealpha=1)

  fig.subplots_adjust(top=0.98, bottom=0.05, left=0.07, right=0.94)
  plt.savefig(buffer, format="png")
  return buffer, df_misure, df_BP, df_target_portata
