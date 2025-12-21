"""
WebPageLoader Form

Single Responsibility: Form field definitions for the WebPageLoader node.
"""

from django.forms import URLField, ChoiceField

from ....Core.Form.Core.BaseForm import BaseForm
from .._shared.form_utils import BrowserSessionField


class WebPageLoaderForm(BaseForm):
    url = URLField(
        required=True, 
        help_text="URL to load. If empty, uses 'url' from input data."
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

