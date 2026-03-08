"""
Human-like wait and typing for browser automation.
Uses delay config and jitter from core.delays. Reusable across any site.
"""
from playwright.async_api import Locator, Page

from .delays import DelayConfig, jitter_ms


async def human_wait(page: Page, config: DelayConfig) -> None:
    """Wait a random delay (jitter) to mimic human behavior."""
    await page.wait_for_timeout(jitter_ms(config))


async def human_typing(locator: Locator, text: str, config: DelayConfig) -> None:
    """Type text character-by-character with random delay (jitter)."""
    for ch in text:
        await locator.type(ch, delay=jitter_ms(config))
