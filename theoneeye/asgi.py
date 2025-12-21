import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "theoneeye.settings")

# Initialize structlog before Django starts
from theoneeye.logging_config import setup_django_logging
setup_django_logging()

# Initialize Django BEFORE importing anything that uses Django models
import django
django.setup()

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
