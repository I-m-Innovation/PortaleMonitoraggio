from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("PortaleZilioService", "0011_fotovoltaicometadata_potenza_contratto_kw"),
    ]

    operations = [
        # No-op migration retained for historical branch compatibility.
        # The FvMetadata model is already removed earlier in the migration graph.
    ]
