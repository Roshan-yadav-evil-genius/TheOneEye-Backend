"""
DynamicDelay Form

Single Responsibility: Form field definitions for the DynamicDelay node.
"""

from django import forms

from ....Core.Form.Core.BaseForm import BaseForm
from .._shared.constants import UNIT_CHOICES


class DynamicDelayForm(BaseForm):
    """Form for configuring Dynamic Delay Node."""
    
    total_time = forms.IntegerField(
        required=True,
        min_value=1,
        help_text="Total time period (delays will sum to this exactly)"
    )
    
    unit = forms.ChoiceField(
        required=True,
        choices=UNIT_CHOICES,
        help_text="Time unit for the total time"
    )
    
    executions = forms.IntegerField(
        required=True,
        min_value=1,
        help_text="Number of executions within the time period"
    )
    
    jitter_percent = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        initial=30,
        help_text="Randomness as percentage of base delay (e.g., 30 = ±30%)"
    )

