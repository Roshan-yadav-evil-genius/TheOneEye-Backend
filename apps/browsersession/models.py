from django.db.models import (
    BooleanField,
    CASCADE,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    JSONField,
    TextField,
    UniqueConstraint,
)
from apps.workflow.models import BaseModel
import uuid


class BrowserSession(BaseModel):
    """Model to represent browser automation sessions"""
    name = CharField(max_length=100)
    description = TextField(blank=True, null=True)
    browser_type = CharField(max_length=20, choices=[
        ('chromium', 'Chromium'),
        ('firefox', 'Firefox'),
        ('webkit', 'WebKit'),
    ], default='chromium')
    
    # Playwright configuration
    playwright_config = JSONField(default=dict, blank=True)
    
    # Session status
    status = CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
    ], default='inactive')
    
    # Session metadata
    created_by = CharField(max_length=100, blank=True, null=True)

    # Settings: throttling and resource blocking
    domain_throttle_enabled = BooleanField(default=True)
    resource_blocking_enabled = BooleanField(default=False)
    blocked_resource_types = JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.name}({self.id})"
    
    class Meta:
        ordering = ["-created_at"]


class DomainThrottleRule(BaseModel):
    """Per-session, per-domain delay (seconds) between navigations/requests."""
    session = ForeignKey(BrowserSession, on_delete=CASCADE, related_name="domain_throttle_rules")
    domain = CharField(max_length=255)
    delay_seconds = FloatField()

    class Meta:
        ordering = ["domain"]
        constraints = [
            UniqueConstraint(
                fields=["session", "domain"],
                name="unique_session_domain",
            ),
        ]

    def __str__(self):
        return f"{self.session_id} / {self.domain} = {self.delay_seconds}s"
