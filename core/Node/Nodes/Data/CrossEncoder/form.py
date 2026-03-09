"""
CrossEncoder Form

Single Responsibility: Form field definitions for the CrossEncoder node.
"""

from django.forms import CharField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm


class CrossEncoderForm(BaseForm):
    """Form for configuring the CrossEncoder node. Two text inputs for relevance scoring."""

    text_1 = CharField(
        label="Text 1 (e.g. intent or reference)",
        required=True,
        widget=Textarea(attrs={"rows": 3}),
        help_text="First text (e.g. reference or intent). Use Jinja (e.g. {{ data.previous_key }}) for dynamic values.",
    )
    text_2 = CharField(
        label="Text 2 (e.g. query or document)",
        required=True,
        widget=Textarea(attrs={"rows": 3}),
        help_text="Second text (e.g. query or document). Use Jinja for dynamic values.",
    )
