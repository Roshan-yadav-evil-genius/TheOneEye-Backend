"""
WebSocket URL routing for workflow execution.
"""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/workflow/<str:workflow_id>/", consumers.WorkflowExecutionConsumer.as_asgi()),
]

