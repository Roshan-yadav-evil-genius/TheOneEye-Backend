"""
LinkedinProfileParser Form

Single Responsibility: Form field definitions for the LinkedinProfileParser node.
"""

from django.forms import CharField
from django.forms.widgets import Textarea

from ....Core.Form.Core.BaseForm import BaseForm


class LinkedinProfileParserForm(BaseForm):
    html_content = CharField(
        widget=Textarea(),
        required=False,
        help_text="Raw HTML content to parse. If provided, overrides input data."
    )

