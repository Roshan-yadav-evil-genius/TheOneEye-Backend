from .BaseAction import BaseAction
from linkedin.selectors.profile_page import LinkedInProfilePageSelectors
from playwright.async_api import Locator, Page
from linkedin.enums.Status import ConnectionStatus, FollowingStatus
import logging

logger = logging.getLogger(__name__)

class BaseProfilePageAction(BaseAction):
    def __init__(self, page: Page):
        super().__init__(page)
        self.profile = LinkedInProfilePageSelectors(self.page)
    
    async def _get_connection_status(self) -> ConnectionStatus:
        print("Getting connection status")
        print(await self.profile.connect_button().count())
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
        """
        Wait for dialog to appear.

        Args:
            context: Description of what triggered the dialog (for error message)

        Returns:
            Dialog locator if found, None otherwise.
        """
        logger.debug("Waiting for dialog after %s", context)
        dialog = self.profile.dialog()
        try:
            await dialog.wait_for(state="visible", timeout=5000)
            logger.debug("Dialog appeared successfully")
            return dialog
        except Exception:
            logger.warning("Dialog did not appear after %s", context)
            return None