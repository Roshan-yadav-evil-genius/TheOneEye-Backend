import os
import structlog
from celery import Celery
from celery.signals import task_prerun, task_postrun

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theoneeye.settings')

# Initialize Django to access settings
import django
django.setup()

# Initialize unified logging with BASE_DIR from settings
from django.conf import settings
from app_logging.config import setup_logging
setup_logging(settings.BASE_DIR)

app = Celery('theoneeye')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Prevent Celery from hijacking root logger
app.conf.worker_hijack_root_logger = False
app.conf.worker_redirect_stdouts = False

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@task_prerun.connect
def bind_task_context(sender=None, task_id=None, task=None, **kwargs):
    """Bind task context to structlog for correlation."""
    structlog.contextvars.bind_contextvars(
        task_id=task_id,
        task_name=task.name if task else None,
    )


@task_postrun.connect
def clear_task_context(**kwargs):
    """Clear task context after task completes."""
    structlog.contextvars.clear_contextvars()