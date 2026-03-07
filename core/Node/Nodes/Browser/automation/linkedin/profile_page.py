import logging
from playwright.async_api import Page, Locator

from linkedin.actions.ConnectionRequest import SendConnectionRequest, WithdrawConnectionRequest
from linkedin.actions.FollowUnFollow import FollowProfile, UnfollowProfile
from linkedin.enums.Status import ConnectionStatus, FollowingStatus
from .selectors.profile_page import LinkedInProfilePageSelectors
from urllib.parse import urlparse
from abc import ABC, abstractmethod
from linkedin.actions.BaseAction import PageAction
logger = logging.getLogger(__name__)





class ProfilePageAction(PageAction):
    def __init__(self, page: Page):
        super().__init__(page)

        self.profile_url = self.page.url

        if not self.is_valid_page():
            logger.error("Invalid LinkedIn profile URL: %s", self.profile_url)
            raise ValueError("Invalid LinkedIn profile URL.")

        self.user_id = self.extract_user_id(self.profile_url)
    # ─────────────────────────────────────────────────────────────
    # Public Methods
    # ─────────────────────────────────────────────────────────────

    def is_valid_page(self)->bool:
        return self.extract_user_id(self.profile_url) is not None


    def extract_user_id(self, url: str):
        parsed = urlparse(url)

        if parsed.netloc != "www.linkedin.com":
            return None

        parts = parsed.path.strip("/").split("/")

        if len(parts) == 2 and parts[0] == "in":
            return parts[1]

        return None


    async def follow_profile(self):
        action = await FollowProfile(self.page).accomplish()
        if not action.accomplished:
            logger.error(f"{action.__class__.__name__} failed While Following Profile")
        else:
            logger.info("Profile followed successfully")
        return action.accomplished

    async def unfollow_profile(self):
        action = await UnfollowProfile(self.page).accomplish()
        if not action.accomplished:
            logger.error(f"{action.__class__.__name__} failed While Unfollowing Profile")
        else:
            logger.info("Profile unfollowed successfully")
        return action.accomplished

    async def send_connection_request(self, note: str = ""):
        action = await SendConnectionRequest(self.page, note).accomplish()
        if not action.accomplished:
            logger.error(f"{action.__class__.__name__} failed While Sending Connection Request")
        else:
            logger.info("Connection request sent successfully")
        return action.accomplished

    async def withdraw_connection_request(self):
        action = await WithdrawConnectionRequest(self.page).accomplish()
        if not action.accomplished:
            logger.error(f"{action.__class__.__name__} failed While Withdrawing Connection Request")
        else:
            logger.info("Connection request withdrawn successfully")
        return action.accomplished