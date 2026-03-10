from django.db import models
from django.contrib.auth.models import User
import uuid


class GoogleConnectedAccount(models.Model):
    """
    Stores Google OAuth connected accounts for users.
    Used to access Google services (Sheets, Gmail, Drive) on behalf of users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='google_accounts',
        help_text="The user who owns this Google account connection"
    )
    name = models.CharField(
        max_length=255,
        help_text="User-given friendly name like 'Work Account'"
    )
    email = models.EmailField(
        help_text="Google account email address"
    )
    picture = models.URLField(
        blank=True, 
        null=True,
        help_text="Google profile picture URL"
    )
    access_token = models.TextField(
        help_text="OAuth2 access token for API calls"
    )
    refresh_token = models.TextField(
        help_text="OAuth2 refresh token for obtaining new access tokens"
    )
    token_expires_at = models.DateTimeField(
        help_text="When the access token expires"
    )
    scopes = models.JSONField(
        default=list,
        help_text="List of granted OAuth scopes"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this connection is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'email']
        ordering = ['-created_at']
        verbose_name = "Google Connected Account"
        verbose_name_plural = "Google Connected Accounts"

    def __str__(self):
        return f"{self.name} ({self.email})"


class APIKey(models.Model):
    """
    Per-user API key for authenticating scripts and external callers.
    Used to perform workflow operations (webhooks, execute, etc.) on behalf of the user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text="The user who owns this API key",
    )
    name = models.CharField(max_length=255, help_text="Friendly name for the key (e.g. Production script)")
    prefix = models.CharField(max_length=16, db_index=True, help_text="Short prefix for lookup (e.g. toe_abc12)")
    key_hash = models.CharField(max_length=255, help_text="Hashed full key (never store the raw key)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'prefix'], name='unique_user_prefix'),
        ]
        ordering = ['-created_at']
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"
