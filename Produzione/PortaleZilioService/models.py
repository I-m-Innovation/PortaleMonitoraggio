from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from MonitoraggioImpianti.models import Impianto





class MonitoraggioImpianto(Impianto):
    class Meta:
        proxy = True
        verbose_name = 'Monitoraggio Impianto'
        verbose_name_plural = 'Monitoraggi Impianti'

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
    potenza_contratto_kw = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    is_oem = models.BooleanField(default=False)
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


class FotovoltaicoStatoEconomico(models.Model):
    class ApiSyncStatus(models.TextChoices):
        NEVER = "never", "Mai sincronizzato"
        OK = "ok", "OK"
        PARTIAL = "partial", "Parziale"
        ERROR = "error", "Errore"

    impianto = models.OneToOneField(
        ImpiantoAnagrafica,
        on_delete=models.CASCADE,
        related_name="fotovoltaico_stato_economico",
    )

    # Dati manuali
    data_inizio_contratto = models.DateField(blank=True, null=True)
    data_fine_contratto = models.DateField(blank=True, null=True)
    importo_stimato_contratto_annuo = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    totale_contratto = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Dati persistiti per dashboard / calcolo
    anni_contratto = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    totale_annuale_su_mw = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    totale_annuo = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Dati da API gestionale
    maturato = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    fatturato = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    incassato = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    data_prossima_fattura = models.DateField(blank=True, null=True)
    importo_prossima_fattura = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Straordinario
    costo_sostenuto_straordinario = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    totale_fatturato_straordinario = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    margine_straordinario = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    numero_fatture_straordinarie_annuo = models.PositiveIntegerField(blank=True, null=True)
    numero_fatture_straordinarie_totali = models.PositiveIntegerField(blank=True, null=True)

    # Metadati sincronizzazione
    last_api_sync_at = models.DateTimeField(blank=True, null=True)
    api_sync_status = models.CharField(
        max_length=20,
        choices=ApiSyncStatus.choices,
        default=ApiSyncStatus.NEVER,
    )
    api_sync_note = models.TextField(blank=True, null=True)

    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stato economico fotovoltaico"
        verbose_name_plural = "Stati economici fotovoltaici"
        ordering = ["impianto__nome_impianto"]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(data_fine_contratto__isnull=True)
                    | Q(data_inizio_contratto__isnull=True)
                    | Q(data_fine_contratto__gte=F("data_inizio_contratto"))
                ),
                name="ck_fv_stato_economico_contract_dates",
            ),
        ]

    def clean(self):
        if self.impianto.tipo_impianto != ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO:
            raise ValidationError("FotovoltaicoStatoEconomico puo' essere associato solo a impianti fotovoltaici.")

    def __str__(self):
        return f"{self.impianto.nome_impianto} - Stato economico FV"


class FotovoltaicoMetricheTecniche(models.Model):
    class StatoOperativo(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        WARNING = "warning", "Warning"
        UNKNOWN = "unknown", "Unknown"

    class SyncStatus(models.TextChoices):
        NEVER = "never", "Mai sincronizzato"
        OK = "ok", "OK"
        PARTIAL = "partial", "Parziale"
        ERROR = "error", "Errore"

    impianto = models.OneToOneField(
        ImpiantoAnagrafica,
        on_delete=models.CASCADE,
        related_name="fotovoltaico_metriche_tecniche",
    )

    pr_ultimi_12_mesi = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True)
    mancata_produzione = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    ore_equivalenti_ultimi_12_mesi = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stato_operativo = models.CharField(
        max_length=20,
        choices=StatoOperativo.choices,
        default=StatoOperativo.UNKNOWN,
    )

    last_sync_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.NEVER,
    )
    sync_note = models.TextField(blank=True, null=True)

    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Metriche tecniche fotovoltaico"
        verbose_name_plural = "Metriche tecniche fotovoltaico"
        ordering = ["impianto__nome_impianto"]

    def clean(self):
        if self.impianto.tipo_impianto != ImpiantoAnagrafica.TipoImpianto.FOTOVOLTAICO:
            raise ValidationError("FotovoltaicoMetricheTecniche puo' essere associato solo a impianti fotovoltaici.")

    def __str__(self):
        return f"{self.impianto.nome_impianto} - Metriche tecniche FV"


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
        STORAGE_INVERTER = "storage_inverter", "Storage inverter"
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
