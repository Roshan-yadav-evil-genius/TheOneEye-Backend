"""
NetworkInterceptor Form

Single Responsibility: Form field definitions for the NetworkInterceptor node.
"""

from django.forms import CharField, ChoiceField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm
from .._shared.form_utils import BrowserSessionField


class NetworkInterceptorForm(BaseForm):
    urls = CharField(
        widget=Textarea(attrs={'rows': 5, 'placeholder': 'https://example.com\nhttps://example2.com\n\nOr use: {{ data.urls }}'}),
        required=False,
        help_text=(
            "URLs to load (one per line, or leave empty to use 'urls' from input data). "
            "You can also use Jinja templates like {{ data.urls }}. "
            "All URLs will be loaded in parallel."
        )
    )
    
    session_name = BrowserSessionField()
    
    wait_mode = ChoiceField(
        choices=[
            ('load', 'Load'),
            ('domcontentloaded', 'DOM Content Loaded'),
            ('networkidle', 'Network Idle')
        ],
        required=True,
        initial='networkidle',
        help_text="Wait strategy for page loading. 'networkidle' is recommended for capturing API calls."
    )
    
    capture_resource_types = ChoiceField(
        choices=[
            ('xhr', 'XHR Only'),
            ('fetch', 'Fetch Only'),
            ('xhr,fetch', 'XHR and Fetch (Recommended)'),
            ('all', 'All Resource Types'),
        ],
        required=True,
        initial='xhr,fetch',
        help_text="Types of network requests to capture. Use 'xhr,fetch' for API calls."
    )
    
    url_pattern = CharField(
        required=False,
        help_text=(
            "Optional regex pattern to filter URLs (e.g., '.*api.*', '/api/v1/.*', '.*linkedin.*'). "
            "Leave empty to capture all URLs matching resource type filter."
        )
    )
    
    http_methods = ChoiceField(
        choices=[
            ('GET', 'GET Only'),
            ('POST', 'POST Only'),
            ('GET,POST', 'GET and POST'),
            ('all', 'All Methods'),
        ],
        required=True,
        initial='all',
        help_text="HTTP methods to capture."
    )
    
    status_codes = CharField(
        required=False,
        help_text="Comma-separated status codes to filter (e.g., '200,201,404'). Leave empty to capture all status codes."
    )
    
    include_response_body = ChoiceField(
        choices=[
            ('true', 'Yes - Include Response Bodies'),
            ('false', 'No - Metadata Only'),
        ],
        required=True,
        initial='true',
        help_text="Whether to capture response body content. Set to 'No' to save memory and only capture headers/metadata."
    )
    
    max_response_size = CharField(
        initial='10MB',
        required=False,
        help_text="Maximum response size to capture (e.g., '10MB', '1MB', '500KB'). Larger responses will be skipped. Supports KB, MB, GB."
    )
    
    wait_after_load = CharField(
        initial='5000',
        required=False,
        help_text="Additional wait time in milliseconds after page load (for JS-rendered requests). Default: 5000ms."
    )
    
    return_timeout = CharField(
        initial='30000',
        required=False,
        help_text="Maximum time to wait for matching response in milliseconds. Default: 30000ms (30 seconds). Set to 0 for no timeout. When a matching response is found, returns immediately without waiting for full page load."
    )
