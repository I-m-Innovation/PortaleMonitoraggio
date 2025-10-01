from django.db import models
from django.core.exceptions import ValidationError
from django.forms import ModelForm, ModelChoiceField, ChoiceField, Select
from django import forms
from django.forms import SelectDateWidget
from django.contrib.admin.widgets import AdminDateWidget
from AutomazioneDati.models import regsegnanti


def check_posizione(self):
	if not (self.lat and self.lon):
		raise ValidationError({
			'latitudine': 'Inserire almeno un dato di posizione',
			'longitudine': 'Inserire almeno un dato di posizione',
		})
	if self.lon:
		if not (-180 < self.lon < 180):
			raise ValidationError({'longitudine': 'Inserire un valore compreso tra -180 e 180'})
	if self.lat:
		if not (-90 < self.lat < 90):
			raise ValidationError({'latitudine': 'Inserire un valore compreso tra -90 e 90'})


# Create your models here.
class Impianto(models.Model):
	nickname = models.CharField(unique=True, max_length=50, blank=False, null=False, editable=True, help_text="Identifica l'impianto", verbose_name='Nickname')
	societa = models.CharField(max_length=150, null=True, blank=True, editable=True, help_text="Fiscale impianto", verbose_name='Società')
	nome_impianto = models.CharField(max_length=150, blank=False, null=False, editable=True, help_text="Nome dell'impianto", verbose_name='Nome')
	tag = models.CharField(max_length=10, blank=False, null=False, editable=True, help_text="Tag di abbreviazione", verbose_name='Tag')
	tipo = models.CharField(max_length=150, blank=False, null=False, editable=True, help_text="Tipologia dell'impianto elettrico", verbose_name='Tipo')
	lat = models.FloatField(null=True, blank=True, editable=True, help_text="Latitudine", verbose_name='Latitudine')
	lon = models.FloatField(null=True, blank=True, editable=True, help_text="Longitudine", verbose_name='Longitudine')
	localita = models.CharField(max_length=150, null=True, blank=True, editable=True, help_text="Località", verbose_name='Località')
	potenza_installata = models.FloatField(null=True, blank=True, editable=True, help_text="Potenza installata",
										   verbose_name='Potenza')

	# IDROELETTRICO
	unita_misura = models.CharField(null=True, blank=True, editable=True, help_text="Unita misura portata (mc/s o l/s)", max_length=150, verbose_name='Unita misura')
	portata_concessione = models.FloatField(null=True, blank=True, editable=True, help_text="Portata di concessione", verbose_name='Portata')
	salto = models.FloatField(null=True, blank=True, editable=True, help_text="Salto impianto", verbose_name='Salto')
	potenza_business_plan = models.FloatField(null=True, blank=True, editable=True, default=0, help_text="Potenza da Business Plan",
										   verbose_name='Potenza Business Plan')

	#
	inizio_esercizio = models.DateField(null=True, blank=True, editable=True, help_text="Data inizio esercizio", verbose_name='Entrata in esercizio')
	lettura_dati = models.CharField(max_length=50, null=True, blank=True, editable=True, help_text="Tipo lettura dati impianti", verbose_name='Lettura dati')
	proprieta = models.BooleanField(default=False, editable=True, help_text="Indica se l'impianto è di propietà Zilio", verbose_name='Proprietà')

	class Meta:
		verbose_name = 'Impianto'
		verbose_name_plural = 'Impianti'

	def __str__(self):
		return self.nome_impianto


tipi_impianto = (
	('Idroelettrico', 'Idroelettrico'),
	('Fotovoltaico', 'Fotovoltaico')
)
misura = (
	('mc/s', 'mc/s'),
	('l/s', 'l/s'),
	('---', '---')
)
letture_dati = (
	('ftp', 'ftp'),
	('API_HIGECO', 'API_HIGECO'),
	('API_LEO', 'API_LEO'),
	('API_ISC', 'API_ISC'),
	('---', '---')
)


class ImpiantoForm(ModelForm):
	class Meta:
		model = Impianto
		fields = "__all__"
		widgets = {
			'tipo': Select(choices=tipi_impianto, attrs={'class': 'form-control'}),
			'unita_misura': Select(choices=misura, attrs={'class': 'form-control'}),
			'lettura_dati': Select(choices=letture_dati, attrs={'class': 'form-control'}),
		}


choices = {
	'empty': 'Nessuno',
	'ok': 'Risolto',
	'standby': 'In lavorazione',
	'alarm': 'Problema',
}


class DiarioLetture(models.Model):
	anno = models.IntegerField(null=False, blank=False, editable=True, help_text="Anno di lettura", verbose_name='Anno')
	nome = models.CharField(null=False, blank=False, editable=True, max_length=150, verbose_name='Nome file')
	cartella = models.CharField(null=False, blank=False, editable=True, max_length=150, verbose_name='Cartella - Percorso', default='-')
	unit = models.CharField(null=False, blank=False, editable=True, max_length=150, verbose_name='Unità - Periferica', default='Z:/')
	impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, null=False, blank=False, editable=True, help_text="Relativo Impianto", verbose_name='Impianto')

	def __str__(self):
		return self.unit + self.cartella + self.nome

	class Meta:
		verbose_name = 'Diario letture'
		verbose_name_plural = 'Diari lettura'


class AddDiarioLettureForm(forms.ModelForm):
	class Meta:
		fields = '__all__'


class Cashflow(models.Model):
	percorso = models.CharField(null=False, blank=False, editable=True, max_length=150, verbose_name='Percorso file')
	impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, null=False, blank=False, editable=True, help_text="Relativo Impianto", verbose_name='Impianto')
	unit = models.CharField(null=False, blank=False, editable=True, max_length=150, verbose_name='Unità - Periferica',
							default='Z:/')

	def __str__(self):
		return self.unit + self.percorso

	class Meta:
		verbose_name = 'File CashFlow'
		verbose_name_plural = 'File CashFlow'


class AddCashflowForm(forms.ModelForm):
	class Meta:
		fields = '__all__'


class DatiMensili(models.Model):
	percorso = models.CharField(null=False, blank=False, editable=True, max_length=150, verbose_name='Percorso file')
	impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, null=False, blank=False, editable=True, help_text="Relativo Impianto", verbose_name='Impianto')
	unit = models.CharField(null=False, blank=False, editable=True, max_length=150, verbose_name='Unità - Periferica',
							default='Z:/')

	def __str__(self):
		return self.unit + self.percorso

	class Meta:
		verbose_name = 'File dati mensili'
		verbose_name_plural = 'File dati mensili'


class AddDatiMensiliForm(forms.ModelForm):
	class Meta:
		fields = '__all__'


class Commento(models.Model):
	testo = models.TextField(null=False, blank=False)
	mese_misura = models.DateField(null=False, blank=False)
	impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, null=False, blank=False)
	stato = models.CharField(max_length=50, null=False, blank=False, default='', choices=choices,)

	def __str__(self):
		return self.testo + ' - ' + self.impianto.nome_impianto + ' - ' + str(self.mese_misura) + ' - ' + self.stato

	class Meta:
		verbose_name = 'Commento'
		verbose_name_plural = 'Commenti'


class AddCommentoForm(forms.ModelForm):
	date_input = forms.DateField(widget=SelectDateWidget(years=range(2021, 2030, 1)), label='Selezionare mese ')
	delete = forms.BooleanField(widget=forms.CheckboxInput(), initial=False, label='Cancella commento', required=False)

	class Meta:
		model = Commento
		fields = ['testo', 'impianto', 'stato']
		widgets = {
			# 'mese_misura': SelectDateWidget(years=range(2021, 2030, 1)),
			'testo': forms.Textarea(attrs={'cols': 30, 'rows': 8}),
		}
		labels = {
			'testo': 'Commento:',
			'impianto': 'Impianto',
		}


class linkportale(models.Model):
	portale = models.CharField(max_length=200, blank=False, null=False, editable=True, default='-', verbose_name='Nome portale')
	tag = models.CharField(max_length=50, blank=False, null=False, editable=True, default='-', verbose_name='tag portale')
	link = models.CharField(max_length=250, blank=False, null=False, editable=True, default='-', verbose_name='link-portale')

	class Meta:
		verbose_name = 'Link Portale'
		verbose_name_plural = 'Link Portali'


class linkportaleForm(ModelForm):
	class Meta:
		model = linkportale
		fields = "__all__"


class DatiMensiliTabella(models.Model):
	impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, null=False, blank=False)
	anno = models.IntegerField(null=False, blank=False, editable=False)  # Non più modificabile manualmente
	mese = models.IntegerField(null=False, blank=False)  # 1-12 per i mesi
	energia_kwh = models.FloatField(null=True, blank=True)
	corrispettivo_incentivo = models.FloatField(null=True, blank=True)
	corrispettivo_altro = models.FloatField(null=True, blank=True)
	fatturazione_tfo = models.FloatField(null=True, blank=True)
	fatturazione_altro = models.FloatField(null=True, blank=True)
	incassi = models.FloatField(null=True, blank=True)
	controllo_scarto = models.FloatField(null=True, blank=True, editable=False)
	controllo_percentuale = models.FloatField(null=True, blank=True, editable=False)
	
	class Meta:
		verbose_name = 'Dato Mensile Tabella'
		verbose_name_plural = 'Dati Mensili Tabella'
		unique_together = ('impianto', 'anno', 'mese')  # Garantisce unicità
	
	def save(self, *args, **kwargs):
		# Se è un nuovo oggetto o l'anno non è ancora impostato
		if not self.pk or not self.anno:
			# Cerca l'anno corrispondente in regsegnanti basato sull'impianto e mese
			# Assumiamo che ci sia un collegamento tramite il codice dell'impianto
			reg_record = regsegnanti.objects.filter(
				impianto=self.impianto.nickname,  # Assumi che esista una corrispondenza tra impianti
				mese=self.mese
			).order_by('-anno').first()  # Prendi il record più recente se ce ne sono diversi
			
			if reg_record:
				self.anno = reg_record.anno
			else:
				# Fallback se non viene trovato un record corrispondente
				from datetime import datetime
				self.anno = datetime.now().year
		
		# Calcola lo scarto tra corrispettivi e fatturazione
		corrispettivi_totali = (self.corrispettivo_incentivo or 0) + (self.corrispettivo_altro or 0)
		fatturazione_totale = (self.fatturazione_tfo or 0) + (self.fatturazione_altro or 0)
		
		self.controllo_scarto = corrispettivi_totali - fatturazione_totale
		
		# Calcola la percentuale di scarto
		if fatturazione_totale != 0:
			self.controllo_percentuale = (self.controllo_scarto / fatturazione_totale) * 100
		
		super().save(*args, **kwargs)





class commento_tabellacorrispettivi(models.Model):
	impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, null=False, blank=False)
	anno = models.IntegerField(null=False, blank=False, editable=False)
	mese = models.IntegerField(null=False, blank=False)
	testo = models.TextField(null=False, blank=False)
	stato = models.CharField(max_length=50, null=False, blank=False, default='', choices=choices,)

	def __str__(self):
		return self.testo + ' - ' + self.impianto.nome_impianto + ' - ' + str(self.mese) + ' - ' + self.stato