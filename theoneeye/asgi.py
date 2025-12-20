import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "theoneeye.settings")

# Initialize Django BEFORE importing anything that uses Django models
import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from browsersession import routing as browsersession_routing
from workflow import routing as workflow_routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        browsersession_routing.websocket_urlpatterns +
        workflow_routing.websocket_urlpatterns
    )
})
