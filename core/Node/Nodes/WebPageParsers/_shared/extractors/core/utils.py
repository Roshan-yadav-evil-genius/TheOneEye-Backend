import re


def clean_text(text: str) -> str:
    """Removes extra whitespace and newlines from text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_int(text: str) -> int:
    """Extracts the first integer found in a string."""
    if not text:
        return 0
    # Remove commas and extract digits
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else 0

