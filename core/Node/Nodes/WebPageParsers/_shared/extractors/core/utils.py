import re


def clean_text(text: str) -> str:
    """Removes extra whitespace and newlines from text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_int(text: str) -> int:
    """Extracts the first integer found in a string, handling commas and + suffix."""
    if not text:
        return 0
    # First, try to match a number with optional commas and + suffix (e.g., "3,210" or "500+")
    match = re.search(r'(\d{1,3}(?:,\d{3})*)\+?', text)
    if match:
        # Remove commas and convert to int
        cleaned = match.group(1).replace(',', '')
        return int(cleaned) if cleaned else 0
    # Fallback: extract all digits (but this shouldn't happen with proper XPaths)
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else 0

