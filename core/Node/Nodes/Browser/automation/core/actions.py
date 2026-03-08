"""
Generic action base classes for browser automation.
Reusable by any site: implement AtomicAction (single step), MoleculerAction (chain), PageAction (page-level).
"""
import logging
from abc import ABC, abstractmethod

from playwright.async_api import Page

from .delays import DelayConfig
from .human_behavior import human_wait

logger = logging.getLogger(__name__)


class AtomicAction:
    """Single browser step. Subclass and implement perform_action() and verify_action()."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self._accomplished = False

    @property
    def accomplished(self) -> bool:
        return self._accomplished

    @abstractmethod
    async def perform_action(self) -> None:
        pass

    @abstractmethod
    async def verify_action(self) -> bool:
        pass

    async def accomplish(self) -> "AtomicAction":
        """Run perform_action then verify_action; set _accomplished. Logs and sets False on failure."""
        try:
            await self.perform_action()
            self._accomplished = await self.verify_action()
        except Exception as e:
            logger.exception("%s Failed: %s", self.__class__.__name__, e)
            self._accomplished = False
        return self


class MoleculerAction(AtomicAction):
    """Action that runs a chain of actions with delay between them. Set chain_of_actions in subclass."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.chain_of_actions: list[AtomicAction] = []

    async def execute_chain_of_actions(
        self,
        delay_between: DelayConfig = DelayConfig(min_ms=500, max_ms=1000),
    ) -> bool:
        """Run each action's accomplish(), then human_wait between. Returns False on first failure."""
        for action in self.chain_of_actions:
            logger.debug("Executing action: %s", action.__class__.__name__)
            action = await action.accomplish()
            if not action.accomplished:
                logger.error("Action %s failed", action.__class__.__name__)
                return False
            await human_wait(self.page, config=delay_between)
        return True

    async def perform_action(self) -> None:
        self._accomplished = await self.execute_chain_of_actions()

    async def verify_action(self) -> bool:
        return self._accomplished


class PageAction(ABC):
    """Abstract page-level orchestrator. Subclass and implement is_valid_page()."""

    def __init__(self, page: Page) -> None:
        self.page = page

    @abstractmethod
    def is_valid_page(self) -> bool:
        pass
