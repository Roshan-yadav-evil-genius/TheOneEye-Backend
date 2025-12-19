"""
Google OAuth Views

Single responsibility: Handle HTTP request/response for Google OAuth operations.
Business logic is delegated to GoogleOAuthService.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404

from authentication.models import GoogleConnectedAccount
from authentication.serializers import (
    GoogleConnectedAccountSerializer,
    GoogleOAuthInitiateSerializer,
    GoogleOAuthCallbackSerializer,
)
from authentication.services.google_oauth_service import google_oauth_service


class GoogleAccountListView(APIView):
    """
    List all Google connected accounts for the current user.
    
    GET /auth/google/accounts/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        accounts = GoogleConnectedAccount.objects.filter(
            user=request.user,
            is_active=True
        )
        serializer = GoogleConnectedAccountSerializer(accounts, many=True)
        return Response(serializer.data)


class GoogleOAuthInitiateView(APIView):
    """
    Initiate Google OAuth flow.
    
    POST /auth/google/initiate/
    
    Request body:
    {
        "name": "Work Account",
        "scopes": ["sheets", "drive_readonly"]
    }
    
    Response:
    {
        "auth_url": "https://accounts.google.com/o/oauth2/...",
        "state": "random_state_token"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = GoogleOAuthInitiateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate state token for CSRF protection
        state = google_oauth_service.generate_state_token()
        
        # Store state and request data in session for callback verification
        request.session['google_oauth_state'] = state
        request.session['google_oauth_name'] = serializer.validated_data['name']
        request.session['google_oauth_scopes'] = serializer.validated_data['scopes']
        
        # Generate authorization URL
        auth_url = google_oauth_service.generate_auth_url(
            scopes=serializer.validated_data['scopes'],
            state=state
        )
        
        return Response({
            'auth_url': auth_url,
            'state': state,
            'name': serializer.validated_data['name'],
            'scopes': serializer.validated_data['scopes'],
        })


class GoogleOAuthCallbackView(APIView):
    """
    Handle OAuth callback from Google.
    
    POST /auth/google/callback/
    
    Request body:
    {
        "code": "authorization_code_from_google",
        "state": "state_token",
        "name": "Work Account",
        "scopes": ["sheets"]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = GoogleOAuthCallbackSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        code = serializer.validated_data['code']
        name = serializer.validated_data['name']
        scopes = serializer.validated_data['scopes']
        
        try:
            # Exchange code for tokens
            token_data = google_oauth_service.exchange_code_for_tokens(code)
            
            access_token = token_data['access_token']
            refresh_token = token_data.get('refresh_token', '')
            expires_in = token_data.get('expires_in', 3600)
            
            # Get user info from Google
            user_info = google_oauth_service.get_user_info(access_token)
            
            email = user_info.get('email', '')
            picture = user_info.get('picture', '')
            
            # Calculate token expiry
            token_expires_at = google_oauth_service.calculate_token_expiry(expires_in)
            
            # Create or update the connected account
            account, created = GoogleConnectedAccount.objects.update_or_create(
                user=request.user,
                email=email,
                defaults={
                    'name': name,
                    'picture': picture,
                    'access_token': access_token,
                    'refresh_token': refresh_token if refresh_token else None,
                    'token_expires_at': token_expires_at,
                    'scopes': scopes,
                    'is_active': True,
                }
            )
            
            # If updating existing account and no new refresh token, keep the old one
            if not created and not refresh_token and account.refresh_token:
                pass  # Keep existing refresh_token
            
            response_serializer = GoogleConnectedAccountSerializer(account)
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class GoogleAccountDeleteView(APIView):
    """
    Delete/disconnect a Google connected account.
    
    DELETE /auth/google/accounts/<id>/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, account_id):
        account = get_object_or_404(
            GoogleConnectedAccount,
            id=account_id,
            user=request.user
        )
        
        # Optionally revoke the token at Google
        try:
            if account.refresh_token:
                google_oauth_service.revoke_token(account.refresh_token)
        except Exception:
            # Continue even if revocation fails
            pass
        
        # Delete the account
        account.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoogleAccountChoicesView(APIView):
    """
    Get Google account choices for form dropdowns.
    
    Returns a simplified list of accounts suitable for populating
    dropdown/select fields in node forms.
    
    GET /auth/google/accounts/choices/
    
    Response:
    [
        {"id": "uuid", "name": "Work Account", "email": "user@gmail.com"},
        ...
    ]
    """
    # AllowAny for now - core node forms don't have user context
    # In production, consider adding authentication
    permission_classes = [AllowAny]
    
    def get(self, request):
        accounts = GoogleConnectedAccount.objects.filter(is_active=True)
        choices = [
            {
                'id': str(acc.id),
                'name': acc.name,
                'email': acc.email
            }
            for acc in accounts
        ]
        return Response(choices)


class GoogleAccountCredentialsView(APIView):
    """
    Get credentials for Google API client.
    
    Returns access token (refreshed if needed), refresh token, and 
    client credentials needed to build google.oauth2.credentials.Credentials.
    
    GET /auth/google/accounts/<id>/credentials/
    
    Response:
    {
        "access_token": "...",
        "refresh_token": "...",
        "client_id": "...",
        "client_secret": "...",
        "scopes": ["..."]
    }
    """
    # AllowAny for now - core nodes call this internally
    # In production, consider adding authentication or using internal-only endpoint
    permission_classes = [AllowAny]
    
    def get(self, request, account_id):
        from django.conf import settings
        
        try:
            account = GoogleConnectedAccount.objects.get(id=account_id)
        except GoogleConnectedAccount.DoesNotExist:
            return Response(
                {'error': 'Account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get valid access token (refreshes if expired)
        access_token, was_refreshed = google_oauth_service.get_valid_credentials(account)
        
        return Response({
            'access_token': access_token,
            'refresh_token': account.refresh_token,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'scopes': account.scopes
        })

