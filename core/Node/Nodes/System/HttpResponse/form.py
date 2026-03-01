"""
HTTP Response Form

Single Responsibility: Form field definitions for the HTTP Response node.
"""

import json
from django import forms

from ....Core.Form import BaseForm
from ....Core.Form.Fields import JSONTextareaWidget


class HttpResponseForm(BaseForm):
    """
    Form for configuring the HTTP Response node.

    Defines status code, body source (from input or custom), and optional custom JSON body.
    """

    BODY_SOURCE_CHOICES = [
        ('from_input', 'From upstream node output'),
        ('custom', 'Custom JSON body'),
    ]

    status_code = forms.IntegerField(
        required=True,
        initial=200,
        min_value=100,
        max_value=599,
        label='Status code',
        help_text='HTTP status code (e.g. 200, 201, 204, 400, 404, 500).'
    )

    body_source = forms.ChoiceField(
        required=True,
        choices=BODY_SOURCE_CHOICES,
        initial='from_input',
        label='Response body',
        help_text='Use upstream node data as body, or define custom JSON.'
    )

    body_json = forms.CharField(
        required=False,
        widget=JSONTextareaWidget(attrs={
            'rows': 10,
            'placeholder': '{\n  "message": "Success",\n  "data": {{ data.webhook.data }}\n}'
        }),
        label='Custom body (JSON)',
        help_text='JSON for response body. Jinja supported when body source is Custom.'
    )

    def clean_body_json(self):
        """Validate body_json is valid JSON when body_source is custom."""
        body_source = self.cleaned_data.get('body_source')
        body_json = (self.cleaned_data.get('body_json') or '').strip()
        if body_source == 'custom' and body_json:
            try:
                json.loads(body_json)
            except json.JSONDecodeError as e:
                raise forms.ValidationError(f'Invalid JSON: {e}')
        return body_json
