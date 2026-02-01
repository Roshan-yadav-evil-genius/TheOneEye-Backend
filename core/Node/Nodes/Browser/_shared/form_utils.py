"""Shared form utilities for browser-related nodes."""
import re
from django.forms import ChoiceField, ValidationError


def get_session_choices():
    """Fetch available browser session choices from Django model."""
    try:
        from apps.browsersession.models import BrowserSession
        
        sessions = BrowserSession.objects.all().order_by('name')
        # Return choices as (id, name) tuples with a placeholder
        choices = [('', '-- Select Session --')]
        choices.extend([(str(session.id), session.name) for session in sessions])
        return choices
    except Exception:
        pass
    # Fallback to placeholder only if model is unavailable
    return [('', '-- Select Session --')]


# UUID v4 pattern (simple)
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I
)


class BrowserSessionField(ChoiceField):
    """
    A ChoiceField that automatically populates with available browser sessions.
    Use this in any browser-related form that needs a session dropdown.
    Accepts a saved session UUID even if that session is no longer in the DB,
    so workflow validation does not fail when a session was deleted.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', True)
        kwargs.setdefault('help_text', "Select a persistent browser session.")
        kwargs.setdefault('choices', [])
        super().__init__(*args, **kwargs)
        # Populate choices dynamically
        self.choices = get_session_choices()

    def clean(self, value):
        if value in (None, ""):
            return super().clean(value)
        # Allow a saved UUID even if it's not in current choices (e.g. session was deleted)
        if _UUID_PATTERN.match(str(value).strip()):
            valid_choices = {str(c[0]) for c in self.choices if c[0]}
            if value not in valid_choices:
                return str(value).strip()
        return super().clean(value)

