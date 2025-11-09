# Generated migration to remove DemoRequest from workflow app
# This migration runs after contact/migrations/0002_demorequest.py
# which copies the data and drops the table.
# Since the table is already dropped, we just need to remove the model from Django's state.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0020_demorequest'),
        ('contact', '0002_demorequest'),  # Ensure this runs after data is copied
    ]

    operations = [
        # Remove the model from Django's state
        # The table was already dropped in contact/migrations/0002_demorequest.py
        migrations.DeleteModel(
            name='DemoRequest',
        ),
    ]

