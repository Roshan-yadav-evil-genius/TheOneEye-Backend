"""Shared form utilities for browser-related nodes."""
from django.forms import ChoiceField


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


class BrowserSessionField(ChoiceField):
    """
    A ChoiceField that automatically populates with available browser sessions.
    Use this in any browser-related form that needs a session dropdown.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', True)
        kwargs.setdefault('help_text', "Select a persistent browser session.")
        kwargs.setdefault('choices', [])
        super().__init__(*args, **kwargs)
        # Populate choices dynamically
        self.choices = get_session_choices()

