"""
FileWriter Form

Single Responsibility: Form field definitions for the FileWriter node.
"""

from django.forms import CharField, ChoiceField

from ....Core.Form import BaseForm
from ....Core.Form.Fields import JSONTextareaWidget


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
        widget=JSONTextareaWidget(attrs={
            'rows': 10,
            'placeholder': 'Enter content (JSON or text). Use Jinja for dynamic values:\n{{ data.result }}\n{{ data.forEachNode.results | tojson }}\n\nLeave empty to write node_data.data.',
        }),
        required=False,
        help_text=(
            "Optional content to write to file. Supports Jinja templates (e.g. {{ data.field }}, {{ data.forEachNode.results | tojson }}). "
            "If empty, writes node_data.data. Rendered in Monaco with JSON + Jinja support."
        )
    )

