from django.db import models
from django.conf import settings
from decimal import Decimal # Assicurati che Decimal sia importato

# Create your models here.



class Contatore(models.Model):
    TIPOLOGIA_CHOICES = [
        ('Produzione', 'Produzione'),
        ('Scambio', 'Scambio'),
        ('Ausiliare', 'Ausiliare'),
    ]
    
    TIPOLOGIAFASCIO_CHOICES = [
        ('Monofascio', 'Monofascio'),
        ('Trifascio', 'Trifascio'),
    ]
    matricola = models.CharField(max_length=50, null=True, blank=True)
    impianto = models.ForeignKey('PortaleCorrispettivi.Impianto', on_delete=models.SET_NULL, related_name='contatori', null=True, blank=True)
    impianto_nickname = models.CharField(max_length=50, null=True, blank=True)
    nome = models.CharField(max_length=100)
    pod = models.CharField(max_length=50)
    tipologia = models.CharField(max_length=20, choices=TIPOLOGIA_CHOICES)
    tipologiafascio = models.CharField(max_length=20, choices=TIPOLOGIAFASCIO_CHOICES, null=True, blank=True)
    k = models.IntegerField()
    marca = models.CharField(max_length=20,  null=True, blank=True)
    modello = models.CharField(max_length=50)
    data_installazione = models.DateField()

    # Può essere vuoto (null=True) per i contatori attivi.
    data_dismissione = models.DateField(null=True, blank=True)
    # --- FINE NUOVO CAMPO ---
    
    def __str__(self):
        # Modifichiamo la rappresentazione testuale per evitare errori se impianto è NULL
        stato = " (Dismesso)" if self.data_dismissione else ""
        if self.impianto:
            return f"{self.nome} ({self.tipologia}) - {self.impianto.nome_impianto}{stato}"
        else:
            return f"{self.nome} ({self.tipologia}) - Impianto rimosso{stato}"

class LetturaContatore(models.Model):
    contatore = models.ForeignKey(Contatore, on_delete=models.CASCADE, related_name='letture')
    anno = models.IntegerField()
    mese = models.IntegerField()  # 1-12 per i mesi dell'anno 
    
    # NUOVO CAMPO: importa tipologia dal contatore
    tipologia = models.CharField(
        max_length=20,
        choices=Contatore.TIPOLOGIA_CHOICES,
        null=True,
        blank=True,
        verbose_name="Tipologia"
    )
    
    # NUOVO CAMPO: importa tipologiafascio dal contatore
    tipologiafascio = models.CharField(
        max_length=20, 
        choices=Contatore.TIPOLOGIAFASCIO_CHOICES, 
        null=True, 
        blank=True,
        verbose_name="Tipologia Fascio"
    )
    
    # Dati per registro segnanti
    data_ora_lettura = models.DateTimeField(null=True, blank=True)
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
    # Aggiungiamo il campo per memorizzare il valore calcolato (totale_180n * k)
    imm_campo_calcolato = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Immissione Calcolata (totale_180n * k)"
    )
    
    class Meta:
        # Rimuoviamo 'tipo_tabella' dal unique_together perché il campo non esiste più
        unique_together = ('contatore', 'anno', 'mese')
        verbose_name = "Lettura Contatore"
        verbose_name_plural = "Letture Contatori"

    def __str__(self):
        # Rimuoviamo anche il riferimento a tipo_tabella dal metodo __str__
        return f"{self.contatore.nome} - {self.mese}/{self.anno}"

    def save(self, *args, **kwargs):
        # Controlla se esiste un contatore associato
        if self.contatore:
            # Copia il valore di tipologia dal contatore.
            # Contatore.tipologia non dovrebbe essere None o blank per come è definito.
            self.tipologia = self.contatore.tipologia
            
            # Copia il valore di tipologiafascio dal contatore.
            # Contatore.tipologiafascio può essere None o una stringa vuota.
            self.tipologiafascio = self.contatore.tipologiafascio
            
        # Procede poi con il normale salvataggio dell'istanza
        super().save(*args, **kwargs)




class regsegnanti(models.Model):
    # NUOVI CAMPI per collegare questa riga a un contatore, anno e mese specifici
    
    contatore = models.ForeignKey(Contatore, on_delete=models.CASCADE, related_name='diarioenergie')
    anno = models.IntegerField()
    mese = models.IntegerField()

    # Campi esistenti
    prod_campo = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    prod_ed = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    prod_gse = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    prel_campo = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    prel_ed = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    
    
    
    
    # Per i contatori Kaifa
    autocons_campo = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    autocons_ed = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    autocons_gse = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    imm_campo = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    imm_ed = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    imm_gse = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)



    class Meta:
        # Assicura che non ci possano essere due righe per lo stesso contatore, anno e mese
        unique_together = ('contatore', 'anno', 'mese')
        verbose_name = "Registro Segnante"
        verbose_name_plural = "Registri Segnanti"

    def __str__(self):
        return f"Reg. Segnanti - {self.contatore.nome} - {self.mese}/{self.anno}"

    def save(self, *args, **kwargs):
        # Se non ti serve salvare il nickname, puoi commentare o rimuovere questa parte
        # if self.contatore and self.contatore.impianto_nickname:
        #     self.impianto_nickname = self.contatore.impianto_nickname
        # else:
        #     self.impianto_nickname = None
        super().save(*args, **kwargs)






    

    

    

            

        
