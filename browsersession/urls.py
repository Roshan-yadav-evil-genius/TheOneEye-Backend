from django.urls import include, path
from rest_framework.routers import DefaultRouter
from browsersession.views import BrowserSessionViewSet

router = DefaultRouter()
router.register("browser-sessions", BrowserSessionViewSet, basename="browser-sessions")

urlpatterns = router.urls

