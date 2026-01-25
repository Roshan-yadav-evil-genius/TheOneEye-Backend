"""
FileWriter Form

Single Responsibility: Form field definitions for the FileWriter node.
"""

from django.forms import CharField, ChoiceField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm


class FileWriterForm(BaseForm):
    file_path = CharField(
        required=True,
        help_text="Path to the output file (e.g., outputs/data.json)."
    )
    mode = ChoiceField(
        choices=[
            ('w', 'Overwrite (w)'),
            ('a', 'Append (a)')
        ],
        required=True,
        initial='w',
        help_text="File write mode."
    )
    content = CharField(
        widget=Textarea(attrs={'rows': 5, 'placeholder': 'Enter content to write, or use Jinja: {{ data.field }}\n\nLeave empty to write node_data.data'}),
        required=False,
        help_text=(
            "Optional content to write to file. Supports Jinja templates like {{ data.field }}. "
            "If empty, writes node_data.data (current behavior). If provided, uses this content value."
        )
    )

