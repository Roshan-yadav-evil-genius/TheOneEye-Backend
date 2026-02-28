# Generated manually for workflow-level variables (workflowenv)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0029_add_workflow_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='env',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
