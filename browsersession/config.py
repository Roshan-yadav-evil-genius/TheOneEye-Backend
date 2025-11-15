"""Configuration management for video streaming."""
from typing import List


class StreamConfig:
    """Centralized configuration for video streaming."""
    
    # Testing URLs
    TESTING_URLS: List[str] = [
        "https://shawon9324.github.io/apps/keytester/",
        "https://cuberto.com/blog/cuberto-mouse-follower/",
        "https://www.w3schools.com/tags/att_a_target.asp",
        "https://codepen.io/calebnance/full/nXPaKN",
        "https://www.checkmytimezone.com/",
        "https://iplocation.io/my-location",
        "https://www.w3schools.com/tags/tryit.asp?filename=tryhtml_input_test"
    ]
    
    # Browser configuration
    HOMEPAGE_URL: str = "https://www.google.com/"  # Default homepage URL
    BROWSER_URL: str = "https://www.google.com/"  # Deprecated: use HOMEPAGE_URL instead
    CANVAS_WIDTH: int = 1920
    CANVAS_HEIGHT: int = 1080
    STREAMING_FPS: float = 15.0
    STREAMING_QUALITY: int = 40  # JPEG quality (1-100), lower = less bandwidth, faster streaming
    
    # Browser settings
    HEADLESS: bool = True
    TESTING: bool = False  # If True, opens all TESTING_URLS in separate tabs on launch

