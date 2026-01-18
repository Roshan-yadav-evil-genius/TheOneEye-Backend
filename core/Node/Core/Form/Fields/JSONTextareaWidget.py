"""
JSON Textarea Widget Module

Single Responsibility: Mark textarea fields as JSON editors for frontend rendering.

This widget adds a data attribute that signals to the frontend that this textarea
should be rendered using Monaco Editor with JSON syntax highlighting and validation.
"""

from django import forms


class JSONTextareaWidget(forms.Textarea):
    """
    Custom textarea widget that indicates JSON mode to the frontend.
    
    Single Responsibility: Mark textarea fields as JSON editors.
    
    This widget adds the 'data-json-mode' attribute to the rendered textarea,
    which is extracted by FormSerializer and passed to the frontend as json_mode.
    """
    
    def __init__(self, attrs=None):
        """
        Initialize JSON textarea widget with JSON mode attribute.
        
        Args:
            attrs: Dictionary of HTML attributes to add to the widget
        """
        default_attrs = {'data-json-mode': 'true'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

