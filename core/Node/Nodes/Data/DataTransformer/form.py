"""
DataTransformer Form

Single Responsibility: Form field definitions for the DataTransformer node.
Provides a single JSON template field with Jinja expression support.
"""

from django.forms import CharField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm


class DataTransformerForm(BaseForm):
    """
    Form for configuring the DataTransformer node.
    
    Users define the output JSON structure using Jinja templates
    to reference incoming data fields.
    
    Example:
    {
      "name": "{{ data.webhook.data.body.name }}",
      "email": "{{ data.webhook.data.body.email }}",
      "count_doubled": {{ data.webhook.data.body.count * 2 }},
      "is_processed": true
    }
    """
    
    output_template = CharField(
        widget=Textarea(attrs={'rows': 15, 'placeholder': '{\n  "field": "{{ data.previous_node.value }}"\n}'}),
        required=True,
        help_text=(
            "JSON template for output. Use Jinja syntax ({{ data.field }}) to reference "
            "incoming data. The rendered JSON will be forwarded to the next node."
        )
    )
