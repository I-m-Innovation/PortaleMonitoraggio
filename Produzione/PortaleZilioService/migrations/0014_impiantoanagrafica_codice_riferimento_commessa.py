from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("PortaleZilioService", "0013_remove_impiantoanagrafica_attivo_portale"),
    ]

    operations = [
        migrations.AddField(
            model_name="impiantoanagrafica",
            name="codice_riferimento_commessa",
            field=models.CharField(
                blank=True,
                help_text="Codice usato per associare fatture e riferimenti di commessa all'impianto.",
                max_length=50,
                null=True,
            ),
        ),
    ]
