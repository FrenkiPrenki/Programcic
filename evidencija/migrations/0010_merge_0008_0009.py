# evidencija/migrations/0010_merge_0008_0009.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('evidencija', '0008_alter_dopis_options_dopis_broj_int_dopis_kategorija_and_more'),
        ('evidencija', '0009_alter_dopis_options_remove_dopis_rb_po_kategoriji_and_more'),
    ]

    operations = [
        # prazno – ovo je samo merge marker
    ]
