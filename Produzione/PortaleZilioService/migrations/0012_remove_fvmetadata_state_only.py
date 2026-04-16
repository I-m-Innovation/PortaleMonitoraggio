from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("PortaleZilioService", "0011_fotovoltaicometadata_potenza_contratto_kw"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(
                    name="FvMetadata",
                ),
            ],
        ),
    ]
