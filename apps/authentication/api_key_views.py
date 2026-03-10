"""
API Key management views.
JWT-only: only authenticated users via JWT can list, create, or revoke API keys.
"""

import secrets
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404

from apps.authentication.models import APIKey
from apps.authentication.serializers import (
    APIKeyCreateInputSerializer,
    APIKeyListSerializer,
    APIKeyCreateResponseSerializer,
)


class APIKeyListCreateView(APIView):
    """List (GET) and Create (POST) API keys. JWT only."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keys = APIKey.objects.filter(user=request.user).order_by('-created_at')
        serializer = APIKeyListSerializer(keys, many=True)
        return Response(serializer.data)

    def post(self, request):
        in_serializer = APIKeyCreateInputSerializer(data=request.data)
        in_serializer.is_valid(raise_exception=True)
        name = in_serializer.validated_data['name']

        raw_key = secrets.token_urlsafe(32)
        prefix = raw_key[:8]
        key_hash = make_password(raw_key)

        api_key = APIKey.objects.create(
            user=request.user,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
        )
        out_serializer = APIKeyCreateResponseSerializer(
            api_key,
            context={'key': raw_key},
        )
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class APIKeyRevokeView(APIView):
    """Revoke (DELETE) an API key by id. JWT only."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        api_key = get_object_or_404(APIKey, id=id)
        if api_key.user_id != request.user.id:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        api_key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
