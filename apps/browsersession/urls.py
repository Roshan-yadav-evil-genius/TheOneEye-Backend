from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.browsersession.views import BrowserSessionViewSet, BrowserSessionChoicesView

router = DefaultRouter()
router.register("browser-sessions", BrowserSessionViewSet, basename="browser-sessions")

urlpatterns = [
    path("browser-sessions/choices/", BrowserSessionChoicesView.as_view(), name="browser-session-choices"),
] + router.urls



