"""
CosineSimilarity Form

Single Responsibility: Form field definitions for the CosineSimilarity node.
"""

from django.forms import CharField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm


class CosineSimilarityForm(BaseForm):
    """Form for configuring the CosineSimilarity node. Two string inputs for comparison."""

    data_1 = CharField(
        label="Data 1",
        required=True,
        widget=Textarea(attrs={"rows": 3}),
        help_text="First string for comparison. Use Jinja (e.g. {{ data.previous_node.value }}) for dynamic values.",
    )
    data_2 = CharField(
        label="Data 2",
        required=True,
        widget=Textarea(attrs={"rows": 3}),
        help_text="Second string for comparison. Use Jinja for dynamic values.",
    )
