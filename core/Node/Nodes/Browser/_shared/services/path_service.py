"""
Path Service for Browser Session Directories

Single Responsibility: Construct browser session directory paths.
"""

from django.conf import settings
from pathlib import Path


class PathService:
    """Service for constructing browser session directory paths."""

    @staticmethod
    def get_browser_session_path(session_id: str) -> str:
        """
        Get absolute path for browser session directory.

        Args:
            session_id: The UUID or name of the browser session

        Returns:
            Absolute path string: {BASE_DIR}/data/Browser/{session_id}
        """
        base_dir = Path(settings.BASE_DIR)
        return str(base_dir / 'data' / 'Browser' / str(session_id))

