from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.browsersession.views import (
    BrowserSessionViewSet,
    BrowserSessionChoicesView,
    BrowserPoolViewSet,
    PoolDomainThrottleRuleViewSet,
)

router = DefaultRouter()
router.register("browser-sessions", BrowserSessionViewSet, basename="browser-sessions")
router.register("browser-pools", BrowserPoolViewSet, basename="browser-pools")

urlpatterns = [
    path("browser-sessions/choices/", BrowserSessionChoicesView.as_view(), name="browser-session-choices"),
    path(
        "browser-pools/<uuid:pool_id>/domain-throttle-rules/",
        PoolDomainThrottleRuleViewSet.as_view({"get": "list", "post": "create"}),
        name="pool-domain-throttle-rule-list",
    ),
    path(
        "browser-pools/<uuid:pool_id>/domain-throttle-rules/<uuid:pk>/",
        PoolDomainThrottleRuleViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="pool-domain-throttle-rule-detail",
    ),
] + router.urls



