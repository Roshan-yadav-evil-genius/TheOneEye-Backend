"""
HTTP Request Form

Single Responsibility: Form field definitions for the HTTP Request node.

This form handles:
- Method, URL, headers, query params, body
- Timeout and auth (Basic, Bearer)
"""

import json
from django import forms

from ....Core.Form import BaseForm
from ....Core.Form.Fields import JSONTextareaWidget


class HttpRequestForm(BaseForm):
    """
    Form for HTTP Request node configuration.

    All JSON fields (headers, query_params, body) support Jinja templates.
    """

    METHOD_CHOICES = [
        ("GET", "GET"),
        ("POST", "POST"),
        ("PUT", "PUT"),
        ("PATCH", "PATCH"),
        ("DELETE", "DELETE"),
        ("HEAD", "HEAD"),
        ("OPTIONS", "OPTIONS"),
    ]

    AUTH_TYPE_CHOICES = [
        ("", "None"),
        ("basic", "Basic"),
        ("bearer", "Bearer"),
    ]

    method = forms.ChoiceField(
        choices=METHOD_CHOICES,
        required=True,
        initial="GET",
        label="Method",
        help_text="HTTP method for the request",
    )

    url = forms.CharField(
        required=True,
        label="URL",
        max_length=2048,
        help_text="Full URL. Jinja supported, e.g. {{ data.webhook.data.body.endpoint }}",
        widget=forms.TextInput(attrs={"placeholder": "https://api.example.com/..."}),
    )

    headers = forms.CharField(
        required=False,
        label="Headers",
        widget=JSONTextareaWidget(attrs={"rows": 5, "placeholder": '{"Content-Type": "application/json"}'}),
        help_text="JSON object with HTTP headers. Jinja supported.",
    )

    query_params = forms.CharField(
        required=False,
        label="Query params",
        widget=JSONTextareaWidget(attrs={"rows": 5, "placeholder": '{"page": "1", "limit": "10"}'}),
        help_text="JSON object for query string. Jinja supported.",
    )

    body = forms.CharField(
        required=False,
        label="Body",
        widget=JSONTextareaWidget(attrs={"rows": 8, "placeholder": '{"key": "value"}'}),
        help_text="Request body for POST/PUT/PATCH. JSON or text. Jinja supported.",
    )

    timeout_seconds = forms.FloatField(
        required=False,
        min_value=0.1,
        initial=30,
        label="Timeout (seconds)",
        help_text="Request timeout in seconds (default 30)",
    )

    auth_type = forms.ChoiceField(
        choices=AUTH_TYPE_CHOICES,
        required=False,
        initial="",
        label="Auth type",
        help_text="Authentication type",
    )

    auth_username = forms.CharField(
        required=False,
        label="Auth username",
        max_length=255,
        help_text="Username for Basic auth",
    )

    auth_password = forms.CharField(
        required=False,
        label="Auth password",
        max_length=255,
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
        help_text="Password for Basic auth",
    )

    auth_bearer_token = forms.CharField(
        required=False,
        label="Bearer token",
        max_length=2048,
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
        help_text="Token for Bearer auth. Jinja supported.",
    )

    def clean_headers(self):
        """Validate that headers is valid JSON object when provided."""
        value = self.cleaned_data.get("headers", "") or ""
        value = value.strip()
        if not value:
            return value
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise forms.ValidationError("Headers must be a JSON object (dictionary)")
            return value
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON in headers: {e}")

    def clean_query_params(self):
        """Validate that query_params is valid JSON object when provided."""
        value = self.cleaned_data.get("query_params", "") or ""
        value = value.strip()
        if not value:
            return value
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise forms.ValidationError("Query params must be a JSON object (dictionary)")
            return value
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON in query params: {e}")

    def clean_body(self):
        """Validate that body is valid JSON when provided (optional; body can be plain text)."""
        value = self.cleaned_data.get("body", "") or ""
        value = value.strip()
        if not value:
            return value
        try:
            json.loads(value)
            return value
        except json.JSONDecodeError:
            # Allow non-JSON body (e.g. plain text for POST)
            return value
