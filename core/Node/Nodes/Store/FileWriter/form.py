"""
FileWriter Form

Single Responsibility: Form field definitions for the FileWriter node.
"""

from django.forms import CharField, ChoiceField

from ....Core.Form.Core.BaseForm import BaseForm


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

