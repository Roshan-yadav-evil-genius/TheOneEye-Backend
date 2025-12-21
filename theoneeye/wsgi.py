"""
WSGI config for theoneeye project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "theoneeye.settings")

from django.core.wsgi import get_wsgi_application

# Initialize Django first
import django
django.setup()

# Initialize unified logging with BASE_DIR from settings
from django.conf import settings
from app_logging.config import setup_logging
setup_logging(settings.BASE_DIR)

application = get_wsgi_application()
