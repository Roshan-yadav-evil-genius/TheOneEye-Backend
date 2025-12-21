"""
WSGI config for theoneeye project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

# Initialize structlog before Django starts
from theoneeye.logging_config import setup_django_logging
setup_django_logging()

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "theoneeye.settings")

application = get_wsgi_application()
