"""
SendConnectionRequest Form

Single Responsibility: Form field definitions for the SendConnectionRequest node.
"""

from django.forms import CharField, BooleanField

from ....Core.Form import BaseForm
from .._shared.form_utils import BrowserSessionField


class SendConnectionRequestForm(BaseForm):
    profile_url = CharField(
        required=True,
        help_text="LinkedIn profile URL."
    )
    session_name = BrowserSessionField()
    send_connection_request = BooleanField(
        required=False,
        initial=True,
        help_text="Send a connection request to the profile."
    )
    follow = BooleanField(
        required=False,
        initial=True,
        help_text="Follow the profile."
    )

