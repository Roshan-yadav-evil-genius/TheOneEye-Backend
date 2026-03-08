"""Profile-page base actions: mixin and base classes for atomic/molecular actions."""
import logging

from core.actions import AtomicAction, MoleculerAction
from linkedin.page.profile_page.selectors.selector_resolver import LinkedInProfilePageSelectors
from playwright.async_api import Locator, Page

from .profile_state import ConnectionStatus, FollowingStatus

logger = logging.getLogger(__name__)


class LinkedInProfilePageMixin:
    def __init__(self, page: Page, **kwargs):
        super().__init__(page, **kwargs)
        self.profile = LinkedInProfilePageSelectors(self.page)

    async def _get_connection_status(self) -> ConnectionStatus:
        if await self.profile.connect_button().count():
            return ConnectionStatus.NOT_CONNECTED
        if await self.profile.pending_button().count():
            return ConnectionStatus.PENDING
        return ConnectionStatus.CONNECTED

    async def _get_following_status(self) -> FollowingStatus:
        if await self.profile.follow_button().count():
            return FollowingStatus.NOT_FOLLOWING
        return FollowingStatus.FOLLOWING

    async def _wait_for_dialog(self, context: str = "action") -> Locator | None:
        logger.debug("Waiting for dialog after %s", context)
        dialog = self.profile.dialog()
        try:
            await dialog.wait_for(state="visible", timeout=5000)
            logger.debug("Dialog appeared successfully")
            return dialog
        except Exception as e:
            logger.warning("Dialog did not appear after %s: %s", context, e)
            return None


class LinkedInBaseAtomicAction(LinkedInProfilePageMixin, AtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)


class LinkedInBaseMolecularAction(LinkedInProfilePageMixin, MoleculerAction):
    def __init__(self, page: Page):
        super().__init__(page)
