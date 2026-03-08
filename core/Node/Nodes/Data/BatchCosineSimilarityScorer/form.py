"""
BatchCosineSimilarityScorer Form

Single Responsibility: Form field definitions and validation for the BatchCosineSimilarityScorer node.
"""

import ast
import json

from django.forms import CharField, ValidationError
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm
from ....Core.Form.Fields import JSONTextareaWidget


def _ensure_list_of_dicts(value):
    """Return True if value is a list of dicts; else False."""
    if not isinstance(value, list):
        return False
    return all(isinstance(x, dict) for x in value)


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

    def clean_query(self):
        value = (self.cleaned_data.get("query") or "").strip()
        if not value:
            raise ValidationError("Query is required and cannot be blank.")
        return value

    def clean_content_key(self):
        value = (self.cleaned_data.get("content_key") or "").strip()
        if not value:
            raise ValidationError("Content key is required and cannot be blank.")
        if len(value) > 255:
            raise ValidationError("Content key must be at most 255 characters.")
        return value

    def clean_records(self):
        raw = (self.cleaned_data.get("records") or "").strip()
        if not raw:
            raise ValidationError("Records are required and cannot be blank.")
        try:
            parsed = json.loads(raw)
            if not _ensure_list_of_dicts(parsed):
                raise ValidationError("Records must be a JSON array of objects (list of dicts).")
            return raw
        except json.JSONDecodeError:
            pass
        try:
            parsed = ast.literal_eval(raw)
            if not _ensure_list_of_dicts(parsed):
                raise ValidationError("Records must be a list of dicts.")
            return raw
        except (ValueError, SyntaxError):
            pass
        return raw
