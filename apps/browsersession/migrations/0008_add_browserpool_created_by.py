# Generated manually for user-scoped browser pools

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('browsersession', '0007_pool_settings_and_pool_domain_throttle_rule'),
    ]

    operations = [
        migrations.AddField(
            model_name='browserpool',
            name='created_by',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
