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


def plot_andamento_centrale(DF, max_portate, unita_misura, fontsize):
  font = {'size': fontsize}
  matplotlib.rc('font', **font)
  buffer = BytesIO()

  fig, ax = plt.subplots(figsize=(10, 3), dpi=300,)
  plt.subplots_adjust(bottom=0.15, right=0.86)
  plt.title('Dati tecnici, ultimi 24 mesi', {'fontsize': fontsize + 2})

  ax.set_facecolor("none")
  ax.tick_params(axis='x', labelrotation=45)
  ax.spines[['top']].set_visible(False)

  twin1 = ax.twinx()
  twin2 = ax.twinx()
  twin1.spines[['top']].set_visible(False)
  twin2.spines[['top']].set_visible(False)

  color1 = 'indianred'
  color2 = 'steelblue'
  color3 = 'royalblue'

  # Offset the right spine of twin2. The ticks and label have already been
  # placed on the right by twinx above.
  twin2.spines.right.set_position(("axes", 1.1))

  x = np.arange(len(DF['mesi']))

  barwidth1 = 0.5
  barwidth2 = 0.15
  x_offset = 0.4
  multiplier = 0

  dz = DF[['energie','volumi']].to_dict('list')

  for attribute, value in dz.items():
    offset = x_offset * multiplier
    if attribute == 'energie':
      rects = ax.bar(x + offset, value, barwidth1, color=color1)
      offset += barwidth1 * multiplier
    elif attribute == 'volumi':
      rects = twin1.bar(x + offset, value, barwidth2, color=color2)
      offset += barwidth1 * multiplier
    multiplier += 1

  x_margin = 0.01
  ax.margins(x=x_margin)
  twin1.margins(x=x_margin)

  x = x+x_offset-2*barwidth2

  p3 = twin2.plot(x, DF['portate_medie'], label="Portata media", color=color3, linestyle='dashdot',)
  ax.set_xticks(x, DF['mesi'])

  ax.set_ylim(0,)
  twin1.set_ylim(0,)
  twin2.set_ylim(0, max_portate)

  ax.yaxis.label.set_color(color1)
  twin1.yaxis.label.set_color(color2)
  twin2.yaxis.label.set_color(color3)
  #
  ax.tick_params(axis='y', colors=color1)
  twin1.tick_params(axis='y', colors=color2)
  twin2.tick_params(axis='y', colors=color3)

  def fmt_number(x, pos):
    return f'{int(x):,}'.replace(',', '.')
  ax.yaxis.set_major_formatter(ticker.FuncFormatter(fmt_number))

  def fmt_number_mln(x, pos):
    return f'{x/1000000:.2f} mln'.replace('.', ',')

  if unita_misura == 'm³/s':
    twin1.yaxis.set_major_formatter(ticker.FuncFormatter(fmt_number_mln))
  else:
    twin1.yaxis.set_major_formatter(ticker.FuncFormatter(fmt_number))

  ax.set_ylabel("Energia prodotta (kWh)", rotation=0)
  ax.yaxis.set_label_coords(-0.05, 1.02)

  twin1.set_ylabel("Volume d'acqua derivato (mc)", rotation=0)
  twin1.yaxis.set_label_coords(1.05, 1.08)

  twin2.set_ylabel("Portate medie ({})".format(unita_misura), rotation=0)
  twin2.yaxis.set_label_coords(1.1, -0.05)

  axb = ax.twinx()
  plt.grid(axis='y', linewidth=0.5)
  axb.spines[['top', 'bottom', 'left', 'right']].set_visible(False)
  axb.spines.right.set_position(("axes", 2))
  ax.set_zorder(ax.get_zorder() + 1)
  twin2.set_zorder(ax.get_zorder() + 1)
  twin1.set_zorder(ax.get_zorder() + 1)

  plt.savefig(buffer, format="png")
  return buffer

# ----------------------------------------------------------------------------------------------------------------------
def plot_corrispettivi_centrale2(DF, max_portate, unita_misura, fontsize, max_corrispettivi):
  font = {'size': fontsize}
  matplotlib.rc('font', **font)
  curr_anno = str(datetime.now().year)
  buffer = BytesIO()

  fig, ax = plt.subplots(figsize=(10, 6), dpi=300,)
  plt.title('Produzione, '+curr_anno, fontsize=fontsize+2)

  barWidth = 0.42
  y_c = np.arange(len(DF['mese']))
  DF['corrispettivi'] = DF['aspettata_inc'] + DF['aspettata_non_inc']
  labels_corr = ['' if amt < 2000 else f'{int(amt):,} €'.replace(',', '.') for amt in DF['corrispettivi']]
  labels_incassi = ['' if amt < 2000 else f'{int(amt):,} €'.replace(',', '.') for amt in DF['incassi']]
  y = [mese[:3] for mese in DF['mese']]

  ax.barh(y=y_c-barWidth/2 - 0.01, width=DF['corrispettivi'], label='Corrispettivi', color='burlywood', height=barWidth)
  ax.barh(y=y_c+barWidth/2 + 0.01, width=DF['incassi'], label='Incassi GSE', color='lightsteelblue', height=barWidth)
  ax.invert_yaxis()
  plt.yticks([r for r in range(len(y_c))], y)

  ax.spines[['top', 'bottom', 'right']].set_visible(False)
  ax.set_xticks([], [])
  y_margin = 0.02
  ax.margins(y=y_margin)
  ax.set_xlim(0, max_corrispettivi)
  fig.subplots_adjust(top=0.95, bottom=0.02)
  ax.legend()

  ax.bar_label(ax.containers[0], labels=labels_corr, label_type='center', padding=0.2)
  ax.bar_label(ax.containers[0],labels=['' if amt == 0 else f'  ⚡{int(amt):,} kWh'.replace(',', '.') for amt in DF['E_incentivata']],
               label_type='edge',)
  plt.rc('font', weight='bold')
  ax.bar_label(ax.containers[1], labels=labels_incassi, label_type='center', color='white')
  plt.rc('font', weight='normal')

  plt.savefig(buffer, format="png")
  return buffer


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
  # if unita_misura == 'm³/s':
  #   l = 0.01
  # else:
  #   l = 1
  # DFTL_target = DFTL_target[DFTL_target['Q'] <= dz_impianto['portata_concessione'] + l]
  # DFTL_target = DFTL_target[DFTL_target['Q'] >= dz_impianto['portata_concessione'] - l]
  # print(unita_misura,DFTL_target.mean(), DFTL_target.std())
  # print(P_year_mean, DFTL_target['P'].mean())

  df_target_portata = pd.DataFrame(data={
    'Energia': [df_TS_target['P'].mean(), df_TS_target['P'].mean()*td_day, df_TS_target['P'].mean()*td_interval, df_TS_target['P'].mean()*td_year],
    'Portata': [impianto['portata_concessione'], df_TS_target['Q'].mean(), df_TS_target['Q'].std(), ''],
    'Corrispettivi': [df_TS_target['P'].mean()*0.21, df_TS_target['P'].mean()*td_day*0.21, df_TS_target['P'].mean()*td_interval*0.21, df_TS_target['P'].mean()*td_year*0.21],
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
