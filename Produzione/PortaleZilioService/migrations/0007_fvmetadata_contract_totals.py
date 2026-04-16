from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("PortaleZilioService", "0006_fotovoltaicometrichetecniche_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="fvmetadata",
            name="totale_annuo",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="fvmetadata",
            name="totale_annuo_su_mv",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="fvmetadata",
            name="totale_contratto",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]
