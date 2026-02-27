"""Shared form utilities for browser-related nodes."""
import re
from django.forms import ChoiceField, ValidationError

POOL_PREFIX = "pool:"

# UUID v4 pattern (simple)
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I
)


def get_session_choices():
    """Fetch available browser session choices (legacy). Used for pool-assignment UIs that list sessions."""
    try:
        from apps.browsersession.models import BrowserSession
        sessions = BrowserSession.objects.all().order_by('name')
        choices = [('', '-- Select Session --')]
        choices.extend([(str(session.id), session.name) for session in sessions])
        return choices
    except Exception:
        pass
    return [('', '-- Select Session --')]


def get_pool_choices():
    """Fetch browser pool choices only. Values are pool:<uuid>. Sessions are only used through pools."""
    try:
        from apps.browsersession.models import BrowserPool
        pools = BrowserPool.objects.all().order_by('name')
        choices = [('', '-- Select Pool --')]
        choices.extend([(f"{POOL_PREFIX}{p.id}", f"Pool: {p.name}") for p in pools])
        return choices
    except Exception:
        pass
    return [('', '-- Select Pool --')]


class BrowserSessionField(ChoiceField):
    """
    ChoiceField for browser pool only. Value is pool:<uuid>. One session is picked from the pool per run.
    Direct session selection is not allowed; sessions are only used through pools.
    """
    # Skip full clean() in async context (BaseNode._validate_template_fields); clean() uses sync ORM.
    _skip_clean_in_async = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', True)
        kwargs.setdefault('help_text', "Select a browser pool; one session is picked from the pool per run.")
        kwargs.setdefault('choices', [])
        super().__init__(*args, **kwargs)
        self.choices = get_pool_choices()

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

        raise ValidationError(
            "Value must be pool:<uuid>. Direct session selection is not supported."
        )

