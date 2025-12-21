from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import GoogleConnectedAccount


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


# Google OAuth Serializers

class GoogleConnectedAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for listing Google connected accounts.
    Excludes sensitive token data from response.
    """
    class Meta:
        model = GoogleConnectedAccount
        fields = [
            'id', 
            'name', 
            'email', 
            'picture', 
            'scopes', 
            'is_active', 
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'email', 'picture', 'created_at', 'updated_at']


class GoogleOAuthInitiateSerializer(serializers.Serializer):
    """
    Serializer for initiating Google OAuth flow.
    """
    name = serializers.CharField(
        max_length=255,
        help_text="Friendly name for this Google account connection"
    )
    scopes = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of scope keys to request (e.g., ['sheets', 'drive_readonly'])"
    )
    
    def validate_scopes(self, value):
        from .services.google_oauth_service import GoogleOAuthService
        valid_scopes = GoogleOAuthService.AVAILABLE_SCOPES.keys()
        
        for scope in value:
            if scope not in valid_scopes:
                raise serializers.ValidationError(
                    f"Invalid scope '{scope}'. Valid scopes are: {list(valid_scopes)}"
                )
        
        if not value:
            raise serializers.ValidationError("At least one scope is required")
        
        return value


class GoogleOAuthCallbackSerializer(serializers.Serializer):
    """
    Serializer for handling OAuth callback.
    """
    code = serializers.CharField(
        help_text="Authorization code from Google"
    )
    state = serializers.CharField(
        help_text="State token for CSRF verification"
    )
    name = serializers.CharField(
        max_length=255,
        help_text="Friendly name for this account (passed from initiate)"
    )
    scopes = serializers.ListField(
        child=serializers.CharField(),
        help_text="Scopes that were requested"
    )
