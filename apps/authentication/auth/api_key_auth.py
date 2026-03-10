"""
API Key authentication for DRF.
Allows scripts and external callers to authenticate using a long-lived API key.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

from apps.authentication.models import APIKey


User = get_user_model()


class APIKeyAuthentication(BaseAuthentication):
    """
    Authenticate using Authorization: Api-Key <key> or X-Api-Key header.
    Returns (user, None) if the key is valid; returns None if no key present (try next auth);
    raises AuthenticationFailed if key is invalid.
    """
    keyword = 'Api-Key'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        raw_key = None

        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0] == self.keyword:
                raw_key = parts[1]

        if not raw_key:
            raw_key = request.META.get('HTTP_X_API_KEY')

        if not raw_key or len(raw_key) < 8:
            return None

        prefix = raw_key[:8]
        api_key = APIKey.objects.filter(prefix=prefix).first()
        if not api_key:
            raise AuthenticationFailed('Invalid or unknown API key.')

        from django.contrib.auth.hashers import check_password
        if not check_password(raw_key, api_key.key_hash):
            raise AuthenticationFailed('Invalid or unknown API key.')

        return (api_key.user, None)
