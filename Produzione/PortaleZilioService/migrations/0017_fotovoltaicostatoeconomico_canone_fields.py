from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("PortaleZilioService", "0016_remove_impiantoanagrafica_codice_riferimento_commessa_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="fotovoltaicostatoeconomico",
            name="periodicita_canone_mesi",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text=(
                    "Periodicita del canone espressa in mesi. "
                    "Ad esempio: 1=mensile, 3=trimestrale, 6=semestrale, 12=annuale."
                ),
            ),
        ),
        migrations.AddField(
            model_name="fotovoltaicostatoeconomico",
            name="importo_canone_periodico",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=2,
                blank=True,
                null=True,
                help_text=(
                    "Importo del singolo canone relativo alla periodicita indicata in "
                    "'periodicita_canone_mesi'."
                ),
            ),
        ),
        migrations.AddConstraint(
            model_name="fotovoltaicostatoeconomico",
            constraint=models.CheckConstraint(
                check=Q(periodicita_canone_mesi__isnull=True) | Q(periodicita_canone_mesi__gt=0),
                name="ck_fv_stato_economico_periodicita_canone_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="fotovoltaicostatoeconomico",
            constraint=models.CheckConstraint(
                check=Q(importo_canone_periodico__isnull=True) | Q(importo_canone_periodico__gte=0),
                name="ck_fv_stato_economico_importo_canone_non_negative",
            ),
        ),
    ]
