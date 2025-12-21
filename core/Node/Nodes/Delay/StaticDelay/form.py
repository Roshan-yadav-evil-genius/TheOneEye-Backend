"""
StaticDelay Form

Single Responsibility: Form field definitions for the StaticDelay node.
"""

from django import forms

from ....Core.Form.Core.BaseForm import BaseForm
from .._shared.constants import UNIT_CHOICES


class StaticDelayForm(BaseForm):
    """Form for configuring Static Delay Node."""
    
    interval = forms.IntegerField(
        required=True,
        min_value=1,
        help_text="Duration to wait"
    )
    
    unit = forms.ChoiceField(
        required=True,
        choices=UNIT_CHOICES,
        help_text="Time unit for the interval"
    )

