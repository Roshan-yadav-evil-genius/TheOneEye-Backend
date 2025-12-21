"""
StringIterator Form

Single Responsibility: Form field definitions for the StringIterator node.
"""

from django.forms import CharField, ChoiceField
from django.forms.widgets import Textarea

from ....Core.Form.Core.BaseForm import BaseForm


class StringIteratorForm(BaseForm):
    data_content = CharField(
        widget=Textarea(),
        help_text="The string data to iterate over.",
        required=True
    )
    separator_type = ChoiceField(
        choices=[
            ('newline', 'New Line (\\n)'),
            ('comma', 'Comma (,)'),
            ('custom', 'Custom')
        ],
        required=True,
        initial='newline',
        help_text="Separator to split that data."
    )
    custom_separator = CharField(
        required=False,
        help_text="Custom separator string (only used if Separator Type is Custom)."
    )

