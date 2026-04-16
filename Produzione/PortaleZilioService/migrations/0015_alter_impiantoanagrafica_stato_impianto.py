from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("PortaleZilioService", "0014_impiantoanagrafica_codice_riferimento_commessa"),
    ]

    operations = [
        migrations.AlterField(
            model_name="impiantoanagrafica",
            name="stato_impianto",
            field=models.CharField(
                choices=[
                    ("attivo", "Attivo"),
                    ("in_costruzione", "In costruzione"),
                    ("sospeso", "Sospeso"),
                    ("dismesso", "Dismesso"),
                    ("unknown", "Unknown"),
                ],
                default="unknown",
                help_text="Al momento questo campo serve solo a collocare l'impianto nella tabella 'In Costruzione' quando il valore e' 'in_costruzione'.",
                max_length=50,
            ),
        ),
    ]
