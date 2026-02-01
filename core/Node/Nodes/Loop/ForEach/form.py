"""
ForEachNode Form

Single Responsibility: Form field definitions for the ForEach (loop) node.
One field: array expression (Jinja or JSON) for drag-drop from input or custom list.
"""

from django.forms import CharField

from ....Core.Form import BaseForm
from ....Core.Form.Fields import JSONTextareaWidget


class ForEachNodeForm(BaseForm):
    """Form for configuring the ForEach loop node. Single expression field."""

    array_expression = CharField(
        required=False,
        widget=JSONTextareaWidget(
            attrs={
                "rows": 5,
                "placeholder": '{{ data.items }}\n\n# or JSON: ["a", "b", "c"]',
            }
        ),
        help_text="Jinja expression that evaluates to the array to iterate over (e.g. {{ data.items }}). Drag-drop from input or write JSON/Jinja.",
    )
