"""
Webhook Producer Form

Single Responsibility: Form field definitions for the Webhook Producer node.

This form handles:
- Webhook ID configuration
- Validation of webhook ID format
"""

from django import forms

from ....Core.Form.Core.BaseForm import BaseForm


class WebhookProducerForm(BaseForm):
    """
    Form for Webhook Producer node configuration.
    
    Defines the webhook_id that this node will listen to.
    """
    
    webhook_id = forms.CharField(
        label="Webhook ID",
        required=True,
        max_length=255,
        help_text="Unique identifier for this webhook. External systems will POST to /api/webhooks/{webhook_id}",
        widget=forms.TextInput(attrs={
            'placeholder': 'my-webhook-id'
        })
    )
    
    def clean_webhook_id(self):
        """Validate webhook_id format."""
        webhook_id = self.cleaned_data.get('webhook_id')
        if webhook_id:
            # Remove any whitespace
            webhook_id = webhook_id.strip()
            # Basic validation: alphanumeric, hyphens, underscores
            if not all(c.isalnum() or c in ['-', '_'] for c in webhook_id):
                raise forms.ValidationError(
                    "Webhook ID can only contain letters, numbers, hyphens, and underscores"
                )
        return webhook_id
