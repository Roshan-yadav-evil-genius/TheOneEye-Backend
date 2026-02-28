# Generated manually for runtime variables (runtime.<key>)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0030_add_workflow_env'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='runtime_state',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
