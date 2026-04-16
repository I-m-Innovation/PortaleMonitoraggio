from decimal import Decimal

from django.db import migrations, models


COMMESSE_SEED = [
    ("3F - Ferro", "oem", "ZEOM002-22", Decimal("0.5")),
    ("3F - Ferro", "str", "ZEOM002-22_S", Decimal("0.5")),
    ("3F - Plastica", "oem", "ZEOM002-22", Decimal("0.5")),
    ("3F - Plastica", "str", "ZEOM002-22_S", Decimal("0.5")),
    ("Alessi", "oem", "ZEFVOM-002_O", Decimal("1")),
    ("Alessi", "str", "ZEFVOM-002_S", Decimal("1")),
    ("CFFT", "oem", "ZEFVOM-003_O", Decimal("1")),
    ("CFFT", "str", "ZEFVOM-003_S", Decimal("1")),
    ("Cavarzan", "oem", "ZEFVOM-001_O", Decimal("1")),
    ("Cavarzan", "str", "ZEFVOM-001_S", Decimal("1")),
    ("RCT", "oem", "ZEFVOM-011_O", Decimal("1")),
    ("RCT", "str", "ZEFVOM-011_S", Decimal("1")),
    ("Sibat Tomarchio", "oem", "ZEFVOM-006_O", Decimal("1")),
    ("Sibat Tomarchio", "str", "ZEFVOM-006_S", Decimal("1")),
    ("Videndum F5", "oem", "ZEFVOM-007_O", Decimal("1")),
    ("Videndum F5", "str", "ZEFVOM-007_S", Decimal("1")),
    ("Videndum F6", "oem", "ZEFVOM-008_O", Decimal("1")),
    ("Videndum F6", "str", "ZEFVOM-008_S", Decimal("1")),
    ("RCT-Bramante", "oem", "ZEFVOM-012_O", Decimal("1")),
    ("Col Roigo 50 kWp", "oem", "ZEO&MAGSROIGOO", Decimal("1")),
]


def seed_commesse(apps, schema_editor):
    ImpiantoAnagrafica = apps.get_model("PortaleZilioService", "ImpiantoAnagrafica")
    ImpiantoCommessa = apps.get_model("PortaleZilioService", "ImpiantoCommessa")

    impianti_by_name = {
        impianto.nome_impianto: impianto
        for impianto in ImpiantoAnagrafica.objects.all().only("id", "nome_impianto")
    }

    for nome_impianto, tipo_commessa, codice_commessa, riparto in COMMESSE_SEED:
        impianto = impianti_by_name.get(nome_impianto)
        if impianto is None:
            continue

        ImpiantoCommessa.objects.update_or_create(
            impianto=impianto,
            tipo_commessa=tipo_commessa,
            codice_commessa=codice_commessa,
            defaults={"riparto": riparto},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("PortaleZilioService", "0018_documentoimpianto"),
    ]

    operations = [
        migrations.AddField(
            model_name="impiantocommessa",
            name="riparto",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True),
        ),
        migrations.RunPython(seed_commesse, migrations.RunPython.noop),
    ]
