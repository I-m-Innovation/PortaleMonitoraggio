import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.platypus import Frame, Image, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import utils
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime


# FUNZIONE FA RESIZING IMMAGINE DA INSERIRE
def get_image(path, width=1 * cm, height=1 * cm):
	img = utils.ImageReader(path)
	iw, ih = img.getSize()
	if width > 1 * cm:
		aspect = ih / float(iw)
		return Image(path, width=width, height=(width * aspect)), width * aspect
	if height > 1 * cm:
		aspect = iw / float(ih)
		return Image(path, width=(height * aspect), height=height), height * aspect


# FORMAT DEI VALORI ALL'ITALIANA
def fformat(value, f):
	if f==2:
		return f"{value:,.2f}".replace('.', '$$').replace(',', '.').replace('$$', ',')
	elif f==3:
		return f"{value:,.3f}".replace('.', '$$').replace(',', '.').replace('$$', ',')
	elif f==0:
		return f"{value:,.0f}".replace('.', '$$').replace(',', '.').replace('$$', ',')


# FORMATTA LE DATE COME PARAGRAFO
def ParaDate(data):
	ps_date = ParagraphStyle('date', leading=9, spaceAfter=0, spaceBefore=0, alignment=TA_CENTER, textColor='grey')
	return Paragraph(f"<font size={7}>{data}</font>", ps_date)


# FORMATTA I VALORI COME PARAGRAFO
def ParaEurkWh(misura, target,tipo):
	ps_cell = ParagraphStyle('date', alignment=TA_CENTER, fontName="Times-Roman", fontSize=9, wordWrap=None)
	if tipo=='eur':
		ss='€'
		f=2
	elif tipo=='kWh':
		ss='kWh'
		f=0
	if misura - target<0:
		color='red'
		sgn = '+'
	else:
		color='green'
		sgn = ''
	return Paragraph(f"""
	<font size={10}>{fformat(target, f)}&nbsp;{ss}</font><br/>
	(<font size={9} color={color}>{sgn}{fformat(target-misura,f)}&nbsp;{ss}</font>,&nbsp;<font size={9} color={color}>{sgn}{fformat((target-misura)/misura*100,2)}&nbsp;%</font>)
	""",
	ps_cell
	)


def generaPDF_datiTecnici(impianto, df_stat, df_target_portata, df_BP, data_inizio, data_fine, chart):

	# VARIABILI
	nome_impianto = impianto['nome_impianto']
	salto = impianto['salto']
	entrata_in_esercizio = impianto['inizio_esercizio']
	unita_misura = impianto['unita_misura']
	comune = impianto['localita']

	# SETUP CANVAS
	buffer = io.BytesIO()
	a4 = (595.27, 841.89)
	# slide_format = (1440, 810)
	width, height = a4
	x_offset = 0.5 * cm
	y_offset = 0.5 * cm
	c = canvas.Canvas(buffer, pagesize=a4)
	c.setFont('Times-Roman', 18)
	show_boundaries = False

	# INSERISCO LOGHI IN ALTO A DESTRA DELLA SLIDE
	logo = []
	img1, LOGO1_height = get_image('static/images/zilio_logo.png', width=3.5 * cm)
	logo.append(img1)
	x, y = width - 3.5 * cm - x_offset, height - LOGO1_height - y_offset
	w, h = 3.5 * cm, LOGO1_height
	frame_LOGO1 = Frame(x, y, w, h, showBoundary=show_boundaries, topPadding=0, bottomPadding=0)
	frame_LOGO1.addFromList(logo, c)
	logo = []
	img2, LOGO2_height = get_image('static/images/logo_IM.png', width=1.5 * cm)
	logo.append(img2)
	x, y = width - frame_LOGO1.width - 1.5 * cm - 1.5 * x_offset, height - frame_LOGO1.height - y_offset
	w, h = 1.5 * cm, LOGO1_height
	frame_LOGO2 = Frame(x, y, w, h, showBoundary=show_boundaries)
	frame_LOGO2.addFromList(logo, c)

	# NOME IMPIANTO IN ALTO A SINISTRA IN GRANDE
	w = stringWidth(nome_impianto, 'Times-Bold',22)
	titolo = c.beginText(2*x_offset, height - 3* y_offset)
	titolo.setFont("Times-Bold", 22)
	titolo.textLine(nome_impianto)
	c.drawText(titolo)

	# LUOGO, DOVE SI TROVA L'IMPIANTO
	luogo = c.beginText(2*x_offset + w + x_offset/2, height - 3* y_offset)
	w = stringWidth(nome_impianto, 'Times-Bold', 9)
	luogo.setFont("Times-Roman", 9)
	luogo.textLine(f"sita in: {comune}")
	c.drawText(luogo)

	# INFO VARIE SOTTO IL TITOLO
	turbina = f"tipo X, - kW"
	generatore = f"- kW"
	salto = f"{salto} m"
	anno = f"{entrata_in_esercizio}"
	info = [
		['INFO ',''],
		['Turbina: ', turbina],
		['Generatore: ', generatore],
		['Salto: ', salto],
		['Entrata in esercizio: ', anno],
	]
	ts = [
		('SPAN', (0, 0), (1, 0)),
		('ALIGN', (0, 0), (1, 0), 'CENTER'),
		('TOPPADDING', (0, 0), (1, 4), 0),
		('BOTTOMPADDING', (0, 0), (1, 4), 0),
		('FONTNAME', (0, 0), (1, 4), "Times-Roman"),
		('FONTSIZE', (0, 0), (1, 4), 9),
	]
	t = Table(info, style=ts)
	t.wrap(0, 0)
	t.drawOn(c, 2.25 * x_offset, height - 3.8*cm)

	# TABELLA
	# numero righe
	t_x = 5
	# numero colonne
	t_y = 16

	# INTERVALLI DATE DI RIFERIMENTO (GIORNO, SCELTO, ANNO)
	format = '%d/%m/%y-%H:%M'
	Now = datetime.now()
	intervallo_day = datetime(data_fine.year,data_fine.month,data_fine.day,0,0).strftime(format) + ' ' + data_fine.strftime(format)
	intervallo = data_inizio.strftime(format) + ' ' + data_fine.strftime(format)
	intervallo_year = datetime(Now.year,1,1,0,0).strftime(format) + ' ' + data_fine.strftime(format)

	# INSERIMENTO NELLA TABELLA DI TUTTI I VALORI
	tab = [
		['','Intervallo', 'Misure', 'Target Portata', 'Business Plan'],
		#
		['Portata','', '', '', ''],
		['Istantanea', ParaDate(data_fine.strftime(format)), f"{fformat(df_stat.Portata.iloc[0],2)} {unita_misura}", f"{df_target_portata.Portata.iloc[0]} {unita_misura}", '-'],
		['Giorno', ParaDate(intervallo_day), f"{fformat(df_stat.Portata.iloc[1],2)} {unita_misura}", '-', '-',],
		['Intervallo', ParaDate(intervallo), f"{fformat(df_stat.Portata.iloc[2],2)} {unita_misura}", '-', '-'],
		['Anno', ParaDate(intervallo_year), f"{fformat(df_stat.Portata.iloc[3],2)} {unita_misura}", '-', '-'],
		#
		['Produzione','', '', '', ''],
		['Istantanea',ParaDate(data_fine.strftime(format)), f"{fformat(df_stat.Energia.iloc[0],3)} kW", f"{fformat(df_target_portata.Energia.iloc[0],3)} kW", f"{fformat(df_BP.Energia.iloc[0],2)} kW"],
		['Giorno', ParaDate(intervallo_day), f"{fformat(df_stat.Energia.iloc[1],0)} kWh", ParaEurkWh(df_stat.Energia.iloc[1],df_target_portata.Energia.iloc[1],'kWh'), ParaEurkWh(df_stat.Energia.iloc[1],df_BP.Energia.iloc[1],'kWh')],
		['Intervallo', ParaDate(intervallo), f"{fformat(df_stat.Energia.iloc[2],0)} kWh", ParaEurkWh(df_stat.Energia.iloc[2],df_target_portata.Energia.iloc[2],'kWh'), ParaEurkWh(df_stat.Energia.iloc[2],df_BP.Energia.iloc[2],'kWh')],
		['Anno', ParaDate(intervallo_year), f"{fformat(df_stat.Energia.iloc[3],0)} kWh", ParaEurkWh(df_stat.Energia.iloc[3],df_target_portata.Energia.iloc[3],'kWh'), ParaEurkWh(df_stat.Energia.iloc[3],df_BP.Energia.iloc[3],'kWh')],
		#
		['Corrispettivi','', '', '', ''],
		['Istantanea',ParaDate(data_fine.strftime(format)), f"{fformat(df_stat.Corrispettivi.iloc[0],2)} €/h", f"{fformat(df_target_portata.Corrispettivi.iloc[0],2)} €/h", fformat(df_BP.Corrispettivi.iloc[0],2) + ' €/h'],
		['Giorno', ParaDate(intervallo_day), f"{fformat(df_stat.Corrispettivi.iloc[1],2)} €", ParaEurkWh(df_stat.Corrispettivi.iloc[1],df_target_portata.Corrispettivi.iloc[1],'eur'), ParaEurkWh(df_stat.Corrispettivi.iloc[1],df_BP.Corrispettivi.iloc[1],'eur')],
		['Intervallo', ParaDate(intervallo), f"{fformat(df_stat.Corrispettivi.iloc[2],2)} €", ParaEurkWh(df_stat.Corrispettivi.iloc[2],df_target_portata.Corrispettivi.iloc[2],'eur'), ParaEurkWh(df_stat.Corrispettivi.iloc[2],df_BP.Corrispettivi.iloc[2],'eur')],
		['Anno', ParaDate(intervallo_year), f"{fformat(df_stat.Corrispettivi.iloc[3],2)} €", ParaEurkWh(df_stat.Corrispettivi.iloc[3],df_target_portata.Corrispettivi.iloc[3],'eur'), ParaEurkWh(df_stat.Corrispettivi.iloc[3],df_BP.Corrispettivi.iloc[3],'eur')],
	]

	# STYLING TABELLA
	ts = [
		('GRID', (0, 0), (t_x-1, t_y-1), 0.5, '#696969'),
		('VALIGN', (0, 0), (t_x-1, t_y-1), 'MIDDLE'),
		('ALIGN', (1, 1), (t_x-1, t_y-1), 'CENTER'),
		('FONTNAME', (1, 1), (t_x - 1, t_y - 1), "Times-Roman"),
		('TOPPADDING', (0, 0),(t_x-1, t_y-1), 2),
		('BOTTOMPADDING', (0, 0), (t_x-1, t_y-1), 2),
		('BACKGROUND', (0, 0), (t_x-1, 0), '#2a415f'),
		# header
		('TEXTCOLOR', (0, 0), (t_x-1, 0), '#FFFFFF'),
		# subheader 1
		('SPAN', (0, 1), (t_x-1, 1)),
		('ALIGN', (0, 1), (t_x-1, 1), 'CENTER'),
		('BACKGROUND', (0, 1), (t_x - 1, 1), '#d1e4e4'),
		('FONTNAME', (0, 1), (t_x - 1, 1), "Times-Bold"),
		# subheader 2
		('SPAN', (0, 6), (t_x-1, 6)),
		('ALIGN', (0, 6), (t_x-1, 6), 'CENTER'),
		('BACKGROUND', (0, 6), (t_x - 1, 6), '#d1e4e4'),
		('FONTNAME', (0, 6), (t_x - 1, 6), "Times-Bold"),
		# subheader 3
		('SPAN', (0, 11), (t_x-1, 11)),
		('ALIGN', (0, 11), (t_x-1, 11), 'CENTER'),
		('BACKGROUND', (0, 11), (t_x - 1, 11), '#d1e4e4'),
		('FONTNAME', (0, 11), (t_x - 1, 11), "Times-Bold"),
	]

	# INSERIMENTO GRAFICO NEL CANVAS
	plot = []
	chart, chart_height = get_image(chart, width= width - 4 * x_offset)
	plot.append(chart)
	x, y = 2 * x_offset, 2 * y_offset
	w, h = width - 4 * x_offset, chart_height
	frame_chart = Frame(x, y, w, h, showBoundary=show_boundaries, topPadding=0, bottomPadding=0)
	frame_chart.addFromList(plot, c)

	# INSERIMENTO TABELLA NEL CANVAS
	t = Table(tab, style=ts)
	t.wrap(0, 0)
	t.drawOn(c, 2 * x_offset, 2*y_offset + chart_height + 0.5 * cm)

	c.save()
	buffer.seek(0)
	return buffer