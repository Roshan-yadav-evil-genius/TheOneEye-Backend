from django.db.models import (
    BooleanField,
    CASCADE,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    IntegerField,
    JSONField,
    TextField,
    UniqueConstraint,
)
from apps.workflow.models import BaseModel


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

    def __str__(self):
        return f"{self.name}({self.id})"
    
    class Meta:
        ordering = ["-created_at"]


class BrowserPool(BaseModel):
    """A pool of browser sessions; at runtime one session is picked (e.g. least used per domain)."""
    name = CharField(max_length=100)
    description = TextField(blank=True, null=True)

    # Pool-level settings: throttling and resource blocking (apply to all sessions in pool)
    domain_throttle_enabled = BooleanField(default=True)
    resource_blocking_enabled = BooleanField(default=False)
    blocked_resource_types = JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.name}({self.id})"

    class Meta:
        ordering = ["-created_at"]


class PoolDomainThrottleRule(BaseModel):
    """Per-pool, per-domain delay (seconds) between navigations/requests."""
    pool = ForeignKey(BrowserPool, on_delete=CASCADE, related_name="domain_throttle_rules")
    domain = CharField(max_length=255)
    delay_seconds = FloatField()
    enabled = BooleanField(default=False)

    class Meta:
        ordering = ["domain"]
        constraints = [
            UniqueConstraint(
                fields=["pool", "domain"],
                name="unique_pool_domain",
            ),
        ]

    def __str__(self):
        return f"{self.pool_id} / {self.domain} = {self.delay_seconds}s"


class BrowserPoolSession(BaseModel):
    """Membership of a session in a pool; usage_count used when domain is not provided (fallback)."""
    pool = ForeignKey(BrowserPool, on_delete=CASCADE, related_name="pool_sessions")
    session = ForeignKey(BrowserSession, on_delete=CASCADE, related_name="pool_memberships")
    usage_count = IntegerField(default=0)

    class Meta:
        ordering = ["usage_count"]
        constraints = [
            UniqueConstraint(fields=["pool", "session"], name="unique_pool_session"),
        ]

    def __str__(self):
        return f"{self.pool_id} / {self.session_id}"


class BrowserPoolSessionDomainUsage(BaseModel):
    """Per-domain usage count for (pool, session); used to pick least-used session for a domain."""
    pool = ForeignKey(BrowserPool, on_delete=CASCADE, related_name="domain_usages")
    session = ForeignKey(BrowserSession, on_delete=CASCADE, related_name="pool_domain_usages")
    domain = CharField(max_length=255)
    usage_count = IntegerField(default=0)

    class Meta:
        ordering = ["usage_count"]
        constraints = [
            UniqueConstraint(fields=["pool", "session", "domain"], name="unique_pool_session_domain"),
        ]

    def __str__(self):
        return f"{self.pool_id} / {self.session_id} / {self.domain} = {self.usage_count}"
