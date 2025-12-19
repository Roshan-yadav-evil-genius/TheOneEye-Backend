from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .Views.GoogleOAuth import (
    GoogleAccountListView,
    GoogleOAuthInitiateView,
    GoogleOAuthCallbackView,
    GoogleAccountDeleteView,
    GoogleAccountChoicesView,
    GoogleAccountCredentialsView,
)

urlpatterns = [
    # User authentication
    path('login/', views.login, name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.register, name='register'),
    path('me/', views.me, name='me'),
    path('logout/', views.logout, name='logout'),
    
    # Google OAuth
    path('google/accounts/', GoogleAccountListView.as_view(), name='google-accounts-list'),
    path('google/initiate/', GoogleOAuthInitiateView.as_view(), name='google-oauth-initiate'),
    path('google/callback/', GoogleOAuthCallbackView.as_view(), name='google-oauth-callback'),
    path('google/accounts/<uuid:account_id>/', GoogleAccountDeleteView.as_view(), name='google-account-delete'),
    
    # Google Account API for Node Forms
    path('google/accounts/choices/', GoogleAccountChoicesView.as_view(), name='google-accounts-choices'),
    path('google/accounts/<uuid:account_id>/credentials/', GoogleAccountCredentialsView.as_view(), name='google-account-credentials'),
]
