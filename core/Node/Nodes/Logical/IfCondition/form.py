"""
IfCondition Form

Single Responsibility: Form field definitions for the IfCondition node.
"""

from django.forms import CharField
from django.forms.widgets import Textarea

from ....Core.Form.Core.BaseForm import BaseForm


class IfConditionForm(BaseForm):
    condition_expression = CharField(
        required=True,
        widget=Textarea(attrs={'rows': 3}),
        help_text="Python expression evaluating to True/False. (e.g., data.get('followers', 0) > 500). variable 'data' is available."
    )

