# Replace created_by CharField with ForeignKey to User on BrowserSession and BrowserPool

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('browsersession', '0008_add_browserpool_created_by'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='browsersession',
            name='created_by',
        ),
        migrations.AddField(
            model_name='browsersession',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='browser_sessions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveField(
            model_name='browserpool',
            name='created_by',
        ),
        migrations.AddField(
            model_name='browserpool',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='browser_pools',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
