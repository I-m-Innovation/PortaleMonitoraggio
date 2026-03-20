from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from MonitoraggioImpianti.models import Impianto





class MonitoraggioImpianto(Impianto):
    class Meta:
        proxy = True
        verbose_name = 'Monitoraggio Impianto'
        verbose_name_plural = 'Monitoraggi Impianti'


class FvMetadata(models.Model):
    class CategoriaFv(models.TextChoices):
        CLIENTE = 'CLIENTE', 'Cliente'
        PROPRIETA = 'PROPRIETA', 'Proprieta'

    impianto = models.OneToOneField(
        Impianto,
        on_delete=models.CASCADE,
        related_name='fv_metadata',
        blank=True,
        null=True,
    )
    nome_impianto = models.CharField(max_length=150)
    nome_proprietario = models.CharField(max_length=150, blank=True, null=True)
    nome_cliente = models.CharField(max_length=150, blank=True, null=True)
    potenza = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    categoria_fv = models.CharField(max_length=20, choices=CategoriaFv.choices)
    is_ppu = models.BooleanField(default=False)
    is_in_costruzione = models.BooleanField(default=False)
    data_inizio_contratto = models.DateField(blank=True, null=True)
    data_fine_contratto = models.DateField(blank=True, null=True)
    pr_contrattuale = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fv_metadata'
        verbose_name = 'FV Metadata'
        verbose_name_plural = 'FV Metadata'
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(data_fine_contratto__isnull=True)
                    | Q(data_inizio_contratto__isnull=True)
                    | Q(data_fine_contratto__gte=F('data_inizio_contratto'))
                ),
                name='ck_fv_metadata_contract_dates',
            ),
        ]

    def __str__(self):
        return f'{self.nome_impianto} ({self.categoria_fv})'

#________________________________________________________________________

class ImpiantoAnagrafica(models.Model):
    class TipoImpianto(models.TextChoices):
        FOTOVOLTAICO = "fotovoltaico", "Fotovoltaico"
        IDROELETTRICO = "idroelettrico", "Idroelettrico"
    class StatoImpianto(models.TextChoices):
        ATTIVO = "attivo", "Attivo"
        IN_COSTRUZIONE = "in_costruzione", "In costruzione"
        SOSPESO = "sospeso", "Sospeso"
        DISMESSO = "dismesso", "Dismesso"
        UNKNOWN = "unknown", "Unknown"

    id = models.AutoField(primary_key=True)
    nome_impianto = models.CharField(max_length=150)
    tag_impianto = models.CharField(max_length=30, unique=True)
    codice_impianto = models.CharField(max_length=30, unique=True, blank=True, null=True)
    tipo_impianto = models.CharField(max_length=50, choices=TipoImpianto.choices)
    stato_impianto = models.CharField(
        max_length=50,
        choices=StatoImpianto.choices,
        default=StatoImpianto.UNKNOWN,
    )

    latitudine = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    longitudine = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    indirizzo = models.CharField(max_length=255, blank=True, null=True)
    localita = models.CharField(max_length=150, blank=True, null=True)
    provincia = models.CharField(max_length=50, blank=True, null=True)
    regione = models.CharField(max_length=50, blank=True, null=True)

    potenza_installata_kw = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    data_entrata_esercizio = models.DateField(blank=True, null=True)

    nome_proprietario = models.CharField(max_length=150, blank=True, null=True)
    nome_cliente = models.CharField(max_length=150, blank=True, null=True)

    attivo_portale = models.BooleanField(default=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Impianto anagrafica"
        verbose_name_plural = "Impianti anagrafica"
        ordering = ["nome_impianto"]

    def __str__(self):
        return self.nome_impianto


class ImpiantoSorgenteDati(models.Model):
    class TipoSorgente(models.TextChoices):
        MONITORAGGIO_TECNICO = "monitoraggio_tecnico", "Monitoraggio tecnico"
        AMMINISTRATIVA = "amministrativa", "Amministrativa"
        GSE = "gse", "GSE"
        ALTRO = "altro", "Altro"

    id = models.AutoField(primary_key=True)
    impianto = models.ForeignKey(
        ImpiantoAnagrafica,
        on_delete=models.CASCADE,
        related_name="sorgenti_dati",
    )
    tipo_sorgente = models.CharField(max_length=50, choices=TipoSorgente.choices)
    nome_sorgente = models.CharField(max_length=100)
    identificativo_esterno = models.CharField(max_length=100, blank=True, null=True)
    nome_riferimento_esterno = models.CharField(max_length=150, blank=True, null=True)
    attiva = models.BooleanField(default=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Sorgente dati impianto"
        verbose_name_plural = "Sorgenti dati impianto"
        ordering = ["impianto__nome_impianto", "tipo_sorgente", "nome_sorgente"]

    def __str__(self):
        return f"{self.impianto.nome_impianto} - {self.tipo_sorgente} - {self.nome_sorgente}"


class FotovoltaicoMetadata(models.Model):
    class CategoriaFV(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        PROPRIETA = "proprieta", "Proprietà"

    id = models.AutoField(primary_key=True)
    impianto = models.OneToOneField(
        ImpiantoAnagrafica,
        on_delete=models.CASCADE,
        related_name="fotovoltaico_metadata",
    )
    categoria_fv = models.CharField(max_length=30, choices=CategoriaFV.choices)
    is_ppu = models.BooleanField(default=False)
    is_agrivoltaico = models.BooleanField(default=False)
    pr_contrattuale = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    note_fotovoltaico = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Metadata fotovoltaico"
        verbose_name_plural = "Metadata fotovoltaico"

    def clean(self):
        if self.impianto.tipo_impianto != ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO:
            raise ValidationError("FotovoltaicoMetadata può essere associato solo a impianti fotovoltaici.")

    def __str__(self):
        return f"{self.impianto.nome_impianto} - FV"


class IdroelettricoMetadata(models.Model):
    class CategoriaIDR(models.TextChoices):
        PROPRIETA = "proprieta", "Proprietà"
        GSE = "gse", "GSE"
        UNKNOWN = "unknown", "Unknown"

    id = models.AutoField(primary_key=True)
    impianto = models.OneToOneField(
        ImpiantoAnagrafica,
        on_delete=models.CASCADE,
        related_name="idroelettrico_metadata",
    )
    categoria_idr = models.CharField(max_length=30, choices=CategoriaIDR.choices)
    portata_concessione = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    unita_misura_portata = models.CharField(max_length=20, blank=True, null=True)
    salto = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    potenza_business_plan_kw = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    note_idroelettrico = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Metadata idroelettrico"
        verbose_name_plural = "Metadata idroelettrico"

    def clean(self):
        if self.impianto.tipo_impianto != ImpiantoAnagrafica.TipoImpianto.IDROELETTRICO:
            raise ValidationError("IdroelettricoMetadata può essere associato solo a impianti idroelettrici.")

    def __str__(self):
        return f"{self.impianto.nome_impianto} - IDR"

class ImpiantoDispositivo(models.Model):
    class TipoDispositivo(models.TextChoices):
        INVERTER = "inverter", "Inverter"
        WEATHER_STATION = "weather_station", "Weather station"

    id = models.AutoField(primary_key=True)
    impianto = models.ForeignKey(
        ImpiantoAnagrafica,
        on_delete=models.CASCADE,
        related_name="dispositivi",
    )
    tipo_dispositivo = models.CharField(max_length=50, choices=TipoDispositivo.choices)
    codice_dispositivo = models.CharField(max_length=100)
    attivo = models.BooleanField(default=True)
    note = models.TextField(blank=True, null=True)
    

    class Meta:
        verbose_name = "Dispositivo impianto"
        verbose_name_plural = "Dispositivi impianto"
        ordering = ["impianto__nome_impianto", "tipo_dispositivo", "codice_dispositivo"]
        unique_together = ("impianto", "codice_dispositivo")

    def clean(self):
        if self.impianto.tipo_impianto != ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO:
            raise ValidationError("I dispositivi possono essere associati solo a impianti fotovoltaici.")

    def __str__(self):
        return f"{self.impianto.nome_impianto} - {self.tipo_dispositivo} - {self.codice_dispositivo}"
