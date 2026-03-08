from enum import Enum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

E = TypeVar("E", bound=Enum)


class SelectorEntry(BaseModel, Generic[E]):
    """One locator definition: key, list of fallback selectors, and optional parent key for scoping."""

    key: E = Field(..., description="Registry key for this entry (e.g. ProfilePageKey.CONNECT_BUTTON)")
    selectors: list[str] = Field(
        ...,
        min_length=1,
        description="XPath/CSS strings for Playwright locator (first wins; rest as .or_() fallbacks)",
    )
    parent: Optional[E] = Field(
        default=None,
        description="Parent key for scoping; None means page root",
    )

    model_config = {"frozen": True}


class SelectorRegistry(Generic[E]):
    """Registry of selector entries. Add entries via register(entry); duplicate key raises."""

    def __init__(self) -> None:
        self._entries: dict[E, SelectorEntry[E]] = {}

    def register(self, entry: SelectorEntry[E]) -> "SelectorRegistry[E]":
        """Add an entry. Key is taken from entry.key. Raises if key already registered."""
        if entry.key in self._entries:
            raise ValueError(f"Duplicate selector key: {entry.key}")
        if entry.parent is not None and entry.parent not in self._entries:
            raise ValueError(f"Parent key {entry.parent} must be registered before {entry.key}")
        self._entries[entry.key] = entry
        return self

    def get(self, key: E) -> Optional[SelectorEntry[E]]:
        """Return the entry for key, or None if not registered."""
        return self._entries.get(key)

    def __len__(self) -> int:
        return len(self._entries)
