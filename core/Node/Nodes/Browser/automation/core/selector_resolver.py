import logging
from enum import Enum
from typing import TypeVar

from playwright.async_api import Page, Locator

from .models import SelectorEntry, SelectorRegistry

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Enum)


class SelectorResolver:
    """Resolves selector keys to Playwright locators using a registry. Reusable by any site (LinkedIn, etc.)."""

    def __init__(self, page: Page, registry: SelectorRegistry[E]) -> None:
        self.page = page
        self.registry = registry
        self._locator_cache: dict = {}
        logger.debug("SelectorResolver initialized with %d registry entries", len(registry))

    def get(self, key: E) -> Locator:
        """
        Resolve a key to a locator.
        Automatically resolves parent hierarchy from the registry.

        Args:
            key: Enum key from the registry (e.g., ProfilePageKey.CONNECT_BUTTON)

        Returns:
            Locator with all fallback selectors chained via .or_()
        """
        logger.debug("Getting locator for key: %s", key)

        if key in self._locator_cache:
            logger.debug("Cache hit for key: %s", key)
            return self._locator_cache[key]

        entry = self.registry.get(key)
        if not entry:
            logger.error("No selector found in registry for key: %s", key)
            raise ValueError(f"No selector found in registry for key: {key}")

        selectors = entry.selectors
        parent_key = entry.parent

        if not selectors:
            logger.error("No selectors defined for key: %s", key)
            raise ValueError(f"No selectors defined for key: {key}")

        if parent_key is not None:
            logger.debug("Resolving parent key: %s", parent_key)
            base = self.get(parent_key)
        else:
            base = self.page

        locator = base.locator(selectors[0])
        for selector in selectors[1:]:
            locator = locator.or_(base.locator(selector))

        logger.debug("Built locator with %d fallback selectors for key: %s", len(selectors), key)
        self._locator_cache[key] = locator
        return locator

    def clear_cache(self) -> None:
        """Clear the locator cache. Call after navigation if needed."""
        logger.debug("Locator cache cleared (%d entries)", len(self._locator_cache))
        self._locator_cache.clear()
