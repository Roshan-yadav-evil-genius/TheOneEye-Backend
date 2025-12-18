"""
Node API URL Configuration
Routes for node-related endpoints.
"""

from django.urls import path
from .views import (
    NodeListView,
    NodeFlatListView,
    NodeCountView,
    NodeRefreshView,
    NodeFormView,
    NodeExecuteView,
    NodeFieldOptionsView,
    NodeDetailView,
)

urlpatterns = [
    # List endpoints
    path('', NodeListView.as_view(), name='node-list'),
    path('flat/', NodeFlatListView.as_view(), name='node-flat-list'),
    path('count/', NodeCountView.as_view(), name='node-count'),
    path('refresh/', NodeRefreshView.as_view(), name='node-refresh'),
    
    # Detail endpoints (must come after list endpoints)
    path('<str:identifier>/', NodeDetailView.as_view(), name='node-detail'),
    path('<str:identifier>/form/', NodeFormView.as_view(), name='node-form'),
    path('<str:identifier>/execute/', NodeExecuteView.as_view(), name='node-execute'),
    path('<str:identifier>/field-options/', NodeFieldOptionsView.as_view(), name='node-field-options'),
]

