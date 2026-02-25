"""
Log-safe truncation for large payloads (e.g. node output, form values).
Converts to string, trims if too long; on failure returns a placeholder.
No dependency on Node or Workflow to avoid circular imports.
"""

import json
from typing import Any

PLACEHOLDER = "📦📦😐📦📦"


def _trim(s: str, max_string_len: int, words_around: int) -> str:
    if len(s) <= max_string_len:
        return s
    words = s.split()
    first = " ".join(words[:words_around]) if words else ""
    last = " ".join(words[-words_around:]) if words else ""
    result = f"{first}...<📦📦len={len(s)}📦📦>...{last}"
    # Minified JSON/HTML has no spaces → word trim returns full string; fall back to char trim
    if len(result) > max_string_len:
        suffix = f"...<📦📦len={len(s)}📦📦>..."
        half = max(0, (max_string_len - len(suffix)) // 2)
        result = f"{s[:half]}{suffix}{s[-half:]}"
    return result


def log_safe_output(
    data: Any,
    max_string_len: int = 500,
    words_around: int = 20,
) -> str:
    """
    Produce a log-safe string: trim long strings, or try to stringify then trim.
    On conversion failure returns a fixed placeholder. Does not mutate the original.
    """
    if isinstance(data, str):
        return _trim(data, max_string_len, words_around)

    try:
        if isinstance(data, (dict, list)):
            s = json.dumps(data)
        else:
            s = str(data)
        return _trim(s, max_string_len, words_around)
    except Exception:
        return PLACEHOLDER
