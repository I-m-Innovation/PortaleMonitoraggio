from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("PortaleZilioService", "0012_remove_fvmetadata_state_only"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="impiantoanagrafica",
            name="attivo_portale",
        ),
    ]
