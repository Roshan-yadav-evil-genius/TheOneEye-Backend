import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "theoneeye.settings")

# Initialize Django BEFORE importing anything that uses Django models
import django
django.setup()

# Initialize unified logging with BASE_DIR from settings
from django.conf import settings
from app_logging.config import setup_logging
setup_logging(settings.BASE_DIR)

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from apps.browsersession import routing as browsersession_routing
from apps.workflow import routing as workflow_routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        browsersession_routing.websocket_urlpatterns +
        workflow_routing.websocket_urlpatterns
    )
})
