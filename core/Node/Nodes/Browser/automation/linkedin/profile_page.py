import logging
from playwright.async_api import Page, Locator

from linkedin.actions import SendConnectionRequest
from linkedin.enums.Status import ConnectionStatus, FollowingStatus
from .selectors.profile_page import LinkedInProfilePageSelectors
from urllib.parse import urlparse

logger = logging.getLogger(__name__)




class ProfilePage:
    def __init__(self, page: Page, profile_url: str):
        self.page = page

        if not self._is_valid_linkedin_profile_url(profile_url):
            logger.error("Invalid LinkedIn profile URL: %s", profile_url)
            raise ValueError("Invalid LinkedIn profile URL.")

        # Normalize URL to use https and www prefix
        self.profile_url = self._normalize_linkedin_url(profile_url)
        self.profile = LinkedInProfilePageSelectors(self.page)
        logger.debug("Initialized ProfilePage for: %s", self.profile_url)

    # ─────────────────────────────────────────────────────────────
    # Public Methods
    # ─────────────────────────────────────────────────────────────

    async def load(self):
        logger.debug("Loading profile page: %s", self.profile_url)
        await self.page.goto(self.profile_url, wait_until="load")
        logger.info("Profile page loaded: %s", self.profile_url)

    async def follow_profile(self):
        following_status = await self._get_following_status()
        logger.debug("Current following status: %s", following_status)

        if following_status == FollowingStatus.NOT_FOLLOWING:
            logger.info("Following profile")
            follow_btn = self.profile.follow_button()
            await self._click_or_expand_more_menu(follow_btn, "Follow")
        else:
            logger.info("Already following this profile")

    async def unfollow_profile(self):
        following_status = await self._get_following_status()
        logger.debug("Current following status: %s", following_status)

        if following_status == FollowingStatus.FOLLOWING:
            logger.info("Unfollowing profile")
            unfollow_btn = self.profile.unfollow_button()
            await self._click_or_expand_more_menu(unfollow_btn, "Unfollow")

            dialog = await self._wait_for_dialog("clicking Unfollow")
            if not dialog:
                return
            confirm_unfollow_btn = self.profile.dialog_unfollow_button()
            if await confirm_unfollow_btn.is_visible():
                await confirm_unfollow_btn.click()
                logger.info("Profile unfollowed successfully")
        else:
            logger.info("Already not following this profile")

    async def send_connection_request(self, note: str = ""):
        action = SendConnectionRequest(self.page, note).accomplish()
        if not action.accomplished:
            logger.error(f"{action.__class__.__name__} failed While Sending Connection Request")
        else:
            logger.info("Connection request sent successfully")

    async def withdraw_connection_request(self):
        connection_status = await self._get_connection_status()
        logger.debug("Current connection status: %s", connection_status)

        if connection_status != ConnectionStatus.PENDING:
            logger.warning("Cannot withdraw - not in Pending state (current: %s)", connection_status)
            return

        logger.info("Withdrawing connection request")
        pending_btn = self.profile.pending_button()

        if not await self._click_or_expand_more_menu(pending_btn, "Pending"):
            return

        dialog = await self._wait_for_dialog("clicking Pending")
        if not dialog:
            return

        withdraw_btn = self.profile.withdraw_button()
        if await withdraw_btn.is_visible():
            await withdraw_btn.click()
            logger.info("Connection request withdrawn successfully")
        else:
            logger.error("Could not find 'Withdraw' button")

    # ─────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _is_valid_linkedin_profile_url(profile_url: str) -> bool:
        # EX: https://www.linkedin.com/in/zackspear/
        # Also accepts http:// URLs (will be normalized to https in __init__)

        parsed = urlparse(profile_url)

        # Accept both http and https
        if parsed.scheme not in ("http", "https"):
            return False

        # Accept with or without www prefix
        netloc = parsed.netloc.lower()
        if netloc not in ("www.linkedin.com", "linkedin.com"):
            return False

        paths = [p for p in parsed.path.strip("/").split("/") if p]

        return len(paths) == 2 and paths[0] == "in"
    
    @staticmethod
    def _normalize_linkedin_url(profile_url: str) -> str:
        """Normalize LinkedIn URL to use https and www prefix."""
        parsed = urlparse(profile_url)
        netloc = parsed.netloc.lower()
        
        # Ensure www prefix
        if netloc == "linkedin.com":
            netloc = "www.linkedin.com"
        
        # Rebuild with https
        return f"https://{netloc}{parsed.path}"
