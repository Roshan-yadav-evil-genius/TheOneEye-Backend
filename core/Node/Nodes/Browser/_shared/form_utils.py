"""Shared form utilities for browser-related nodes."""
import re
from django.forms import ChoiceField, ValidationError

SESSION_PREFIX = "session:"
POOL_PREFIX = "pool:"

# UUID v4 pattern (simple)
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I
)


def get_session_choices():
    """Fetch available browser session choices (legacy). Prefer get_session_and_pool_choices."""
    try:
        from apps.browsersession.models import BrowserSession
        sessions = BrowserSession.objects.all().order_by('name')
        choices = [('', '-- Select Session --')]
        choices.extend([(str(session.id), session.name) for session in sessions])
        return choices
    except Exception:
        pass
    return [('', '-- Select Session --')]


def get_session_and_pool_choices():
    """Fetch session and pool choices. Values are session:<uuid> or pool:<uuid> (no raw UUID)."""
    try:
        from apps.browsersession.models import BrowserSession, BrowserPool
        sessions = BrowserSession.objects.all().order_by('name')
        pools = BrowserPool.objects.all().order_by('name')
        choices = [('', '-- Select Session or Pool --')]
        choices.extend([(f"{SESSION_PREFIX}{s.id}", f"Session: {s.name}") for s in sessions])
        choices.extend([(f"{POOL_PREFIX}{p.id}", f"Pool: {p.name}") for p in pools])
        return choices
    except Exception:
        pass
    return [('', '-- Select Session or Pool --')]


class BrowserSessionField(ChoiceField):
    """
    ChoiceField for browser session or pool. Values are session:<uuid> or pool:<uuid> only.
    No backward compatibility for raw UUID.
    """
    # Skip full clean() in async context (BaseNode._validate_template_fields); clean() uses sync ORM.
    _skip_clean_in_async = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', True)
        kwargs.setdefault('help_text', "Select a browser session or a pool (pool picks one session per run).")
        kwargs.setdefault('choices', [])
        super().__init__(*args, **kwargs)
        self.choices = get_session_and_pool_choices()

    def clean(self, value):
        if value in (None, ""):
            return super().clean(value)
        value = str(value).strip()
        if not value:
            return super().clean(value)

        if value.startswith(POOL_PREFIX):
            pool_id = value[len(POOL_PREFIX):].strip()
            if not _UUID_PATTERN.match(pool_id):
                raise ValidationError("Invalid pool id.")
            from apps.browsersession.models import BrowserPool
            if not BrowserPool.objects.filter(id=pool_id).exists():
                raise ValidationError("Selected pool does not exist.")
            return value

        if value.startswith(SESSION_PREFIX):
            session_id = value[len(SESSION_PREFIX):].strip()
            if not _UUID_PATTERN.match(session_id):
                raise ValidationError("Invalid session id.")
            from apps.browsersession.models import BrowserSession
            if not BrowserSession.objects.filter(id=session_id).exists():
                raise ValidationError("Selected session does not exist.")
            return value

        raise ValidationError(
            "Value must be session:<uuid> or pool:<uuid>. Raw UUID is not supported."
        )

