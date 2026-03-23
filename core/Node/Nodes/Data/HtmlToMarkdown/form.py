"""
HtmlToMarkdown Form

Single Responsibility: Form field definitions for the HtmlToMarkdown node.
"""

from django.forms import BooleanField, CharField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm


class HtmlToMarkdownForm(BaseForm):
    overwrite = BooleanField(
        required=False,
        initial=True,
        label="Overwrite",
        help_text=(
            "When on, output data is only the markdown result. When off, prior data is kept "
            "and the result is added under a unique key so multiple converters do not overwrite each other."
        ),
    )

    html_content = CharField(
        widget=Textarea(attrs={"rows": 18, "placeholder": "<p>{{ data.someField }}</p>"}),
        required=True,
        help_text=(
            "HTML to convert to markdown. Use Jinja (e.g. {{ data.previous.html }}) to pull HTML from upstream nodes."
        ),
    )
