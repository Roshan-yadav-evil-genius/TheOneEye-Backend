# Replace created_by CharField with ForeignKey to User

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workflow', '0031_add_workflow_runtime_state'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workflow',
            name='created_by',
        ),
        migrations.AddField(
            model_name='workflow',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='workflows',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
