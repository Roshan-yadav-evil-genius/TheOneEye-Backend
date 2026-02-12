"""
WebPageLoader Form

Single Responsibility: Form field definitions for the WebPageLoader node.
"""

from django.forms import BooleanField, CharField, ChoiceField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm
from .._shared.form_utils import BrowserSessionField


class WebPageLoaderForm(BaseForm):
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
            ('load', 'Load (Default)'),
            ('domcontentloaded', 'DOM Content Loaded'),
            ('networkidle', 'Network Idle')
        ],
        required=True,
        initial='load',
        help_text="Wait strategy for page loading."
    )
    respect_domain_throttle = BooleanField(
        required=False,
        initial=True,
        help_text="When enabled, waits for the session's domain throttle delay before each request. Disable to bypass throttle for this node."
    )

