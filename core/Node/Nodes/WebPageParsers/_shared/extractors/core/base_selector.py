import logging
from scrapy import Selector
from typing import Optional, List, Union
from enum import Enum

logger = logging.getLogger(__name__)


class BaseSelector:
    """
    Base class for selector resolution with parent hierarchy.
    Same pattern as automation's BasePage.
    """

    def __init__(self, selector: Selector, registry: dict):
        self.selector = selector
        self.registry = registry
        self._cache: dict = {}
        logger.debug("BaseSelector initialized with %d registry entries", len(registry))

    def get(self, key: Enum) -> List[str]:
        """
        Get XPath list for a key.

        Args:
            key: Enum key from registry

        Returns:
            List of XPath strings
        """
        logger.debug("Getting XPath list for key: %s", key)
        entry = self.registry.get(key)
        if not entry:
            logger.error("No selector found for key: %s", key)
            raise ValueError(f"No selector found for key: {key}")

        selectors = entry.get("selectors", [])
        # Handle case where selectors is a single string (for simple xpaths like section root)
        if isinstance(selectors, str):
            return [selectors]
        return selectors

    def resolve(self, key: Enum) -> Optional[Selector]:
        """
        Resolve a key to a Selector, following parent hierarchy.
        Same pattern as automation's BasePage.get()

        Returns the first matching Selector, or None.
        """
        logger.debug("Resolving selector for key: %s", key)

        # Check cache
        if key in self._cache:
            logger.debug("Cache hit for key: %s", key)
            return self._cache[key]

        entry = self.registry.get(key)
        if not entry:
            logger.error("No selector found for key: %s", key)
            raise ValueError(f"No selector found for key: {key}")

        selectors = entry.get("selectors", [])
        parent_key = entry.get("parent")

        # Handle single string selector
        if isinstance(selectors, str):
            selectors = [selectors]

        # Determine base: parent selector or document root
        if parent_key is not None:
            logger.debug("Resolving parent: %s", parent_key)
            base = self.resolve(parent_key)  # Recursive resolution
            if base is None:
                logger.debug("Parent resolution failed for key: %s", key)
                return None
        else:
            base = self.selector

        # Try each XPath until one works
        for xpath in selectors:
            result = base.xpath(xpath)
            if result:
                # Cache and return first match
                resolved = result[0] if len(result) == 1 else result[0]
                self._cache[key] = resolved
                logger.debug("Selector resolved successfully for: %s", key)
                return resolved

        logger.debug("No match found for key: %s", key)
        return None

    def resolve_all(self, key: Enum) -> List[Selector]:
        """
        Resolve a key to all matching Selectors.
        """
        logger.debug("Resolving all selectors for key: %s", key)

        entry = self.registry.get(key)
        if not entry:
            logger.error("No selector found for key: %s", key)
            raise ValueError(f"No selector found for key: {key}")

        selectors = entry.get("selectors", [])
        parent_key = entry.get("parent")

        # Handle single string selector
        if isinstance(selectors, str):
            selectors = [selectors]

        # Determine base
        if parent_key is not None:
            logger.debug("Resolving parent for resolve_all: %s", parent_key)
            base = self.resolve(parent_key)
            if base is None:
                logger.debug("Parent resolution failed, returning empty list")
                return []
        else:
            base = self.selector

        # Try each XPath until one works
        for xpath in selectors:
            result = base.xpath(xpath)
            if result:
                logger.debug("Found %d matches for key: %s", len(result), key)
                return list(result)

        logger.debug("No matches found for key: %s", key)
        return []

    def clear_cache(self):
        """Clear the selector cache."""
        logger.debug("Selector cache cleared (%d entries)", len(self._cache))
        self._cache.clear()
