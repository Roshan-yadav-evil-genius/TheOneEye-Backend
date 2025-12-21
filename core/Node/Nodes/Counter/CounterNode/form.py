"""
Counter Form

Single Responsibility: Form field definitions for the Counter node.

This form handles:
- Min/max value bounds
- Direction (increment/decrement)
- Step size configuration
"""

from django import forms

from ....Core.Form.Core.BaseForm import BaseForm


class CounterForm(BaseForm):
    """
    Form for Counter node configuration.
    
    Defines the bounds and behavior for the counter iteration.
    """
    
    DIRECTION_CHOICES = [
        ("increment", "Increment"),
        ("decrement", "Decrement"),
    ]
    
    min_value = forms.IntegerField(
        required=True,
        initial=0,
        help_text="Minimum value (start for increment mode)"
    )
    
    max_value = forms.IntegerField(
        required=True,
        initial=10,
        help_text="Maximum value (start for decrement mode)"
    )
    
    direction = forms.ChoiceField(
        choices=DIRECTION_CHOICES,
        initial="increment",
        required=True,
        help_text="Counter direction: increment or decrement"
    )
    
    step = forms.IntegerField(
        min_value=1,
        initial=1,
        required=True,
        help_text="Value to increment/decrement by each iteration"
    )
    
    def clean(self):
        """Validate that min_value < max_value."""
        cleaned_data = super().clean()
        min_val = cleaned_data.get('min_value')
        max_val = cleaned_data.get('max_value')
        
        if min_val is not None and max_val is not None:
            if min_val >= max_val:
                raise forms.ValidationError(
                    "min_value must be less than max_value"
                )
        
        return cleaned_data

