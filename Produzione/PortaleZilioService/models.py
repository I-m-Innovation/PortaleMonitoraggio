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
