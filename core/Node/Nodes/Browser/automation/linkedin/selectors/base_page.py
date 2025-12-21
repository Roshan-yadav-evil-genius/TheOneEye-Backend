import logging
from playwright.async_api import Page, Locator
from typing import Union
from enum import Enum

logger = logging.getLogger(__name__)


class BasePage:
    def __init__(self, page: Page, registry: dict):
        self.page = page
        self.registry = registry
        self._locator_cache: dict = {}
        logger.debug("BasePage initialized with %d registry entries", len(registry))

    def get(self, key: Enum) -> Locator:
        """
        Unified method to get a locator by key.
        Automatically resolves parent hierarchy from the registry.

        Args:
            key: Enum key from the registry (e.g., ProfilePageKey.CONNECT_BUTTON)

        Returns:
            Locator with all fallback selectors chained via .or_()
        """
        logger.debug("Getting locator for key: %s", key)

        # Check cache first
        if key in self._locator_cache:
            logger.debug("Cache hit for key: %s", key)
            return self._locator_cache[key]

        entry = self.registry.get(key)
        if not entry:
            logger.error("No selector found in registry for key: %s", key)
            raise ValueError(f"No selector found in registry for key: {key}")

        selectors = entry.get("selectors", [])
        parent_key = entry.get("parent")

        if not selectors:
            logger.error("No selectors defined for key: %s", key)
            raise ValueError(f"No selectors defined for key: {key}")

        # Determine base: parent locator or page
        if parent_key is not None:
            logger.debug("Resolving parent key: %s", parent_key)
            base = self.get(parent_key)  # Recursive resolution
        else:
            base = self.page

        # Build locator with .or_() chaining
        locator = base.locator(selectors[0])
        for selector in selectors[1:]:
            locator = locator.or_(base.locator(selector))

        logger.debug("Built locator with %d fallback selectors for key: %s", len(selectors), key)

        # Cache and return
        self._locator_cache[key] = locator
        return locator

    def clear_cache(self):
        """Clear the locator cache. Call after navigation if needed."""
        logger.debug("Locator cache cleared (%d entries)", len(self._locator_cache))
        self._locator_cache.clear()
