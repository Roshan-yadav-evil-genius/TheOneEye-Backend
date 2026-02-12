from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.browsersession.views import (
    BrowserSessionViewSet,
    BrowserSessionChoicesView,
    DomainThrottleRuleViewSet,
)

router = DefaultRouter()
router.register("browser-sessions", BrowserSessionViewSet, basename="browser-sessions")

urlpatterns = [
    path("browser-sessions/choices/", BrowserSessionChoicesView.as_view(), name="browser-session-choices"),
    path(
        "browser-sessions/<uuid:session_id>/domain-throttle-rules/",
        DomainThrottleRuleViewSet.as_view({"get": "list", "post": "create"}),
        name="domain-throttle-rule-list",
    ),
    path(
        "browser-sessions/<uuid:session_id>/domain-throttle-rules/<uuid:pk>/",
        DomainThrottleRuleViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="domain-throttle-rule-detail",
    ),
] + router.urls



