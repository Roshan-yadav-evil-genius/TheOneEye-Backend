"""Page-level orchestrator for LinkedIn profile page."""
import logging

from playwright.async_api import Page

from core.actions import PageAction
from linkedin.utils import extract_profile_user_id, is_valid_linkedin_profile_url

from .base_action import LinkedInProfilePageMixin
from .molecular_action import (
    FollowProfile,
    SendConnectionRequest,
    UnfollowProfile,
    WithdrawConnectionRequest,
)

logger = logging.getLogger(__name__)


class ProfilePageAction(LinkedInProfilePageMixin, PageAction):
    """Orchestrates profile flows; delegates to molecular actions (SendConnectionRequest, WithdrawConnectionRequest, FollowProfile, UnfollowProfile)."""

    def __init__(self, page: Page):
        super().__init__(page)
        self.profile_url = self.page.url
        if not is_valid_linkedin_profile_url(self.profile_url):
            logger.error("Invalid LinkedIn profile URL: %s", self.profile_url)
            raise ValueError("Invalid LinkedIn profile URL.")
        self.user_id = extract_profile_user_id(self.profile_url)

    def is_valid_page(self) -> bool:
        return is_valid_linkedin_profile_url(self.profile_url)
    
    async def wait_for_page_to_load(self):
        await self._wait_for_page_to_load()


    async def follow_profile(self):
        logger.info("Following profile...")
        action = await FollowProfile(self.page).accomplish()
        if not action.accomplished:
            logger.error("%s failed While Following Profile", action.__class__.__name__)
        else:
            logger.info("Profile followed successfully")
        return action.accomplished

    async def unfollow_profile(self):
        action = await UnfollowProfile(self.page).accomplish()
        if not action.accomplished:
            logger.error("%s failed While Unfollowing Profile", action.__class__.__name__)
        else:
            logger.info("Profile unfollowed successfully")
        return action.accomplished

    async def send_connection_request(self, note: str = ""):
        logger.info("Sending connection request...")
        action = await SendConnectionRequest(self.page, note).accomplish()
        if not action.accomplished:
            logger.error("%s failed While Sending Connection Request", action.__class__.__name__)
        else:
            logger.info("Connection request sent successfully")
        return action.accomplished

    async def withdraw_connection_request(self):
        logger.info("Withdrawing connection request...")
        action = await WithdrawConnectionRequest(self.page).accomplish()
        if not action.accomplished:
            logger.error("%s failed While Withdrawing Connection Request", action.__class__.__name__)
        else:
            logger.info("Connection request withdrawn successfully")
        return action.accomplished
