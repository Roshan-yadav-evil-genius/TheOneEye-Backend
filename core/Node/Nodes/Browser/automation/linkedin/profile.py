"""
LinkedIn profile URL validation and user ID extraction.
Single responsibility: determine if a URL is a valid LinkedIn profile and extract the profile user id.
"""
from urllib.parse import urlparse


def is_valid_linkedin_profile_url(url: str) -> bool:
    """Return True if url is a valid LinkedIn profile URL (e.g. https://www.linkedin.com/in/username)."""
    return extract_profile_user_id(url) is not None


def extract_profile_user_id(url: str) -> str | None:
    """
    Extract the profile user id from a LinkedIn profile URL.

    Expects path of the form /in/<user_id>. Returns None if netloc is not www.linkedin.com
    or path does not match.
    """
    parsed = urlparse(url)
    if parsed.netloc != "www.linkedin.com":
        return None
    parts = parsed.path.strip("/").split("/")
    if len(parts) == 2 and parts[0] == "in":
        return parts[1]
    return None
