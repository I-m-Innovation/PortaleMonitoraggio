from django.db import models
from django.core.exceptions import ValidationError
from django.forms import ModelForm, ModelChoiceField, ChoiceField, Select


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


class FileMonitoraggio(models.Model):
	cartella = models.CharField(max_length=150, blank=False, null=False, editable=True, help_text="Cartella", verbose_name='Cartella')
	tipo = models.CharField(max_length=50, blank=False, null=False, editable=True, help_text="Tipo", verbose_name='Tipo')
	impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, blank=False, null=False)

	class Meta:
		verbose_name = 'File Monitoraggio'
		verbose_name_plural = 'File Monitoraggio'

	def __str__(self):
		return self.impianto.tag + self.tipo + '.csv'


tipi_file = (
	('last24hTL', 'last24hTL'),
	('MonthTL', 'MonthTL'),
	('YearTL', 'YearTL'),
	('_dati_gauge', '_dati_gauge'),
	('DayStat', 'DayStat'),
	('MonthStat', 'MonthStat'),
	('YearStat', 'YearStat')
)

cartelle = (
	('San_Teodoro', 'San_Teodoro'),
	('ponte_giurino', 'ponte_giurino'),
	('Torrino_Foresta', 'Torrino_Foresta'),
	('SA3', 'SA3'),
)


class FileMonitoraggioForm(ModelForm):
	class Meta:
		model = FileMonitoraggio
		fields = "__all__"
		impianto = ModelChoiceField(queryset=Impianto.objects.all())
		widgets = {
			'tipo': Select(choices=tipi_file, attrs={'class': 'form-control'}),
			'cartella': Select(choices=cartelle, attrs={'class': 'form-control'}),
		}


class InfoStat(models.Model):
	impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, blank=False, null=False)
	variabile = models.CharField(max_length=50, blank=False, null=False, editable=True, help_text="Variabile di riferimento", verbose_name='Variabile')
	valore = models.FloatField(null=True, blank=True, editable=True, help_text="Valore", verbose_name='Valore')

	class Meta:
		verbose_name = 'Statistica variabili'
		verbose_name_plural = 'Statistiche variabili'

	def __str__(self):
		return f"{self.variabile}, {self.valore}"


scelta_variabile = (
	('Var2_media', 'Portata media'),
	('Var2_max', 'Portata massima'),
	('Var2_dev', 'Dev.St. Portata'),
	('Var3_min', 'Pressione minima'),
	('Var3_media', 'Pressione media'),
	('Var3_max', 'Pressione massima'),
	('Var3_dev', 'Dev.St. Pressione'),
)


class InfoStatForm(ModelForm):
	class Meta:
		model = InfoStat
		fields = "__all__"
		impianto = ModelChoiceField(queryset=Impianto.objects.all()),
		widgets = {
			'variabile': Select(choices=scelta_variabile, attrs={'class': 'form-control'}),
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

