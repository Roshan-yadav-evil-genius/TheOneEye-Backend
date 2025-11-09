from django.db.models import JSONField, UUIDField, CharField, TextField, DateTimeField
from workflow.models import BaseModel
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
    tags = JSONField(default=list)
    
    def __str__(self):
        return f"{self.name}({self.id})"
    
    class Meta:
        ordering = ["-created_at"]
