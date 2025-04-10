from django.db import models
from django.conf import settings
from decimal import Decimal # Assicurati che Decimal sia importato

# Create your models here.

class Impianto(models.Model):
    nome_impianto = models.CharField(max_length=100)
    nickname = models.CharField(max_length=50)
    # Altri campi...

    def __str__(self):
        return self.nome_impianto

class Contatore(models.Model):
    TIPOLOGIA_CHOICES = [
        ('Produzione', 'Produzione'),
        ('Scambio', 'Scambio'),
        ('Ausiliare', 'Ausiliare'),
    ]
    
    MARCA_CHOICES = [
        ('Kaifa', 'Kaifa'),
        ('Gesis', 'Gesis'),
    ]
    
    impianto = models.ForeignKey(Impianto, on_delete=models.CASCADE, related_name='contatori', null=True, blank=True)
    impianto_nickname = models.CharField(max_length=50, null=True, blank=True)
    nome = models.CharField(max_length=100)
    pod = models.CharField(max_length=50)
    tipologia = models.CharField(max_length=20, choices=TIPOLOGIA_CHOICES)
    k = models.IntegerField()
    marca = models.CharField(max_length=20, choices=MARCA_CHOICES)
    modello = models.CharField(max_length=50)
    data_installazione = models.DateField()
    
    def __str__(self):
        return f"{self.nome} ({self.tipologia}) - {self.impianto.nome_impianto}"

class LetturaContatore(models.Model):
    contatore = models.ForeignKey(Contatore, on_delete=models.CASCADE, related_name='letture')
    anno = models.IntegerField()
    mese = models.IntegerField()  # 1-12 per i mesi dell'anno
    tipo_tabella = models.CharField(max_length=20)  # 'reg_segnanti', 'libro_energie', 'libro_kaifa'
    
    # Dati per Registro Segnanti
    prod_campo = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    prod_ed = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    prod_gse = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    prel_campo = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    prel_ed = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    prel_gse = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    imm_campo = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    imm_ed = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    imm_gse = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    scambio_prelevata_campo = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    scambio_prelevata_ed = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    scambio_prelevata_gse = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    
    # Dati per Libro Energie
    data_presa = models.DateField(null=True, blank=True)
    a1_neg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    a2_neg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    a3_neg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    totale_neg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    a1_pos = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    a2_pos = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    a3_pos = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    totale_pos = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    # Dati per Libro Kaifa
    kaifa_180n = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    kaifa_280n = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    totale_180n = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    totale_280n = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    
    # --- NUOVO CAMPO ---
    # Aggiungiamo il campo per memorizzare il valore calcolato (totale_180n * k)
    imm_campo_calcolato = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Immissione Calcolata (totale_180n * k)"
    )
    # --- FINE NUOVO CAMPO ---

    # Campi per la tabella reg_segnanti (se li salvi qui)
    prod_campo = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    prelevata_campo = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    # Nota: Il campo 'imm_campo' originale nella tabella HTML ora userà 'imm_campo_calcolato'

    data_presa = models.DateField(null=True, blank=True)
    data_reg = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True, null=True)


    class Meta:
        # Assicurati che ci sia un vincolo di unicità per contatore, anno, mese, tipo_tabella
        unique_together = ('contatore', 'anno', 'mese', 'tipo_tabella')
        verbose_name = "Lettura Contatore"
        verbose_name_plural = "Letture Contatori"

    def __str__(self):
        return f"{self.contatore.nome} - {self.tipo_tabella} - {self.mese}/{self.anno}"

    # Potresti aggiungere un metodo per calcolare e salvare qui,
    # ma un comando di gestione è più adatto per aggiornamenti di massa.
    # def calcola_e_salva_imm_campo(self):
    #     if self.totale_180n is not None and self.contatore and self.contatore.k is not None:
    #         self.imm_campo_calcolato = self.totale_180n * self.contatore.k
    #         self.save(update_fields=['imm_campo_calcolato']) # Salva solo questo campo
    #     elif self.imm_campo_calcolato is not None:
    #         # Se totale_180n diventa None, azzera anche il campo calcolato
    #         self.imm_campo_calcolato = None
    #         self.save(update_fields=['imm_campo_calcolato'])