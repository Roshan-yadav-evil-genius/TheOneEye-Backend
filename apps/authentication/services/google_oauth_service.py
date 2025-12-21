"""
Google OAuth Service

Single responsibility: Handle all Google OAuth operations including
authorization URL generation, token exchange, token refresh, and user info retrieval.
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

from apps.authentication.models import GoogleConnectedAccount


class GoogleOAuthService:
    """
    Service class for Google OAuth operations.
    Follows Single Responsibility Principle - only handles OAuth logic.
    """
    
    # Google OAuth endpoints
    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    
    # Available scopes for Google Sheets
    AVAILABLE_SCOPES = {
        'sheets_readonly': 'https://www.googleapis.com/auth/spreadsheets.readonly',
        'sheets': 'https://www.googleapis.com/auth/spreadsheets',
        'drive_readonly': 'https://www.googleapis.com/auth/drive.readonly',
        'drive': 'https://www.googleapis.com/auth/drive',
        'gmail_readonly': 'https://www.googleapis.com/auth/gmail.readonly',
        'gmail_send': 'https://www.googleapis.com/auth/gmail.send',
    }
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    def generate_state_token(self) -> str:
        """
        Generate a secure random state token for CSRF protection.
        
        Returns:
            str: A secure random string
        """
        return secrets.token_urlsafe(32)
    
    def get_scope_urls(self, scope_keys: List[str]) -> List[str]:
        """
        Convert scope keys to actual Google scope URLs.
        
        Args:
            scope_keys: List of scope keys like ['sheets', 'drive_readonly']
            
        Returns:
            List of Google scope URLs
        """
        scope_urls = []
        for key in scope_keys:
            if key in self.AVAILABLE_SCOPES:
                scope_urls.append(self.AVAILABLE_SCOPES[key])
        
        # Always include basic profile scopes for user info
        scope_urls.extend([
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
        ])
        
        return list(set(scope_urls))  # Remove duplicates
    
    def generate_auth_url(self, scopes: List[str], state: str) -> str:
        """
        Generate the Google OAuth authorization URL.
        
        Args:
            scopes: List of scope keys to request
            state: State token for CSRF protection
            
        Returns:
            str: The authorization URL to redirect the user to
        """
        scope_urls = self.get_scope_urls(scopes)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scope_urls),
            'state': state,
            'access_type': 'offline',  # Request refresh token
            'prompt': 'consent',  # Always show consent screen for refresh token
        }
        
        return f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict:
        """
        Exchange the authorization code for access and refresh tokens.
        
        Args:
            code: The authorization code from Google
            
        Returns:
            Dict containing access_token, refresh_token, expires_in, scope
            
        Raises:
            Exception: If token exchange fails
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}")
        
        return response.json()
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            Dict containing new access_token and expires_in
            
        Raises:
            Exception: If token refresh fails
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"Token refresh failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}")
        
        return response.json()
    
    def get_user_info(self, access_token: str) -> Dict:
        """
        Fetch the user's Google profile information.
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dict containing email, name, picture, etc.
            
        Raises:
            Exception: If user info fetch fails
        """
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(self.USERINFO_URL, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch user info: {response.status_code}")
        
        return response.json()
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token (can be access or refresh token).
        
        Args:
            token: The token to revoke
            
        Returns:
            bool: True if revocation succeeded
        """
        response = requests.post(
            self.REVOKE_URL,
            params={'token': token},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        return response.status_code == 200
    
    def get_valid_credentials(self, account: GoogleConnectedAccount) -> Tuple[str, bool]:
        """
        Get a valid access token for an account, refreshing if necessary.
        
        Args:
            account: The GoogleConnectedAccount instance
            
        Returns:
            Tuple of (access_token, was_refreshed)
            
        Raises:
            Exception: If token refresh fails
        """
        # Check if token is expired or will expire in next 5 minutes
        buffer_time = timezone.now() + timedelta(minutes=5)
        
        if account.token_expires_at > buffer_time:
            # Token is still valid
            return account.access_token, False
        
        # Token needs refresh
        token_data = self.refresh_access_token(account.refresh_token)
        
        # Update the account with new token
        account.access_token = token_data['access_token']
        account.token_expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])
        account.save(update_fields=['access_token', 'token_expires_at', 'updated_at'])
        
        return account.access_token, True
    
    def calculate_token_expiry(self, expires_in: int) -> datetime:
        """
        Calculate the token expiry datetime.
        
        Args:
            expires_in: Seconds until token expires
            
        Returns:
            datetime: When the token will expire
        """
        return timezone.now() + timedelta(seconds=expires_in)


# Singleton instance
google_oauth_service = GoogleOAuthService()

