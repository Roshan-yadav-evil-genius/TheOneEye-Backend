"""
BatchCosineSimilarityScorer Form

Single Responsibility: Form field definitions for the BatchCosineSimilarityScorer node.
"""

from django.forms import CharField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm
from ....Core.Form.Fields import JSONTextareaWidget


class BatchCosineSimilarityScorerForm(BaseForm):
    """Form for configuring the BatchCosineSimilarityScorer node. Query, records list, and content key."""

    query = CharField(
        label="Query",
        required=True,
        widget=Textarea(attrs={"rows": 5}),
        help_text="Query string to compare against (e.g. product description, intent). Jinja supported.",
    )
    records = CharField(
        label="Records",
        required=True,
        widget=JSONTextareaWidget(
            attrs={
                "rows": 8,
                "placeholder": '{{ data.all_posts }}\n\n# or JSON: [{"post_content": "..."}, ...]',
            }
        ),
        help_text="Jinja or JSON list of dicts. Each dict should contain the key specified below (e.g. post_content).",
    )
    content_key = CharField(
        label="Content key",
        required=True,
        max_length=255,
        help_text="Key in each record to use as text for embedding and similarity (e.g. post_content).",
    )
